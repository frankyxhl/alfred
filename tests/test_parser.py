"""Tests for fx_alfred.core.parser — H1_PATTERN named groups."""

from fx_alfred.core.parser import H1_PATTERN


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
