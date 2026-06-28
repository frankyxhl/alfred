"""Tests for `af tag` command group (tag_cmd.py)."""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from fx_alfred.cli import cli

pytestmark = pytest.mark.cli


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def tagged_project(tmp_path):
    """Project with rules/ containing documents with **Tags:** metadata.

    Tags are prefixed with "xtag-" to avoid colliding with PKG COR doc tags,
    which are also included in all-layer scans.

    Doc inventory:
      ALF-1001-SOP  tags: xtag-alpha, xtag-common
      ALF-1002-PRP  tags: xtag-beta, xtag-common
      ALF-1003-CHG  tags: xtag-gamma, xtag-common
      ALF-1004-REF  tags: xtag-alpha
    """
    rules = tmp_path / "rules"
    rules.mkdir()

    (rules / "ALF-1001-SOP-First-SOP.md").write_text(
        "# SOP-1001: First SOP\n\n**Tags:** xtag-alpha, xtag-common\n\n---\n",
        encoding="utf-8",
    )
    (rules / "ALF-1002-PRP-A-Proposal.md").write_text(
        "# PRP-1002: A Proposal\n\n**Tags:** xtag-beta, xtag-common\n\n---\n",
        encoding="utf-8",
    )
    (rules / "ALF-1003-CHG-A-Change.md").write_text(
        "# CHG-1003: A Change\n\n**Tags:** xtag-gamma, xtag-common\n\n---\n",
        encoding="utf-8",
    )
    (rules / "ALF-1004-REF-A-Reference.md").write_text(
        "# REF-1004: A Reference\n\n**Tags:** xtag-alpha\n\n---\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def write_project(tmp_path):
    """Project with writable PRJ-layer REF documents for tag add/rm tests.

    Doc inventory:
      ALF-6001-REF  tags: xtag-existing   (single tag; fully valid for af validate)
      ALF-6002-REF  (no Tags field)
      ALF-6003-REF  tags: xtag-a, xtag-b  (multiple tags for rm-one tests)
    """
    rules = tmp_path / "rules"
    rules.mkdir()

    # ALF-6001: properly structured REF doc — passes af validate ALF-6001
    (rules / "ALF-6001-REF-Write-Test.md").write_text(
        "# REF-6001: Write Test\n\n"
        "**Applies to:** ALF project\n"
        "**Last updated:** 2026-06-28\n"
        "**Last reviewed:** 2026-06-28\n"
        "**Status:** Active\n"
        "**Tags:** xtag-existing\n\n"
        "---\n\n"
        "## What Is It?\n\n"
        "A test reference document for tag write tests.\n\n"
        "## Change History\n\n"
        "| Date | Change | By |\n"
        "|------|--------|----|",
        encoding="utf-8",
    )

    # ALF-6002: minimal REF doc with NO Tags field
    (rules / "ALF-6002-REF-No-Tags.md").write_text(
        "# REF-6002: No Tags\n\n"
        "**Applies to:** ALF project\n"
        "**Last updated:** 2026-06-28\n"
        "**Last reviewed:** 2026-06-28\n"
        "**Status:** Active\n\n"
        "---\n",
        encoding="utf-8",
    )

    # ALF-6003: REF doc with two tags (for removing one of them)
    (rules / "ALF-6003-REF-Multi-Tags.md").write_text(
        "# REF-6003: Multi Tags\n\n"
        "**Applies to:** ALF project\n"
        "**Last updated:** 2026-06-28\n"
        "**Last reviewed:** 2026-06-28\n"
        "**Status:** Active\n"
        "**Tags:** xtag-a, xtag-b\n\n"
        "---\n",
        encoding="utf-8",
    )

    return tmp_path


# ── af tag ls: list all tags with counts ──────────────────────────────────────


def test_tag_ls_lists_tags_alphabetically(tagged_project):
    """af tag ls lists all distinct tags sorted alphabetically."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["tag", "ls", "--root", str(tagged_project)], catch_exceptions=False
    )
    assert result.exit_code == 0
    lines = result.output.strip().splitlines()
    tag_names = [line.split()[0] for line in lines]
    assert tag_names == sorted(tag_names), "Tags must be sorted alphabetically"
    assert "xtag-alpha" in tag_names
    assert "xtag-beta" in tag_names
    assert "xtag-common" in tag_names
    assert "xtag-gamma" in tag_names


def test_tag_ls_shows_correct_counts(tagged_project):
    """af tag ls shows accurate usage counts per unique-to-fixture tag."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["tag", "ls", "--root", str(tagged_project)], catch_exceptions=False
    )
    assert result.exit_code == 0
    lines_map: dict[str, int] = {}
    for line in result.output.strip().splitlines():
        parts = line.split()
        if len(parts) >= 2:
            lines_map[parts[0]] = int(parts[1])

    assert lines_map["xtag-common"] == 3
    assert lines_map["xtag-alpha"] == 2
    assert lines_map["xtag-beta"] == 1
    assert lines_map["xtag-gamma"] == 1


