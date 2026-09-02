"""Tests for af update command (PRP-2104)."""

import os
import sys

import click
import pytest


from pathlib import Path

from click.testing import CliRunner

from fx_alfred.cli import cli
from fx_alfred.commands.update_cmd import _rename_case_only


pytestmark = [pytest.mark.cli, pytest.mark.integration]

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


def test_update_history_ignores_fenced_change_history_example(tmp_path, monkeypatch):
    """Append history to the real table, not a fenced example table."""
    project = _make_project(
        tmp_path,
        """# TST-2100: Test Document

**Applies to:** All projects
**Status:** Draft
**Last updated:** 2026-01-01

---

## What Is It?

Example:

```markdown
## Change History

| Date | Change | By |
|------|--------|----|
| 1999-01-01 | Fenced example | Nobody |
```

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
""",
    )
    monkeypatch.chdir(project)
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--history", "Real change", "--by", "Frank"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    content = (project / "rules" / "TST-2100-SOP-Test-Document.md").read_text()
    assert content.rfind("## Change History") < content.rfind("Real change")
    assert content.count("| 1999-01-01 | Fenced example | Nobody |") == 1


# ── PRJ layer: rename ───────────────────────────────────────────────────────


def test_update_rename_case_only_title(tmp_path, monkeypatch):
    """Case-only title rename succeeds on case-insensitive and case-sensitive filesystems.

    On case-insensitive filesystems (macOS APFS), a rename that changes
    only letter case (e.g., ``Four Col`` to ``FOUR COL``) must not falsely
    trigger the collision guard.  The guard uses ``os.path.samefile()`` to
    distinguish the same file (same inode) from a genuine collision at a
    different inode.
    """
    # Detect filesystem case-sensitivity (diagnostic only — no skip)
    probe = tmp_path / "case_probe.tmp"
    probe.write_text("x")
    fs_case_insensitive = (tmp_path / "CASE_PROBE.tmp").exists()

    doc_content = """\
# TST-2100: Four Col

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
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "TST-2100-SOP-Four-Col.md").write_text(doc_content)

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--title", "FOUR COL", "-y"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, (
        f"Case-only rename failed (FS case-insensitive={fs_case_insensitive}):\n"
        f"{result.output}"
    )
    new_path = rules / "TST-2100-SOP-FOUR-COL.md"
    assert new_path.exists()
    content = new_path.read_text()
    assert "# TST-2100: FOUR COL" in content

    # Assert the directory entry carries the new casing (not just that
    # .exists() resolved case-insensitively).  On case-insensitive
    # filesystems the single entry for this file must show the new casing;
    # on case-sensitive filesystems the old-case entry must be gone.
    names = [p.name for p in rules.iterdir()]
    assert "TST-2100-SOP-FOUR-COL.md" in names
    assert "TST-2100-SOP-Four-Col.md" not in names


def test_update_rename_case_only_simulated(tmp_path, monkeypatch):
    """Case-only rename takes the _rename_case_only path on ANY filesystem.

    The case-insensitive-FS detection (``_is_same_file``) can never return
    True on case-sensitive filesystems (ext4 CI runners), so the guarded
    rename path is never exercised there.  Monkeypatching ``_is_same_file``
    to True simulates a case-insensitive filesystem and drives the
    ``case_only`` branch deterministically on every platform.
    """
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "TST-2100-SOP-Four-Col.md").write_text(SAMPLE_DOC)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "fx_alfred.commands.update_cmd._is_same_file", lambda a, b: True
    )

    result = CliRunner().invoke(
        cli,
        ["update", "TST-2100", "--title", "FOUR COL", "-y"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    names = [p.name for p in rules.iterdir()]
    assert "TST-2100-SOP-FOUR-COL.md" in names
    assert "TST-2100-SOP-Four-Col.md" not in names
    assert (
        "Renamed TST-2100-SOP-Four-Col.md -> TST-2100-SOP-FOUR-COL.md" in result.output
    )


def test_rename_case_only_tmp_collision(tmp_path):
    """_rename_case_only refuses when its temporary path already exists."""
    file_path = tmp_path / "TST-2100-SOP-Four-Col.md"
    file_path.write_text(SAMPLE_DOC)
    new_file_path = tmp_path / "TST-2100-SOP-FOUR-COL.md"
    tmp_guard = tmp_path / f"{new_file_path.name}.{os.getpid()}.casefix.tmp"
    tmp_guard.write_text("leftover")

    with pytest.raises(click.ClickException, match="Temporary rename path exists"):
        _rename_case_only(file_path, new_file_path)

    assert file_path.read_text() == SAMPLE_DOC
    assert tmp_guard.read_text() == "leftover"


def test_rename_case_only_rollback_restores_original(tmp_path, monkeypatch):
    """A failed second rename restores the original filename."""
    file_path = tmp_path / "TST-2100-SOP-Four-Col.md"
    file_path.write_text(SAMPLE_DOC)
    new_file_path = tmp_path / "TST-2100-SOP-FOUR-COL.md"

    real_rename = Path.rename

    def failing_rename(self, target):
        if Path(str(target)).name == new_file_path.name:
            raise OSError("simulated rename failure")
        return real_rename(self, target)

    monkeypatch.setattr(Path, "rename", failing_rename)

    with pytest.raises(click.ClickException, match="restored original path"):
        _rename_case_only(file_path, new_file_path)

    names = [p.name for p in tmp_path.iterdir()]
    assert "TST-2100-SOP-Four-Col.md" in names
    assert "TST-2100-SOP-FOUR-COL.md" not in names
    assert not any(n.endswith(".casefix.tmp") for n in names)
    assert file_path.read_text() == SAMPLE_DOC


def test_rename_case_only_rollback_failure_keeps_tmp(tmp_path, monkeypatch):
    """If the rollback rename also fails, the file stays at the tmp path."""
    file_path = tmp_path / "TST-2100-SOP-Four-Col.md"
    file_path.write_text(SAMPLE_DOC)
    new_file_path = tmp_path / "TST-2100-SOP-FOUR-COL.md"

    real_rename = Path.rename

    def failing_rename(self, target):
        # First hop (original -> tmp) succeeds; every later rename fails.
        if Path(str(self)).name != file_path.name:
            raise OSError("simulated rename failure")
        return real_rename(self, target)

    monkeypatch.setattr(Path, "rename", failing_rename)

    with pytest.raises(click.ClickException, match="remains at temporary path"):
        _rename_case_only(file_path, new_file_path)

    names = [p.name for p in tmp_path.iterdir()]
    casefix = [n for n in names if n.endswith(".casefix.tmp")]
    assert len(casefix) == 1
    assert "TST-2100-SOP-Four-Col.md" not in names
    assert "TST-2100-SOP-FOUR-COL.md" not in names
    assert (tmp_path / casefix[0]).read_text() == SAMPLE_DOC


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


def test_update_rename_file_collision(tmp_path, monkeypatch):
    """Rename fails when target path already exists as a file (different inode).

    The existing ``test_update_rename_conflict`` blocks with a directory.
    This test verifies the collision guard also catches a genuine
    file-vs-file collision — two different inodes at the same path.
    The scanner is monkeypatched to return only the source document so
    the colliding target file does not cause ambiguity during resolution.
    """
    from fx_alfred.core.scanner import scan_documents

    project = _make_project(tmp_path)
    rules = project / "rules"

    # Resolve doc A before creating the colliding file
    monkeypatch.chdir(project)
    docs = scan_documents(project)
    doc_a = [d for d in docs if d.prefix == "TST" and d.acid == "2100"][0]

    # Create a genuine file (not a directory) at the rename target path
    target = rules / "TST-2100-SOP-Beta-Doc.md"
    target.write_text("colliding file content")

    # Monkeypatch the scanner so the colliding file is invisible to doc resolution
    monkeypatch.setattr(
        "fx_alfred.commands.update_cmd.scan_or_fail",
        lambda ctx: [doc_a],
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--title", "Beta Doc", "-y"],
        catch_exceptions=False,
    )

    assert result.exit_code != 0
    assert "Target path already exists" in result.output
    # Source file still exists with original content
    source = rules / "TST-2100-SOP-Test-Document.md"
    assert source.exists()
    assert "TST-2100: Test Document" in source.read_text()
    # Colliding file untouched
    assert target.read_text() == "colliding file content"


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
    """Dry run shows unified diff with ---/+++ headers and @@ hunk markers."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--status", "Active", "--dry-run"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    output = result.output
    # Unified diff markers
    assert "--- " in output
    assert "+++ " in output
    assert "@@" in output
    # Changed lines appear with unified-diff prefixes (no space after -/+)
    assert "-**Status:** Draft" in output
    assert "+**Status:** Active" in output


