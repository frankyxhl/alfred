"""Tests for fx_alfred.core.parser — H1_PATTERN named groups."""

from fx_alfred.core.parser import H1_PATTERN, parse_metadata


def test_h1_pattern_named_groups_extract_type_code_and_acid():
    """H1_PATTERN should expose named groups 'type_code' and 'acid'."""
    m = H1_PATTERN.match("# SOP-1300: Update Document")
    assert m is not None
    assert m.group("type_code") == "SOP"
    assert m.group("acid") == "1300"


def test_h1_pattern_named_groups_different_values():
    m = H1_PATTERN.match("# CHG-2102: Consolidate H1 Regex")
    assert m is not None
    assert m.group("type_code") == "CHG"
    assert m.group("acid") == "2102"


def test_h1_pattern_still_works_as_boolean_match():
    """Existing boolean-check usage must not break."""
    assert H1_PATTERN.match("# REF-0001: Glossary") is not None
    assert H1_PATTERN.match("Not a heading") is None
    assert H1_PATTERN.match("## SOP-1000: Wrong level") is None


def test_parse_metadata_change_history_heading_without_table():
    """parse_metadata returns empty history when heading exists but no table follows.

    Pins the documented early-return arm at parser.py:194: when the document has
    a `## Change History` heading but no `|---|---|---|` separator row is found
    in the section, parse_metadata returns with history_header="", history_rows=[],
    and the raw text folded back into body. This preserves round-trip fidelity
    for in-progress templates before the table is filled in. Breaking this would
    cascade into fmt_cmd / update_cmd trying to rewrite a nonexistent table.
    """
    content = (
        "# SOP-2100: Test\n\n"
        "**Applies to:** Test\n"
        "**Status:** Active\n\n---\n\n"
        "## What Is It?\n\nBody.\n\n---\n\n"
        "## Change History\n\n"
        "Table will be added later.\n"
    )
    parsed = parse_metadata(content)
    assert parsed.history_header == ""
    assert parsed.history_rows == []
    assert "Change History" in parsed.body
