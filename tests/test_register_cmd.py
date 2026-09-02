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
    sample_project = _mk(tmp_path)
    result = CliRunner().invoke(
        cli,
        ["register", "--root", str(sample_project)],
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


def test_register_rejects_prj_usr9000_conflict(tmp_path, monkeypatch):
    """explicit register errors loudly when PRJ already holds USR-9000."""
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "USR-9000-SOP-Custom.md").write_text("# custom", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli, ["register"])
    assert result.exit_code != 0
    assert "USR-9000" in result.output
    assert not (
        Path.home() / ".alfred" / "USR-9000-REF-Project-SOP-Registry.md"
    ).exists()


def test_register_slot_conflict_message_not_rewrapped(tmp_path, monkeypatch):
    """the slot-conflict error reaches the user verbatim — never
    double-prefixed as 'Project registry update failed: …'."""
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "ALF-2201-PRP-AF-CLI-Tool.md").write_text("# AF CLI", encoding="utf-8")
    home = Path.home() / ".alfred"
    home.mkdir(parents=True, exist_ok=True)
    # foreign occupant at the slot: no ownership marker, no table needed
    (home / REGISTRY_FILENAME).write_text("# someone else's doc\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli, ["register"])
    assert result.exit_code != 0
    assert "already occupies the USR-9000 slot" in result.output
    assert "Project registry update failed" not in result.output


def test_register_validates_slot_even_on_noop_upsert(tmp_path, monkeypatch):
    """a foreign table-bearing doc that happens to parse with
    matching rows must still be rejected — 'already current' must not skip
    the ownership validation."""
    from fx_alfred.core.registry import REGISTRY_MARKER

    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "ALF-2201-PRP-AF-CLI-Tool.md").write_text("# AF CLI", encoding="utf-8")
    home = Path.home() / ".alfred"
    home.mkdir(parents=True, exist_ok=True)
    # foreign doc (no marker) whose rows coincidentally match a fresh upsert
    (home / REGISTRY_FILENAME).write_text(
        "# someone's table doc\n\n"
        "| PRJ | Root | Docs | Last Seen |\n"
        "|-----|------|------|-----------|\n"
        f"| ALF | `{tmp_path.resolve()}` | 1 | 2026-09-02 |\n",
        encoding="utf-8",
    )
    assert (
        not (home / REGISTRY_FILENAME)
        .read_text(encoding="utf-8")
        .startswith(REGISTRY_MARKER)
    )
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli, ["register"])
    assert result.exit_code != 0
    assert "USR-9000" in result.output
