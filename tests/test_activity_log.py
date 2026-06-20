"""Tests for the append-only activity ledger (FXA-2307)."""

from __future__ import annotations

import json
from zipfile import ZipFile

import pytest

from fx_alfred.core import activity_log
from fx_alfred.core.scanner import scan_documents


pytestmark = pytest.mark.unit


def test_compose_and_append_user_usage_record_round_trips():
    log_dir = activity_log.user_log_dir()
    record = activity_log.compose_record(
        summary="af guide routing docs",
        command="guide",
        usage_kind="routing_docs",
        refs=["COR-1103", "FXA-2125"],
        result_count=2,
    )

    path = activity_log.append_record(record, log_dir=log_dir)

    assert path.parent == log_dir
    payload = json.loads(path.read_text(encoding="utf-8").strip())
    assert payload["schema"] == "alfred.activity/v1"
    assert payload["agent"] == "other"
    assert payload["agent_name"] == "af"
    assert payload["command"] == "guide"
    assert payload["usage_kind"] == "routing_docs"
    assert payload["refs"] == ["COR-1103", "FXA-2125"]
    assert activity_log.validate_record(payload) == []


def test_task_text_is_hashed_and_redacted_for_sensitive_values():
    record = activity_log.compose_record(
        summary="af plan task gap",
        command="plan",
        usage_kind="plan_task_gap",
        task_text="ship feature with API_KEY=super-secret-token",
        result_count=0,
    )

    assert "task_text" not in record
    assert record["task_text_redacted"] is True
    assert len(record["task_text_sha256"]) == 64
    assert activity_log.validate_record(record) == []


def test_validate_record_rejects_unknown_fields():
    record = activity_log.compose_record(summary="manual note")
    record["surprise"] = "not allowed"

    violations = activity_log.validate_record(record)

    assert any(v.field == "surprise" for v in violations)


def test_iter_records_reads_zip_with_double_colon_source(tmp_path):
    archive = tmp_path / "archive.zip"
    with ZipFile(archive, "w") as zf:
        zf.writestr(
            "2026-06-20.jsonl",
            json.dumps(activity_log.compose_record(summary="archived")) + "\n",
        )

    records = list(activity_log.iter_records(archive))

    assert len(records) == 1
    source, lineno, record = records[0]
    assert source.endswith("archive.zip::2026-06-20.jsonl")
    assert lineno == 1
    assert record["summary"] == "archived"


def test_archive_directory_moves_closed_day_to_zip(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    old_file = log_dir / "2026-06-20.jsonl"
    old_file.write_text(
        json.dumps(activity_log.compose_record(summary="old")) + "\n",
        encoding="utf-8",
    )

    result = activity_log.archive_directory(log_dir, today="2026-06-21")

    assert result.archived_files == ["2026-06-20.jsonl"]
    assert not old_file.exists()
    with ZipFile(log_dir / "archive.zip") as zf:
        assert "2026-06-20.jsonl" in zf.namelist()


def test_append_record_rolls_to_next_part_when_part_one_is_full(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    monkeypatch.setattr(activity_log, "FILE_SIZE_CAP_BYTES", 260)
    day = activity_log.log_file_for_dir(log_dir).stem
    (log_dir / f"{day}.jsonl").write_text("x" * 240, encoding="utf-8")
    (log_dir / f"{day}.part1.jsonl").write_text("x" * 240, encoding="utf-8")

    path = activity_log.append_record(
        activity_log.compose_record(summary="small rollover record"),
        log_dir=log_dir,
    )

    assert path.name == f"{day}.part2.jsonl"
    assert path.stat().st_size <= activity_log.FILE_SIZE_CAP_BYTES


def test_append_record_trims_refs_and_files_until_line_fits(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    monkeypatch.setattr(activity_log, "RECORD_LINE_CAP_BYTES", 700)
    record = activity_log.compose_record(
        summary="oversize",
        refs=[f"TST-{i:04d}" for i in range(16)],
        files=[f"very/long/path/{i}/" + ("x" * 80) for i in range(32)],
    )

    path = activity_log.append_record(record, log_dir=log_dir)
    line = path.read_bytes()
    payload = json.loads(line)

    assert len(line) <= activity_log.RECORD_LINE_CAP_BYTES
    assert payload["summary_truncated"] is True


def test_log_dir_resolution_uses_project_rules_log_when_project_exists(sample_project):
    assert activity_log.resolve_log_dir(root=sample_project) == (
        sample_project / "rules" / "logs"
    )


def test_log_dir_resolution_falls_back_to_user_home_when_no_project(tmp_path):
    assert activity_log.resolve_log_dir(root=tmp_path) == activity_log.user_log_dir()


def test_collect_evolve_signals_reports_usage_gaps_and_never_used(sample_project):
    rules_dir = sample_project / "rules"
    (rules_dir / "TST-6101-SOP-Used-Once.md").write_text(
        """# TST-6101: Used Once

**Applies to:** Test
**Status:** Active
---
## Steps
1. used
""",
        encoding="utf-8",
    )
    (rules_dir / "TST-6102-SOP-Never-Used.md").write_text(
        """# TST-6102: Never Used

**Applies to:** Test
**Status:** Active
---
## Steps
1. unused
""",
        encoding="utf-8",
    )
    log_dir = activity_log.user_log_dir()
    activity_log.append_record(
        activity_log.compose_record(
            summary="plan",
            command="plan",
            usage_kind="plan_explicit",
            refs=["TST-6101"],
            result_count=1,
        ),
        log_dir=log_dir,
    )
    activity_log.append_record(
        activity_log.compose_record(
            summary="gap",
            command="plan",
            usage_kind="plan_task_gap",
            task_text="missing flow",
            result_count=0,
        ),
        log_dir=log_dir,
    )

    signals = activity_log.collect_evolve_signals(
        scan_documents(sample_project), log_dir=log_dir
    )

    assert signals["usage_counts"]["TST-6101"] == 1
    assert "TST-6102" in signals["never_used_sops"]
    assert signals["plan_task_gaps"][0]["task_text"] == "missing flow"
