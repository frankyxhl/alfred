"""Tests for af update command (PRP-2104)."""

from pathlib import Path

from click.testing import CliRunner

from fx_alfred.cli import cli

# ── Helpers ──────────────────────────────────────────────────────────────────

SAMPLE_DOC = """\
# TST-2100: Test Document

**Applies to:** All projects
**Status:** Draft
**Last updated:** 2026-01-01

---

## What Is It?

A test document body.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
"""

SAMPLE_DOC_LIST_STYLE = """\
# TST-2100: Test Document

- **Applies to:** All projects
- **Status:** Draft
- **Last updated:** 2026-01-01

---

## What Is It?

A test document body.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
"""

SAMPLE_DOC_NO_HISTORY = """\
# TST-2100: Test Document

**Applies to:** All projects
**Status:** Draft
**Last updated:** 2026-01-01

---

## What Is It?

A test document body.
"""

SAMPLE_DOC_MALFORMED_H1 = """\
Not a heading

**Status:** Draft

---

Body text
"""

SAMPLE_DOC_NO_SEPARATOR = """\
# TST-2100: Test Document

**Status:** Draft
**Last updated:** 2026-01-01
"""

SAMPLE_DOC_NO_FIELDS = """\
# TST-2100: Test Document

Some random text here

---

Body
"""


def _make_project(tmp_path: Path, content: str = SAMPLE_DOC) -> Path:
    """Create a minimal project with one PRJ doc."""
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "TST-2100-SOP-Test-Document.md").write_text(content)
    return tmp_path


def _make_usr_project(tmp_path: Path, content: str = SAMPLE_DOC) -> tuple[Path, Path]:
    """Create a project + user-layer doc. Returns (project_root, user_alfred).

    Uses fake_home created by conftest's isolate_home fixture.
    """
    project = tmp_path / "project"
    project.mkdir()
    (project / "rules").mkdir()

    # conftest creates fake_home at tmp_path / "fake_home"
    fake_home = tmp_path / "fake_home"
    user_alfred = fake_home / ".alfred"
    user_alfred.mkdir(exist_ok=True)
    (user_alfred / "TST-2100-SOP-Test-Document.md").write_text(content)
    return project, user_alfred


# ── PRJ layer: field update ──────────────────────────────────────────────────


def test_update_status_field(tmp_path, monkeypatch):
    """Update an existing Status field."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--status", "Active"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2100-SOP-Test-Document.md").read_text()
    assert "**Status:** Active" in content


def test_update_cli_status_invalid_rejected(tmp_path, monkeypatch):
    """Plain --status with invalid value must be rejected (FXA-2101)."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--status", "InvalidValue"],
    )
    assert result.exit_code != 0
    assert (
        "not allowed" in result.output.lower()
        or "not allowed" in str(result.exception).lower()
    )


def test_update_cli_status_valid_succeeds(tmp_path, monkeypatch):
    """Plain --status with valid value must succeed (FXA-2101 regression guard)."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--status", "Active"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2100-SOP-Test-Document.md").read_text()
    assert "**Status:** Active" in content


def test_update_generic_field(tmp_path, monkeypatch):
    """Update a generic metadata field via --field."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--field", "Applies to", "New scope"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2100-SOP-Test-Document.md").read_text()
    assert "**Applies to:** New scope" in content


def test_update_auto_touches_last_updated(tmp_path, monkeypatch):
    """Last updated field is auto-touched on any update."""
    from datetime import date

    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--status", "Active"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2100-SOP-Test-Document.md").read_text()
    assert f"**Last updated:** {date.today().isoformat()}" in content


def test_update_does_not_touch_date_field(tmp_path, monkeypatch):
    """Date fields (not Last updated) are not modified."""
    doc_with_date = """\
# TST-2100: Test Document

**Date:** 2025-06-15
**Status:** Draft
**Last updated:** 2026-01-01

---

## Body

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2025-06-15 | Created | Author |
"""
    project = _make_project(tmp_path, doc_with_date)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--status", "Active"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2100-SOP-Test-Document.md").read_text()
    assert "**Date:** 2025-06-15" in content


# ── PRJ layer: history append ────────────────────────────────────────────────


