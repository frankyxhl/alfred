"""Tests for `af tag` command (tag_cmd.py)."""

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


# ── No-arg form: list all tags with counts ───────────────────────────────────


def test_tag_no_arg_lists_tags_alphabetically(tagged_project):
    """af tag lists all distinct tags sorted alphabetically."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["tag", "--root", str(tagged_project)], catch_exceptions=False
    )
    assert result.exit_code == 0
    lines = result.output.strip().splitlines()
    # Extract tag names from first column
    tag_names = [line.split()[0] for line in lines]
    assert tag_names == sorted(tag_names), "Tags must be sorted alphabetically"
    # fixture-specific tags must appear (xtag- prefix avoids PKG collisions)
    assert "xtag-alpha" in tag_names
    assert "xtag-beta" in tag_names
    assert "xtag-common" in tag_names
    assert "xtag-gamma" in tag_names


def test_tag_no_arg_shows_correct_counts(tagged_project):
    """af tag shows accurate usage counts per unique-to-fixture tag."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["tag", "--root", str(tagged_project)], catch_exceptions=False
    )
    assert result.exit_code == 0
    lines_map: dict[str, int] = {}
    for line in result.output.strip().splitlines():
        parts = line.split()
        if len(parts) >= 2:
            lines_map[parts[0]] = int(parts[1])

    # xtag-* tags are unique to the fixture; counts are exact
    assert lines_map["xtag-common"] == 3  # ALF-1001, 1002, 1003
    assert lines_map["xtag-alpha"] == 2  # ALF-1001, 1004
    assert lines_map["xtag-beta"] == 1
    assert lines_map["xtag-gamma"] == 1


def test_tag_no_arg_json(tagged_project):
    """af tag --json emits sorted JSON array of {tag, count}."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["tag", "--json", "--root", str(tagged_project)], catch_exceptions=False
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    # Each element has tag and count keys
    for item in data:
        assert "tag" in item
        assert "count" in item
        assert isinstance(item["tag"], str)
        assert isinstance(item["count"], int)
    # Sorted alphabetically
    tag_names = [item["tag"] for item in data]
    assert tag_names == sorted(tag_names)
    # Exact counts for xtag-* tags (unique to fixture, no PKG collision)
    by_tag = {item["tag"]: item["count"] for item in data}
    assert by_tag["xtag-common"] == 3
    assert by_tag["xtag-alpha"] == 2
    assert by_tag["xtag-beta"] == 1
    assert by_tag["xtag-gamma"] == 1


# ── With-name form: list docs for a given tag ────────────────────────────────


def test_tag_with_name_lists_matching_docs(tagged_project):
    """af tag xtag-common lists all documents tagged with xtag-common."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "xtag-common", "--root", str(tagged_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "ALF-1001" in result.output
    assert "ALF-1002" in result.output
    assert "ALF-1003" in result.output
    # ALF-1004 does NOT have xtag-common
    assert "ALF-1004" not in result.output


def test_tag_with_name_multiple_types(tagged_project):
    """af tag xtag-common returns docs of multiple types (SOP, PRP, CHG)."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "xtag-common", "--root", str(tagged_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "SOP" in result.output
    assert "PRP" in result.output
    assert "CHG" in result.output


def test_tag_with_name_output_format(tagged_project):
    """af tag <name> uses same row format as af list (LABEL  PREFIX-ACID  TYPE  TITLE)."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "xtag-alpha", "--root", str(tagged_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    # Each line has source label and document ID
    assert "PRJ" in result.output


def test_tag_with_name_case_insensitive(tagged_project):
    """Tag name matching is case-insensitive (XTAG-COMMON matches xtag-common-tagged docs)."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "XTAG-COMMON", "--root", str(tagged_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "ALF-1001" in result.output
    assert "ALF-1002" in result.output
    assert "ALF-1003" in result.output


def test_tag_with_name_mixed_case(tagged_project):
    """Tag name matching is case-insensitive (Xtag-Common matches xtag-common-tagged docs)."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "Xtag-Common", "--root", str(tagged_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "ALF-1001" in result.output