def test_tag_ls_json(tagged_project):
    """af tag ls --json emits sorted JSON array of {tag, count}."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "ls", "--json", "--root", str(tagged_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    for item in data:
        assert "tag" in item
        assert "count" in item
        assert isinstance(item["tag"], str)
        assert isinstance(item["count"], int)
    tag_names = [item["tag"] for item in data]
    assert tag_names == sorted(tag_names)
    by_tag = {item["tag"]: item["count"] for item in data}
    assert by_tag["xtag-common"] == 3
    assert by_tag["xtag-alpha"] == 2
    assert by_tag["xtag-beta"] == 1
    assert by_tag["xtag-gamma"] == 1


# ── af tag show: list docs for a given tag ────────────────────────────────────


def test_tag_show_lists_matching_docs(tagged_project):
    """af tag show xtag-common lists all documents tagged with xtag-common."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "show", "xtag-common", "--root", str(tagged_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "ALF-1001" in result.output
    assert "ALF-1002" in result.output
    assert "ALF-1003" in result.output
    assert "ALF-1004" not in result.output


def test_tag_show_multiple_types(tagged_project):
    """af tag show xtag-common returns docs of multiple types (SOP, PRP, CHG)."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "show", "xtag-common", "--root", str(tagged_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "SOP" in result.output
    assert "PRP" in result.output
    assert "CHG" in result.output


def test_tag_show_output_format(tagged_project):
    """af tag show <name> uses same row format as af list (LABEL  PREFIX-ACID  TYPE  TITLE)."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "show", "xtag-alpha", "--root", str(tagged_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "PRJ" in result.output


def test_tag_show_case_insensitive(tagged_project):
    """Tag name matching is case-insensitive (XTAG-COMMON matches xtag-common-tagged docs)."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "show", "XTAG-COMMON", "--root", str(tagged_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "ALF-1001" in result.output
    assert "ALF-1002" in result.output
    assert "ALF-1003" in result.output


def test_tag_show_mixed_case(tagged_project):
    """Tag name matching is case-insensitive (Xtag-Common matches xtag-common-tagged docs)."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "show", "Xtag-Common", "--root", str(tagged_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "ALF-1001" in result.output


def test_tag_show_unknown_tag_no_docs(tagged_project):
    """af tag show nonexistent-tag prints 'No documents found.' when no match."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "show", "nonexistent-tag", "--root", str(tagged_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "No documents found." in result.output


def test_tag_show_json(tagged_project):
    """af tag show xtag-common --json emits same shape as af list --json."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "show", "xtag-common", "--json", "--root", str(tagged_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert len(data) == 3
    for item in data:
        assert "prefix" in item
        assert "acid" in item
        assert "type_code" in item
        assert "title" in item
        assert "source" in item
        assert "directory" in item
    acids = {item["acid"] for item in data}
    assert "1001" in acids
    assert "1002" in acids
    assert "1003" in acids