def test_update_dry_run_spec_shrink_shows_deletions(tmp_path, monkeypatch):
    """--spec replacing a long section with a short one shows deleted lines.

    The old hand-rolled zip-diff only handled the grew-longer case
    (len(new) > len(old)); shrinking updates never showed removed
    trailing lines.  Unified diff fixes this.
    """
    long_doc = """\
# TST-2100: Test Document

**Applies to:** All projects
**Status:** Draft
**Last updated:** 2026-01-01

---

## What Is It?

Line alpha.
Line beta.
Line gamma.
Line delta.
Line epsilon.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
"""
    project = _make_project(tmp_path, long_doc)
    monkeypatch.chdir(project)

    spec = tmp_path / "shrink.yaml"
    spec.write_text('sections:\n  "What Is It?": "Short replacement."\n')

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--spec", str(spec), "--dry-run"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    output = result.output

    # Unified diff markers
    assert "--- " in output
    assert "+++ " in output
    assert "@@" in output

    # Deleted lines from the old longer section MUST appear
    assert "-Line alpha." in output
    assert "-Line beta." in output
    assert "-Line gamma." in output
    # New short content appears
    assert "+Short replacement." in output


def test_update_dry_run_spec_insertion_no_cascade(tmp_path, monkeypatch):
    """--spec inserting a line mid-document does not cascade false -/+ pairs.

    The old zip(old_lines, new_lines) misaligns every subsequent pair
    after an insertion point, producing bogus -/+ for every line that
    follows.  Unified diff only shows genuinely changed lines.
    """
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)

    # Add a new metadata field that gets inserted before the --- separator
    spec = tmp_path / "insert.yaml"
    spec.write_text('metadata:\n  "Reviewed by": "Alice"\n')

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--spec", str(spec), "--dry-run"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    output = result.output

    # Unified diff markers
    assert "--- " in output
    assert "+++ " in output
    assert "@@" in output

    # Count deletion-prefixed lines (excluding the "--- " from-file header).
    # In unified diff, adding one metadata field + auto-touching Last updated
    # should produce very few deletions.  The old zip-diff would cascade and
    # show dozens of bogus -/+ pairs for every line after the insertion.
    lines = output.split("\n")
    delete_count = sum(
        1 for line in lines if line.startswith("-") and not line.startswith("---")
    )
    assert delete_count <= 2, (
        f"Expected ≤2 deletions, got {delete_count} (cascade bug).\nOutput:\n{output}"
    )

    # The new field appears
    assert "+**Reviewed by:** Alice" in output


