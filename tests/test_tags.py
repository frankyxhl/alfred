"""Tests for Document Tags metadata field (FXA-2200).

Covers: parse_tags, Document.tags property, af list --tag,
af validate tags checks, af fmt tags normalization, sort_metadata with Tags.
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from fx_alfred.cli import cli
from fx_alfred.core.parser import parse_tags
from fx_alfred.core.schema import DocType, OPTIONAL_METADATA


# ── parse_tags ───────────────────────────────────────────────────────────────


def test_parse_tags_basic():
    assert parse_tags("tdd, review, release") == ["tdd", "review", "release"]


def test_parse_tags_strips_whitespace():
    assert parse_tags("  tdd ,  review  ") == ["tdd", "review"]


def test_parse_tags_lowercases():
    assert parse_tags("TDD, Review") == ["tdd", "review"]


def test_parse_tags_filters_empty():
    assert parse_tags("tdd,,review,") == ["tdd", "review"]


def test_parse_tags_empty_string():
    assert parse_tags("") == []


def test_parse_tags_single_tag():
    assert parse_tags("tdd") == ["tdd"]


# ── OPTIONAL_METADATA schema ────────────────────────────────────────────────


def test_optional_metadata_exists():
    assert OPTIONAL_METADATA is not None


def test_optional_metadata_has_tags_for_all_types():
    for dt in DocType:
        assert "Tags" in OPTIONAL_METADATA[dt], f"Tags missing for {dt}"


# ── Document.tags property ───────────────────────────────────────────────────


def test_document_tags_property(tmp_path):
    from fx_alfred.core.document import Document

    rules = tmp_path / "rules"
    rules.mkdir()
    doc_file = rules / "TST-1000-SOP-Test-Doc.md"
    doc_file.write_text(
        "# SOP-1000: Test Doc\n\n"
        "**Applies to:** TST project\n"
        "**Last updated:** 2026-04-04\n"
        "**Last reviewed:** 2026-04-04\n"
        "**Status:** Draft\n"
        "**Tags:** tdd, review\n\n"
        "---\n\n## What Is It?\n\nTest.\n\n"
        "---\n\n## Change History\n\n"
        "| Date | Change | By |\n|------|--------|----|"
    )
    doc = Document.from_filename(
        "TST-1000-SOP-Test-Doc.md", directory="rules", source="prj", base_path=rules
    )
    assert doc.tags == ["tdd", "review"]


def test_document_tags_absent(tmp_path):
    from fx_alfred.core.document import Document

    rules = tmp_path / "rules"
    rules.mkdir()
    doc_file = rules / "TST-1000-SOP-Test-Doc.md"
    doc_file.write_text(
        "# SOP-1000: Test Doc\n\n"
        "**Applies to:** TST project\n"
        "**Last updated:** 2026-04-04\n"
        "**Last reviewed:** 2026-04-04\n"
        "**Status:** Draft\n\n"
        "---\n\n## What Is It?\n\nTest.\n\n"
        "---\n\n## Change History\n\n"
        "| Date | Change | By |\n|------|--------|----|"
    )
    doc = Document.from_filename(
        "TST-1000-SOP-Test-Doc.md", directory="rules", source="prj", base_path=rules
    )
    assert doc.tags == []


def test_document_tags_malformed_returns_empty(tmp_path):
    from fx_alfred.core.document import Document

    rules = tmp_path / "rules"
    rules.mkdir()
    doc_file = rules / "TST-1000-SOP-Test-Doc.md"
    doc_file.write_text("not a valid document")
    doc = Document.from_filename(
        "TST-1000-SOP-Test-Doc.md", directory="rules", source="prj", base_path=rules
    )
    assert doc.tags == []


# ── af list --tag ────────────────────────────────────────────────────────────


def _make_tagged_project(tmp_path):
    """Create a project with tagged documents."""
    rules = tmp_path / "rules"
    rules.mkdir()

    (rules / "TST-1000-SOP-Test-One.md").write_text(
        "# SOP-1000: Test One\n\n"
        "**Applies to:** TST project\n"
        "**Last updated:** 2026-04-04\n"
        "**Last reviewed:** 2026-04-04\n"
        "**Status:** Draft\n"
        "**Tags:** tdd, review\n\n"
        "---\n\n## What Is It?\n\nTest.\n\n"
        "---\n\n## Change History\n\n"
        "| Date | Change | By |\n|------|--------|----|"
    )
    (rules / "TST-1001-SOP-Test-Two.md").write_text(
        "# SOP-1001: Test Two\n\n"
        "**Applies to:** TST project\n"
        "**Last updated:** 2026-04-04\n"
        "**Last reviewed:** 2026-04-04\n"
        "**Status:** Draft\n"
        "**Tags:** release\n\n"
        "---\n\n## What Is It?\n\nTest.\n\n"
        "---\n\n## Change History\n\n"
        "| Date | Change | By |\n|------|--------|----|"
    )
    (rules / "TST-1002-SOP-Test-Three.md").write_text(
        "# SOP-1002: Test Three\n\n"
        "**Applies to:** TST project\n"
        "**Last updated:** 2026-04-04\n"
        "**Last reviewed:** 2026-04-04\n"
        "**Status:** Draft\n\n"
        "---\n\n## What Is It?\n\nTest.\n\n"
        "---\n\n## Change History\n\n"
        "| Date | Change | By |\n|------|--------|----|"
    )
    return tmp_path


def test_list_tag_filter(tmp_path, monkeypatch):
    proj = _make_tagged_project(tmp_path)
    monkeypatch.chdir(proj)
    runner = CliRunner()
    result = runner.invoke(cli, ["list", "--tag", "tdd"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "TST-1000" in result.output
    assert "TST-1001" not in result.output
    assert "TST-1002" not in result.output


def test_list_tag_case_insensitive(tmp_path, monkeypatch):
    proj = _make_tagged_project(tmp_path)
    monkeypatch.chdir(proj)
    runner = CliRunner()
    result = runner.invoke(cli, ["list", "--tag", "TDD"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "TST-1000" in result.output


def test_list_tag_no_match(tmp_path, monkeypatch):
    proj = _make_tagged_project(tmp_path)
    monkeypatch.chdir(proj)
    runner = CliRunner()
    result = runner.invoke(cli, ["list", "--tag", "nonexistent"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "No documents found." in result.output


def test_list_tag_combined_with_type(tmp_path, monkeypatch):
    proj = _make_tagged_project(tmp_path)
    monkeypatch.chdir(proj)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["list", "--tag", "review", "--source", "prj"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "TST-1000" in result.output


# ── af validate tags ─────────────────────────────────────────────────────────


def test_validate_tags_empty_value(tmp_path, monkeypatch):
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "TST-1000-SOP-Test-Doc.md").write_text(
        "# SOP-1000: Test Doc\n\n"
        "**Applies to:** TST project\n"
        "**Last updated:** 2026-04-04\n"
        "**Last reviewed:** 2026-04-04\n"
        "**Status:** Draft\n"
        "**Tags:** tdd,,review\n\n"
        "---\n\n## What Is It?\n\nWhy.\n\n"
        "## Why\n\nWhy.\n\n## When to Use\n\nWhen.\n\n"
        "## When NOT to Use\n\nNot.\n\n## Steps\n\n1. Do it.\n\n"
        "---\n\n## Change History\n\n"
        "| Date | Change | By |\n|------|--------|----|"
    )
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate"], catch_exceptions=False)
    assert "empty tag" in result.output.lower()


def test_validate_tags_duplicate(tmp_path, monkeypatch):
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "TST-1000-SOP-Test-Doc.md").write_text(
        "# SOP-1000: Test Doc\n\n"
        "**Applies to:** TST project\n"
        "**Last updated:** 2026-04-04\n"
        "**Last reviewed:** 2026-04-04\n"
        "**Status:** Draft\n"
        "**Tags:** tdd, TDD\n\n"
        "---\n\n## What Is It?\n\nWhy.\n\n"
        "## Why\n\nWhy.\n\n## When to Use\n\nWhen.\n\n"
        "## When NOT to Use\n\nNot.\n\n## Steps\n\n1. Do it.\n\n"
        "---\n\n## Change History\n\n"
        "| Date | Change | By |\n|------|--------|----|"
    )
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate"], catch_exceptions=False)
    assert "duplicate" in result.output.lower()


def test_validate_tags_valid_no_issue(tmp_path, monkeypatch):
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "TST-1000-SOP-Test-Doc.md").write_text(
        "# SOP-1000: Test Doc\n\n"
        "**Applies to:** TST project\n"
        "**Last updated:** 2026-04-04\n"
        "**Last reviewed:** 2026-04-04\n"
        "**Status:** Draft\n"
        "**Tags:** tdd, review\n\n"
        "---\n\n## What Is It?\n\nWhat.\n\n"
        "## Why\n\nWhy.\n\n## When to Use\n\nWhen.\n\n"
        "## When NOT to Use\n\nNot.\n\n## Steps\n\n1. Do it.\n\n"
        "---\n\n## Change History\n\n"
        "| Date | Change | By |\n|------|--------|----|"
    )
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate"], catch_exceptions=False)
    assert "TST-1000" not in result.output or "0 issues" in result.output


# ── af fmt tags normalization ────────────────────────────────────────────────


def test_fmt_normalizes_tags(tmp_path, monkeypatch):
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "TST-1000-SOP-Test-Doc.md").write_text(
        "# SOP-1000: Test Doc\n\n"
        "**Applies to:** TST project\n"
        "**Last updated:** 2026-04-04\n"
        "**Last reviewed:** 2026-04-04\n"
        "**Status:** Draft\n"
        "**Tags:** Review, tdd,  Release, tdd\n\n"
        "---\n\n## What Is It?\n\nTest.\n\n"
        "---\n\n## Change History\n\n"
        "| Date | Change | By |\n"
        "|------|--------|----|"
    )
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["fmt", "--write", "TST-1000"], catch_exceptions=False
    )
    assert result.exit_code == 0
    content = (rules / "TST-1000-SOP-Test-Doc.md").read_text()
    assert "**Tags:** release, review, tdd" in content


# ── sort_metadata with Tags ─────────────────────────────────────────────────


def test_sort_metadata_tags_after_required():
    from fx_alfred.core.normalize import sort_metadata

    fields = ["Tags", "Applies to", "Last updated", "Last reviewed", "Status"]
    result = sort_metadata(fields, DocType.SOP)
    # Required fields first, then Tags
    assert result.index("Tags") > result.index("Status")


def test_sort_metadata_tags_before_unknown():
    from fx_alfred.core.normalize import sort_metadata

    fields = [
        "Applies to", "Last updated", "Last reviewed", "Status",
        "Unknown field", "Tags",
    ]
    result = sort_metadata(fields, DocType.SOP)
    assert result.index("Tags") < result.index("Unknown field")
