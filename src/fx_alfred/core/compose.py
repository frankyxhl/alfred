"""Auto-composition helpers for `af plan --task`.

Pure stdlib. No filesystem access. Operates on already-parsed
Document objects and workflow metadata to resolve SOP ordering
via tag matching and topological sort.

FXA-2205 PR4.
"""

from __future__ import annotations

import string
from collections import deque
from dataclasses import dataclass

import click

from fx_alfred.core.document import Document
from fx_alfred.core.parser import parse_metadata
from fx_alfred.core.workflow import parse_workflow_signature

# Verbatim from FXA-2205 §C1
STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "to",
        "for",
        "of",
        "in",
        "on",
        "at",
        "by",
        "with",
        "from",
        "and",
        "or",
        "but",
        "if",
        "then",
        "else",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "do",
        "does",
        "did",
        "please",
        "need",
        "needs",
        "needed",
    }
)


def tokenize(task: str) -> frozenset[str]:
    """Tokenize a task description for tag matching.

    Algorithm:
    1. Lowercase the input.
    2. Split on whitespace.
    3. Strip string.punctuation from each token.
    4. Drop tokens in STOPWORDS.
    5. Drop empty tokens.
    6. Return deduplicated frozenset.

    Determinism guarantee: same input → same output.
    """
    lowered = task.lower()
    raw_tokens = lowered.split()

    tokens: set[str] = set()
    for raw in raw_tokens:
        # Strip punctuation (but keep hyphens, underscores, etc. inside tokens)
        stripped = raw.strip(string.punctuation)
        # Drop stopwords
        if stripped in STOPWORDS:
            continue
        # Drop empty
        if not stripped:
            continue
        tokens.add(stripped)

    return frozenset(tokens)


def tokenize_ordered(task: str) -> list[str]:
    """Tokenize a task description preserving original order.

    Same algorithm as tokenize() but returns a list with original order
    preserved (minus deduplication - keeps first occurrence).
    Used for bigram generation.
    """
    lowered = task.lower()
    raw_tokens = lowered.split()

    tokens: list[str] = []
    seen: set[str] = set()
    for raw in raw_tokens:
        stripped = raw.strip(string.punctuation)
        if stripped in STOPWORDS:
            continue
        if not stripped:
            continue
        if stripped not in seen:
            tokens.append(stripped)
            seen.add(stripped)

    return tokens


def bigrams(tokens_list: list[str]) -> frozenset[str]:
    """Build hyphen-joined bigrams from adjacent token pairs.

    Input is a LIST (preserves order) of tokens.
    Output is a frozenset of "{a}-{b}" strings for adjacent pairs.
    """
    if len(tokens_list) < 2:
        return frozenset()

    pairs: set[str] = set()
    for i in range(len(tokens_list) - 1):
        pair = f"{tokens_list[i]}-{tokens_list[i + 1]}"
        pairs.add(pair)

    return frozenset(pairs)


# Layer priority for tiebreak: PKG (highest) → USR → PRJ (lowest)
_LAYER_PRIORITY = {"pkg": 0, "usr": 1, "prj": 2}


@dataclass(frozen=True)
class _DocNode:
    """Internal node for topological sort."""

    doc: Document
    doc_id: str  # "PREFIX-ACID"

    def __lt__(self, other: "_DocNode") -> bool:
        """Comparison for deterministic tiebreak: layer priority, then ASCII doc_id."""
        self_prio = _LAYER_PRIORITY.get(self.doc.source, 99)
        other_prio = _LAYER_PRIORITY.get(other.doc.source, 99)
        if self_prio != other_prio:
            return self_prio < other_prio
        return self.doc_id < other.doc_id


def compose_order(
    candidates: list[Document],
    workflow_edges: dict[str, tuple[str | None, str | None]] | None = None,
) -> list[Document]:
    """Order SOP candidates via Kahn's topological sort.

    Edges are derived from Workflow input/output metadata:
    - If SOP-A's output matches SOP-B's input, there's an edge A → B.
    - workflow_edges is an optional pre-computed map:
        {doc_id: (workflow_input, workflow_output)}.
      If not provided, all docs are treated as independent.

    Deterministic tiebreak: layer priority (PKG → USR → PRJ), then ASCII doc_id.

    Fail-closed on TRUE cycle (raises ClickException with cycle nodes).

    Returns ordered list of Document objects.
    """
    if len(candidates) <= 1:
        return list(candidates)

    # Build doc_id → Document map
    doc_map: dict[str, Document] = {}
    for doc in candidates:
        doc_id = f"{doc.prefix}-{doc.acid}"
        doc_map[doc_id] = doc

    doc_ids = list(doc_map.keys())

    # If no workflow edges provided, treat as independent
    if workflow_edges is None:
        # Sort by layer priority, then ASCII
        nodes = [_DocNode(doc_map[d], d) for d in doc_ids]
        nodes.sort()
        return [n.doc for n in nodes]

    # Build adjacency list: edge from A to B means A must come before B
    # A → B if A.output == B.input (typed edge)
    adjacency: dict[str, set[str]] = {d: set() for d in doc_ids}
    in_degree: dict[str, int] = {d: 0 for d in doc_ids}

    # Find edges
    for a_id, (a_in, a_out) in workflow_edges.items():
        if a_id not in doc_map:
            continue
        if not a_out:
            continue
        for b_id, (b_in, b_out) in workflow_edges.items():
            if b_id not in doc_map:
                continue
            if a_id == b_id:
                continue
            if not b_in:
                continue
            if a_out == b_in:
                # Edge: a_id → b_id
                adjacency[a_id].add(b_id)
                in_degree[b_id] += 1

    # Kahn's algorithm
    # Use sorted list for deterministic tiebreak
    available = sorted([_DocNode(doc_map[d], d) for d in doc_ids if in_degree[d] == 0])
    queue = deque(available)
    result: list[Document] = []

    while queue:
        node = queue.popleft()
        result.append(node.doc)

        # Find neighbors to update
        neighbors = sorted(
            [
                _DocNode(doc_map[n], n)
                for n in adjacency[node.doc_id]
                if in_degree[n] > 0
            ]
        )
        for neighbor in neighbors:
            in_degree[neighbor.doc_id] -= 1
            if in_degree[neighbor.doc_id] == 0:
                # Insert in sorted position (keep deterministic order)
                queue.append(neighbor)
                # Re-sort queue to maintain priority
                queue = deque(sorted(queue))

    # Check for cycle
    if len(result) != len(doc_ids):
        # Find cycle nodes
        remaining = [d for d in doc_ids if doc_map[d] not in result]
        cycle_nodes = ", ".join(sorted(remaining))
        raise click.ClickException(f"Workflow cycle detected among: {cycle_nodes}")

    return result