@pytest.mark.parametrize(
    "args,old_marker,new_marker",
    [
        (
            ["update", "TST-2100", "--status", "Active", "--dry-run"],
            "-**Status:** Draft",
            "+**Status:** Active",
        ),
        (
            [
                "update",
                "TST-2100",
                "--history",
                "New entry",
                "--by",
                "Tester",
                "--dry-run",
            ],
            None,  # no specific deletion expected
            "+|",  # the appended history row
        ),
    ],
)
def test_update_dry_run_unified_format(
    tmp_path, monkeypatch, args, old_marker, new_marker
):
    """Dry-run through --status / --history produces unified diff format.

    Both paths share the same dry-run branch in update_cmd.
    """
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(cli, args, catch_exceptions=False)
    assert result.exit_code == 0
    output = result.output

    # Unified diff markers
    assert "--- " in output
    assert "+++ " in output
    assert "@@" in output

    if old_marker is not None:
        assert old_marker in output
    assert new_marker in output


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


SAMPLE_DOC_WIDE_HISTORY = """\
# SOP-2100: Test Document

**Applies to:** All projects
**Status:** Draft
**Last updated:** 2026-01-01

---

## What Is It?

A test document body.

---

## Change History

| Date | Change | By | Reviewer | Evidence |
|------|--------|----|----------|----------|
| 2026-01-01 | Initial version | Author | GLM | PR #260 |
"""


