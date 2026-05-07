"""Tests for af star/unstar/starred commands (FXA-2274)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from fx_alfred.cli import cli


pytestmark = pytest.mark.cli


def _prefs_path() -> Path:
    return Path.home() / ".alfred" / "preferences.yaml"


def _project_doc(
    root: Path, prefix: str, acid: str, type_code: str, title: str
) -> None:
    """Create a minimal valid document at <root>/rules/."""
    rules = root / "rules"
    rules.mkdir(exist_ok=True)
    (rules / f"{prefix}-{acid}-{type_code}-{title}.md").write_text(
        f"# {type_code}-{acid}: {title.replace('-', ' ')}\n\n"
        "**Applies to:** TST project\n"
        "**Last updated:** 2026-05-07\n"
        "**Last reviewed:** 2026-05-07\n"
        "**Status:** Active\n\n"
        "---\n\n## What Is It?\n\nDoc.\n"
    )


@pytest.fixture
def project_with_doc(tmp_path):
    _project_doc(tmp_path, "TST", "5001", "REF", "Sample-Doc")
    return tmp_path


def test_star_creates_preferences_with_starred_docs_key(project_with_doc, monkeypatch):
    monkeypatch.chdir(project_with_doc)
    runner = CliRunner()
    result = runner.invoke(cli, ["star", "TST-5001"])

    assert result.exit_code == 0, result.output
    assert "starred: TST-5001" in result.output
    data = yaml.safe_load(_prefs_path().read_text())
    assert data["starred_docs"] == ["TST-5001"]


def test_star_is_idempotent(project_with_doc, monkeypatch):
    monkeypatch.chdir(project_with_doc)
    runner = CliRunner()
    runner.invoke(cli, ["star", "TST-5001"])
    result = runner.invoke(cli, ["star", "TST-5001"])

    assert result.exit_code == 0
    assert "already starred: TST-5001" in result.output
    data = yaml.safe_load(_prefs_path().read_text())
    assert data["starred_docs"] == ["TST-5001"]


def test_star_acid_only_resolves(project_with_doc, monkeypatch):
    """`af star 5001` resolves to canonical TST-5001."""
    monkeypatch.chdir(project_with_doc)
    runner = CliRunner()
    result = runner.invoke(cli, ["star", "5001"])

    assert result.exit_code == 0, result.output
    assert "starred: TST-5001" in result.output
    data = yaml.safe_load(_prefs_path().read_text())
    assert data["starred_docs"] == ["TST-5001"]


def test_star_lowercase_prefix_canonicalises(project_with_doc, monkeypatch):
    """`af star tst-5001` stores TST-5001 (canonical uppercase)."""
    monkeypatch.chdir(project_with_doc)
    runner = CliRunner()
    result = runner.invoke(cli, ["star", "tst-5001"])

    assert result.exit_code == 0
    data = yaml.safe_load(_prefs_path().read_text())
    assert data["starred_docs"] == ["TST-5001"]


def test_star_unknown_id_errors(project_with_doc, monkeypatch):
    monkeypatch.chdir(project_with_doc)
    runner = CliRunner()
    result = runner.invoke(cli, ["star", "ZZZ-9999"])

    assert result.exit_code != 0
    assert not _prefs_path().exists() or "starred_docs" not in (
        yaml.safe_load(_prefs_path().read_text()) or {}
    )


def test_star_acid_only_ambiguous_errors(tmp_path, monkeypatch):
    """`af star 5001` errors when multiple prefixes match."""
    _project_doc(tmp_path, "TST", "5001", "REF", "A")
    _project_doc(tmp_path, "ALF", "5001", "SOP", "B")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["star", "5001"])

    assert result.exit_code != 0
    # Did not write
    assert not _prefs_path().exists()


def test_unstar_removes_entry(project_with_doc, monkeypatch):
    monkeypatch.chdir(project_with_doc)
    runner = CliRunner()
    runner.invoke(cli, ["star", "TST-5001"])
    result = runner.invoke(cli, ["unstar", "TST-5001"])

    assert result.exit_code == 0
    assert "unstarred: TST-5001" in result.output
    data = yaml.safe_load(_prefs_path().read_text())
    assert data["starred_docs"] == []


def test_unstar_idempotent_when_not_starred(project_with_doc, monkeypatch):
    monkeypatch.chdir(project_with_doc)
    runner = CliRunner()
    result = runner.invoke(cli, ["unstar", "TST-5001"])

    assert result.exit_code == 0
    assert "not starred" in result.output


def test_unstar_works_when_doc_deleted(tmp_path, monkeypatch):
    """AC #4: unstar must succeed even when underlying doc is gone."""
    _project_doc(tmp_path, "TST", "5001", "REF", "Sample-Doc")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(cli, ["star", "TST-5001"])

    # Delete the doc from disk
    (tmp_path / "rules" / "TST-5001-REF-Sample-Doc.md").unlink()

    result = runner.invoke(cli, ["unstar", "TST-5001"])
    assert result.exit_code == 0
    assert "unstarred: TST-5001" in result.output


