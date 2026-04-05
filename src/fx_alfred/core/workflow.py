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

    Returns ``None`` when neither ``Workflow input`` nor ``Workflow output``
    metadata is present (i.e. the document is untyped).
    """
    field_map = {mf.key: mf.value for mf in parsed.metadata_fields}

    input_val = field_map.get(WORKFLOW_INPUT)
    output_val = field_map.get(WORKFLOW_OUTPUT)

    # Untyped document — no workflow metadata at all.
    if input_val is None and output_val is None:
        return None

    # Both must be present if either is present; however ``parse`` returns
    # whatever it finds and ``validate`` catches the error.  Treat a missing
    # value as empty string so ``validate`` produces the right diagnostic.
    return WorkflowSignature(
        input=input_val.strip() if input_val else "",
        output=output_val.strip() if output_val else "",
        requires=_parse_token_list(field_map.get(WORKFLOW_REQUIRES, "")),
        provides=_parse_token_list(field_map.get(WORKFLOW_PROVIDES, "")),
    )


def validate_workflow_signature(sig: WorkflowSignature) -> list[str]:
    """Return a list of error strings.  Empty list means valid."""
    errors: list[str] = []

    # Both input and output must be present if either exists.
    if not sig.input or not sig.output:
        if sig.input and not sig.output:
            errors.append("Workflow input is set but Workflow output is missing")
        elif sig.output and not sig.input:
            errors.append("Workflow output is set but Workflow input is missing")
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
    when **both** signatures have non-empty ``input``/``output``.
    """
    edges: list[WorkflowEdge] = []
    for i in range(len(chain) - 1):
        left_id, left_sig = chain[i]
        right_id, right_sig = chain[i + 1]

        typed = bool(left_sig.output and right_sig.input)
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