def test_tag_with_name_unknown_tag_no_docs(tagged_project):
    """af tag nonexistent-tag prints 'No documents found.' when no match."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "nonexistent-tag", "--root", str(tagged_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "No documents found." in result.output


def test_tag_with_name_json(tagged_project):
    """af tag xtag-common --json emits same shape as af list --json."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "xtag-common", "--json", "--root", str(tagged_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    # xtag-common is unique to fixture; exactly 3 docs match
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


def test_tag_with_name_json_unknown_tag_empty_array(tagged_project):
    """af tag nonexistent --json emits [] when no match."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "nonexistent", "--json", "--root", str(tagged_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert result.output.strip() == "[]"
    assert json.loads(result.output) == []


# ── --root option ─────────────────────────────────────────────────────────────


def test_tag_root_before_subcommand(tagged_project):
    """af --root <path> tag works (root before subcommand)."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["--root", str(tagged_project), "tag"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "xtag-common" in result.output


def test_tag_root_after_subcommand(tagged_project):
    """af tag --root <path> works (root after subcommand)."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["tag", "--root", str(tagged_project)], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "xtag-alpha" in result.output


def test_tag_no_arg_with_root_monkeypatched(tagged_project, monkeypatch):
    """af tag picks up documents from the specified root."""
    monkeypatch.chdir(tagged_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["tag"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "xtag-common" in result.output
    assert "xtag-alpha" in result.output


# ── Fix 1: duplicate-tag count dedup within a single doc ─────────────────────


def test_tag_no_arg_dedupes_within_doc(tmp_path):
    """A doc with duplicate tags (xtag-duped, xtag-duped) must count xtag-duped only once."""
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "ALF-2001-SOP-Dedup-Test.md").write_text(
        "# SOP-2001: Dedup Test\n\n**Tags:** xtag-duped, xtag-duped\n\n---\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli, ["tag", "--root", str(tmp_path)], catch_exceptions=False
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


def test_tag_no_arg_no_tags_prints_no_tags_found():
    """af tag (no arg) prints 'No tags found.' when all docs carry no Tags field.

    PKG layer always provides tagged docs in integration scans, so scan_or_fail
    is mocked to isolate the zero-tag empty branch.
    """
    mock_doc = MagicMock()
    mock_doc.tags = []

    runner = CliRunner()
    with patch("fx_alfred.commands.tag_cmd.scan_or_fail", return_value=[mock_doc]):
        result = runner.invoke(cli, ["tag"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "No tags found." in result.output
    assert "No documents found." not in result.output


def test_tag_with_name_unknown_still_prints_no_documents_found(tmp_path):
    """af tag <unknown> still prints 'No documents found.' (named form unchanged)."""
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "ALF-3001-SOP-No-Tags.md").write_text(
        "# SOP-3001: No Tags\n\n---\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "xtag-nonexistent", "--root", str(tmp_path)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "No documents found." in result.output


# ── Fix 3: coverage gaps ──────────────────────────────────────────────────────


def test_tag_no_arg_doc_without_tags_field_is_absent(tmp_path):
    """A doc with no Tags field is absent from the no-arg listing and causes no error."""
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
        cli, ["tag", "--root", str(tmp_path)], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "xtag-present" in result.output
    assert "ALF-4002" not in result.output


def test_tag_with_name_exact_match_not_substring(tmp_path):
    """af tag common must NOT match a doc tagged only xtag-common (membership, not substring)."""
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "ALF-5001-SOP-Tag-Test.md").write_text(
        "# SOP-5001: Tag Test\n\n**Tags:** xtag-common\n\n---\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tag", "common", "--root", str(tmp_path)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "ALF-5001" not in result.output