def test_tag_show_json_unknown_tag_empty_array(tagged_project):
    """af tag show nonexistent --json emits [] when no match."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "show", "nonexistent", "--json", "--root", str(tagged_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert result.output.strip() == "[]"
    assert json.loads(result.output) == []


# ── --root option ─────────────────────────────────────────────────────────────


def test_tag_root_before_subcommand(tagged_project):
    """af --root <path> tag ls works (root before subcommand)."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["--root", str(tagged_project), "tag", "ls"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "xtag-common" in result.output


def test_tag_root_after_subcommand(tagged_project):
    """af tag ls --root <path> works (root after subcommand)."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["tag", "ls", "--root", str(tagged_project)], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "xtag-alpha" in result.output


def test_tag_ls_with_root_monkeypatched(tagged_project, monkeypatch):
    """af tag ls picks up documents from the specified root."""
    monkeypatch.chdir(tagged_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["tag", "ls"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "xtag-common" in result.output
    assert "xtag-alpha" in result.output


# ── Fix 1: duplicate-tag count dedup within a single doc ─────────────────────


def test_tag_ls_dedupes_within_doc(tmp_path):
    """A doc with duplicate tags (xtag-duped, xtag-duped) counts xtag-duped only once."""
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "ALF-2001-SOP-Dedup-Test.md").write_text(
        "# SOP-2001: Dedup Test\n\n**Tags:** xtag-duped, xtag-duped\n\n---\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli, ["tag", "ls", "--root", str(tmp_path)], catch_exceptions=False
    )
    assert result.exit_code == 0
    for line in result.output.strip().splitlines():
        parts = line.split()
        if parts[0] == "xtag-duped":
            assert int(parts[1]) == 1, (
                f"Expected count 1 for xtag-duped, got {parts[1]}"
            )
            return
    pytest.fail("xtag-duped tag not found in output")


# ── Fix 2: no-arg empty branch message when docs exist but carry no tags ──────


def test_tag_ls_no_tags_prints_no_tags_found():
    """af tag ls prints 'No tags found.' when all docs carry no Tags field.

    PKG layer always provides tagged docs in integration scans, so scan_or_fail
    is mocked to isolate the zero-tag empty branch.
    """
    mock_doc = MagicMock()
    mock_doc.tags = []

    runner = CliRunner()
    with patch("fx_alfred.commands.tag_cmd.scan_or_fail", return_value=[mock_doc]):
        result = runner.invoke(cli, ["tag", "ls"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "No tags found." in result.output
    assert "No documents found." not in result.output


def test_tag_show_unknown_still_prints_no_documents_found(tmp_path):
    """af tag show <unknown> still prints 'No documents found.' (named form unchanged)."""
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "ALF-3001-SOP-No-Tags.md").write_text(
        "# SOP-3001: No Tags\n\n---\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "show", "xtag-nonexistent", "--root", str(tmp_path)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "No documents found." in result.output


# ── Fix 3: coverage gaps ──────────────────────────────────────────────────────


def test_tag_ls_doc_without_tags_field_is_absent(tmp_path):
    """A doc with no Tags field is absent from the ls listing and causes no error."""
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "ALF-4001-SOP-With-Tag.md").write_text(
        "# SOP-4001: With Tag\n\n**Tags:** xtag-present\n\n---\n",
        encoding="utf-8",
    )
    (rules / "ALF-4002-REF-No-Tag.md").write_text(
        "# REF-4002: No Tag\n\n---\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli, ["tag", "ls", "--root", str(tmp_path)], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "xtag-present" in result.output
    assert "ALF-4002" not in result.output


def test_tag_show_exact_match_not_substring(tmp_path):
    """af tag show common must NOT match a doc tagged only xtag-common (membership not substring)."""
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "ALF-5001-SOP-Tag-Test.md").write_text(
        "# SOP-5001: Tag Test\n\n**Tags:** xtag-common\n\n---\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "show", "common", "--root", str(tmp_path)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "ALF-5001" not in result.output


# ── af tag add: write tags ─────────────────────────────────────────────────────


def test_tag_add_writes_tags_to_existing(write_project):
    """af tag add ALF-6001 xtag-new adds a tag to the existing Tags field."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "add", "ALF-6001", "xtag-new", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (write_project / "rules" / "ALF-6001-REF-Write-Test.md").read_text(
        encoding="utf-8"
    )
    assert "xtag-existing" in content
    assert "xtag-new" in content
    assert "ALF-6001 tags:" in result.output


