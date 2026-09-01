"""FXA-2330: `af register` — explicit Project SOP Registry upsert."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from fx_alfred.cli import cli
from fx_alfred.core.registry import REGISTRY_FILENAME, load_registry

pytestmark = pytest.mark.cli


def _registry_file():
    return Path.home() / ".alfred" / REGISTRY_FILENAME


def test_register_creates_row(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    result = CliRunner().invoke(cli, ["register"], catch_exceptions=False)
    assert result.exit_code == 0
    entries = load_registry(_registry_file())
    assert [(e.prefix, e.doc_count) for e in entries] == [("ALF", 3)]
    assert entries[0].root == str(sample_project.resolve())


def test_register_json(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    result = CliRunner().invoke(cli, ["register", "--json"], catch_exceptions=False)
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload[0]["prefix"] == "ALF"
    assert payload[0]["doc_count"] == 3


def test_register_is_idempotent(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    assert runner.invoke(cli, ["register"], catch_exceptions=False).exit_code == 0
    before = _registry_file().read_text(encoding="utf-8")
    assert runner.invoke(cli, ["register"], catch_exceptions=False).exit_code == 0
    assert _registry_file().read_text(encoding="utf-8") == before


def test_register_with_explicit_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        cli,
        ["register", "--root", str(sample_project := _mk(tmp_path))],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    entries = load_registry(_registry_file())
    assert entries[0].root == str(Path(sample_project).resolve())


def _mk(tmp_path):
    rules = tmp_path / "proj" / "rules"
    rules.mkdir(parents=True)
    (rules / "NEW-3001-SOP-Thing.md").write_text("# Thing", encoding="utf-8")
    return tmp_path / "proj"


def test_register_no_docs_fails_loudly(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli, ["register"], catch_exceptions=False)
    assert result.exit_code != 0
    assert "No Alfred" in result.output


def test_register_write_failure_is_loud(sample_project, monkeypatch):
    from unittest.mock import patch

    monkeypatch.chdir(sample_project)
    with patch(
        "fx_alfred.commands.register_cmd.save_registry",
        side_effect=OSError("disk full"),
    ):
        result = CliRunner().invoke(cli, ["register"])
    assert result.exit_code != 0
    assert "disk full" in result.output


def test_register_preserves_other_rows(sample_project, monkeypatch):
    from fx_alfred.core.registry import RegistryEntry, save_registry

    save_registry(
        _registry_file(),
        [RegistryEntry("WUK", "/Users/frank/Projects/wukong", 8, "2026-01-01")],
        today="2026-01-01",
    )
    monkeypatch.chdir(sample_project)
    result = CliRunner().invoke(cli, ["register"], catch_exceptions=False)
    assert result.exit_code == 0
    entries = load_registry(_registry_file())
    assert [(e.prefix, e.root) for e in entries] == [
        ("WUK", "/Users/frank/Projects/wukong"),
        ("ALF", str(sample_project.resolve())),
    ]