def test_update_append_history(tmp_path, monkeypatch):
    """Append a Change History row."""
    from datetime import date

    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--history", "Fixed typo", "--by", "Frank"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2100-SOP-Test-Document.md").read_text()
    assert f"| {date.today().isoformat()} | Fixed typo | Frank |" in content
    # Original row still exists
    assert "| 2026-01-01 | Initial version | Author |" in content


def test_update_history_default_by(tmp_path, monkeypatch):
    """Default --by is em dash."""
    from datetime import date

    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--history", "Some change"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2100-SOP-Test-Document.md").read_text()
    assert f"| {date.today().isoformat()} | Some change | \u2014 |" in content


def test_update_history_pipe_escaping(tmp_path, monkeypatch):
    """Pipe characters in history text are escaped."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--history", "A|B|C", "--by", "X|Y"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2100-SOP-Test-Document.md").read_text()
    assert "A\\|B\\|C" in content
    assert "X\\|Y" in content


# ── PRJ layer: rename ───────────────────────────────────────────────────────


def test_update_rename_with_yes(tmp_path, monkeypatch):
    """Rename document with -y flag (no confirmation prompt)."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--title", "New Name", "-y"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert not (project / "rules" / "TST-2100-SOP-Test-Document.md").exists()
    new_path = project / "rules" / "TST-2100-SOP-New-Name.md"
    assert new_path.exists()
    content = new_path.read_text()
    assert "# TST-2100: New Name" in content


def test_update_rename_auto_indexes_prj(tmp_path, monkeypatch):
    """Rename on PRJ layer triggers auto-index."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--title", "Renamed Doc", "-y"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    # Index file should exist after auto-index
    index_path = project / "rules" / "TST-0000-REF-Document-Index.md"
    assert index_path.exists()


def test_update_rename_conflict(tmp_path, monkeypatch):
    """Rename fails if target file already exists."""
    project = _make_project(tmp_path)
    rules = project / "rules"
    # Create a non-document file at the target path (won't be picked up by scanner)
    target = rules / "TST-2100-SOP-Taken-Name.md"
    target.write_text("placeholder")
    # We need a file that won't be parsed as a valid document by scanner
    # but occupies the filename. Actually the scanner will pick this up as
    # a duplicate TST-2100. Instead, manually create the target after scanning
    # would run. Better approach: rename to a name that collides with an
    # existing non-document file.
    # Simplest fix: put a non-.md file or directory at the target path.
    target.unlink()
    target.mkdir()  # directory blocks the rename
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--title", "Taken Name", "-y"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "already exists" in result.output


def test_update_rename_bad_title_path_separator(tmp_path, monkeypatch):
    """Rename rejects titles with path separators."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--title", "Bad/Title", "-y"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "path separator" in result.output.lower()


def test_update_rename_empty_title(tmp_path, monkeypatch):
    """Rename rejects empty titles."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--title", "", "-y"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "empty" in result.output.lower()


def test_update_rename_non_interactive_without_yes(tmp_path, monkeypatch):
    """Non-interactive rename without -y produces error."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()
    # CliRunner has no TTY, so stdin.isatty() returns False
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--title", "New Name"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "non-interactive" in result.output.lower()


# ── PRJ layer: dry-run ──────────────────────────────────────────────────────


def test_update_dry_run_no_write(tmp_path, monkeypatch):
    """Dry run does not modify the file."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    original = (project / "rules" / "TST-2100-SOP-Test-Document.md").read_text()
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--status", "Active", "--dry-run"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "Dry run" in result.output
    after = (project / "rules" / "TST-2100-SOP-Test-Document.md").read_text()
    assert after == original


def test_update_dry_run_shows_diff(tmp_path, monkeypatch):
    """Dry run shows what would change."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--status", "Active", "--dry-run"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "- **Status:** Draft" in result.output
    assert "+ **Status:** Active" in result.output


