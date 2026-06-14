"""Tests for core/schema.py — document type schema."""

import pytest


from fx_alfred.core.schema import (
    ALLOWED_DISPOSITIONS,
    ALLOWED_STATUSES,
    ALWAYS_INCLUDED,
    COR_REFERENCE_PATTERN,
    DISPOSITION,
    DISPOSITION_INHERIT_ONLY,
    DISPOSITION_MANDATORY_BIND,
    DISPOSITION_OPTIONAL_OVERLAY,
    DocType,
    DocRole,
    INSTANTIATES,
    OPTIONAL_METADATA,
    OVERLAYS,
    REQUIRED_METADATA,
    REQUIRED_SECTIONS,
    ROUTING_ROLE_METADATA_KEY,
    WORKFLOW_LOOPS,
)


pytestmark = pytest.mark.unit


def test_doctype_has_all_seven_values():
    values = {e.value for e in DocType}
    assert values == {"SOP", "PRP", "CHG", "ADR", "REF", "PLN", "INC"}


def test_docrole_has_four_values():
    values = {e.value for e in DocRole}
    assert values == {"routing", "sop", "index", "general"}


def test_allowed_statuses_inc():
    assert ALLOWED_STATUSES[DocType.INC] == ["Open", "Resolved", "Monitoring"]


def test_allowed_statuses_sop():
    assert ALLOWED_STATUSES[DocType.SOP] == ["Draft", "Active", "Deprecated"]


def test_all_required_metadata_have_four_fields():
    for doc_type, fields in REQUIRED_METADATA.items():
        assert len(fields) == 4, f"{doc_type} has {len(fields)} fields, expected 4"


def test_required_metadata_prp():
    assert REQUIRED_METADATA[DocType.PRP] == [
        "Applies to",
        "Last updated",
        "Last reviewed",
        "Status",
    ]


def test_required_sections_sop():
    sections = REQUIRED_SECTIONS[DocType.SOP]
    assert len(sections) == 5
    assert "What Is It?" in sections
    assert "Steps" in sections


def test_required_sections_prp():
    sections = REQUIRED_SECTIONS[DocType.PRP]
    assert len(sections) == 5
    assert "Problem" in sections
    assert "Open Questions" in sections


def test_routing_role_metadata_key():
    assert ROUTING_ROLE_METADATA_KEY == "Document role"


def test_schema_import_has_no_side_effects():
    # Re-importing should not raise any error (no filesystem access on import)
    import importlib
    import fx_alfred.core.schema as m

    importlib.reload(m)


# ---------------------------------------------------------------------------
# FXA-2205: Workflow loops and Always included constants
# ---------------------------------------------------------------------------


def test_workflow_loops_constant():
    """WORKFLOW_LOOPS constant has correct literal value."""
    assert WORKFLOW_LOOPS == "Workflow loops"


def test_always_included_constant():
    """ALWAYS_INCLUDED constant has correct literal value."""
    assert ALWAYS_INCLUDED == "Always included"


def test_optional_metadata_sop_contains_workflow_loops():
    """OPTIONAL_METADATA for SOP contains 'Workflow loops'."""
    assert "Workflow loops" in OPTIONAL_METADATA[DocType.SOP]


def test_optional_metadata_sop_contains_always_included():
    """OPTIONAL_METADATA for SOP contains 'Always included'."""
    assert "Always included" in OPTIONAL_METADATA[DocType.SOP]


def test_optional_metadata_non_sop_does_not_contain_workflow_loops():
    """Non-SOP document types do not have 'Workflow loops'."""
    for dt in DocType:
        if dt != DocType.SOP:
            assert "Workflow loops" not in OPTIONAL_METADATA[dt]


def test_optional_metadata_non_sop_does_not_contain_always_included():
    """Non-SOP document types do not have 'Always included'."""
    for dt in DocType:
        if dt != DocType.SOP:
            assert "Always included" not in OPTIONAL_METADATA[dt]


# ---------------------------------------------------------------------------
# COR-204: Disposition, Instantiates, Overlays constants
# ---------------------------------------------------------------------------


def test_disposition_constant():
    """DISPOSITION constant has correct literal value."""
    assert DISPOSITION == "Disposition"


def test_instantiates_constant():
    """INSTANTIATES constant has correct literal value."""
    assert INSTANTIATES == "Instantiates"


def test_overlays_constant():
    """OVERLAYS constant has correct literal value."""
    assert OVERLAYS == "Overlays"


def test_disposition_mandatory_bind_constant():
    """DISPOSITION_MANDATORY_BIND constant has correct literal value."""
    assert DISPOSITION_MANDATORY_BIND == "mandatory-bind"


def test_disposition_optional_overlay_constant():
    """DISPOSITION_OPTIONAL_OVERLAY constant has correct literal value."""
    assert DISPOSITION_OPTIONAL_OVERLAY == "optional-overlay"


def test_disposition_inherit_only_constant():
    """DISPOSITION_INHERIT_ONLY constant has correct literal value."""
    assert DISPOSITION_INHERIT_ONLY == "inherit-only"


def test_allowed_dispositions_contains_all_three():
    """ALLOWED_DISPOSITIONS contains exactly the three values."""
    assert ALLOWED_DISPOSITIONS == {
        "mandatory-bind",
        "optional-overlay",
        "inherit-only",
    }


def test_cor_reference_pattern():
    """COR_REFERENCE_PATTERN matches COR-NNNN format."""
    import re

    pattern = re.compile(COR_REFERENCE_PATTERN)
    assert pattern.match("COR-1622")
    assert pattern.match("COR-0001")
    assert pattern.match("COR-9999")
    assert not pattern.match("COR-123")
    assert not pattern.match("FXA-1622")
    assert not pattern.match("COR-12345")
    assert not pattern.match("cor-1622")


def test_optional_metadata_contains_disposition_for_all_types():
    """OPTIONAL_METADATA for all doc types contains 'Disposition'."""
    for dt in DocType:
        assert DISPOSITION in OPTIONAL_METADATA[dt]


def test_optional_metadata_contains_instantiates_for_all_types():
    """OPTIONAL_METADATA for all doc types contains 'Instantiates'."""
    for dt in DocType:
        assert INSTANTIATES in OPTIONAL_METADATA[dt]


def test_optional_metadata_contains_overlays_for_all_types():
    """OPTIONAL_METADATA for all doc types contains 'Overlays'."""
    for dt in DocType:
        assert OVERLAYS in OPTIONAL_METADATA[dt]