def test_update_history_append_preserves_existing_wide_rows(tmp_path, monkeypatch):
    """Appending history must not collapse existing rows to the first three cells."""
    from datetime import date

    project = _make_project(tmp_path, SAMPLE_DOC_WIDE_HISTORY)
    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--history", "Follow-up entry", "--by", "Frank"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (project / "rules" / "TST-2100-SOP-Test-Document.md").read_text()
    assert "| 2026-01-01 | Initial version | Author | GLM | PR #260 |" in content
    assert f"| {date.today().isoformat()} | Follow-up entry | Frank |" in content


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


def test_update_status_preserves_metadata_comment(tmp_path, monkeypatch):
    """Updating Status must not erase non-field lines in the metadata block."""
    doc = (
        "# TST-2100: Test Document\n"
        "\n"
        "**Applies to:** All projects\n"
        "**Status:** Draft\n"
        "<!-- reviewer note -->\n"
        "**Last updated:** 2026-01-01\n"
        "\n"
        "---\n"
        "\n"
        "## What Is It?\n"
        "\n"
        "A test document body.\n"
    )
    project = _make_project(tmp_path, doc)
    monkeypatch.chdir(project)
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--status", "Active"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    content = (project / "rules" / "TST-2100-SOP-Test-Document.md").read_text()
    assert "<!-- reviewer note -->\n**Last updated:**" in content


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


# ── Permission preservation (FXA-274) ───────────────────────────────────────


@pytest.mark.skipif(
    sys.platform == "win32", reason="permission bits not portable on Windows"
)
def test_update_preserves_file_permissions(tmp_path, monkeypatch):
    """af update preserves the document file's permission bits (FXA-274).

    Regression: atomic_write uses tempfile.mkstemp (mode 0o600); os.replace
    keeps that mode, silently narrowing a 0o664/0o644 doc to owner-only.
    """
    project = _make_project(tmp_path)
    doc_path = project / "rules" / "TST-2100-SOP-Test-Document.md"
    doc_path.chmod(0o664)
    assert (doc_path.stat().st_mode & 0o777) == 0o664  # precondition

    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--status", "Active"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    content = doc_path.read_text()
    assert "**Status:** Active" in content
    mode = doc_path.stat().st_mode
    assert (mode & 0o777) == 0o664, f"Expected 0o664, got {oct(mode & 0o777)}"


# ── Fix: Status change triggers reindex (FXA-270) ────────────────────────────


def _prebuild_index(runner: CliRunner) -> None:
    """Pre-build the PRJ index so we can verify it gets updated."""
    result = runner.invoke(cli, ["index"], catch_exceptions=False)
    assert result.exit_code == 0, f"af index failed: {result.output}"


def test_update_status_triggers_reindex(tmp_path, monkeypatch):
    """af update --status Active reindexes: index row shows new status (regression guard)."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()

    # Pre-build the index (initial Status: Draft)
    _prebuild_index(runner)

    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--status", "Active"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    index_path = project / "rules" / "TST-0000-REF-Document-Index.md"
    index_content = index_path.read_text()
    assert "| 2100 | SOP | Test Document | Active |" in index_content


def test_update_spec_status_triggers_reindex(tmp_path, monkeypatch):
    """--spec file patching metadata Status triggers reindex.

    The spec path merges spec_field_updates into field_updates;
    when 'Status' is in that merged dict, the index must refresh.
    """
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()

    # Pre-build the index (initial Status: Draft)
    _prebuild_index(runner)

    spec = tmp_path / "patch.yaml"
    spec.write_text("metadata:\n  Status: Active\n")

    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--spec", str(spec)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    index_path = project / "rules" / "TST-0000-REF-Document-Index.md"
    index_content = index_path.read_text()
    assert "| 2100 | SOP | Test Document | Active |" in index_content


def test_update_field_status_triggers_reindex(tmp_path, monkeypatch):
    """--field Status triggers reindex.

    The --field option populates cli_field_updates under 'Status';
    the merged field_updates dict should trigger the same reindex
    path as --status.
    """
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()

    # Pre-build the index (initial Status: Draft)
    _prebuild_index(runner)

    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--field", "Status", "Active"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    index_path = project / "rules" / "TST-0000-REF-Document-Index.md"
    index_content = index_path.read_text()
    assert "| 2100 | SOP | Test Document | Active |" in index_content


def test_update_dry_run_status_does_not_reindex(tmp_path, monkeypatch):
    """--dry-run --status Active never reindexes (byte-compare before/after)."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    runner = CliRunner()

    # Pre-build the index
    _prebuild_index(runner)

    index_path = project / "rules" / "TST-0000-REF-Document-Index.md"
    before = index_path.read_bytes()

    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--status", "Active", "--dry-run"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    after = index_path.read_bytes()
    assert before == after, "dry-run must not modify the index file"