def test_update_dry_run_rename(tmp_path, monkeypatch):
    """Dry run for rename shows old -> new filename."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--title", "New Name", "--dry-run"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "TST-2100-SOP-Test-Document.md" in result.output
    assert "TST-2100-SOP-New-Name.md" in result.output
    # File should still have old name
    assert (project / "rules" / "TST-2100-SOP-Test-Document.md").exists()


# ── USR layer ────────────────────────────────────────────────────────────────


def test_update_usr_field(tmp_path, monkeypatch):
    """Update field on USR layer document."""
    project, user_alfred = _make_usr_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--status", "Active"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (user_alfred / "TST-2100-SOP-Test-Document.md").read_text()
    assert "**Status:** Active" in content


def test_update_usr_history(tmp_path, monkeypatch):
    """Append history on USR layer document."""
    from datetime import date

    project, user_alfred = _make_usr_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--history", "User change", "--by", "User"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (user_alfred / "TST-2100-SOP-Test-Document.md").read_text()
    assert f"| {date.today().isoformat()} | User change | User |" in content


# ── PKG layer: rejection ────────────────────────────────────────────────────


def test_update_pkg_rejected(tmp_path, monkeypatch):
    """PKG layer documents cannot be updated."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "COR-1000", "--status", "Active"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "PKG layer" in result.output
    assert "read-only" in result.output


# ── Error cases ──────────────────────────────────────────────────────────────


def test_update_field_not_found(tmp_path, monkeypatch):
    """Error when trying to update a non-existent field."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--field", "Nonexistent", "value"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "not found" in result.output


def test_update_malformed_document_bad_h1(tmp_path, monkeypatch):
    """Error on malformed H1."""
    project = _make_project(tmp_path, SAMPLE_DOC_MALFORMED_H1)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--status", "Active"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "H1 header" in result.output


def test_update_malformed_document_no_separator(tmp_path, monkeypatch):
    """Error when --- separator is missing."""
    project = _make_project(tmp_path, SAMPLE_DOC_NO_SEPARATOR)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--status", "Active"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "separator" in result.output.lower()


def test_update_malformed_document_no_fields(tmp_path, monkeypatch):
    """Error when no metadata fields are found."""
    project = _make_project(tmp_path, SAMPLE_DOC_NO_FIELDS)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--status", "Active"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "metadata" in result.output.lower()


def test_update_history_section_missing(tmp_path, monkeypatch):
    """Error when Change History section is not found."""
    project = _make_project(tmp_path, SAMPLE_DOC_NO_HISTORY)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--history", "Some change"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "Change History" in result.output


def test_update_document_not_found(tmp_path, monkeypatch):
    """Error when document identifier does not match."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-9999", "--status", "Active"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "TST-9999" in result.output


def test_update_ambiguous_identifier(tmp_path, monkeypatch):
    """Error when ACID-only matches multiple docs."""
    project = _make_project(tmp_path)
    rules = project / "rules"
    (rules / "AAA-2100-REF-Other.md").write_text("# AAA-2100: Other")
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "2100", "--status", "Active"],
    )
    assert result.exit_code != 0
    assert "Ambiguous" in result.output


def test_update_no_options(tmp_path, monkeypatch):
    """Error when no update options are provided."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "Nothing to update" in result.output


# ── Multi-option ─────────────────────────────────────────────────────────────


def test_update_multi_option(tmp_path, monkeypatch):
    """Combine --title + --history + --field in one call."""
    from datetime import date

    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "update",
            "TST-2100",
            "--title",
            "Combined Test",
            "--history",
            "Major update",
            "--by",
            "Tester",
            "--field",
            "Status",
            "Active",
            "-y",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    new_path = project / "rules" / "TST-2100-SOP-Combined-Test.md"
    assert new_path.exists()
    content = new_path.read_text()
    assert "# TST-2100: Combined Test" in content
    assert "**Status:** Active" in content
    assert f"| {date.today().isoformat()} | Major update | Tester |" in content


# ── Metadata format variants ────────────────────────────────────────────────


def test_update_list_style_metadata(tmp_path, monkeypatch):
    """Update works with list-prefixed metadata (- **Key:** value)."""
    project = _make_project(tmp_path, SAMPLE_DOC_LIST_STYLE)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--status", "Active"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2100-SOP-Test-Document.md").read_text()
    # Should preserve list style
    assert "- **Status:** Active" in content
    # Other fields should keep list style too
    assert "- **Applies to:** All projects" in content


def test_update_list_style_last_updated(tmp_path, monkeypatch):
    """Last updated auto-touch preserves list-prefix style."""
    from datetime import date

    project = _make_project(tmp_path, SAMPLE_DOC_LIST_STYLE)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--status", "Active"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2100-SOP-Test-Document.md").read_text()
    assert f"- **Last updated:** {date.today().isoformat()}" in content


# ── ACID-only lookup ─────────────────────────────────────────────────────────


def test_update_by_acid_only(tmp_path, monkeypatch):
    """Update using ACID-only identifier."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "2100", "--status", "Active"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2100-SOP-Test-Document.md").read_text()
    assert "**Status:** Active" in content


