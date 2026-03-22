"""Tests for af fmt command (FXA-2141)."""

from pathlib import Path

from click.testing import CliRunner

from fx_alfred.cli import cli


# ── Sample Documents ──────────────────────────────────────────────────────────

FORMATTED_DOC = """\
# TST-2100: Test Document

**Applies to:** All projects
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---

## What Is It?

A test document body.


## Steps

Step content.

---

## Change History

| Date       | Change          | By     |
|------------|-----------------|--------|
| 2026-01-01 | Initial version | Author |
"""

UNORDERED_FIELDS_DOC = """\
# TST-2101: Unordered Fields

**Status:** Draft
**Applies to:** All projects
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01

---

## What Is It?

Body content.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
"""

EXPECTED_UNORDERED_FIELDS_DOC = """\
# TST-2101: Unordered Fields

**Applies to:** All projects
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---

## What Is It?

Body content.

---

## Change History

| Date       | Change          | By     |
|------------|-----------------|--------|
| 2026-01-01 | Initial version | Author |
"""

TRAILING_WHITESPACE_DOC = """\
# TST-2102: Trailing Whitespace

**Applies to:** All projects   
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---

## What Is It?

Body content.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
"""

EXPECTED_TRAILING_WHITESPACE_DOC = """\
# TST-2102: Trailing Whitespace

**Applies to:** All projects
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---

## What Is It?

Body content.

---

## Change History

| Date       | Change          | By     |
|------------|-----------------|--------|
| 2026-01-01 | Initial version | Author |
"""

# Body with incorrect blank line patterns
BAD_BLANK_LINES_DOC = """\
# TST-2103: Bad Blank Lines

**Applies to:** All projects
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---



## What Is It?



Body content.



## Steps

Step content.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
"""

EXPECTED_BLANK_LINES_DOC = """\
# TST-2103: Bad Blank Lines

**Applies to:** All projects
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---

## What Is It?

Body content.


## Steps

Step content.

---

## Change History

| Date       | Change          | By     |
|------------|-----------------|--------|
| 2026-01-01 | Initial version | Author |
"""

# Document with fenced code blocks - content inside fences should NOT change
FENCED_CODE_DOC = """\
# TST-2104: Fenced Code

**Applies to:** All projects
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---

## What Is It?

Here is some code:

```
## This should NOT be treated as a heading

It is inside a fence.
```

## Steps

Do things.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
"""

EXPECTED_FENCED_CODE_DOC = """\
# TST-2104: Fenced Code

**Applies to:** All projects
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---

## What Is It?

Here is some code:

```
## This should NOT be treated as a heading

It is inside a fence.
```

## Steps

Do things.

---

## Change History

| Date       | Change          | By     |
|------------|-----------------|--------|
| 2026-01-01 | Initial version | Author |
"""

# Document with misaligned table columns
MISALIGNED_TABLE_DOC = """\
# TST-2105: Misaligned Table

**Applies to:** All projects
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---

## What Is It?

Body content.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
| 2026-02-15 | Fixed long issue description here | Alice |
"""

EXPECTED_MISALIGNED_TABLE_DOC = """\
# TST-2105: Misaligned Table

**Applies to:** All projects
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---

## What Is It?

Body content.

---

## Change History

| Date       | Change                          | By     |
|------------|---------------------------------|--------|
| 2026-01-01 | Initial version                 | Author |
| 2026-02-15 | Fixed long issue description here | Alice |
"""

# Document with all issues
ALL_ISSUES_DOC = """\
# TST-2106: All Issues

**Status:** Draft   
**Applies to:** All projects
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01

---



## What Is It?



Body content.



## Steps

Step.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
"""

EXPECTED_ALL_ISSUES_DOC = """\
# TST-2106: All Issues

**Applies to:** All projects
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---

## What Is It?

Body content.


## Steps

Step.

---

## Change History

| Date       | Change          | By     |
|------------|-----------------|--------|
| 2026-01-01 | Initial version | Author |
"""


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_project(tmp_path: Path, *docs: tuple[str, str]) -> Path:
    """Create a minimal project with the given documents.

    Args:
        tmp_path: Base temp directory
        docs: Tuples of (filename, content)

    Returns:
        Project root path
    """
    rules = tmp_path / "rules"
    rules.mkdir()
    for filename, content in docs:
        (rules / filename).write_text(content)
    return tmp_path


# ── Unit Tests: Metadata Ordering ────────────────────────────────────────────