def test_tag_add_dedupes_against_existing(write_project):
    """Re-adding an existing tag is idempotent — no duplicate in Tags field."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "add", "ALF-6001", "xtag-existing", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (write_project / "rules" / "ALF-6001-REF-Write-Test.md").read_text(
        encoding="utf-8"
    )
    tag_line = next(
        (line for line in content.splitlines() if line.startswith("**Tags:**")), None
    )
    assert tag_line is not None
    # Count occurrences of xtag-existing — must be exactly 1
    assert tag_line.count("xtag-existing") == 1


def test_tag_add_creates_tags_field_when_absent(write_project):
    """af tag add on a doc with no Tags field creates the field."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "add", "ALF-6002", "xtag-new", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (write_project / "rules" / "ALF-6002-REF-No-Tags.md").read_text(
        encoding="utf-8"
    )
    assert "**Tags:** xtag-new" in content


def test_tag_add_and_validate_stays_clean(write_project):
    """After af tag add, af validate ALF-6001 reports 0 issues (exit 0)."""
    runner = CliRunner()
    # Add a controlled-vocabulary tag so there are no OV issues either
    add_result = runner.invoke(
        cli,
        ["tag", "add", "ALF-6001", "maintain", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert add_result.exit_code == 0

    validate_result = runner.invoke(
        cli,
        ["validate", "ALF-6001", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert validate_result.exit_code == 0, (
        f"af validate reported issues:\n{validate_result.output}"
    )
    assert "0 issues found" in validate_result.output


def test_tag_add_comma_separated_and_multiple_args_flatten(write_project):
    """af tag add ALF-6001 'xtag-x,xtag-y' xtag-z adds all three tags."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "tag",
            "add",
            "ALF-6001",
            "xtag-x,xtag-y",
            "xtag-z",
            "--root",
            str(write_project),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (write_project / "rules" / "ALF-6001-REF-Write-Test.md").read_text(
        encoding="utf-8"
    )
    assert "xtag-x" in content
    assert "xtag-y" in content
    assert "xtag-z" in content


# ── af tag rm: remove tags ────────────────────────────────────────────────────


def test_tag_rm_removes_single_tag_from_multi(write_project):
    """af tag rm ALF-6003 xtag-a removes xtag-a, leaving xtag-b."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "rm", "ALF-6003", "xtag-a", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (write_project / "rules" / "ALF-6003-REF-Multi-Tags.md").read_text(
        encoding="utf-8"
    )
    assert "xtag-b" in content
    assert "xtag-a" not in content


def test_tag_rm_absent_tag_is_idempotent(write_project):
    """Removing a tag not present exits 0 with a friendly message."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "rm", "ALF-6001", "xtag-nonexistent", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "xtag-nonexistent" in result.output


def test_tag_rm_last_tag_drops_field(write_project):
    """Removing the last tag removes the Tags field entirely."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "rm", "ALF-6001", "xtag-existing", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (write_project / "rules" / "ALF-6001-REF-Write-Test.md").read_text(
        encoding="utf-8"
    )
    assert "**Tags:**" not in content


# ── PKG guard ─────────────────────────────────────────────────────────────────


def test_tag_add_pkg_doc_refused(tmp_path):
    """af tag add on a PKG/COR doc is refused with a read-only error."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "add", "COR-1000", "maintain", "--root", str(tmp_path)],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "Cannot update PKG layer documents" in result.output


def test_tag_rm_pkg_doc_refused(tmp_path):
    """af tag rm on a PKG/COR doc is refused with a read-only error."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "rm", "COR-1000", "maintain", "--root", str(tmp_path)],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "Cannot update PKG layer documents" in result.output