def test_update_rename_and_status_calls_invoke_index_once(tmp_path, monkeypatch):
    """Combined rename + status update triggers invoke_index_update exactly once.

    Both a title change and a status change independently qualify for
    reindex, but the command must not call invoke_index_update twice.
    """
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)

    # Counting wrapper that delegates to the real invoke_index_update
    real_invoke = __import__(
        "fx_alfred.commands._helpers", fromlist=["invoke_index_update"]
    ).invoke_index_update
    call_count = 0

    def counting_wrapper(ctx):
        nonlocal call_count
        call_count += 1
        real_invoke(ctx)

    monkeypatch.setattr(
        "fx_alfred.commands.update_cmd.invoke_index_update",
        counting_wrapper,
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--title", "New Name", "--status", "Active", "-y"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert call_count == 1, f"Expected 1 call to invoke_index_update, got {call_count}"


def test_update_usr_status_does_not_reindex(tmp_path, monkeypatch):
    """USR-layer doc status update does NOT reindex any PRJ index.

    The index is a PRJ-layer artifact; USR-layer changes must not touch it.
    """
    project, _user_alfred = _make_usr_project(tmp_path)
    monkeypatch.chdir(project)

    call_count = 0

    def counting_wrapper(ctx):
        nonlocal call_count
        call_count += 1

    monkeypatch.setattr(
        "fx_alfred.commands.update_cmd.invoke_index_update",
        counting_wrapper,
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--status", "Active"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert call_count == 0, (
        f"Expected 0 calls to invoke_index_update for USR doc, got {call_count}"
    )


# ── Spec-file validation and title edge cases (coverage-completing) ──────────


def test_update_spec_rejects_non_mapping(tmp_path, monkeypatch):
    """A spec file whose root is not a YAML mapping is a friendly error."""
    project = _make_project(tmp_path)
    spec = tmp_path / "spec.yml"
    spec.write_text("- just\n- a list\n", encoding="utf-8")
    monkeypatch.chdir(project)
    result = CliRunner().invoke(
        cli, ["update", "TST-2100", "--spec", str(spec)], catch_exceptions=False
    )
    assert result.exit_code != 0
    assert "YAML mapping" in result.output


def test_update_spec_rejects_non_mapping_metadata(tmp_path, monkeypatch):
    """Spec 'metadata' must itself be a mapping."""
    project = _make_project(tmp_path)
    spec = tmp_path / "spec.yml"
    spec.write_text("metadata:\n  - a list\n", encoding="utf-8")
    monkeypatch.chdir(project)
    result = CliRunner().invoke(
        cli, ["update", "TST-2100", "--spec", str(spec)], catch_exceptions=False
    )
    assert result.exit_code != 0
    assert "'metadata' must be a mapping" in result.output


def test_update_spec_rejects_non_mapping_sections(tmp_path, monkeypatch):
    """Spec 'sections' must itself be a mapping."""
    project = _make_project(tmp_path)
    spec = tmp_path / "spec.yml"
    spec.write_text("sections: just a string\n", encoding="utf-8")
    monkeypatch.chdir(project)
    result = CliRunner().invoke(
        cli, ["update", "TST-2100", "--spec", str(spec)], catch_exceptions=False
    )
    assert result.exit_code != 0
    assert "'sections' must be a mapping" in result.output


def test_update_title_rejects_surrounding_whitespace(tmp_path, monkeypatch):
    """Leading/trailing whitespace in a new title never reaches the rename."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    result = CliRunner().invoke(
        cli, ["update", "TST-2100", "--title", " Padded ", "-y"]
    )
    assert result.exit_code != 0
    assert "leading/trailing whitespace" in result.output


def test_resolve_type_invalid_code_returns_none():
    """An unknown type code resolves to None instead of raising."""
    from fx_alfred.commands.update_cmd import _get_doc_type

    assert _get_doc_type("SOP") is not None
    assert _get_doc_type("ZZZ") is None