# ── --root option ────────────────────────────────────────────────────────────


def test_update_with_root_option(tmp_path):
    """--root option works for update."""
    project = _make_project(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--root", str(project), "update", "TST-2100", "--status", "Active"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2100-SOP-Test-Document.md").read_text()
    assert "**Status:** Active" in content


# ── Body preservation ────────────────────────────────────────────────────────


def test_update_preserves_body(tmp_path, monkeypatch):
    """Body content is never modified by update."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--status", "Active"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2100-SOP-Test-Document.md").read_text()
    assert "A test document body." in content


# ── Rename interactive confirmation ──────────────────────────────────────────


def test_update_rename_with_confirmation(tmp_path, monkeypatch):
    """Interactive rename with user confirming 'y'."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    # Patch the module-level _is_interactive to return True so the
    # confirmation prompt is shown instead of erroring for non-interactive.
    monkeypatch.setattr("fx_alfred.commands.update_cmd._is_interactive", lambda: True)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--title", "Confirmed Rename"],
        input="y\n",
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert (project / "rules" / "TST-2100-SOP-Confirmed-Rename.md").exists()


def test_update_rename_cancelled(tmp_path, monkeypatch):
    """Interactive rename cancelled by user."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    monkeypatch.setattr("fx_alfred.commands.update_cmd._is_interactive", lambda: True)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--title", "Cancelled Rename"],
        input="n\n",
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    # Original file still exists
    assert (project / "rules" / "TST-2100-SOP-Test-Document.md").exists()


# ── Fix 1: Escaped pipe round-trip in history rows ─────────────────────────


SAMPLE_DOC_ESCAPED_PIPE = """\
# TST-2100: Test Document

**Applies to:** All projects
**Status:** Draft
**Last updated:** 2026-01-01

---

## What Is It?

A test document body.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Fixed A\\|B issue | Author |
"""


def test_update_history_escaped_pipe_preserved(tmp_path, monkeypatch):
    """Existing history rows with escaped pipes are preserved after update."""
    from datetime import date

    project = _make_project(tmp_path, SAMPLE_DOC_ESCAPED_PIPE)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--history", "new entry"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2100-SOP-Test-Document.md").read_text()
    # The original escaped-pipe row must survive the round-trip
    assert "Fixed A\\|B issue" in content
    # The new entry was also appended
    assert f"| {date.today().isoformat()} | new entry |" in content


# ── Fix 2: Parse/render round-trip fidelity ─────────────────────────────────


def test_update_roundtrip_preserves_formatting(tmp_path, monkeypatch):
    """Only the changed field line differs; everything else is byte-identical."""
    from datetime import date

    # Document with specific formatting: blank line after H1, trailing newline
    doc = (
        "# TST-2100: Test Document\n"
        "\n"
        "**Applies to:** All projects\n"
        "**Status:** Draft\n"
        "**Last updated:** 2026-01-01\n"
        "\n"
        "---\n"
        "\n"
        "## What Is It?\n"
        "\n"
        "A test document body.\n"
        "\n"
        "---\n"
        "\n"
        "## Change History\n"
        "\n"
        "| Date | Change | By |\n"
        "|------|--------|----|\n"
        "| 2026-01-01 | Initial version | Author |\n"
    )
    project = _make_project(tmp_path, doc)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--field", "Status", "Active"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2100-SOP-Test-Document.md").read_text()

    # Build expected: only Status and Last updated lines change
    today = date.today().isoformat()
    expected = (
        "# TST-2100: Test Document\n"
        "\n"
        "**Applies to:** All projects\n"
        f"**Status:** Active\n"
        f"**Last updated:** {today}\n"
        "\n"
        "---\n"
        "\n"
        "## What Is It?\n"
        "\n"
        "A test document body.\n"
        "\n"
        "---\n"
        "\n"
        "## Change History\n"
        "\n"
        "| Date | Change | By |\n"
        "|------|--------|----|\n"
        "| 2026-01-01 | Initial version | Author |\n"
    )
    assert content == expected


def test_update_roundtrip_preserves_trailing_newline(tmp_path, monkeypatch):
    """Trailing newline in original document is preserved."""
    doc_with_newline = SAMPLE_DOC  # ends with \n
    assert doc_with_newline.endswith("\n"), "test precondition: doc ends with newline"
    project = _make_project(tmp_path, doc_with_newline)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--status", "Active"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2100-SOP-Test-Document.md").read_text()
    assert content.endswith("\n")


# ── Fix 3: Rename H1 uses type_code, not prefix ────────────────────────────


SAMPLE_DOC_TYPE_CODE = """\
# SOP-2100: Test Document

