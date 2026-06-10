"""Tests for fx_alfred.core.parser — H1_PATTERN named groups."""

import pytest


from fx_alfred.core.parser import H1_PATTERN, extract_section, parse_metadata


pytestmark = pytest.mark.unit


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


# --- extract_section fence-awareness (CHG-2294) ---


_FENCED_BASH_COMMENT_BODY = """\
intro text

## Steps

Step one:

```bash
# a column-0 bash comment must not terminate the section
echo hello
```

More steps here.

## Next Section

other content
"""


def test_extract_section_basic_boundaries():
    """Baseline: section runs from after its heading to the next heading."""
    body = "## Steps\n\nalpha\n\n## Next\n\nbeta\n"
    assert extract_section(body, "Steps") == "alpha"
    assert extract_section(body, "Next") == "beta"
    assert extract_section(body, "Absent") is None


def test_extract_section_h3_fallback():
    """Baseline: falls back to ### when no ## heading matches."""
    body = "## Outer\n\n### Steps\n\ngamma\n\n### After\n\ndelta\n"
    assert extract_section(body, "Steps") == "gamma"


def test_extract_section_ignores_bash_comment_inside_backtick_fence():
    """A `# comment` at column 0 inside ``` fences is not a section boundary."""
    section = extract_section(_FENCED_BASH_COMMENT_BODY, "Steps")
    assert section is not None
    assert "More steps here." in section
    assert "other content" not in section  # still stops at the real heading


def test_extract_section_ignores_heading_lookalike_inside_fence():
    """A `## Fake` line inside a fence is not a section boundary."""
    body = (
        "## Steps\n\nbefore\n\n"
        "```\n## Fake Heading\n```\n\n"
        "after\n\n## Real Next\n\nnope\n"
    )
    section = extract_section(body, "Steps")
    assert section is not None
    assert "before" in section
    assert "after" in section
    assert "nope" not in section


def test_extract_section_tilde_fence():
    """Tilde fences (~~~) shield their content like backtick fences."""
    body = "## Steps\n\none\n\n~~~sh\n# fenced comment\n~~~\n\ntwo\n\n## End\n\nx\n"
    section = extract_section(body, "Steps")
    assert section is not None
    assert "two" in section
    assert "x" not in section


def test_extract_section_fence_closer_must_match_opener_length():
    """A shorter fence run does not close a longer opener (CommonMark)."""
    body = (
        "## Steps\n\nstart\n\n"
        "````md\n"
        "```\n"
        "# still inside the 4-backtick fence\n"
        "```\n"
        "# also still inside\n"
        "````\n\n"
        "end\n\n## Tail\n\ny\n"
    )
    section = extract_section(body, "Steps")
    assert section is not None
    assert "end" in section
    assert "y" not in section


def test_extract_section_heading_inside_fence_is_not_section_start():
    """A heading-shaped line inside a fence cannot anchor a section."""
    body = (
        "intro\n\n"
        "```\n## Steps\nfenced sample, not a real section\n```\n\n"
        "## Steps\n\nreal content\n\n## After\n\nz\n"
    )
    section = extract_section(body, "Steps")
    assert section == "real content"
