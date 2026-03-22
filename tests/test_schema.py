"""Tests for core/schema.py — document type schema."""

from fx_alfred.core.schema import (
    DocType,
    DocRole,
    ALLOWED_STATUSES,
    REQUIRED_METADATA,
    REQUIRED_SECTIONS,
    ROUTING_ROLE_METADATA_KEY,
)


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
