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


def test_reject_empty_string_token_in_validate():
    requires_sig = WorkflowSignature(
        input="proposal:none",
        output="proposal:draft",
        requires=[""],
    )
    requires_errors = validate_workflow_signature(requires_sig)
    assert any("Workflow requires: empty token" in e for e in requires_errors)

    provides_sig = WorkflowSignature(
        input="proposal:none",
        output="proposal:draft",
        provides=[""],
    )
    provides_errors = validate_workflow_signature(provides_sig)
    assert any("Workflow provides: empty token" in e for e in provides_errors)


def test_reject_empty_token_in_requires_list():
    """Invalid token format in requires list should be rejected."""
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


# ---------------------------------------------------------------------------
# _parse_token_list — empty token preservation (CHG-2204 §Validation #4)
# ---------------------------------------------------------------------------


def test_parse_preserves_empty_token_from_double_comma():
    """Empty token between commas must survive parsing so validate can flag it.

    CHG-2204 validation rule #4: 'Empty tokens are invalid.'
    af validate must report: 'empty token after comma splitting'.
    """
    parsed = _make_parsed(
        [
            ("Workflow input", "proposal:none"),
            ("Workflow output", "proposal:draft"),
            ("Workflow requires", "repo:clean, ,tests:green"),
        ]
    )
    sig = parse_workflow_signature(parsed)
    assert sig is not None
    # The empty token must be preserved in the list
    assert "" in sig.requires
    # Validation must catch it
    errors = validate_workflow_signature(sig)
    assert any("empty token" in e for e in errors)


def test_parse_preserves_empty_token_from_trailing_comma():
    """Trailing comma produces an empty token that must be flagged."""
    parsed = _make_parsed(
        [
            ("Workflow input", "proposal:none"),
            ("Workflow output", "proposal:draft"),
            ("Workflow provides", "proposal:draft,"),
        ]
    )
    sig = parse_workflow_signature(parsed)
    assert sig is not None
    assert "" in sig.provides
    errors = validate_workflow_signature(sig)
    assert any("empty token" in e for e in errors)


def test_parse_absent_requires_produces_empty_list():
    """Missing Workflow requires field must still produce an empty list, not ['']."""
    parsed = _make_parsed(
        [
            ("Workflow input", "proposal:none"),
            ("Workflow output", "proposal:draft"),
        ]
    )
    sig = parse_workflow_signature(parsed)
    assert sig is not None
    assert sig.requires == []
    assert sig.provides == []


# ---------------------------------------------------------------------------
# Fix 1: parse returns signature when ANY workflow key present
# ---------------------------------------------------------------------------


def test_parse_returns_sig_for_requires_only():
    """SOP with only Workflow requires must still return a signature."""
    parsed = _make_parsed(
        [
            ("Status", "Active"),
            ("Workflow requires", "repo:clean"),
        ]
    )
    sig = parse_workflow_signature(parsed)
    assert sig is not None
    assert sig.input == ""
    assert sig.output == ""
    assert sig.requires == ["repo:clean"]


def test_parse_returns_sig_for_provides_only():
    """SOP with only Workflow provides must still return a signature."""
    parsed = _make_parsed(
        [
            ("Status", "Active"),
            ("Workflow provides", "proposal:draft"),
        ]
    )
    sig = parse_workflow_signature(parsed)
    assert sig is not None
    assert sig.provides == ["proposal:draft"]


def test_validate_requires_without_input_output():
    """requires/provides present without input/output must be flagged."""
    sig = WorkflowSignature(
        input="", output="", requires=["repo:clean"], provides=["proposal:draft"]
    )
    errors = validate_workflow_signature(sig)
    assert any("without" in e.lower() and "input" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# Fix 2: edge typed requires complete signatures on both sides
# ---------------------------------------------------------------------------


def test_edge_untyped_when_left_has_partial_signature():
    """Partial signature (only output, no input) must not make an edge typed."""
    sig_a = WorkflowSignature(input="", output="proposal:draft")  # partial
    sig_b = WorkflowSignature(input="proposal:draft", output="proposal:reviewed")
    edges = check_composition([("A", sig_a), ("B", sig_b)])
    assert len(edges) == 1
    assert edges[0].typed is False  # partial left → untyped


def test_edge_untyped_when_right_has_partial_signature():
    """Partial signature (only input, no output) must not make an edge typed."""
    sig_a = WorkflowSignature(input="proposal:none", output="proposal:draft")
    sig_b = WorkflowSignature(input="proposal:draft", output="")  # partial
    edges = check_composition([("A", sig_a), ("B", sig_b)])
    assert len(edges) == 1
    assert edges[0].typed is False  # partial right → untyped
