"""Tests for `af tag` command group (tag_cmd.py)."""

import json
from datetime import date
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
      ALF-6004-REF  tags: xtag-a           (old Last updated: 2025-01-01; for bump tests)
      ALF-6006-REF  (no Tags; has Custom-Field unknown opt; fully valid; for canonical-pos tests)
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

    # ALF-6004: REF doc with old Last-updated date — used by fix-4 (bump) tests.
    # Date is 2025-01-01 (clearly in the past) so bumping to today is detectable.
    (rules / "ALF-6004-REF-Date-Test.md").write_text(
        "# REF-6004: Date Test\n\n"
        "**Applies to:** ALF project\n"
        "**Last updated:** 2025-01-01\n"
        "**Last reviewed:** 2025-01-01\n"
        "**Status:** Active\n"
        "**Tags:** xtag-a\n\n"
        "---\n",
        encoding="utf-8",
    )

    # ALF-6006: fully valid REF doc with an unknown optional field but NO Tags field.
    # Custom-Field is unknown (not in KNOWN_OPTIONAL_ORDER), so sort_metadata puts
    # Tags (a known optional) BEFORE Custom-Field.  Append-at-end (current buggy
    # behaviour) puts Tags AFTER Custom-Field — giving a clear RED signal for fix-2.
    (rules / "ALF-6006-REF-Full-No-Tags.md").write_text(
        "# REF-6006: Full No Tags\n\n"
        "**Applies to:** ALF project\n"
        "**Last updated:** 2025-01-01\n"
        "**Last reviewed:** 2025-01-01\n"
        "**Status:** Active\n"
        "**Custom-Field:** custom value\n\n"
        "---\n\n"
        "## What Is It?\n\n"
        "A test reference document for canonical-position tests.\n\n"
        "## Change History\n\n"
        "| Date | Change | By |\n"
        "|------|--------|----|",
        encoding="utf-8",
    )

    # ALF-6005: REF doc with unsorted tags — used by sort/rm tests.
    # xtag-zoo > xtag-mango > xtag-apple alphabetically, so all three orderings
    # are wrong; sorted canonical form is xtag-apple, xtag-mango, xtag-zoo.
    (rules / "ALF-6005-REF-Sortable.md").write_text(
        "# REF-6005: Sortable\n\n"
        "**Applies to:** ALF project\n"
        "**Last updated:** 2026-06-28\n"
        "**Last reviewed:** 2026-06-28\n"
        "**Status:** Active\n"
        "**Tags:** xtag-zoo, xtag-mango, xtag-apple\n\n"
        "---\n\n"
        "## What Is It?\n\n"
        "A sortable test reference document.\n\n"
        "## Change History\n\n"
        "| Date | Change | By |\n"
        "|------|--------|----|",
        encoding="utf-8",
    )

    # ALF-6007: REF doc with unsorted tags — used by no-op/set-unchanged test.
    # xtag-zoo > xtag-apple alphabetically; unsorted in file intentionally to
    # test that re-adding an already-present tag on an unsorted doc stays no-op.
    (rules / "ALF-6007-REF-Unsorted-Present.md").write_text(
        "# REF-6007: Unsorted Present\n\n"
        "**Applies to:** ALF project\n"
        "**Last updated:** 2026-06-28\n"
        "**Last reviewed:** 2026-06-28\n"
        "**Status:** Active\n"
        "**Tags:** xtag-zoo, xtag-apple\n\n"
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


def test_tag_root_at_group_level_ls(tagged_project):
    """af tag --root <path> ls works (root at group level — P2 regression)."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["tag", "--root", str(tagged_project), "ls"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "xtag-common" in result.output


def test_tag_root_at_group_level_add(write_project):
    """af tag --root <path> add <id> <tag> works (root at group level — P2 regression)."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "--root", str(write_project), "add", "ALF-6001", "xtag-new"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "ALF-6001 tags:" in result.output


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


# ── Fix 1: empty/comma-only tag arg guard ─────────────────────────────────────


def test_tag_add_empty_string_no_write(write_project):
    """af tag add <ID> '' emits 'No valid tags provided.' and does not write."""
    runner = CliRunner()
    file_path = write_project / "rules" / "ALF-6001-REF-Write-Test.md"
    before = file_path.read_text(encoding="utf-8")
    result = runner.invoke(
        cli,
        ["tag", "add", "ALF-6001", "", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "No valid tags provided." in result.output
    assert file_path.read_text(encoding="utf-8") == before


def test_tag_add_comma_only_no_write(write_project):
    """af tag add <ID> ',' emits 'No valid tags provided.' and does not write."""
    runner = CliRunner()
    file_path = write_project / "rules" / "ALF-6001-REF-Write-Test.md"
    before = file_path.read_text(encoding="utf-8")
    result = runner.invoke(
        cli,
        ["tag", "add", "ALF-6001", ",", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "No valid tags provided." in result.output
    assert file_path.read_text(encoding="utf-8") == before


def test_tag_add_empty_on_no_tags_doc_no_corrupt(write_project):
    """af tag add on a doc with no Tags field and empty arg must not write a malformed field.

    Without the guard, the code appends an empty Tags field (**Tags:** ) and
    af validate then reports 'Tags field contains empty tag values'.  After the
    fix the file is unchanged and the message 'No valid tags provided.' is printed.
    """
    runner = CliRunner()
    file_path = write_project / "rules" / "ALF-6002-REF-No-Tags.md"
    before = file_path.read_text(encoding="utf-8")
    result = runner.invoke(
        cli,
        ["tag", "add", "ALF-6002", "", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "No valid tags provided." in result.output
    assert file_path.read_text(encoding="utf-8") == before
    assert "**Tags:**" not in file_path.read_text(encoding="utf-8")


def test_tag_rm_empty_string_no_write(write_project):
    """af tag rm <ID> '' emits 'No valid tags provided.' and does not write."""
    runner = CliRunner()
    file_path = write_project / "rules" / "ALF-6001-REF-Write-Test.md"
    before = file_path.read_text(encoding="utf-8")
    result = runner.invoke(
        cli,
        ["tag", "rm", "ALF-6001", "", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "No valid tags provided." in result.output
    assert file_path.read_text(encoding="utf-8") == before


# ── Fix 2: new Tags field in canonical metadata position ─────────────────────


def test_tag_add_new_field_canonical_position(write_project):
    """After tag add on a doc with no Tags field, Tags lands in canonical position.

    ALF-6006 has a Custom-Field (unknown optional) after Status.  sort_metadata
    places Tags (a known optional) BEFORE unknown fields, so Tags must appear
    before Custom-Field.  The current append-at-end puts it AFTER, giving a
    clear RED.  After fix, af fmt --check must also exit 0 (no reorder needed).
    """
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "add", "ALF-6006", "maintain", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (write_project / "rules" / "ALF-6006-REF-Full-No-Tags.md").read_text(
        encoding="utf-8"
    )
    assert "**Tags:** maintain" in content

    lines = content.splitlines()
    tags_idx = next(
        (i for i, ln in enumerate(lines) if ln.startswith("**Tags:**")), None
    )
    custom_idx = next(
        (i for i, ln in enumerate(lines) if ln.startswith("**Custom-Field:**")), None
    )
    assert tags_idx is not None, "Tags field not found in output"
    assert custom_idx is not None, "Custom-Field not found in output"
    assert tags_idx < custom_idx, (
        "Tags must appear before unknown Custom-Field in canonical order"
    )

    fmt_result = runner.invoke(
        cli,
        ["fmt", "ALF-6006", "--check", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert fmt_result.exit_code == 0, (
        f"af fmt --check found reorder pending:\n{fmt_result.output}"
    )


# ── Fix 3: PKG_READONLY_MSG constant importable from _helpers ────────────────


def test_pkg_readonly_msg_constant():
    """PKG_READONLY_MSG is importable from _helpers with the exact expected text."""
    from fx_alfred.commands._helpers import PKG_READONLY_MSG

    assert PKG_READONLY_MSG == "Cannot update PKG layer documents. They are read-only."


# ── Fix 4: Last updated bumped on successful add/rm ──────────────────────────


def test_tag_add_bumps_last_updated(write_project):
    """After af tag add, Last updated is set to today's date.

    ALF-6004 has Last updated: 2025-01-01.  After add, it must become today.
    """
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "add", "ALF-6004", "xtag-b", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (write_project / "rules" / "ALF-6004-REF-Date-Test.md").read_text(
        encoding="utf-8"
    )
    assert f"**Last updated:** {date.today().isoformat()}" in content
    assert "**Last updated:** 2025-01-01" not in content


def test_tag_rm_bumps_last_updated(write_project):
    """After af tag rm, Last updated is set to today's date.

    ALF-6004 has Last updated: 2025-01-01.  After rm, it must become today.
    """
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "rm", "ALF-6004", "xtag-a", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (write_project / "rules" / "ALF-6004-REF-Date-Test.md").read_text(
        encoding="utf-8"
    )
    assert f"**Last updated:** {date.today().isoformat()}" in content
    assert "**Last updated:** 2025-01-01" not in content


# ── Fix 5: out-of-vocabulary tag warning on add ───────────────────────────────


def test_tag_add_out_of_vocab_warns_stderr(write_project):
    """Adding an OOV tag emits a warning to stderr but still writes (advisory-only).

    'bogus-tag-zzz' is not in CONTROLLED_TAGS so a warning must appear on stderr.
    The tag must also be written to the doc and the exit code must be 0.
    """
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "add", "ALF-6001", "bogus-tag-zzz", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "bogus-tag-zzz" in result.stderr
    assert "warning" in result.stderr.lower()
    content = (write_project / "rules" / "ALF-6001-REF-Write-Test.md").read_text(
        encoding="utf-8"
    )
    assert "bogus-tag-zzz" in content


def test_tag_add_in_vocab_no_warning(write_project):
    """Adding a tag in CONTROLLED_TAGS produces no stderr warning."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "add", "ALF-6001", "maintain", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert result.stderr == ""


# ── Fix 6: add is a true no-op when all requested tags already present ────────


def test_tag_add_noop_when_all_tags_already_present_file_unchanged(write_project):
    """af tag add <tag-already-present> exits 0, prints 'unchanged', does NOT rewrite file.

    ALF-6004 has Last updated: 2025-01-01 and tag xtag-a.  Without the fix,
    mutate() returns the unchanged list and _edit_tags bumps Last updated to today
    — spurious write.  With the fix, mutate returns None and _edit_tags skips
    write entirely, so Last updated stays 2025-01-01 and file is byte-for-byte
    unchanged.
    """
    runner = CliRunner()
    file_path = write_project / "rules" / "ALF-6004-REF-Date-Test.md"
    before = file_path.read_text(encoding="utf-8")
    result = runner.invoke(
        cli,
        ["tag", "add", "ALF-6004", "xtag-a", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "unchanged" in result.output
    after = file_path.read_text(encoding="utf-8")
    assert after == before, (
        "File must be byte-for-byte unchanged when all requested tags already exist"
    )


def test_tag_add_genuinely_new_tag_still_writes(write_project):
    """af tag add with a new tag still writes the file and bumps Last updated.

    Confirms the no-op guard does not suppress real writes: ALF-6004 has only
    xtag-a; adding xtag-b must write the file and update Last updated.
    """
    runner = CliRunner()
    file_path = write_project / "rules" / "ALF-6004-REF-Date-Test.md"
    before = file_path.read_text(encoding="utf-8")
    result = runner.invoke(
        cli,
        ["tag", "add", "ALF-6004", "xtag-b", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    after = file_path.read_text(encoding="utf-8")
    assert after != before, "File must be rewritten when a genuinely new tag is added"
    assert "xtag-b" in after
    assert f"**Last updated:** {date.today().isoformat()}" in after


# ── Fix 7: tag add/rm writes sorted (fmt-canonical) Tags field ───────────────


def test_tag_add_result_is_sorted_and_fmt_clean(write_project):
    """af tag add writes tags in sorted order; af fmt --check exits 0 after.

    ALF-6001 has Tags: xtag-existing.  Adding xtag-alpha ('a' < 'e') must
    produce Tags: xtag-alpha, xtag-existing — NOT the insertion-order
    'xtag-existing, xtag-alpha' that the unfixed code writes.
    af fmt --check must exit 0 (canonical == written).
    """
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "add", "ALF-6001", "xtag-alpha", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (write_project / "rules" / "ALF-6001-REF-Write-Test.md").read_text(
        encoding="utf-8"
    )
    tag_line = next(
        (ln for ln in content.splitlines() if ln.startswith("**Tags:**")), None
    )
    assert tag_line == "**Tags:** xtag-alpha, xtag-existing", (
        f"Expected sorted tags; got: {tag_line!r}"
    )
    fmt_result = runner.invoke(
        cli,
        ["fmt", "ALF-6001", "--check", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert fmt_result.exit_code == 0, (
        f"af fmt --check reported changes after tag add:\n{fmt_result.output}"
    )


def test_tag_add_new_field_multiple_tags_written_sorted(write_project):
    """af tag add creating a new Tags field writes multiple tags sorted.

    ALF-6002 has no Tags field.  Adding 'xtag-zoo,xtag-alpha' (z before a
    as provided) must write Tags: xtag-alpha, xtag-zoo — sorted, not
    input-order.
    """
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "tag",
            "add",
            "ALF-6002",
            "xtag-zoo,xtag-alpha",
            "--root",
            str(write_project),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (write_project / "rules" / "ALF-6002-REF-No-Tags.md").read_text(
        encoding="utf-8"
    )
    tag_line = next(
        (ln for ln in content.splitlines() if ln.startswith("**Tags:**")), None
    )
    assert tag_line is not None, "Tags field not written"
    assert tag_line == "**Tags:** xtag-alpha, xtag-zoo", (
        f"Expected sorted tags in new field; got: {tag_line!r}"
    )


def test_tag_rm_result_is_sorted_and_fmt_clean(write_project):
    """af tag rm leaving multiple tags writes them sorted; af fmt --check exits 0.

    ALF-6005 has Tags: xtag-zoo, xtag-mango, xtag-apple (unsorted in file).
    Removing xtag-zoo yields ['xtag-mango', 'xtag-apple'] in insertion order
    — currently written unsorted.  After fix: xtag-apple, xtag-mango.
    af fmt --check must exit 0.
    """
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "rm", "ALF-6005", "xtag-zoo", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = (write_project / "rules" / "ALF-6005-REF-Sortable.md").read_text(
        encoding="utf-8"
    )
    tag_line = next(
        (ln for ln in content.splitlines() if ln.startswith("**Tags:**")), None
    )
    assert tag_line == "**Tags:** xtag-apple, xtag-mango", (
        f"Expected sorted remaining tags; got: {tag_line!r}"
    )
    fmt_result = runner.invoke(
        cli,
        ["fmt", "ALF-6005", "--check", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert fmt_result.exit_code == 0, (
        f"af fmt --check reported changes after tag rm:\n{fmt_result.output}"
    )


def test_tag_add_leaves_aligned_history_table_unchanged(tmp_path):
    """af tag add on a doc with an aligned history table must not churn the table.

    Regression: render_document re-rendered rows from stripped cell values, losing
    alignment padding that af fmt --write had produced.  After this fix, rows must
    be emitted verbatim (raw_line round-trip), so a fmt-clean doc stays fmt-clean.
    """
    rules = tmp_path / "rules"
    rules.mkdir()
    doc_path = rules / "ALF-9001-SOP-History-Roundtrip.md"
    original = (
        "# SOP-9001: History Roundtrip\n\n"
        "**Applies to:** Test\n"
        "**Last updated:** 2025-01-01\n"
        "**Last reviewed:** 2025-01-01\n"
        "**Status:** Active\n\n"
        "---\n\n"
        "## Change History\n\n"
        "| Date       | Change                    | By          |\n"
        "|------------|---------------------------|-------------|\n"
        "| 2025-01-01 | Initial version           | Alice       |\n"
        "| 2025-06-28 | A much longer description | Charlie Bob |\n"
    )
    doc_path.write_text(original, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "add", "ALF-9001", "xtag-new", "--root", str(tmp_path)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    after = doc_path.read_text(encoding="utf-8")

    def _history_lines(text: str) -> list[str]:
        lines = text.splitlines()
        idx = next((i for i, ln in enumerate(lines) if ln == "## Change History"), None)
        return lines[idx:] if idx is not None else []

    assert _history_lines(after) == _history_lines(original), (
        "History table must be byte-for-byte unchanged after af tag add\n"
        f"Before: {_history_lines(original)}\nAfter:  {_history_lines(after)}"
    )
    assert "**Tags:** xtag-new" in after


def test_tag_add_preserves_existing_wide_history_rows(tmp_path):
    """af tag add must not collapse existing Change History rows to three cells."""
    rules = tmp_path / "rules"
    rules.mkdir()
    doc_path = rules / "ALF-9003-SOP-Wide-History.md"
    original = (
        "# SOP-9003: Wide History\n\n"
        "**Applies to:** Test\n"
        "**Last updated:** 2025-01-01\n"
        "**Last reviewed:** 2025-01-01\n"
        "**Status:** Active\n\n"
        "---\n\n"
        "## Change History\n\n"
        "| Date | Change | By | Reviewer | Evidence |\n"
        "|------|--------|----|----------|----------|\n"
        "| 2025-01-01 | Initial version | Alice | GLM | PR #260 |\n"
    )
    doc_path.write_text(original, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "add", "ALF-9003", "xtag-new", "--root", str(tmp_path)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    after = doc_path.read_text(encoding="utf-8")
    assert "| 2025-01-01 | Initial version | Alice | GLM | PR #260 |" in after
    assert "**Tags:** xtag-new" in after


def test_tag_rm_leaves_aligned_history_table_unchanged(tmp_path):
    """af tag rm on a doc with an aligned history table must not churn the table."""
    rules = tmp_path / "rules"
    rules.mkdir()
    doc_path = rules / "ALF-9002-SOP-Rm-History.md"
    original = (
        "# SOP-9002: Rm History\n\n"
        "**Applies to:** Test\n"
        "**Last updated:** 2025-01-01\n"
        "**Last reviewed:** 2025-01-01\n"
        "**Status:** Active\n"
        "**Tags:** xtag-a, xtag-b\n\n"
        "---\n\n"
        "## Change History\n\n"
        "| Date       | Change                    | By          |\n"
        "|------------|---------------------------|-------------|\n"
        "| 2025-01-01 | Initial version           | Alice       |\n"
        "| 2025-06-28 | A much longer description | Charlie Bob |\n"
    )
    doc_path.write_text(original, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "rm", "ALF-9002", "xtag-b", "--root", str(tmp_path)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    after = doc_path.read_text(encoding="utf-8")

    def _history_lines(text: str) -> list[str]:
        lines = text.splitlines()
        idx = next((i for i, ln in enumerate(lines) if ln == "## Change History"), None)
        return lines[idx:] if idx is not None else []

    assert _history_lines(after) == _history_lines(original), (
        "History table must be byte-for-byte unchanged after af tag rm\n"
        f"Before: {_history_lines(original)}\nAfter:  {_history_lines(after)}"
    )
    assert "xtag-a" in after
    assert "xtag-b" not in after


def test_tag_add_noop_set_unchanged_with_unsorted_existing(write_project):
    """af tag add of an already-present tag on an unsorted doc is a no-op.

    Design decision: the no-op gate is 'no change to the tag SET', not
    'no change to the rendered string'.  ALF-6007 has Tags: xtag-zoo,
    xtag-apple (unsorted).  Re-adding xtag-apple (already present) must
    leave the file byte-for-byte unchanged — the sort must NOT trigger a
    rewrite just to reorder an already-correct set.
    """
    runner = CliRunner()
    file_path = write_project / "rules" / "ALF-6007-REF-Unsorted-Present.md"
    before = file_path.read_text(encoding="utf-8")
    result = runner.invoke(
        cli,
        ["tag", "add", "ALF-6007", "xtag-apple", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "unchanged" in result.output
    after = file_path.read_text(encoding="utf-8")
    assert after == before, (
        "File must be byte-for-byte unchanged when tag set is unchanged "
        "(even if existing order is unsorted)"
    )


# ── af tag vocab: manage user custom tag vocabulary ───────────────────────────


def test_tag_vocab_ls_empty_when_no_custom_tags(write_project):
    """af tag vocab ls prints a friendly message when no custom tags are defined."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "vocab", "ls"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    # Either empty output or a "No custom tags" message — not an error.
    assert "Error" not in result.output


def test_tag_vocab_add_single_tag(write_project):
    """af tag vocab add my-tag adds it and echoes the resulting list."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "vocab", "add", "my-tag"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "my-tag" in result.output


def test_tag_vocab_add_multiple_positional(write_project):
    """af tag vocab add foo bar adds both tags."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "vocab", "add", "foo", "bar"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "foo" in result.output
    assert "bar" in result.output


def test_tag_vocab_add_comma_separated(write_project):
    """af tag vocab add 'foo,bar' handles comma-separated tags."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "vocab", "add", "foo,bar"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "foo" in result.output
    assert "bar" in result.output


def test_tag_vocab_add_idempotent(write_project):
    """af tag vocab add the same tag twice exits 0 both times."""
    runner = CliRunner()
    runner.invoke(cli, ["tag", "vocab", "add", "my-tag"], catch_exceptions=False)
    result = runner.invoke(
        cli,
        ["tag", "vocab", "add", "my-tag"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0


def test_tag_vocab_ls_shows_added_tags(write_project):
    """af tag vocab ls shows previously added custom tags."""
    runner = CliRunner()
    runner.invoke(cli, ["tag", "vocab", "add", "alpha", "beta"], catch_exceptions=False)
    result = runner.invoke(cli, ["tag", "vocab", "ls"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "alpha" in result.output
    assert "beta" in result.output


def test_tag_vocab_rm_removes_tag(write_project):
    """af tag vocab rm removes a previously added tag."""
    runner = CliRunner()
    runner.invoke(cli, ["tag", "vocab", "add", "foo", "bar"], catch_exceptions=False)
    result = runner.invoke(
        cli,
        ["tag", "vocab", "rm", "foo"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "foo" not in result.output or "bar" in result.output

    ls_result = runner.invoke(cli, ["tag", "vocab", "ls"], catch_exceptions=False)
    assert "foo" not in ls_result.output
    assert "bar" in ls_result.output


def test_tag_vocab_rm_absent_tag_is_friendly(write_project):
    """af tag vocab rm on a tag not in vocab exits 0 with no crash."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "vocab", "rm", "nonexistent-tag"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0


def test_tag_vocab_does_not_take_root(write_project):
    """af tag vocab commands do NOT require --root (vocab is user-global)."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "vocab", "add", "my-tag"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0


# ── Union behavior: custom tags suppress OOV warnings ─────────────────────────


def test_tag_add_custom_vocab_tag_no_warning(write_project):
    """After vocab add 'my-custom-tag', af tag add emits NO out-of-vocab warning."""
    from fx_alfred.core.preferences import add_custom_tags

    add_custom_tags(["my-custom-tag"])
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "add", "ALF-6001", "my-custom-tag", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "warning" not in result.stderr.lower()
    assert "my-custom-tag" not in result.stderr


def test_tag_add_unknown_tag_still_warns_when_not_in_vocab(write_project):
    """Without vocab add, an unknown tag still emits the OOV warning."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "tag",
            "add",
            "ALF-6001",
            "totally-unknown-tag-xyz",
            "--root",
            str(write_project),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "warning" in result.stderr.lower()


def test_validate_does_not_flag_custom_tag(write_project):
    """af validate does NOT emit out-of-vocab warning for a custom tag."""
    from fx_alfred.core.preferences import add_custom_tags

    add_custom_tags(["my-custom-tag"])

    # Write a doc with the custom tag
    (write_project / "rules" / "ALF-7001-REF-Custom-Tag.md").write_text(
        "# REF-7001: Custom Tag\n\n"
        "**Applies to:** ALF project\n"
        "**Last updated:** 2026-06-29\n"
        "**Last reviewed:** 2026-06-29\n"
        "**Status:** Active\n"
        "**Tags:** my-custom-tag\n\n"
        "---\n\n"
        "## What Is It?\n\n"
        "A test doc with a user-defined custom tag.\n\n"
        "## Change History\n\n"
        "| Date | Change | By |\n"
        "|------|--------|----|",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "validate",
            "ALF-7001",
            "--root",
            str(write_project),
            "--tag-warnings",
            "detail",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, f"validate failed:\n{result.output}"
    assert "my-custom-tag" not in result.output
    assert "out-of-vocabulary" not in result.output


def test_validate_flags_unknown_tag_not_in_vocab(write_project):
    """af validate DOES emit OOV warning for a tag that is neither controlled nor custom."""
    (write_project / "rules" / "ALF-7002-REF-Unknown-Tag.md").write_text(
        "# REF-7002: Unknown Tag\n\n"
        "**Applies to:** ALF project\n"
        "**Last updated:** 2026-06-29\n"
        "**Last reviewed:** 2026-06-29\n"
        "**Status:** Active\n"
        "**Tags:** totally-unknown-zzz\n\n"
        "---\n\n"
        "## What Is It?\n\n"
        "A test doc with an unknown tag.\n\n"
        "## Change History\n\n"
        "| Date | Change | By |\n"
        "|------|--------|----|",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "validate",
            "ALF-7002",
            "--root",
            str(write_project),
            "--tag-warnings",
            "detail",
        ],
        catch_exceptions=False,
    )
    # The validate command should still warn about truly unknown tags
    assert (
        "totally-unknown-zzz" in result.output or "out-of-vocabulary" in result.output
    )


def test_tag_vocab_rm_last_tag_shows_friendly_message(write_project):
    """After removing the last custom tag, rm shows 'No custom tags defined.'."""
    runner = CliRunner()
    runner.invoke(cli, ["tag", "vocab", "add", "foo"], catch_exceptions=False)
    result = runner.invoke(cli, ["tag", "vocab", "rm", "foo"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "No custom tags defined." in result.output


def test_tag_vocab_ls_and_rm_empty_phrasing_consistent(write_project):
    """vocab ls and vocab rm use identical wording when the list is empty."""
    runner = CliRunner()
    runner.invoke(cli, ["tag", "vocab", "add", "bar"], catch_exceptions=False)
    runner.invoke(cli, ["tag", "vocab", "rm", "bar"], catch_exceptions=False)

    ls_result = runner.invoke(cli, ["tag", "vocab", "ls"], catch_exceptions=False)
    rm_result = runner.invoke(
        cli, ["tag", "vocab", "rm", "nonexistent"], catch_exceptions=False
    )
    assert ls_result.output.strip() == rm_result.output.strip()


# ── FXA-2315 / feat-256: malformed preferences.yaml → clean ClickException ────


@pytest.fixture
def malformed_prefs():
    """Write a malformed preferences.yaml (custom_tags: scalar string) to the isolated HOME.

    The isolate_home autouse fixture already patches Path.home() for every test,
    so Path.home() / ".alfred" / "preferences.yaml" resolves to a safe temp path.
    """
    from pathlib import Path

    prefs_dir = Path.home() / ".alfred"
    prefs_dir.mkdir(parents=True, exist_ok=True)
    (prefs_dir / "preferences.yaml").write_text("custom_tags: todo\n", encoding="utf-8")


def test_tag_add_malformed_prefs_yields_click_exception(write_project, malformed_prefs):
    """af tag add with malformed custom_tags (scalar) must exit non-zero as a clean
    ClickException — PreferencesError must never escape uncaught to the caller.
    """
    from fx_alfred.core.preferences import PreferencesError

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "add", "ALF-6001", "maintain", "--root", str(write_project)],
    )
    assert not isinstance(result.exception, PreferencesError), (
        f"PreferencesError escaped uncaught: {result.exception!r}"
    )
    assert result.exit_code != 0
    assert "list" in result.output


def test_tag_vocab_ls_malformed_prefs_yields_click_exception(malformed_prefs):
    """af tag vocab ls with malformed custom_tags must exit non-zero as a clean ClickException."""
    from fx_alfred.core.preferences import PreferencesError

    runner = CliRunner()
    result = runner.invoke(cli, ["tag", "vocab", "ls"])
    assert not isinstance(result.exception, PreferencesError), (
        f"PreferencesError escaped uncaught: {result.exception!r}"
    )
    assert result.exit_code != 0
    assert "list" in result.output


def test_tag_vocab_add_malformed_prefs_yields_click_exception(malformed_prefs):
    """af tag vocab add with malformed custom_tags must exit non-zero as a clean ClickException."""
    from fx_alfred.core.preferences import PreferencesError

    runner = CliRunner()
    result = runner.invoke(cli, ["tag", "vocab", "add", "newtag"])
    assert not isinstance(result.exception, PreferencesError), (
        f"PreferencesError escaped uncaught: {result.exception!r}"
    )
    assert result.exit_code != 0
    assert "list" in result.output


def test_tag_vocab_rm_malformed_prefs_yields_click_exception(malformed_prefs):
    """af tag vocab rm with malformed custom_tags must exit non-zero as a clean ClickException."""
    from fx_alfred.core.preferences import PreferencesError

    runner = CliRunner()
    result = runner.invoke(cli, ["tag", "vocab", "rm", "sometag"])
    assert not isinstance(result.exception, PreferencesError), (
        f"PreferencesError escaped uncaught: {result.exception!r}"
    )
    assert result.exit_code != 0
    assert "list" in result.output


def test_tag_add_valid_custom_tags_list_works(write_project):
    """With a VALID custom_tags list in preferences, af tag add completes normally."""
    from pathlib import Path

    prefs_dir = Path.home() / ".alfred"
    prefs_dir.mkdir(parents=True, exist_ok=True)
    (prefs_dir / "preferences.yaml").write_text(
        "custom_tags:\n  - my-tag\n", encoding="utf-8"
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "add", "ALF-6001", "maintain", "--root", str(write_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0


def test_tag_vocab_commands_valid_prefs_still_work():
    """With a VALID custom_tags list, vocab ls/add/rm all complete normally."""
    from pathlib import Path

    prefs_dir = Path.home() / ".alfred"
    prefs_dir.mkdir(parents=True, exist_ok=True)
    (prefs_dir / "preferences.yaml").write_text(
        "custom_tags:\n  - my-tag\n", encoding="utf-8"
    )
    runner = CliRunner()

    ls_result = runner.invoke(cli, ["tag", "vocab", "ls"], catch_exceptions=False)
    assert ls_result.exit_code == 0
    assert "my-tag" in ls_result.output

    add_result = runner.invoke(
        cli, ["tag", "vocab", "add", "extra-tag"], catch_exceptions=False
    )
    assert add_result.exit_code == 0

    rm_result = runner.invoke(
        cli, ["tag", "vocab", "rm", "extra-tag"], catch_exceptions=False
    )
    assert rm_result.exit_code == 0
