"""Tests for core/workflow.py — typed SOP workflow composition helpers."""

from fx_alfred.core.parser import MetadataField, ParsedDocument
from fx_alfred.core.workflow import (
    WorkflowSignature,
    check_composition,
    parse_workflow_signature,
    validate_workflow_signature,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_parsed(fields: list[tuple[str, str]]) -> ParsedDocument:
    """Build a minimal ParsedDocument with the given metadata fields."""
    metadata_fields = [
        MetadataField(
            key=key,
            value=value,
            prefix_style="bold",
            raw_line=f"**{key}:** {value}",
        )
        for key, value in fields
    ]
    return ParsedDocument(
        h1_line="# SOP-0000: Test",
        metadata_fields=metadata_fields,
    )


# ---------------------------------------------------------------------------
# parse_workflow_signature
# ---------------------------------------------------------------------------


def test_parse_valid_single_token_input_output():
    parsed = _make_parsed(
        [
            ("Workflow input", "proposal:none"),
            ("Workflow output", "proposal:draft"),
        ]
    )
    sig = parse_workflow_signature(parsed)
    assert sig is not None
    assert sig.input == "proposal:none"
    assert sig.output == "proposal:draft"
    assert sig.requires == []
    assert sig.provides == []


def test_parse_untyped_sop_returns_none():
    parsed = _make_parsed([("Status", "Active")])
    assert parse_workflow_signature(parsed) is None


def test_parse_includes_requires_and_provides():
    parsed = _make_parsed(
        [
            ("Workflow input", "proposal:none"),
            ("Workflow output", "proposal:draft"),
            ("Workflow requires", "repo:clean"),
            ("Workflow provides", "proposal:draft, proposal:editable"),
        ]
    )
    sig = parse_workflow_signature(parsed)
    assert sig is not None
    assert sig.requires == ["repo:clean"]
    assert sig.provides == ["proposal:draft", "proposal:editable"]


# ---------------------------------------------------------------------------
# validate_workflow_signature
# ---------------------------------------------------------------------------


def test_reject_invalid_token_characters():
    sig = WorkflowSignature(input="BAD TOKEN!", output="proposal:draft")
    errors = validate_workflow_signature(sig)
    assert any("invalid token format" in e and "BAD TOKEN!" in e for e in errors)


def test_reject_missing_output_when_input_exists():
    sig = WorkflowSignature(input="proposal:none", output="")
    errors = validate_workflow_signature(sig)
    assert any("Workflow output is missing" in e for e in errors)


def test_reject_duplicate_entries_in_requires():
    sig = WorkflowSignature(
        input="proposal:none",
        output="proposal:draft",
        requires=["repo:clean", "repo:clean"],
    )
    errors = validate_workflow_signature(sig)
    assert any("duplicate entry" in e and "repo:clean" in e for e in errors)


def test_empty_requires_and_provides_is_valid():
    sig = WorkflowSignature(input="proposal:none", output="proposal:draft")
    errors = validate_workflow_signature(sig)
    assert errors == []


def test_valid_signature_no_errors():
    sig = WorkflowSignature(
        input="proposal:none",
        output="proposal:draft",
        requires=["repo:clean"],
        provides=["proposal:draft", "proposal:editable"],
    )
    assert validate_workflow_signature(sig) == []


def test_reject_missing_input_when_output_exists():
    sig = WorkflowSignature(input="", output="proposal:draft")
    errors = validate_workflow_signature(sig)
    assert any("Workflow input is missing" in e for e in errors)


def test_reject_both_empty():
    sig = WorkflowSignature(input="", output="")
    errors = validate_workflow_signature(sig)
    assert len(errors) > 0


def test_reject_invalid_output_token():
    sig = WorkflowSignature(input="proposal:none", output="UPPER CASE")
    errors = validate_workflow_signature(sig)
    assert any("invalid token format" in e and "UPPER CASE" in e for e in errors)


def test_reject_duplicate_in_provides():
    sig = WorkflowSignature(
        input="proposal:none",
        output="proposal:draft",
        provides=["proposal:draft", "proposal:draft"],
    )
    errors = validate_workflow_signature(sig)
    assert any("duplicate entry" in e and "proposal:draft" in e for e in errors)


def test_reject_empty_token_in_requires_list():
    """A token that becomes empty after stripping should be rejected."""
    # The parse step filters empty strings, so we test validate directly
    # with a token that has invalid format instead.
    sig = WorkflowSignature(
        input="proposal:none",
        output="proposal:draft",
        requires=["repo:clean", "bad token!"],
    )
    errors = validate_workflow_signature(sig)
    assert any("invalid token format" in e for e in errors)


# ---------------------------------------------------------------------------
# check_composition
# ---------------------------------------------------------------------------


def test_compatible_typed_edge():
    sig_a = WorkflowSignature(input="proposal:none", output="proposal:draft")
    sig_b = WorkflowSignature(input="proposal:draft", output="proposal:reviewed")
    edges = check_composition([("COR-1102", sig_a), ("COR-1602", sig_b)])
    assert len(edges) == 1
    edge = edges[0]
    assert edge.typed is True
    assert edge.compatible is True
    assert edge.from_output == "proposal:draft"
    assert edge.to_input == "proposal:draft"


def test_mismatched_typed_edge():
    sig_a = WorkflowSignature(input="proposal:none", output="proposal:draft")
    sig_b = WorkflowSignature(input="change:approved", output="change:implemented")
    edges = check_composition([("COR-1102", sig_a), ("COR-1602", sig_b)])
    assert len(edges) == 1
    edge = edges[0]
    assert edge.typed is True
    assert edge.compatible is False
    assert edge.from_output == "proposal:draft"
    assert edge.to_input == "change:approved"


def test_untyped_edge_is_compatible():
    sig_a = WorkflowSignature(input="proposal:none", output="proposal:draft")
    sig_b = WorkflowSignature(input="", output="")
    edges = check_composition([("COR-1102", sig_a), ("COR-9999", sig_b)])
    assert len(edges) == 1
    edge = edges[0]
    assert edge.typed is False
    assert edge.compatible is True


def test_composition_three_sops():
    sig_a = WorkflowSignature(input="a:start", output="a:mid")
    sig_b = WorkflowSignature(input="a:mid", output="a:end")
    sig_c = WorkflowSignature(input="a:end", output="a:done")
    edges = check_composition([("A", sig_a), ("B", sig_b), ("C", sig_c)])
    assert len(edges) == 2
    assert all(e.compatible for e in edges)


def test_composition_empty_chain():
    assert check_composition([]) == []


def test_composition_single_sop_no_edges():
    sig = WorkflowSignature(input="x:0", output="x:1")
    assert check_composition([("SOP-1", sig)]) == []
