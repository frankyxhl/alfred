"""Tests for af tag command (FXA-2273)."""

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


def test_tag_star_creates_preferences_file_and_starred_tags_key():
    runner = CliRunner()
    result = runner.invoke(cli, ["tag", "star", "release"])

    assert result.exit_code == 0
    assert "starred: release" in result.output
    assert _prefs_path().exists()
    data = yaml.safe_load(_prefs_path().read_text())
    assert data["starred_tags"] == ["release"]


def test_tag_star_is_idempotent():
    runner = CliRunner()
    runner.invoke(cli, ["tag", "star", "release"])
    result = runner.invoke(cli, ["tag", "star", "release"])

    assert result.exit_code == 0
    assert "already starred: release" in result.output
    data = yaml.safe_load(_prefs_path().read_text())
    assert data["starred_tags"] == ["release"]


def test_tag_star_lowercases_name():
    runner = CliRunner()
    result = runner.invoke(cli, ["tag", "star", "Release"])

    assert result.exit_code == 0
    data = yaml.safe_load(_prefs_path().read_text())
    assert data["starred_tags"] == ["release"]


def test_tag_star_rejects_empty_name():
    runner = CliRunner()
    result = runner.invoke(cli, ["tag", "star", "  "])

    assert result.exit_code != 0
    assert "tag name cannot be empty" in result.output
    assert not _prefs_path().exists()


def test_tag_unstar_removes_tag():
    runner = CliRunner()
    runner.invoke(cli, ["tag", "star", "release"])
    runner.invoke(cli, ["tag", "star", "review"])
    result = runner.invoke(cli, ["tag", "unstar", "release"])

    assert result.exit_code == 0
    assert "unstarred: release" in result.output
    data = yaml.safe_load(_prefs_path().read_text())
    assert data["starred_tags"] == ["review"]


def test_tag_unstar_is_idempotent_when_not_starred():
    runner = CliRunner()
    result = runner.invoke(cli, ["tag", "unstar", "nonexistent"])

    assert result.exit_code == 0
    assert "not starred: nonexistent" in result.output


def test_tag_list_when_empty():
    runner = CliRunner()
    result = runner.invoke(cli, ["tag", "list"])

    assert result.exit_code == 0
    assert result.output.strip() == ""


def test_tag_list_when_populated_sorted():
    runner = CliRunner()
    runner.invoke(cli, ["tag", "star", "review"])
    runner.invoke(cli, ["tag", "star", "release"])
    runner.invoke(cli, ["tag", "star", "bdd"])
    result = runner.invoke(cli, ["tag", "list"])

    assert result.exit_code == 0
    assert result.output.strip().splitlines() == ["bdd", "release", "review"]


def test_tag_list_json_output():
    runner = CliRunner()
    runner.invoke(cli, ["tag", "star", "release"])
    runner.invoke(cli, ["tag", "star", "review"])
    result = runner.invoke(cli, ["tag", "list", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["schema_version"] == "1"
    assert sorted(data["starred_tags"]) == ["release", "review"]


def test_tag_list_json_when_empty():
    runner = CliRunner()
    result = runner.invoke(cli, ["tag", "list", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data == {"schema_version": "1", "starred_tags": []}


def test_preferences_file_missing_treated_as_empty():
    """No file → no error, empty starred set."""
    runner = CliRunner()
    assert not _prefs_path().exists()
    result = runner.invoke(cli, ["tag", "list"])

    assert result.exit_code == 0
    assert result.output.strip() == ""


def test_malformed_yaml_raises_click_exception():
    prefs = _prefs_path()
    prefs.parent.mkdir(parents=True, exist_ok=True)
    prefs.write_text("starred_tags: [unclosed")

    runner = CliRunner()
    result = runner.invoke(cli, ["tag", "list"])

    assert result.exit_code != 0
    assert str(prefs) in result.output


def test_starred_tags_not_a_list_raises():
    prefs = _prefs_path()
    prefs.parent.mkdir(parents=True, exist_ok=True)
    prefs.write_text("starred_tags: 'not-a-list'")

    runner = CliRunner()
    result = runner.invoke(cli, ["tag", "list"])

    assert result.exit_code != 0


def test_preferences_file_preserves_unknown_keys():
    """Forward-compat: future preference keys must survive a star/unstar write."""
    prefs = _prefs_path()
    prefs.parent.mkdir(parents=True, exist_ok=True)
    prefs.write_text("future_key: keep-me\nstarred_tags:\n  - existing\n")

    runner = CliRunner()
    runner.invoke(cli, ["tag", "star", "release"])

    data = yaml.safe_load(prefs.read_text())
    assert data["future_key"] == "keep-me"
    assert sorted(data["starred_tags"]) == ["existing", "release"]


def test_atomic_write_no_tmp_artifacts_after_two_writes():
    runner = CliRunner()
    runner.invoke(cli, ["tag", "star", "release"])
    runner.invoke(cli, ["tag", "star", "review"])

    alfred_dir = _prefs_path().parent
    leftover = [
        p.name
        for p in alfred_dir.iterdir()
        if p.name.startswith(".") or "tmp" in p.name.lower()
    ]
    assert leftover == []


def test_alfred_dir_created_on_first_write():
    """If ~/.alfred/ does not exist, first `af tag star` creates it."""
    alfred_dir = Path.home() / ".alfred"
    if alfred_dir.exists():
        # The conftest isolate_home should have left this absent
        for p in alfred_dir.iterdir():
            p.unlink()
        alfred_dir.rmdir()

    assert not alfred_dir.exists()
    runner = CliRunner()
    result = runner.invoke(cli, ["tag", "star", "release"])

    assert result.exit_code == 0
    assert alfred_dir.exists()
    assert _prefs_path().exists()