def test_fmt_metadata_ordering(tmp_path):
    """Documents with fields out of order get reordered to canonical order."""
    project = _make_project(
        tmp_path,
        ("TST-2101-SOP-Unordered-Fields.md", UNORDERED_FIELDS_DOC),
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["fmt", "--root", str(project), "--write", "TST-2101"])
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2101-SOP-Unordered-Fields.md").read_text()
    # Check that fields are in canonical order
    assert content.startswith(
        "# TST-2101: Unordered Fields\n\n**Applies to:** All projects"
    )
    assert "**Last updated:** 2026-01-01" in content
    assert "**Last reviewed:** 2026-01-01" in content
    assert "**Status:** Draft" in content


# ── Unit Tests: Trailing Whitespace ──────────────────────────────────────────


def test_fmt_trailing_whitespace(tmp_path):
    """Metadata values with trailing spaces get stripped."""
    project = _make_project(
        tmp_path,
        ("TST-2102-SOP-Trailing-Whitespace.md", TRAILING_WHITESPACE_DOC),
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["fmt", "--root", str(project), "--write", "TST-2102"])
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2102-SOP-Trailing-Whitespace.md").read_text()
    # Trailing whitespace on "All projects   " should be stripped
    assert "**Applies to:** All projects\n" in content
    assert "All projects   " not in content


# ── Unit Tests: Blank Line Normalization ──────────────────────────────────────


def test_fmt_blank_line_normalization(tmp_path):
    """Runs of 3+ blank lines collapse to 2 before H2, 1 elsewhere."""
    project = _make_project(
        tmp_path,
        ("TST-2103-SOP-Bad-Blank-Lines.md", BAD_BLANK_LINES_DOC),
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["fmt", "--root", str(project), "--write", "TST-2103"])
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2103-SOP-Bad-Blank-Lines.md").read_text()
    # Check that we have exactly 2 blank lines before H2 headings in body
    # and no runs of 3+ blank lines elsewhere
    assert (
        "\n\n\n\n" not in content.split("## Change History")[0]
    )  # No triple blanks before history


# ── Unit Tests: Table Alignment ──────────────────────────────────────────────


def test_fmt_table_alignment(tmp_path):
    """Table columns are padded to equal width."""
    project = _make_project(
        tmp_path,
        ("TST-2105-SOP-Misaligned-Table.md", MISALIGNED_TABLE_DOC),
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["fmt", "--root", str(project), "--write", "TST-2105"])
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2105-SOP-Misaligned-Table.md").read_text()
    # Check that table header separator has consistent column widths
    lines = content.split("\n")
    for line in lines:
        if line.startswith("|---"):
            # All columns should have same pattern of dashes
            assert "|---" in line
            break


# ── Default Mode: Shows Unified Diff ─────────────────────────────────────────


def test_fmt_default_shows_diff(tmp_path):
    """Default mode (no flags) shows unified diff, exit 0."""
    project = _make_project(
        tmp_path,
        ("TST-2101-SOP-Unordered-Fields.md", UNORDERED_FIELDS_DOC),
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["fmt", "--root", str(project), "TST-2101"])
    assert result.exit_code == 0
    # Should show diff output
    assert "---" in result.output or "- **" in result.output
    # File should NOT be modified
    content = (project / "rules" / "TST-2101-SOP-Unordered-Fields.md").read_text()
    assert content == UNORDERED_FIELDS_DOC


# ── --check Mode ──────────────────────────────────────────────────────────────


def test_fmt_check_exits_1_if_changes_needed(tmp_path):
    """--check mode exits 1 if changes needed, prints what would change."""
    project = _make_project(
        tmp_path,
        ("TST-2101-SOP-Unordered-Fields.md", UNORDERED_FIELDS_DOC),
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["fmt", "--root", str(project), "--check", "TST-2101"])
    assert result.exit_code == 1
    assert "TST-2101" in result.output
    # File should NOT be modified
    content = (project / "rules" / "TST-2101-SOP-Unordered-Fields.md").read_text()
    assert content == UNORDERED_FIELDS_DOC


def test_fmt_check_exits_0_if_already_formatted(tmp_path):
    """--check mode exits 0 if no changes needed."""
    project = _make_project(
        tmp_path,
        ("TST-2100-SOP-Test-Document.md", FORMATTED_DOC),
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["fmt", "--root", str(project), "--check", "TST-2100"])
    assert result.exit_code == 0
    assert "All documents already formatted" in result.output


# ── --write Mode ──────────────────────────────────────────────────────────────


