"""Pure workflow composition helpers for typed SOP chains.

This module has no filesystem access. It operates on already-parsed
workflow metadata to build signatures, validate them, and check
adjacent-SOP composition in an ``af plan`` chain.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import yaml

from fx_alfred.core.parser import MalformedDocumentError, ParsedDocument
from fx_alfred.core.schema import (
    WORKFLOW_INPUT,
    WORKFLOW_OUTPUT,
    WORKFLOW_PROVIDES,
    WORKFLOW_REQUIRES,
    WORKFLOW_LOOPS,
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

# Regex to match numbered steps: "1. text" or "### 1. text"
_STEP_INDEX_RE = re.compile(r"^(?:###\s+)?(\d+)\.\s+")
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
    ``1. First``) and ``### 1. First``-style headings.

    The regex is applied to the *raw* line (not stripped), so indented
    sub-items (e.g. ``    1. Sub-item``) and numbered lines inside fenced
    code blocks are **not** counted as top-level steps — top-level Markdown
    numbered items are flush-left by convention.
    """
    from fx_alfred.core.parser import extract_section

    section = extract_section(parsed.body, "Steps")
    if section is None:
        return None

    indices: set[int] = set()
    for line in section.split("\n"):
        m = _STEP_INDEX_RE.match(line)
        if m:
            indices.add(int(m.group(1)))
    return frozenset(indices)


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

        # Skip intra-SOP back-edge direction + membership checks for cross-SOP
        # refs: target step lives in a different SOP's corpus entry.
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

        # Membership check: only meaningful if we know the step indices.
        # The spec requires that 'from' and 'to' reference *existing* step
        # indexes in the Steps section — gapped or sparse numbering means
        # intermediate values are not valid references.
        if step_indices is not None:
            found_desc = (
                "{" + ", ".join(str(i) for i in sorted(step_indices)) + "}"
                if step_indices
                else "{}"
            )
            if loop.from_step not in step_indices:
                errors.append(
                    LoopError(
                        msg=(
                            f"loop '{loop.id}': 'from' ({loop.from_step}) "
                            f"does not reference an existing step in Steps section "
                            f"(found: {found_desc})"
                        ),
                        loop_id=loop.id,
                    )
                )
            if loop.to_step not in step_indices:
                errors.append(
                    LoopError(
                        msg=(
                            f"loop '{loop.id}': 'to' ({loop.to_step}) "
                            f"does not reference an existing step in Steps section "
                            f"(found: {found_desc})"
                        ),
                        loop_id=loop.id,
                    )
                )

    return errors
