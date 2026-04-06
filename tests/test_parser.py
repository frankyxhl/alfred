"""Tests for fx_alfred.core.parser."""

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


def test_parse_metadata_stops_history_rows_on_malformed_table_row():
    """Malformed history rows should remain trailing text, not parsed row data."""
    content = """# SOP-1300: Update Document
**Status:** Active
---

## Change History

| Date | Change | By |
|---|---|---|
| 2026-01-01 | Initial version | Alice |
| malformed-row |
Trailing note
"""

    parsed = parse_metadata(content)

    assert len(parsed.history_rows) == 1
    assert parsed.history_rows[0].date == "2026-01-01"
    assert parsed.history_rows[0].change == "Initial version"
    assert parsed.history_rows[0].by == "Alice"
    assert parsed.trailing.startswith("| malformed-row |")
