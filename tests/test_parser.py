"""Tests for fx_alfred.core.parser — H1_PATTERN named groups."""

import pytest


from fx_alfred.core.parser import (
    H1_PATTERN,
    extract_section,
    iter_lines_with_fence_state,
    parse_metadata,
    render_document,
)


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


def test_parse_metadata_ignores_fenced_change_history_example():
    """Fenced Change History examples must not bind the parsed history table."""
    content = (
        "# SOP-2101: Test\n\n"
        "**Applies to:** Test\n"
        "**Status:** Active\n\n"
        "---\n\n"
        "## What Is It?\n\n"
        "Example:\n\n"
        "```markdown\n"
        "## Change History\n\n"
        "| Date | Change | By |\n"
        "|------|--------|----|\n"
        "| 1999-01-01 | Fenced example | Nobody |\n"
        "```\n\n"
        "---\n\n"
        "## Change History\n\n"
        "| Date | Change | By |\n"
        "|------|--------|----|\n"
        "| 2026-01-01 | Real row | Author |\n"
    )

    parsed = parse_metadata(content)

    assert len(parsed.history_rows) == 1
    assert parsed.history_rows[0].date == "2026-01-01"
    assert parsed.history_rows[0].change == "Real row"
    assert "Fenced example" in parsed.body


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


# --- iter_lines_with_fence_state direct unit tests (FXA-2294 R1 advisory:
# glm + deepseek convergent — isolate the shared helper from its consumers) ---


def _states(text):
    return [(line, fenced) for line, fenced in iter_lines_with_fence_state(text)]


def test_fence_state_empty_and_fenceless_input():
    assert _states("") == [("", False)]
    assert _states("plain\ntext") == [("plain", False), ("text", False)]


def test_fence_state_opener_interior_closer_all_fenced():
    states = _states("a\n```\ncode\n```\nb")
    assert states == [
        ("a", False),
        ("```", True),
        ("code", True),
        ("```", True),
        ("b", False),
    ]


def test_fence_state_unclosed_fence_runs_to_end():
    states = _states("a\n```\nrest\nstays fenced")
    assert [f for _, f in states] == [False, True, True, True]


def test_fence_state_mixed_chars_do_not_cross_close():
    # A tilde line cannot close a backtick fence, and vice versa.
    backtick = _states("```\n~~~\nstill\n```\nout")
    assert [f for _, f in backtick] == [True, True, True, True, False]
    tilde = _states("~~~\n```\nstill\n~~~\nout")
    assert [f for _, f in tilde] == [True, True, True, True, False]


def test_fence_state_closer_run_length_rule():
    # 3-backtick line cannot close a 4-backtick opener; 5 can close 4.
    states = _states("````\n```\nin\n`````\nout")
    assert [f for _, f in states] == [True, True, True, True, False]


def test_fence_state_consecutive_fences_reset():
    states = _states("```\none\n```\nmid\n~~~\ntwo\n~~~\nend")
    assert [f for _, f in states] == [
        True,
        True,
        True,
        False,
        True,
        True,
        True,
        False,
    ]


def test_fence_state_blank_lines_inside_and_outside():
    states = _states("\n```\n\n```\n\nx")
    assert [f for _, f in states] == [False, True, True, True, False, False]


def test_fence_state_indented_opener_counts():
    # Openers are detected after lstrip(), matching steps.py discipline.
    states = _states("  ```\nin\n  ```\nout")
    assert [f for _, f in states] == [True, True, True, False]


def test_fence_state_short_run_is_not_a_fence():
    # Runs of 1-2 backticks (inline code) do not open a fence.
    states = _states("``\nx\n`code`\ny")
    assert [f for _, f in states] == [False, False, False, False]


# --- HistoryRow raw_line preservation (P2 bug fix) ---


def test_parse_metadata_stores_raw_line_on_history_rows():
    """parse_metadata stores the original line text in HistoryRow.raw_line.

    This is the data required for render_document to emit verbatim lines
    instead of re-rendering from stripped cell values.
    """
    content = (
        "# REF-9001: Test\n\n"
        "**Applies to:** Test\n"
        "**Status:** Active\n\n"
        "---\n\n"
        "## Change History\n\n"
        "| Date       | Change                    | By          |\n"
        "|------------|---------------------------|-------------|\n"
        "| 2026-01-01 | Initial version           | Alice       |\n"
    )
    parsed = parse_metadata(content)
    assert len(parsed.history_rows) == 1
    assert parsed.history_rows[0].raw_line == (
        "| 2026-01-01 | Initial version           | Alice       |"
    )