**Applies to:** All projects
**Status:** Draft
**Last updated:** 2026-01-01

---

## What Is It?

A test document body.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
"""


def test_update_rename_h1_uses_type_code(tmp_path, monkeypatch):
    """Rename H1 preserves original type_code (SOP), not prefix (TST).

    The filename pattern is PREFIX-ACID-TYPECODE-Title.md, so for
    TST-2100-SOP-Test-Document.md, prefix=TST and type_code=SOP.
    When H1 says '# SOP-2100: ...', rename must keep 'SOP-2100', not
    replace it with the prefix form 'TST-2100'.
    """
    # Use SAMPLE_DOC_TYPE_CODE whose H1 is '# SOP-2100: Test Document'
    # while filename prefix is TST (prefix != type_code).
    project = _make_project(tmp_path, SAMPLE_DOC_TYPE_CODE)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--title", "New Name", "-y"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    new_path = project / "rules" / "TST-2100-SOP-New-Name.md"
    assert new_path.exists()
    content = new_path.read_text()
    # H1 must use type_code form (SOP-2100), NOT prefix form (TST-2100)
    assert "# SOP-2100: New Name" in content
    assert "# TST-2100: New Name" not in content


def test_update_rename_h1_fallback_uses_type_code(tmp_path, monkeypatch):
    """After H1 validation tightening, a non-conforming H1 is rejected
    before rename fallback logic is reached."""
    doc_unusual_h1 = """\
# Unusual Heading Without Colon

**Applies to:** All projects
**Status:** Draft
**Last updated:** 2026-01-01

---

## What Is It?

A test document body.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
"""
    project = _make_project(tmp_path, doc_unusual_h1)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--title", "Fixed Name", "-y"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "H1 does not match expected format" in result.output


# ── Fix 1 (Round 3): H1 semantic validation ──────────────────────────────────


SAMPLE_DOC_MISMATCHED_H1 = """\
# ADR-9999: Wrong Title

**Applies to:** All projects
**Status:** Draft
**Last updated:** 2026-01-01

---

## What Is It?

A test document body.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
"""


def test_update_h1_semantic_mismatch_warns(tmp_path, monkeypatch):
    """H1 TYP/ACID mismatch with filename emits warning but update proceeds."""
    project = _make_project(tmp_path, SAMPLE_DOC_MISMATCHED_H1)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--status", "Active"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    # click.echo(err=True) is captured in result.stderr by CliRunner
    assert "Warning: H1 mismatch" in result.stderr
    assert "ADR" in result.stderr
    assert "9999" in result.stderr
    # Update still proceeds
    content = (project / "rules" / "TST-2100-SOP-Test-Document.md").read_text()
    assert "**Status:** Active" in content


# ── Fix 2 (Round 2): Malformed H1 without colon ─────────────────────────────


def test_update_malformed_h1_no_colon(tmp_path, monkeypatch):
    """H1 starting with '# ' but lacking '<TYP>-<ACID>: <Title>' format is rejected."""
    doc_bad_h1 = """\
# Unusual Heading Without Colon

**Applies to:** All projects
**Status:** Draft
**Last updated:** 2026-01-01

---

## Body
"""
    project = _make_project(tmp_path, doc_bad_h1)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--status", "Active"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "H1 does not match expected format" in result.output


# ── Fix 2 (Round 2): Rename with real type_code H1 format ───────────────────


def test_update_rename_real_type_code_format(tmp_path, monkeypatch):
    """Rename works correctly when H1 uses type_code (e.g. SOP-2100) as produced by 'af create'."""
    project = _make_project(tmp_path, SAMPLE_DOC_TYPE_CODE)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--title", "Renamed Document", "-y"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    new_path = project / "rules" / "TST-2100-SOP-Renamed-Document.md"
    assert new_path.exists()
    content = new_path.read_text()
    # H1 should preserve the type_code format from the original document
    assert "# SOP-2100: Renamed Document" in content
