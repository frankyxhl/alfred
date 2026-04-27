"""Pure workflow composition helpers for typed SOP chains.

This module has no filesystem access. It operates on already-parsed
workflow metadata to build signatures, validate them, and check
adjacent-SOP composition in an ``af plan`` chain.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import NamedTuple

import yaml

from fx_alfred.core.parser import MalformedDocumentError, ParsedDocument
from fx_alfred.core.schema import (
    WORKFLOW_INPUT,
    WORKFLOW_OUTPUT,
    WORKFLOW_PROVIDES,
    WORKFLOW_REQUIRES,
    WORKFLOW_LOOPS,
    WORKFLOW_BRANCHES,
)

# Token format per the CHG-2204 contract.
_TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9:_/-]*$")


def _validate_token(token: str) -> str | None:
    """Return an error string if *token* is invalid, else ``None``."""
    if not token:
        return "empty token"
    if not _TOKEN_RE.match(token):
        return f"invalid token format: {token!r}"
    return None


def _parse_token_list(value: str) -> list[str]:
    """Split a comma-separated token string, strip whitespace.

    Empty tokens (e.g. from ``"a, ,b"`` or ``"a,"`` ) are preserved so
    that ``validate_workflow_signature`` can report them per CHG-2204 §4.
    """
    if not value.strip():
        return []
    return [t.strip() for t in value.split(",")]


@dataclass(frozen=True)
class WorkflowSignature:
    """Typed workflow signature extracted from SOP metadata."""

    input: str
    output: str
    requires: list[str] = field(default_factory=list)
    provides: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WorkflowEdge:
    """Composition edge between two adjacent SOPs in a plan chain."""

    from_doc: str
    to_doc: str
    typed: bool
    compatible: bool
    from_output: str
    to_input: str


def parse_workflow_signature(parsed: ParsedDocument) -> WorkflowSignature | None:
    """Extract a workflow signature from a parsed document.

    Returns ``None`` only when *none* of the four workflow metadata keys
    are present (i.e. the document is fully untyped).  If any workflow
    key exists — even just ``Workflow requires`` — a signature is returned
    so that ``validate_workflow_signature`` can lint it.
    """
    field_map = {mf.key: mf.value for mf in parsed.metadata_fields}

    input_val = field_map.get(WORKFLOW_INPUT)
    output_val = field_map.get(WORKFLOW_OUTPUT)
    requires_val = field_map.get(WORKFLOW_REQUIRES)
    provides_val = field_map.get(WORKFLOW_PROVIDES)

    # Fully untyped document — no workflow metadata at all.
    if all(v is None for v in (input_val, output_val, requires_val, provides_val)):
        return None

    return WorkflowSignature(
        input=input_val.strip() if input_val else "",
        output=output_val.strip() if output_val else "",
        requires=_parse_token_list(requires_val or ""),
        provides=_parse_token_list(provides_val or ""),
    )


def validate_workflow_signature(sig: WorkflowSignature) -> list[str]:
    """Return a list of error strings.  Empty list means valid."""
    errors: list[str] = []

    has_list_fields = bool(sig.requires or sig.provides)

    # Both input and output must be present if either exists.
    if not sig.input or not sig.output:
        if sig.input and not sig.output:
            errors.append("Workflow input is set but Workflow output is missing")
        elif sig.output and not sig.input:
            errors.append("Workflow output is set but Workflow input is missing")
        elif has_list_fields:
            errors.append(
                "Workflow requires/provides present without Workflow input/output"
            )
        else:
            errors.append("Workflow input and Workflow output are both empty")

    # Validate single tokens.
    for label, token in (
        ("Workflow input", sig.input),
        ("Workflow output", sig.output),
    ):
        if token:
            err = _validate_token(token)
            if err:
                errors.append(f"{label}: {err}")

    # Validate token lists.
    for label, tokens in (
        ("Workflow requires", sig.requires),
        ("Workflow provides", sig.provides),
    ):
        seen: set[str] = set()
        for tok in tokens:
            err = _validate_token(tok)
            if err:
                errors.append(f"{label}: {err}")
            if tok in seen:
                errors.append(f"{label}: duplicate entry {tok!r}")
            seen.add(tok)

    return errors


def check_composition(
    chain: list[tuple[str, WorkflowSignature]],
) -> list[WorkflowEdge]:
    """Check adjacent SOP pairs in *chain* for typed composition.

    *chain* is a list of ``(doc_id, WorkflowSignature)`` tuples.  Each
    adjacent pair produces a :class:`WorkflowEdge`.  An edge is typed only
    when **both** signatures have complete (non-empty) ``input`` *and*
    ``output``.
    """
    edges: list[WorkflowEdge] = []
    for i in range(len(chain) - 1):
        left_id, left_sig = chain[i]
        right_id, right_sig = chain[i + 1]

        left_complete = bool(left_sig.input and left_sig.output)
        right_complete = bool(right_sig.input and right_sig.output)
        typed = left_complete and right_complete
        compatible = left_sig.output == right_sig.input if typed else True

        edges.append(
            WorkflowEdge(
                from_doc=left_id,
                to_doc=right_id,
                typed=typed,
                compatible=compatible,
                from_output=left_sig.output,
                to_input=right_sig.input,
            )
        )
    return edges


# ---------------------------------------------------------------------------
# FXA-2205: Loop metadata parsing and validation
# ---------------------------------------------------------------------------

# Regex to match numbered steps. FXA-2226 Path B: extended to also match
# sub-step lines like ``3a.`` so ``_parse_step_indices`` injects the parent
# integer (3) from each sibling. The optional ``[a-z]?`` is OUTSIDE the
# int-capturing group, so ``int(m.group(1))`` always yields a clean int.
_STEP_INDEX_RE = re.compile(r"^(?:###\s+)?(\d+)[a-z]?\.\s+")
# Required keys in a loop declaration
_LOOP_REQUIRED_KEYS = ("id", "from", "to", "max_iterations", "condition")
# Cross-SOP loop reference — authored as "PREFIX-ACID.step" (FXA-2218 Commit 2).
CROSS_SOP_REF = re.compile(r"^(?P<prefix>[A-Z]{3})-(?P<acid>\d{4})\.(?P<step>\d+)$")


@dataclass(frozen=True)
class LoopSignature:
    """Loop declaration extracted from ``Workflow loops`` metadata.

    ``to_step`` is ``int`` for intra-SOP loops (the traditional form) and
    a ``"PREFIX-ACID.step"`` string for cross-SOP loops (FXA-2218).
    """

    id: str
    from_step: int
    to_step: int | str
    max_iterations: int
    condition: str

    def is_cross_sop(self) -> bool:
        """Return True if this loop targets a different SOP."""
        return isinstance(self.to_step, str)

    def cross_sop_target(self) -> tuple[str, str, int] | None:
        """Return ``(prefix, acid, step_idx)`` for cross-SOP refs, else ``None``.

        Parses lazily. The stored ``to_step`` string was validated during
        ``parse_workflow_loops`` so the regex must match here.
        """
        if not isinstance(self.to_step, str):
            return None
        m = CROSS_SOP_REF.match(self.to_step)
        if m is None:  # pragma: no cover — parser enforces the shape
            raise MalformedDocumentError(
                f"LoopSignature.cross_sop_target: stored to_step "
                f"{self.to_step!r} does not match CROSS_SOP_REF"
            )
        return m.group("prefix"), m.group("acid"), int(m.group("step"))


# ---------------------------------------------------------------------------
# FXA-2226 Path B: Branch metadata parsing.
#
# `Workflow branches:` declares forward branches with edge labels. Schema:
#
#     Workflow branches:
#       - from: 2
#         to:
#           - {id: 3a, label: pass}
#           - {id: 3b, label: fail}
#
# Sub-step `id` values are split into ``parent`` (int — leading digits) and
# ``branch`` (str — single trailing letter). Path B keeps types int-stable;
# the branch suffix is exposed via a separate field.
# ---------------------------------------------------------------------------

# Sub-step ID format: one or more digits followed by a single letter.
_BRANCH_TO_ID_RE = re.compile(r"^(?P<parent>\d+)(?P<branch>[a-z])$")


class BranchTarget(NamedTuple):
    """A single sibling of a forward branch.

    ``parent`` is the integer step (e.g. ``3`` for ``3a``); ``branch`` is the
    suffix letter (``"a"``); ``label`` is the edge label printed above the
    branch arrow.
    """

    parent: int
    branch: str
    label: str


@dataclass(frozen=True)
class BranchSignature:
    """Forward-branch declaration extracted from ``Workflow branches:`` metadata."""

    from_step: int
    to: tuple[BranchTarget, ...]


@dataclass(frozen=True)
class BranchError:
    """Validation error for a Workflow branches: entry (or a file-level issue)."""

    msg: str
    branch_idx: int | None = None


# CHG-2226 Path B intermediate-state guardrail. The parser+schema land in
# this CHG (Phase 1) but the renderer support arrives in CHG-2227. Until
# CHG-2227 Phase 8a flips this flag to ``True`` as a separately-reviewable
# commit, ``af validate`` rejects any SOP authoring ``Workflow branches:``
# so production SOPs cannot land branchy declarations that misrender in
# nested/flat/Mermaid output.
_BRANCHES_RENDERER_READY = False


def has_workflow_branches_field(parsed: ParsedDocument) -> bool:
    """Return True if the SOP authors the ``Workflow branches:`` field at all.

    True even for empty values (``Workflow branches: []`` or ``null``). Used by
    the renderer-readiness gate to enforce the spec rule "MUST NOT author this
    field until CHG-2227 lands" — authoring an empty list still counts as
    authoring the field (per Codex PR #68 R2 review).
    """
    return any(mf.key == WORKFLOW_BRANCHES for mf in parsed.metadata_fields)


def parse_workflow_branches(parsed: ParsedDocument) -> list[BranchSignature]:
    """Parse the optional ``Workflow branches:`` metadata into BranchSignatures.

    Returns ``[]`` when the field is absent or its value is empty.

    Raises :class:`MalformedDocumentError` if the YAML is not a list, if any
    entry is not a dict, if a required key is missing, or if any sub-step
    ``id`` does not match ``\\d+[a-z]``.
    """
    field_map = {mf.key: mf.value for mf in parsed.metadata_fields}
    raw = field_map.get(WORKFLOW_BRANCHES)
    if raw is None or not raw.strip():
        return []

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise MalformedDocumentError(
            f"Workflow branches: invalid YAML — {exc}"
        ) from exc

    if data is None:
        return []
    if not isinstance(data, list):
        raise MalformedDocumentError(
            "Workflow branches: expected a YAML list of branch objects"
        )

    branches: list[BranchSignature] = []
    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise MalformedDocumentError(
                f"Workflow branches[{i}]: expected a YAML mapping, got {type(entry).__name__}"
            )
        if "from" not in entry or "to" not in entry:
            raise MalformedDocumentError(
                f"Workflow branches[{i}]: missing required key 'from' or 'to'"
            )
        from_step_raw = entry["from"]
        if isinstance(from_step_raw, bool) or not isinstance(from_step_raw, int):
            raise MalformedDocumentError(
                f"Workflow branches[{i}]: 'from' must be an integer step index"
            )
        to_raw = entry["to"]
        if not isinstance(to_raw, list) or not to_raw:
            raise MalformedDocumentError(
                f"Workflow branches[{i}]: 'to' must be a non-empty list of "
                f"{{id, label}} entries"
            )
        targets: list[BranchTarget] = []
        for j, target_raw in enumerate(to_raw):
            if not isinstance(target_raw, dict):
                raise MalformedDocumentError(
                    f"Workflow branches[{i}].to[{j}]: expected a mapping"
                )
            target_id = target_raw.get("id")
            if not isinstance(target_id, str):
                raise MalformedDocumentError(
                    f"Workflow branches[{i}].to[{j}]: 'id' must be a string "
                    f"matching '\\d+[a-z]'"
                )
            m = _BRANCH_TO_ID_RE.match(target_id)
            if m is None:
                raise MalformedDocumentError(
                    f"Workflow branches[{i}].to[{j}]: 'id' {target_id!r} "
                    f"does not match '\\d+[a-z]'"
                )
            label = target_raw.get("label", "")
            if not isinstance(label, str):
                raise MalformedDocumentError(
                    f"Workflow branches[{i}].to[{j}]: 'label' must be a string"
                )
            targets.append(
                BranchTarget(
                    parent=int(m.group("parent")),
                    branch=m.group("branch"),
                    label=label,
                )
            )
        branches.append(
            BranchSignature(from_step=int(from_step_raw), to=tuple(targets))
        )
    return branches


def validate_branches(
    parsed: ParsedDocument,
    branches: list[BranchSignature],
    *,
    _gate_open_for_test: bool = False,
) -> list[BranchError]:
    """Validate ``Workflow branches:`` declarations against the SOP body.

    Returns a list of :class:`BranchError`.  Empty list means valid.

    Validation rules:

    1. **Renderer-readiness gate** — if ``_BRANCHES_RENDERER_READY`` is False
       (the default in CHG-2226 until CHG-2227 Phase 8a flips it), the
       presence of *any* branch declaration is a hard error directing
       authors to wait for CHG-2227. ``_gate_open_for_test`` bypasses this
       gate for tests that need to exercise the structural rules below.
    2. **`from` exists** — must reference an existing integer step in
       ``## Steps``.
    3. **`to.parent == from + 1`** — every sibling's parent integer must
       equal ``from + 1`` (the convention is that branches fork from step
       N to siblings ``(N+1)a``, ``(N+1)b``, ...).
    4. **Sub-step exists** — every ``to.id`` (e.g. ``3a``) must appear in
       ``## Steps`` as an actual sub-step line.
    5. **Siblings contiguous** — sibling lines must appear consecutively in
       ``## Steps`` (no integer step interleaved between them).
    6. **No orphan sub-steps** — every sub-step letter present in ``## Steps``
       must appear in some ``branches.to`` declaration.
    """
    errors: list[BranchError] = []

    # Rule 1: gate. Per Codex PR #68 R2 review, fire on FIELD PRESENCE
    # (including `Workflow branches: []` / `null`), not on parsed-list
    # non-emptiness. The spec is "MUST NOT author this field until
    # CHG-2227 lands" — authoring an empty list still authors the field.
    field_present = has_workflow_branches_field(parsed)
    if field_present and not (_BRANCHES_RENDERER_READY or _gate_open_for_test):
        errors.append(
            BranchError(
                msg=(
                    "Workflow branches: schema is parsed but renderer support is "
                    "not yet shipped (CHG-2227 pending). Production SOPs MUST NOT "
                    "author this field until CHG-2227 lands."
                ),
            )
        )
        # Continue running structural checks too — useful for early authors.

    # Pull the actual ## Steps lines (in document order) for sub-step
    # presence and contiguity checks.
    from fx_alfred.core.parser import extract_section as _extract_section

    section = _extract_section(parsed.body, "Steps") if parsed.body else None
    sub_steps_in_order: list[tuple[int, str]] = []  # [(parent, branch), ...]
    plain_step_positions: dict[int, int] = {}  # int_index -> first occurrence
    if section is not None:
        position = 0  # logical position counting ALL parsed step lines
        fence_char: str | None = None
        fence_len = 0
        for raw in section.split("\n"):
            stripped = raw.lstrip()
            # Skip fenced code blocks (mirrors parse_top_level_step_indices).
            if fence_char is not None:
                if stripped and stripped[0] == fence_char:
                    run = 0
                    while run < len(stripped) and stripped[run] == fence_char:
                        run += 1
                    if run >= fence_len:
                        fence_char = None
                        fence_len = 0
                continue
            if stripped and stripped[0] in ("`", "~"):
                ch = stripped[0]
                run = 0
                while run < len(stripped) and stripped[run] == ch:
                    run += 1
                if run >= 3:
                    fence_char = ch
                    fence_len = run
                    continue
            # Match either "3." (plain) or "3a." (sub-step).
            m = re.match(r"^(?:###\s+)?(\d+)([a-z])?\.\s+", raw)
            if not m:
                continue
            parent = int(m.group(1))
            sub = m.group(2)
            if sub is None:
                if parent not in plain_step_positions:
                    plain_step_positions[parent] = position
            else:
                sub_steps_in_order.append((parent, sub))
            position += 1

    # Build a lookup set of (parent, branch) pairs that exist in ## Steps.
    sub_steps_set = set(sub_steps_in_order)
    # Build a lookup set of (parent, branch) pairs DECLARED across all branches.
    declared: set[tuple[int, str]] = set()
    for sig in branches:
        for tgt in sig.to:
            declared.add((tgt.parent, tgt.branch))

    # Plain-step ints only (excluding parent ints injected from sub-step
    # lines) — used by Rule 2 below per PR #68 Codex F1 finding. The
    # spec says `from` must reference an EXISTING INTEGER step in
    # `## Steps`; sub-stepped-only parents (no bare `2.` line) should
    # NOT satisfy `from: 2`.
    plain_only_ints = frozenset(plain_step_positions.keys())

    for i, sig in enumerate(branches):
        # Rule 2: from references existing INTEGER step (must be a bare
        # plain step line — not satisfied solely by parent-int injection
        # from sub-step siblings).
        if sig.from_step not in plain_only_ints:
            errors.append(
                BranchError(
                    msg=(
                        f"Workflow branches[{i}]: from = {sig.from_step} does "
                        f"not reference an existing step in ## Steps"
                    ),
                    branch_idx=i,
                )
            )
        for j, tgt in enumerate(sig.to):
            # Rule 3: parent must equal from + 1
            if tgt.parent != sig.from_step + 1:
                errors.append(
                    BranchError(
                        msg=(
                            f"Workflow branches[{i}].to[{j}]: id "
                            f"{tgt.parent}{tgt.branch!r} parent must be "
                            f"{sig.from_step + 1} (from + 1), got {tgt.parent}"
                        ),
                        branch_idx=i,
                    )
                )
            # Rule 4: sub-step exists
            if (tgt.parent, tgt.branch) not in sub_steps_set:
                errors.append(
                    BranchError(
                        msg=(
                            f"Workflow branches[{i}].to[{j}]: id "
                            f"{tgt.parent}{tgt.branch} does not reference "
                            f"an existing sub-step in ## Steps"
                        ),
                        branch_idx=i,
                    )
                )

        # Rule 5: siblings contiguous in ## Steps. Find positions of declared
        # siblings; assert they are consecutive (allowing only sub-step lines
        # between them).
        sibling_positions = [
            idx
            for idx, (parent, branch) in enumerate(sub_steps_in_order)
            if (parent, branch) in {(t.parent, t.branch) for t in sig.to}
        ]
        if sibling_positions:
            expected_parent = sig.from_step + 1
            interleaved_plain = False
            # Build a unified ordered list of (kind, parent, branch_or_None)
            # and verify no plain integer step appears between the first and
            # last declared sibling.
            unified: list[tuple[str, int, str | None]] = []
            if section is not None:
                fence_char = None
                fence_len = 0
                for raw in section.split("\n"):
                    stripped = raw.lstrip()
                    if fence_char is not None:
                        if stripped and stripped[0] == fence_char:
                            run = 0
                            while run < len(stripped) and stripped[run] == fence_char:
                                run += 1
                            if run >= fence_len:
                                fence_char = None
                                fence_len = 0
                        continue
                    if stripped and stripped[0] in ("`", "~"):
                        ch = stripped[0]
                        run = 0
                        while run < len(stripped) and stripped[run] == ch:
                            run += 1
                        if run >= 3:
                            fence_char = ch
                            fence_len = run
                            continue
                    m = re.match(r"^(?:###\s+)?(\d+)([a-z])?\.\s+", raw)
                    if not m:
                        continue
                    p = int(m.group(1))
                    s = m.group(2)
                    unified.append(("sub" if s else "plain", p, s))
            sibling_set = {(t.parent, t.branch) for t in sig.to}
            sib_unified_positions = [
                u_idx
                for u_idx, (kind, p, s) in enumerate(unified)
                if kind == "sub" and (p, s) in sibling_set
            ]
            if sib_unified_positions and len(sib_unified_positions) >= 2:
                lo = min(sib_unified_positions)
                hi = max(sib_unified_positions)
                for u_idx in range(lo + 1, hi):
                    kind, p, s = unified[u_idx]
                    if kind == "plain":
                        interleaved_plain = True
                        break
            if interleaved_plain:
                errors.append(
                    BranchError(
                        msg=(
                            f"Workflow branches[{i}]: siblings must be "
                            f"contiguous in ## Steps (parent {expected_parent}); "
                            f"found a plain integer step interleaved between "
                            f"sub-step siblings"
                        ),
                        branch_idx=i,
                    )
                )

    # Rule 6: no orphan sub-steps (sub-steps in ## Steps not declared).
    for parent, branch in sub_steps_in_order:
        if (parent, branch) not in declared:
            errors.append(
                BranchError(
                    msg=(
                        f"sub-step {parent}{branch} appears in ## Steps but "
                        f"is an orphan — not declared in any "
                        f"Workflow branches.to entry"
                    ),
                )
            )

    return errors


@dataclass(frozen=True)
class LoopError:
    """Validation error for a single loop entry (or a file-level issue)."""

    msg: str
    loop_id: str | None


def parse_workflow_loops(parsed: ParsedDocument) -> list[LoopSignature]:
    """Parse the optional ``Workflow loops:`` metadata value into LoopSignatures.

    Returns ``[]`` when the field is absent or its value is empty.

    Raises :class:`MalformedDocumentError` if the YAML is not a list, if any
    entry is not a dict, if any required key is missing, or if any typed key
    has the wrong type. The error message cites the loop ``id`` when known.
    """
    field_map = {mf.key: mf.value for mf in parsed.metadata_fields}
    raw = field_map.get(WORKFLOW_LOOPS)
    if raw is None or not raw.strip():
        return []

    # Two supported shapes:
    #   1) Inline YAML on the field line (rare): "[{id: x, from: 3, to: 1, ...}]"
    #   2) A block following the key on subsequent lines — not representable in
    #      bold-field prefix. So authors use the inline form.
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise MalformedDocumentError(f"Workflow loops: invalid YAML — {exc}") from exc

    if data is None:
        return []
    if not isinstance(data, list):
        raise MalformedDocumentError(
            "Workflow loops: expected a YAML list of loop objects"
        )

    loops: list[LoopSignature] = []
    for idx, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise MalformedDocumentError(
                f"Workflow loops[{idx}]: expected a mapping, got {type(entry).__name__}"
            )
        loop_id = entry.get("id")
        id_label = loop_id if isinstance(loop_id, str) and loop_id else f"#{idx}"

        for key in _LOOP_REQUIRED_KEYS:
            if key not in entry:
                raise MalformedDocumentError(
                    f"Workflow loops[{id_label}]: missing required key '{key}'"
                )

        if not isinstance(loop_id, str) or not loop_id:
            raise MalformedDocumentError(
                f"Workflow loops[{id_label}]: 'id' must be a non-empty string"
            )
        from_step = entry["from"]
        to_step = entry["to"]
        max_iter = entry["max_iterations"]
        condition = entry["condition"]

        if isinstance(from_step, bool) or not isinstance(from_step, int):
            raise MalformedDocumentError(
                f"Workflow loops[{loop_id}]: 'from' must be an integer"
            )
        if isinstance(to_step, bool):
            raise MalformedDocumentError(
                f"Workflow loops[{loop_id}]: 'to' must be an integer or "
                f"'PREFIX-ACID.step' cross-SOP reference, not bool"
            )
        if isinstance(to_step, int):
            pass  # intra-SOP loop, traditional form
        elif isinstance(to_step, str):
            # Cross-SOP reference must match PREFIX-ACID.step (FXA-2218 Commit 2).
            # Quoted digit strings like "27" are rejected — use int 27 for intra-SOP.
            if not CROSS_SOP_REF.match(to_step):
                raise MalformedDocumentError(
                    f"Workflow loops[{loop_id}]: 'to' must be an integer or "
                    f"'PREFIX-ACID.step' cross-SOP reference, got {to_step!r}"
                )
        else:
            raise MalformedDocumentError(
                f"Workflow loops[{loop_id}]: 'to' must be an integer or "
                f"'PREFIX-ACID.step' cross-SOP reference, not "
                f"{type(to_step).__name__}"
            )
        if isinstance(max_iter, bool) or not isinstance(max_iter, int):
            raise MalformedDocumentError(
                f"Workflow loops[{loop_id}]: 'max_iterations' must be an integer"
            )
        if not isinstance(condition, str) or not condition.strip():
            raise MalformedDocumentError(
                f"Workflow loops[{loop_id}]: 'condition' must be a non-empty string"
            )

        loops.append(
            LoopSignature(
                id=loop_id,
                from_step=from_step,
                to_step=to_step,
                max_iterations=max_iter,
                condition=condition,
            )
        )

    return loops


def _parse_step_indices(parsed: ParsedDocument) -> frozenset[int] | None:
    """Parse the set of step indices observed in the SOP's Steps section.

    Returns ``None`` if no ``Steps`` heading is present; otherwise a frozenset
    of the step indices parsed from top-level numbered Markdown lines (e.g.
    ``1. First``, ``### 1. First``, or ``3a. Sub-step``).

    Delegates to :func:`fx_alfred.core.steps.parse_top_level_step_indices`,
    which is fence-aware: numbered lines inside ```` ``` ```` / ``~~~``
    fenced code blocks are skipped. Fence-awareness is critical for FXA-2226
    Path B because the widened regex (``\\d+[a-z]?``) matches sub-step
    lines too, and a fenced ``3a. example`` line would otherwise inject
    parent step 3 into existence checks for `Workflow loops.from/to: 3`
    (Codex PR #68 R3 inline review).
    """
    from fx_alfred.core.parser import extract_section
    from fx_alfred.core.steps import parse_top_level_step_indices

    section = extract_section(parsed.body, "Steps")
    if section is None:
        return None
    return parse_top_level_step_indices(section)


def validate_loops(
    parsed: ParsedDocument, loops: list[LoopSignature]
) -> list[LoopError]:
    """Return a list of LoopError.  Empty list means valid.

    Pure intra-SOP validation. Cross-SOP references (string ``to_step``)
    are skipped here — they are checked at ``af validate`` corpus level
    (FXA-2218 D2/D3) and ``af plan`` composition time (FXA-2218 D4).
    """
    errors: list[LoopError] = []
    step_indices = _parse_step_indices(parsed)

    # Helper for the shared "existing step" diagnostic string.
    def _found_desc() -> str:
        if step_indices:
            return "{" + ", ".join(str(i) for i in sorted(step_indices)) + "}"
        return "{}"

    for loop in loops:
        if loop.max_iterations <= 0:
            errors.append(
                LoopError(
                    msg=(
                        f"loop '{loop.id}': 'max_iterations' "
                        f"({loop.max_iterations}) must be a positive integer"
                    ),
                    loop_id=loop.id,
                )
            )

        # `from_step` is ALWAYS intra-SOP — regardless of whether `to_step`
        # is int (intra-SOP) or str (cross-SOP), the source step must
        # reference an existing local step. Run this check first so the
        # cross-SOP branch can't silently accept `from: 99` in a SOP that
        # only has steps 1–3 (PR #59 Codex review P1 #3).
        if step_indices is not None and loop.from_step not in step_indices:
            errors.append(
                LoopError(
                    msg=(
                        f"loop '{loop.id}': 'from' ({loop.from_step}) "
                        f"does not reference an existing step in Steps section "
                        f"(found: {_found_desc()})"
                    ),
                    loop_id=loop.id,
                )
            )

        # Remaining checks (back-edge direction + to_step membership) are
        # only meaningful when `to_step` is intra-SOP. Cross-SOP targets
        # are validated at the corpus level by `af validate` D2/D3 and at
        # composition time by `af plan` D4.
        # Use isinstance rather than is_cross_sop() so pyright can narrow
        # loop.to_step from (int | str) to int for the rest of this body.
        if not isinstance(loop.to_step, int):
            continue

        if loop.from_step <= loop.to_step:
            errors.append(
                LoopError(
                    msg=(
                        f"loop '{loop.id}': 'from' ({loop.from_step}) must be greater "
                        f"than 'to' ({loop.to_step}) — loops are back-edges only"
                    ),
                    loop_id=loop.id,
                )
            )

        if step_indices is not None and loop.to_step not in step_indices:
            errors.append(
                LoopError(
                    msg=(
                        f"loop '{loop.id}': 'to' ({loop.to_step}) "
                        f"does not reference an existing step in Steps section "
                        f"(found: {_found_desc()})"
                    ),
                    loop_id=loop.id,
                )
            )

    return errors