def test_unstar_acid_only_matches_unique_starred(project_with_doc, monkeypatch):
    """`af unstar 5001` removes TST-5001 when it is the unique starred entry."""
    monkeypatch.chdir(project_with_doc)
    runner = CliRunner()
    runner.invoke(cli, ["star", "TST-5001"])
    result = runner.invoke(cli, ["unstar", "5001"])

    assert result.exit_code == 0, result.output
    assert "unstarred: TST-5001" in result.output


def test_unstar_acid_only_ambiguous_with_multiple_starred(tmp_path, monkeypatch):
    """AC #3b: ambiguous unstar errors when multiple starred entries share an ACID."""
    _project_doc(tmp_path, "TST", "5001", "REF", "A")
    _project_doc(tmp_path, "ALF", "5001", "SOP", "B")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(cli, ["star", "TST-5001"])
    runner.invoke(cli, ["star", "ALF-5001"])
    result = runner.invoke(cli, ["unstar", "5001"])

    assert result.exit_code != 0
    # Both should still be starred
    data = yaml.safe_load(_prefs_path().read_text())
    assert sorted(data["starred_docs"]) == ["ALF-5001", "TST-5001"]


def test_starred_text_output_sorted(tmp_path, monkeypatch):
    _project_doc(tmp_path, "TST", "5001", "REF", "A")
    _project_doc(tmp_path, "TST", "5002", "SOP", "B")
    _project_doc(tmp_path, "TST", "5003", "CHG", "C")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(cli, ["star", "TST-5003"])
    runner.invoke(cli, ["star", "TST-5001"])
    runner.invoke(cli, ["star", "TST-5002"])

    result = runner.invoke(cli, ["starred"])
    assert result.exit_code == 0
    assert result.output.strip().splitlines() == ["TST-5001", "TST-5002", "TST-5003"]


def test_starred_when_empty(project_with_doc, monkeypatch):
    monkeypatch.chdir(project_with_doc)
    runner = CliRunner()
    result = runner.invoke(cli, ["starred"])

    assert result.exit_code == 0
    assert result.output.strip() == ""


def test_starred_marks_missing(tmp_path, monkeypatch):
    """AC #5: docs that no longer resolve are marked (missing)."""
    _project_doc(tmp_path, "TST", "5001", "REF", "Sample-Doc")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(cli, ["star", "TST-5001"])
    (tmp_path / "rules" / "TST-5001-REF-Sample-Doc.md").unlink()

    result = runner.invoke(cli, ["starred"])
    assert result.exit_code == 0
    assert "TST-5001" in result.output
    assert "(missing)" in result.output


def test_starred_json_output(tmp_path, monkeypatch):
    _project_doc(tmp_path, "TST", "5001", "REF", "A")
    _project_doc(tmp_path, "TST", "5002", "SOP", "B")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(cli, ["star", "TST-5001"])
    runner.invoke(cli, ["star", "TST-5002"])
    (tmp_path / "rules" / "TST-5002-SOP-B.md").unlink()

    result = runner.invoke(cli, ["starred", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["schema_version"] == "1"
    assert sorted(data["starred_docs"]) == ["TST-5001", "TST-5002"]
    assert data["missing"] == ["TST-5002"]


def test_starred_json_when_empty(project_with_doc, monkeypatch):
    monkeypatch.chdir(project_with_doc)
    runner = CliRunner()
    result = runner.invoke(cli, ["starred", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data == {"schema_version": "1", "starred_docs": [], "missing": []}


def test_atomic_write_no_tmp_after_star_unstar_star(project_with_doc, monkeypatch):
    """AC #8: atomic writes leave no .tmp artefacts."""
    monkeypatch.chdir(project_with_doc)
    runner = CliRunner()
    runner.invoke(cli, ["star", "TST-5001"])
    runner.invoke(cli, ["unstar", "TST-5001"])
    runner.invoke(cli, ["star", "TST-5001"])

    alfred_dir = _prefs_path().parent
    leftover = [
        p.name
        for p in alfred_dir.iterdir()
        if p.name.startswith(".") or "tmp" in p.name.lower()
    ]
    assert leftover == []


def test_starred_ignores_unknown_top_level_keys(project_with_doc, monkeypatch):
    """Forward-compat: hand-edited preferences with unknown keys still work."""
    monkeypatch.chdir(project_with_doc)
    prefs = _prefs_path()
    prefs.parent.mkdir(parents=True, exist_ok=True)
    prefs.write_text("future_key: keep-me\nstarred_docs:\n  - TST-5001\n")

    runner = CliRunner()
    result = runner.invoke(cli, ["starred"])
    assert result.exit_code == 0
    assert "TST-5001" in result.output

    # Star another doc; future_key must survive the round-trip
    runner.invoke(cli, ["star", "TST-5001"])  # idempotent
    data = yaml.safe_load(prefs.read_text())
    assert data["future_key"] == "keep-me"
