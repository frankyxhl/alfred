"""Pure workflow composition helpers for typed SOP chains.

This module has no filesystem access. It operates on already-parsed
workflow metadata to build signatures, validate them, and check
adjacent-SOP composition in an ``af plan`` chain.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from fx_alfred.core.parser import ParsedDocument
from fx_alfred.core.schema import (
    WORKFLOW_INPUT,
    WORKFLOW_OUTPUT,
    WORKFLOW_PROVIDES,
    WORKFLOW_REQUIRES,
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