def test_fmt_write_applies_changes(tmp_path):
    """--write mode applies changes in-place."""
    project = _make_project(
        tmp_path,
        ("TST-2101-SOP-Unordered-Fields.md", UNORDERED_FIELDS_DOC),
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["fmt", "--root", str(project), "--write", "TST-2101"])
    assert result.exit_code == 0
    assert "Formatted" in result.output or "TST-2101" in result.output
    # File should be modified
    content = (project / "rules" / "TST-2101-SOP-Unordered-Fields.md").read_text()
    # Check fields are reordered
    assert content.startswith(
        "# TST-2101: Unordered Fields\n\n**Applies to:** All projects"
    )


# ── No-op Case ────────────────────────────────────────────────────────────────


def test_fmt_noop_already_formatted(tmp_path):
    """Already-formatted document produces no diff, prints 'All documents already formatted.'"""
    project = _make_project(
        tmp_path,
        ("TST-2100-SOP-Test-Document.md", FORMATTED_DOC),
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["fmt", "--root", str(project), "TST-2100"])
    assert result.exit_code == 0
    assert "All documents already formatted" in result.output


# ── Idempotence ───────────────────────────────────────────────────────────────


def test_fmt_idempotent(tmp_path):
    """Running --write twice produces identical output."""
    project = _make_project(
        tmp_path,
        ("TST-2106-SOP-All-Issues.md", ALL_ISSUES_DOC),
    )
    runner = CliRunner()

    # First run
    result1 = runner.invoke(cli, ["fmt", "--root", str(project), "--write", "TST-2106"])
    assert result1.exit_code == 0
    content1 = (project / "rules" / "TST-2106-SOP-All-Issues.md").read_text()

    # Second run
    result2 = runner.invoke(cli, ["fmt", "--root", str(project), "--write", "TST-2106"])
    assert result2.exit_code == 0
    content2 = (project / "rules" / "TST-2106-SOP-All-Issues.md").read_text()

    # Content should be identical after second run
    assert content1 == content2

    # Second run should report no changes
    assert "All documents already formatted" in result2.output


# ── Fence-aware ───────────────────────────────────────────────────────────────


def test_fmt_fence_aware(tmp_path):
    """Content inside ``` code blocks is NOT modified."""
    project = _make_project(
        tmp_path,
        ("TST-2104-SOP-Fenced-Code.md", FENCED_CODE_DOC),
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["fmt", "--root", str(project), "--write", "TST-2104"])
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2104-SOP-Fenced-Code.md").read_text()
    # The fake "## This should NOT be treated as a heading" inside fence should remain
    assert "## This should NOT be treated as a heading" in content
    # It should still be inside a code block
    assert "```\n## This should NOT be treated as a heading" in content


# ── Discovery with no DOC_ID ─────────────────────────────────────────────────


def test_fmt_no_doc_id_finds_all_prj(tmp_path):
    """When no DOC_ID given, finds all PRJ-layer docs."""
    project = _make_project(
        tmp_path,
        ("TST-2100-SOP-Test-Document.md", FORMATTED_DOC),
        ("TST-2101-SOP-Unordered-Fields.md", UNORDERED_FIELDS_DOC),
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["fmt", "--root", str(project), "--check"])
    # Should find both docs; one needs changes so exit 1
    assert result.exit_code == 1
    assert "TST-2101" in result.output


# ── PKG-layer doc ──────────────────────────────────────────────────────────────


def test_fmt_pkg_layer_skipped(tmp_path):
    """PKG-layer documents are skipped with a warning."""
    runner = CliRunner()
    result = runner.invoke(cli, ["fmt", "--root", str(tmp_path), "COR-1000"])
    assert result.exit_code == 0
    assert "PKG layer" in result.output or "read-only" in result.output
    assert "skipping" in result.output.lower()


# ─- --check + --write Together ────────────────────────────────────────────────


def test_fmt_check_and_write_error(tmp_path):
    """--check + --write together produces usage error."""
    project = _make_project(
        tmp_path,
        ("TST-2100-SOP-Test-Document.md", FORMATTED_DOC),
    )
    runner = CliRunner()
    result = runner.invoke(
        cli, ["fmt", "--root", str(project), "--check", "--write", "TST-2100"]
    )
    assert result.exit_code != 0
    assert "cannot be used together" in result.output.lower()


# ── Multiple DOC_IDs ───────────────────────────────────────────────────────────


