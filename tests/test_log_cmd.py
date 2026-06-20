"""CLI tests for activity ledger commands (FXA-2307)."""

from __future__ import annotations

import json
from zipfile import ZipFile

import pytest
from click.testing import CliRunner

from fx_alfred.cli import cli


pytestmark = pytest.mark.cli


def test_log_commands_are_registered():
    runner = CliRunner()

    for command in ("log", "log-validate", "log-archive"):
        result = runner.invoke(cli, [command, "--help"], catch_exceptions=False)
        assert result.exit_code == 0


def test_log_writes_to_project_rules_log(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    result = CliRunner().invoke(
        cli,
        ["log", "manual checkpoint", "--ref", "COR-1205"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    files = sorted((sample_project / "rules" / "logs").glob("*.jsonl"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text(encoding="utf-8").strip())
    assert payload["summary"] == "manual checkpoint"
    assert payload["command"] == "log"
    assert payload["usage_kind"] == "manual_log"
    assert payload["refs"] == ["COR-1205"]


def test_log_lazily_archives_closed_day_before_append(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    log_dir = sample_project / "rules" / "logs"
    log_dir.mkdir(parents=True)
    (log_dir / "2000-01-01.jsonl").write_text(
        json.dumps(
            {
                "schema": "alfred.activity/v1",
                "ts": "2000-01-01T00:00:00Z",
                "agent": "other",
                "agent_name": "af",
                "agent_version": "unknown",
                "event": "note",
                "summary": "old",
                "session_id": "session",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(cli, ["log", "new"], catch_exceptions=False)

    assert result.exit_code == 0
    assert not (log_dir / "2000-01-01.jsonl").exists()
    assert (log_dir / "archive.zip").exists()
    with ZipFile(log_dir / "archive.zip") as zf:
        assert zf.namelist() == ["2000-01-01.jsonl"]
    current_files = [path for path in log_dir.glob("*.jsonl")]
    assert len(current_files) == 1
    payload = json.loads(current_files[0].read_text(encoding="utf-8"))
    assert payload["summary"] == "new"


def test_log_continues_when_lazy_archive_fails(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    log_dir = sample_project / "rules" / "logs"
    log_dir.mkdir(parents=True)
    (log_dir / "archive.zip").write_text("not a zip", encoding="utf-8")
    (log_dir / "2000-01-01.jsonl").write_text(
        json.dumps(
            {
                "schema": "alfred.activity/v1",
                "ts": "2000-01-01T00:00:00Z",
                "agent": "other",
                "agent_name": "af",
                "agent_version": "unknown",
                "event": "note",
                "summary": "old",
                "session_id": "session",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(cli, ["log", "new"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "archive skipped" in result.stderr
    assert (log_dir / "2000-01-01.jsonl").exists()
    current_files = [
        path for path in log_dir.glob("*.jsonl") if path.name != "2000-01-01.jsonl"
    ]
    assert len(current_files) == 1
    payload = json.loads(current_files[0].read_text(encoding="utf-8"))
    assert payload["summary"] == "new"


def test_log_rejects_invalid_event_before_append(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)

    result = CliRunner().invoke(cli, ["log", "bad", "--event", "not-an-event"])

    assert result.exit_code == 1
    assert "event" in result.output
    assert not (sample_project / "rules" / "logs").exists()


def test_log_validate_reports_unknown_field(tmp_path):
    log_file = tmp_path / "bad.jsonl"
    log_file.write_text(
        json.dumps(
            {
                "schema": "alfred.activity/v1",
                "ts": "2026-06-21T00:00:00Z",
                "agent": "other",
                "agent_name": "af",
                "agent_version": "unknown",
                "event": "note",
                "summary": "bad",
                "session_id": "session",
                "surprise": "not allowed",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(cli, ["log-validate", str(log_file)])

    assert result.exit_code == 1
    assert "surprise" in result.output


def test_log_validate_rejects_oversized_loose_jsonl_line(tmp_path):
    log_file = tmp_path / "oversized.jsonl"
    payload = {
        "schema": "alfred.activity/v1",
        "ts": "2026-06-21T00:00:00Z",
        "agent": "other",
        "agent_name": "af",
        "agent_version": "unknown",
        "event": "note",
        "summary": "ok",
        "session_id": "session",
        "files": ["x" * 4100],
    }
    log_file.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = CliRunner().invoke(cli, ["log-validate", str(log_file)])

    assert result.exit_code == 1
    assert "JSONL line exceeds 4096 bytes" in result.output


def test_log_validate_rejects_oversized_archived_jsonl_line(tmp_path):
    archive = tmp_path / "archive.zip"
    payload = {
        "schema": "alfred.activity/v1",
        "ts": "2026-06-21T00:00:00Z",
        "agent": "other",
        "agent_name": "af",
        "agent_version": "unknown",
        "event": "note",
        "summary": "ok",
        "session_id": "session",
        "files": ["x" * 4100],
    }
    with ZipFile(archive, "w") as zf:
        zf.writestr("2026-06-21.jsonl", json.dumps(payload) + "\n")

    result = CliRunner().invoke(cli, ["log-validate", str(archive)])

    assert result.exit_code == 1
    assert "archive.zip::2026-06-21.jsonl" in result.output
    assert "JSONL line exceeds 4096 bytes" in result.output


def test_log_validate_rejects_non_object_jsonl_record(tmp_path):
    log_file = tmp_path / "bad.jsonl"
    log_file.write_text("[]\n", encoding="utf-8")

    result = CliRunner().invoke(cli, ["log-validate", str(log_file)])

    assert result.exit_code == 1
    assert "JSONL record must be an object" in result.output


def test_log_validate_corrupt_archive_uses_exit_code_five(tmp_path):
    archive = tmp_path / "archive.zip"
    archive.write_text("not a zip", encoding="utf-8")

    result = CliRunner().invoke(cli, ["log-validate", str(archive)])

    assert result.exit_code == 5
    assert "corrupt archive.zip" in result.output


def test_log_validate_missing_default_log_dir_is_empty(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)

    result = CliRunner().invoke(cli, ["log-validate"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "activity log ok" in result.output


def test_log_archive_moves_closed_project_log(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    log_dir = sample_project / "rules" / "logs"
    log_dir.mkdir(parents=True)
    (log_dir / "2000-01-01.jsonl").write_text(
        json.dumps(
            {
                "schema": "alfred.activity/v1",
                "ts": "2026-06-20T00:00:00Z",
                "agent": "other",
                "agent_name": "af",
                "agent_version": "unknown",
                "event": "note",
                "summary": "old",
                "session_id": "session",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(cli, ["log-archive"], catch_exceptions=False)

    assert result.exit_code == 0
    assert (log_dir / "archive.zip").exists()
    assert not (log_dir / "2000-01-01.jsonl").exists()
