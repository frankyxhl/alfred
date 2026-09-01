"""FXA-2330: `af projects` — list/manage the Project SOP Registry."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from fx_alfred.cli import cli
from fx_alfred.core.registry import (
    REGISTRY_FILENAME,
    RegistryEntry,
    load_registry,
    save_registry,
)

pytestmark = pytest.mark.cli


def _registry_file():
    return Path.home() / ".alfred" / REGISTRY_FILENAME


def _seed(entries):
    save_registry(_registry_file(), entries, today="2026-09-02")


def test_projects_lists_entries(tmp_path, monkeypatch):
    live = tmp_path / "proj"
    (live / "rules").mkdir(parents=True)
    _seed(
        [
            RegistryEntry("FXA", str(live), 12, "2026-09-01"),
            RegistryEntry("WUK", "/Users/frank/Projects/wukong", 8, "2026-08-30"),
        ]
    )
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli, ["projects"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "FXA" in result.output
    assert str(live) in result.output
    assert "2026-09-01" in result.output


def test_projects_json(tmp_path, monkeypatch):
    live = tmp_path / "proj"
    (live / "rules").mkdir(parents=True)
    _seed([RegistryEntry("FXA", str(live), 12, "2026-09-01")])
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli, ["projects", "--json"], catch_exceptions=False)
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload == [
        {
            "prefix": "FXA",
            "root": str(live),
            "doc_count": 12,
            "last_seen": "2026-09-01",
        }
    ]


def test_projects_empty_registry_hints(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli, ["projects"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "No projects registered" in result.output


def test_projects_empty_registry_json_is_array(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli, ["projects", "--json"], catch_exceptions=False)
    assert result.exit_code == 0
    assert json.loads(result.output) == []


def test_projects_prune_removes_dead_roots(tmp_path, monkeypatch):
    live = tmp_path / "proj"
    (live / "rules").mkdir(parents=True)
    dead = tmp_path / "gone"
    _seed(
        [
            RegistryEntry("FXA", str(live), 12, "2026-09-01"),
            RegistryEntry("OLD", str(dead), 3, "2026-01-01"),
        ]
    )
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli, ["projects", "--prune"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "OLD" in result.output  # reports the removed entry
    entries = load_registry(_registry_file())
    assert [(e.prefix, e.root) for e in entries] == [("FXA", str(live))]


def test_projects_prune_json_returns_survivors(tmp_path, monkeypatch):
    live = tmp_path / "proj"
    (live / "rules").mkdir(parents=True)
    _seed(
        [
            RegistryEntry("FXA", str(live), 12, "2026-09-01"),
            RegistryEntry("OLD", str(tmp_path / "gone"), 3, "2026-01-01"),
        ]
    )
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        cli, ["projects", "--prune", "--json"], catch_exceptions=False
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert [row["prefix"] for row in payload] == ["FXA"]


def test_projects_unreadable_registry_is_cli_error(tmp_path, monkeypatch):
    """R2 P2: read failures surface as friendly CLI errors, not tracebacks."""
    from fx_alfred.core.registry import save_registry

    p = Path.home() / ".alfred" / REGISTRY_FILENAME
    save_registry(
        p, [RegistryEntry("FXA", str(tmp_path), 1, "2026-09-02")], today="2026-09-02"
    )
    p.chmod(0o000)
    monkeypatch.chdir(tmp_path)
    try:
        result = CliRunner().invoke(cli, ["projects"])
        assert result.exit_code != 0
        assert "registry" in result.output.lower()
        assert "Traceback" not in result.output
    finally:
        p.chmod(0o644)