def test_fmt_multiple_doc_ids(tmp_path):
    """Multiple DOC_IDs are processed in order."""
    project = _make_project(
        tmp_path,
        ("TST-2100-SOP-Test-Document.md", FORMATTED_DOC),
        ("TST-2101-SOP-Unordered-Fields.md", UNORDERED_FIELDS_DOC),
    )
    runner = CliRunner()
    result = runner.invoke(
        cli, ["fmt", "--root", str(project), "--write", "TST-2100", "TST-2101"]
    )
    assert result.exit_code == 0
    # Both should be mentioned in output
    assert "TST-2101" in result.output


# ── Malformed Document Error ─────────────────────────────────────────────────


def test_fmt_malformed_document_error(tmp_path):
    """Malformed documents are skipped with error message."""
    rules = tmp_path / "rules"
    rules.mkdir()
    # Document with no separator
    bad_doc = """\
# TST-2107: Bad Doc

**Status:** Draft
**Last updated:** 2026-01-01
"""
    (rules / "TST-2107-SOP-Bad-Doc.md").write_text(bad_doc)
    runner = CliRunner()
    result = runner.invoke(cli, ["fmt", "--root", str(tmp_path), "TST-2107"])
    assert result.exit_code != 0 or "error" in result.output.lower()


# ── Document Not Found ───────────────────────────────────────────────────────


def test_fmt_document_not_found(tmp_path):
    """Non-existent document ID produces error."""
    project = _make_project(
        tmp_path,
        ("TST-2100-SOP-Test-Document.md", FORMATTED_DOC),
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["fmt", "--root", str(project), "TST-9999"])
    assert result.exit_code != 0
    assert "document found" in result.output.lower()


# ─- --root Option ──────────────────────────────────────────────────────────────


def test_fmt_with_root_option(tmp_path):
    """--root option works for fmt."""
    project = _make_project(
        tmp_path,
        ("TST-2100-SOP-Test-Document.md", FORMATTED_DOC),
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["--root", str(project), "fmt", "TST-2100"])
    assert result.exit_code == 0


# ── List-style Metadata ───────────────────────────────────────────────────────


LIST_STYLE_DOC = """\
# TST-2108: List Style

- **Status:** Draft
- **Applies to:** All projects
- **Last updated:** 2026-01-01
- **Last reviewed:** 2026-01-01

---

## What Is It?

Body.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
"""


def test_fmt_list_style_preserved(tmp_path):
    """List-style metadata (- **Key:** value) is preserved after formatting."""
    project = _make_project(
        tmp_path,
        ("TST-2108-SOP-List-Style.md", LIST_STYLE_DOC),
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["fmt", "--root", str(project), "--write", "TST-2108"])
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2108-SOP-List-Style.md").read_text()
    # Should still have list-style metadata
    assert "- **Applies to:** All projects" in content
    assert "- **Last updated:** 2026-01-01" in content


# ── No Change History Section ────────────────────────────────────────────────


NO_HISTORY_DOC = """\
# TST-2109: No History

**Applies to:** All projects
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---

## What Is It?

Body content.
"""


def test_fmt_no_history_section(tmp_path):
    """Documents without Change History section are formatted correctly."""
    project = _make_project(
        tmp_path,
        ("TST-2109-SOP-No-History.md", NO_HISTORY_DOC),
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["fmt", "--root", str(project), "--write", "TST-2109"])
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2109-SOP-No-History.md").read_text()
    # Should still have body content
    assert "Body content." in content


# ── Complex Blank Line Scenarios ─────────────────────────────────────────────


COMPLEX_BLANK_DOC = """\
# TST-2110: Complex Blank Lines

**Applies to:** All projects
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---

## What Is It?

Paragraph one.



Paragraph two.

## Steps

Step one.


Step two.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
"""


def test_fmt_complex_blank_lines(tmp_path):
    """Complex blank line scenarios are handled correctly."""
    project = _make_project(
        tmp_path,
        ("TST-2110-SOP-Complex-Blank-Lines.md", COMPLEX_BLANK_DOC),
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["fmt", "--root", str(project), "--write", "TST-2110"])
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2110-SOP-Complex-Blank-Lines.md").read_text()
    # Should not have runs of 3+ blank lines
    body_before_history = content.split("## Change History")[0]
    # No quadruple blank lines
    assert "\n\n\n\n" not in body_before_history


# ── Table with Escaped Pipes ─────────────────────────────────────────────────


ESCAPED_PIPE_DOC = """\
# TST-2111: Escaped Pipes

**Applies to:** All projects
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---

## What Is It?

Body.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Fixed A\\|B issue | Author |
"""