def resolve_sops_from_task(
    task_description: str,
    all_sops: list[tuple[Document, frozenset[str], bool]],
    positional_ids: list[str],
) -> tuple[list[str], dict[str, list[str]]]:
    """Resolve ordered SOP IDs from a task description.

    Full C1 algorithm from FXA-2205 §C1.

    Parameters
    ----------
    task_description:
        Natural language task string (e.g., "implement FXA-2117 PRP").
    all_sops:
        List of (Document, task_tags, always_included) tuples.
        - Document: the SOP document object.
        - task_tags: frozenset of lowercase tag strings (may be empty).
        - always_included: True if this SOP has Always included: true.
    positional_ids:
        List of explicit "PREFIX-ACID" strings from command line.

    Returns
    -------
    tuple of (ordered_sop_ids, provenance):
        - ordered_sop_ids: list of "PREFIX-ACID" strings in composition order.
        - provenance: dict with keys "always", "auto", "explicit", each a list
          of "PREFIX-ACID" strings in the order they were resolved.

    Raises
    ------
    click.ClickException:
        If tag matching produces nothing and no positional IDs given
        (tag_cands is empty and positional_set is empty), exit code 2.
    """
    # 1. Tokenize (as set for probing)
    tokens = tokenize(task_description)

    # 2. Build bigrams from original-ordered tokens
    tokens_list = tokenize_ordered(task_description)
    bg = bigrams(tokens_list)

    # 3. Probes = tokens ∪ bigrams
    probes = tokens | bg

    # 4. Tag candidates
    tag_cands: set[str] = set()
    for doc, task_tags, _ in all_sops:
        if task_tags and task_tags & probes:
            tag_cands.add(f"{doc.prefix}-{doc.acid}")

    # 5. Always-included
    always_set: set[str] = set()
    for doc, _, always_included in all_sops:
        if always_included:
            always_set.add(f"{doc.prefix}-{doc.acid}")

    # 6. Validate positional IDs exist, then build candidates
    doc_map_for_validation = {f"{d.prefix}-{d.acid}": d for d, _, _ in all_sops}
    for sop_id in positional_ids:
        if sop_id not in doc_map_for_validation:
            raise click.ClickException(f"SOP '{sop_id}' not found")

    positional_set = set(positional_ids)
    candidates = positional_set | tag_cands | always_set

    # 7. Empty result check
    # Only fail if NO user intent signals (tags or positional IDs).
    # Always-included SOPs alone do not count as a plan — they are a baseline,
    # not a signal. Previously this checked `candidates == always_set`, which
    # wrongly fired when an always-included SOP also had a matching Task tag
    # (because tag_cands ⊆ always_set keeps set equality True).
    if not tag_cands and not positional_set:
        exc = click.ClickException(
            f'--task "{task_description}" matched 0 tagged SOPs. '
            "No routing fallback in v1.\n"
            "Try: af plan <SOP_ID> ... explicitly, or tag a relevant SOP with `Task tags:`."
        )
        exc.exit_code = 2
        raise exc

    # 8. Order via compose_order with workflow edges
    # Build doc map for ordering
    doc_map = {f"{d.prefix}-{d.acid}": d for d, _, _ in all_sops}
    candidate_docs = [doc_map[d] for d in candidates if d in doc_map]

    # Build workflow edges map from Workflow input/output metadata
    workflow_edges: dict[str, tuple[str | None, str | None]] = {}
    for doc in candidate_docs:
        doc_id = f"{doc.prefix}-{doc.acid}"
        try:
            content_raw = doc.resolve_resource().read_text()
            parsed = parse_metadata(content_raw)
            sig = parse_workflow_signature(parsed)
            if sig is not None:
                workflow_edges[doc_id] = (sig.input or None, sig.output or None)
            else:
                workflow_edges[doc_id] = (None, None)
        except Exception:
            # If parsing fails, treat as untyped
            workflow_edges[doc_id] = (None, None)

    ordered_docs = compose_order(candidate_docs, workflow_edges)

    # 9. Build provenance
    provenance: dict[str, list[str]] = {
        "always": [],
        "auto": [],
        "explicit": [],
    }

    ordered_ids = []
    for doc in ordered_docs:
        doc_id = f"{doc.prefix}-{doc.acid}"
        ordered_ids.append(doc_id)

        if doc_id in always_set:
            provenance["always"].append(doc_id)
        elif doc_id in positional_set:
            provenance["explicit"].append(doc_id)
        elif doc_id in tag_cands:
            provenance["auto"].append(doc_id)

    return ordered_ids, provenance