# --- Metadata-block raw line preservation (issue #261) ---


def test_metadata_roundtrip_preserves_comment_between_fields():
    content = (
        "# REF-9002: Test\n\n"
        "**Applies to:** Test\n"
        "<!-- reviewer note -->\n"
        "**Status:** Active\n"
        "\n---\n"
    )

    parsed = parse_metadata(content)

    assert render_document(parsed) == content


def test_metadata_roundtrip_preserves_blank_line_between_fields():
    content = "# REF-9003: Test\n\n**Applies to:** Test\n\n**Status:** Active\n\n---\n"

    parsed = parse_metadata(content)

    assert render_document(parsed) == content


def test_metadata_roundtrip_preserves_comment_and_blanks_after_last_field():
    content = (
        "# REF-9004: Test\n\n"
        "**Applies to:** Test\n"
        "**Status:** Active\n"
        "\n"
        "<!-- reviewer note -->\n"
        "\n"
        "---\n"
    )

    parsed = parse_metadata(content)

    assert render_document(parsed) == content


def test_metadata_roundtrip_preserves_consecutive_comments_before_field():
    content = (
        "# REF-9005: Test\n\n"
        "**Applies to:** Test\n"
        "<!-- note a -->\n"
        "<!-- note b -->\n"
        "\n"
        "**Status:** Active\n"
        "\n---\n"
    )

    parsed = parse_metadata(content)

    assert render_document(parsed) == content


def test_parse_metadata_history_row_retains_all_cells():
    content = (
        "# REF-9002: Wide History\n\n"
        "**Applies to:** Test\n"
        "**Status:** Active\n\n"
        "---\n\n"
        "## Change History\n\n"
        "| Date | Change | By | Reviewer | Evidence |\n"
        "|------|--------|----|----------|----------|\n"
        "| 2026-01-01 | Initial version | Alice | GLM | PR #260 |\n"
    )
    parsed = parse_metadata(content)
    row = parsed.history_rows[0]
    assert row.date == "2026-01-01"
    assert row.change == "Initial version"
    assert row.by == "Alice"
    assert row.cells == ["2026-01-01", "Initial version", "Alice", "GLM", "PR #260"]
    assert row.raw_line == "| 2026-01-01 | Initial version | Alice | GLM | PR #260 |"


def test_render_document_preserves_aligned_history_rows_verbatim():
    """render_document must round-trip aligned history table rows byte-for-byte.

    Regression: rows were always re-rendered from stripped cell values, so
    padding added by af fmt --write was silently discarded on the next write
    (af tag add / af update), leaving the doc fmt-dirty.
    """
    content = (
        "# SOP-9001: History Round-Trip\n\n"
        "**Applies to:** Test\n"
        "**Last updated:** 2026-01-01\n"
        "**Status:** Active\n\n"
        "---\n\n"
        "## Change History\n\n"
        "| Date       | Change                    | By          |\n"
        "|------------|---------------------------|-------------|\n"
        "| 2026-01-01 | Initial version           | Alice       |\n"
        "| 2026-06-28 | A much longer description | Charlie Bob |\n"
    )
    parsed = parse_metadata(content)
    rendered = render_document(parsed)
    assert rendered == content, (
        "render_document must emit aligned history rows verbatim via raw_line"
    )


def test_render_document_dirty_wide_history_row_preserves_extra_cells():
    content = (
        "# REF-9003: Dirty Wide History\n\n"
        "**Applies to:** Test\n"
        "**Status:** Active\n\n"
        "---\n\n"
        "## Change History\n\n"
        "| Date | Change | By | Reviewer | Evidence |\n"
        "|------|--------|----|----------|----------|\n"
        "| 2026-01-01 | Initial version | Alice | GLM | PR #260 |\n"
    )
    parsed = parse_metadata(content)
    row = parsed.history_rows[0]
    row.cells[1] = "Updated version"
    row.change = "Updated version"
    row.dirty = True

    rendered = render_document(parsed)
    assert "| 2026-01-01 | Updated version | Alice | GLM | PR #260 |" in rendered