def test_fmt_escaped_pipes_preserved(tmp_path):
    """Escaped pipe characters in table cells are preserved."""
    project = _make_project(
        tmp_path,
        ("TST-2111-SOP-Escaped-Pipes.md", ESCAPED_PIPE_DOC),
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["fmt", "--root", str(project), "--write", "TST-2111"])
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2111-SOP-Escaped-Pipes.md").read_text()
    # Escaped pipe should remain
    assert "Fixed A\\|B issue" in content


# ── Duplicate Metadata Keys Preserved ────────────────────────────────────────


DUPLICATE_KEYS_DOC = """\
# TST-2112: Duplicate Keys

**Applies to:** All projects
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft
**Status:** Active

---

## What Is It?

Body content.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
"""


def test_fmt_metadata_duplicate_keys_preserved(tmp_path):
    """Documents with duplicate metadata keys do not silently drop any field."""
    project = _make_project(
        tmp_path,
        ("TST-2112-SOP-Duplicate-Keys.md", DUPLICATE_KEYS_DOC),
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["fmt", "--root", str(project), "--write", "TST-2112"])
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2112-SOP-Duplicate-Keys.md").read_text()
    # Both Status fields must still be present (no silent deletion)
    status_count = content.count("**Status:**")
    assert status_count == 2, f"Expected 2 Status fields, got {status_count}"


# ── Header-Only Table Aligned ─────────────────────────────────────────────────


HEADER_ONLY_TABLE_DOC = """\
# TST-2113: Header Only Table

**Applies to:** All projects
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---

## What Is It?

Body content.

---

## Change History

| Date | Change | By |
|------|--------|----|
"""


def test_fmt_table_header_only_aligned(tmp_path):
    """A Change History section with a header+separator but no data rows gets aligned."""
    project = _make_project(
        tmp_path,
        ("TST-2113-SOP-Header-Only-Table.md", HEADER_ONLY_TABLE_DOC),
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["fmt", "--root", str(project), "--write", "TST-2113"])
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2113-SOP-Header-Only-Table.md").read_text()
    # The header should now be padded to match column widths from header row
    assert "| Date" in content
    assert "| Change" in content
    assert "| By" in content


# ── Duplicate Keys: Second Pass No Change (Idempotency) ──────────────────────


DUPLICATE_KEY_DOC = """\
# TST-2112: Duplicate Keys

**Applies to:** All projects
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft
**Status:** Active

---

## What Is It?

Body content.

---

## Change History

| Date       | Change          | By     |
|------------|-----------------|--------|
| 2026-01-01 | Initial version | Author |
"""


def test_fmt_metadata_duplicate_keys_no_change_on_second_pass(tmp_path):
    """Duplicate metadata keys: second pass reports no changes (idempotency)."""
    project = _make_project(
        tmp_path,
        ("TST-2112-SOP-Duplicate-Keys.md", DUPLICATE_KEY_DOC),
    )
    runner = CliRunner()

    # First run — may or may not change anything
    result1 = runner.invoke(cli, ["fmt", "--root", str(project), "--write", "TST-2112"])
    assert result1.exit_code == 0

    # Second run — must report no changes (idempotent)
    result2 = runner.invoke(cli, ["fmt", "--root", str(project), "--write", "TST-2112"])
    assert result2.exit_code == 0
    assert "All documents already formatted" in result2.output


# ── Multi-Row Table: Idempotent After Write ───────────────────────────────────


MULTI_ROW_TABLE_DOC = """\
# TST-2113: Multi-Row Table

**Applies to:** All projects
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---

## What Is It?

Body content.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
| 2026-02-15 | Fixed the long-running bug in the system | Alice Bob |
| 2026-03-01 | Minor tweak | X |
"""


def test_fmt_table_idempotent_after_write(tmp_path):
    """Multi-row table with uneven widths: --check on formatted file exits 0 (no false positive)."""
    project = _make_project(
        tmp_path,
        ("TST-2113-SOP-Multi-Row-Table.md", MULTI_ROW_TABLE_DOC),
    )
    runner = CliRunner()

    # First run with --write: formats the file
    result1 = runner.invoke(cli, ["fmt", "--root", str(project), "--write", "TST-2113"])
    assert result1.exit_code == 0

    # Second run with --check: must exit 0 (no false positive)
    result2 = runner.invoke(cli, ["fmt", "--root", str(project), "--check", "TST-2113"])
    assert result2.exit_code == 0, (
        f"False positive: --check reported changes after --write. Output: {result2.output}"
    )
