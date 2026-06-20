"""Tests for the append-only activity ledger (FXA-2307)."""

from __future__ import annotations

import json
import re
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


def test_append_usage_event_skips_invalid_composed_record(tmp_path, monkeypatch):
    monkeypatch.setattr(activity_log, "user_log_dir", lambda: tmp_path / "logs")
    monkeypatch.setenv("ALFRED_AGENT_VERSION", "Codex CLI")

    path = activity_log.append_usage_event(
        command="guide",
        usage_kind="routing_docs",
        refs=["COR-1103"],
    )

    assert path is None
    assert not (tmp_path / "logs").exists()


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


@pytest.mark.parametrize(
    "task_text",
    [
        "deploy with sk-" + ("a" * 24),
        "push with ghp_" + ("A" * 32),
        "rotate AWS_SECRET_ACCESS_KEY=" + ("b" * 40),
        "connect DATABASE_URL=postgres://user:pass@host/db",
        "call https://user:pass@example.com/api",
        "curl -H 'Authorization: Bearer abcdef1234567890'",
    ],
)
def test_task_text_redacts_provider_token_shapes(task_text):
    record = activity_log.compose_record(summary="secret", task_text=task_text)

    assert "task_text" not in record
    assert record["task_text_redacted"] is True
    assert len(record["task_text_sha256"]) == 64


def test_validate_record_rejects_unknown_fields():
    record = activity_log.compose_record(summary="manual note")
    record["surprise"] = "not allowed"

    violations = activity_log.validate_record(record)

    assert any(v.field == "surprise" for v in violations)


def test_compose_record_deduplicates_refs_before_truncation():
    record = activity_log.compose_record(
        summary="refs",
        refs=["TST-6101", "TST-6101", "COR-1205"],
    )

    assert record["refs"] == ["TST-6101", "COR-1205"]


def test_compose_record_deduplicates_files_before_truncation():
    record = activity_log.compose_record(
        summary="files",
        files=["src/a.py", "src/a.py", "src/b.py"],
    )

    assert record["files"] == ["src/a.py", "src/b.py"]


def test_validate_record_rejects_noncanonical_refs():
    record = activity_log.compose_record(summary="refs", refs=["TST-6101"])
    record["refs"] = ["not-a-doc-id"]

    violations = activity_log.validate_record(record)

    assert any(violation.field == "refs" for violation in violations)


def test_validate_record_rejects_invalid_required_values():
    record = activity_log.compose_record(summary="valid")
    record.update(
        {
            "ts": "not-a-date",
            "summary": "bad\nsummary",
            "agent_version": "bad version",
            "session_id": "bad session",
        }
    )

    violations = activity_log.validate_record(record)

    fields = {violation.field for violation in violations}
    assert {"ts", "summary", "agent_version", "session_id"} <= fields


def test_validate_record_rejects_invalid_optional_values():
    record = activity_log.compose_record(summary="optional")
    record.update(
        {
            "agent_name": "bad name",
            "duration_ms": -1,
            "parent_event": "bad parent",
        }
    )

    violations = activity_log.validate_record(record)

    fields = {violation.field for violation in violations}
    assert {"agent_name", "duration_ms", "parent_event"} <= fields


def test_validate_record_rejects_non_repo_relative_files():
    record = activity_log.compose_record(summary="files")
    record["files"] = [
        "src/fx_alfred/core/activity_log.py",
        "/Users/alice/token.txt",
        "../secrets",
        "rules\\private.md",
    ]

    violations = activity_log.validate_record(record)

    assert any(violation.field == "files" for violation in violations)


def test_validate_record_rejects_bool_integer_fields():
    record = activity_log.compose_record(summary="bool counters")
    record["result_count"] = True
    record["duration_ms"] = False

    violations = activity_log.validate_record(record)

    fields = {violation.field for violation in violations}
    assert {"result_count", "duration_ms"} <= fields


def test_validate_record_rejects_false_summary_truncated_marker():
    record = activity_log.compose_record(summary="summary")
    record["summary_truncated"] = False

    violations = activity_log.validate_record(record)

    assert any(violation.field == "summary_truncated" for violation in violations)


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


def test_archive_directory_locks_log_dir_fd(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    old_file = log_dir / "2026-06-20.jsonl"
    old_file.write_text(
        json.dumps(activity_log.compose_record(summary="old")) + "\n",
        encoding="utf-8",
    )
    locked_inodes = []
    original_flock = activity_log.fcntl.flock

    def tracking_flock(fd, operation):
        if operation & activity_log.fcntl.LOCK_EX:
            locked_inodes.append(activity_log.os.fstat(fd).st_ino)
        return original_flock(fd, operation)

    monkeypatch.setattr(activity_log.fcntl, "flock", tracking_flock)

    result = activity_log.archive_directory(log_dir, today="2026-06-21")

    assert result.archived_files == ["2026-06-20.jsonl"]
    assert locked_inodes == [log_dir.stat().st_ino]
    assert not (log_dir / ".archive.lock").exists()


def test_archive_directory_skips_when_directory_lock_is_held(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    old_file = log_dir / "2026-06-20.jsonl"
    old_file.write_text(
        json.dumps(activity_log.compose_record(summary="old")) + "\n",
        encoding="utf-8",
    )

    def busy_flock(fd, operation):
        if operation & activity_log.fcntl.LOCK_EX:
            raise BlockingIOError("busy")

    monkeypatch.setattr(activity_log.fcntl, "flock", busy_flock)

    result = activity_log.archive_directory(log_dir, today="2026-06-21")

    assert result.skipped is True
    assert old_file.exists()
    assert not (log_dir / "archive.zip").exists()


def test_archive_directory_writes_readable_archive_permissions(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    old_file = log_dir / "2026-06-20.jsonl"
    old_file.write_text(
        json.dumps(activity_log.compose_record(summary="old")) + "\n",
        encoding="utf-8",
    )

    activity_log.archive_directory(log_dir, today="2026-06-21")

    assert (log_dir / "archive.zip").stat().st_mode & 0o777 == 0o644


def test_archive_directory_preserves_live_pid_tmpfile(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    old_file = log_dir / "2026-06-20.jsonl"
    old_file.write_text(
        json.dumps(activity_log.compose_record(summary="old")) + "\n",
        encoding="utf-8",
    )
    live_tmp = log_dir / f"archive.zip.tmp.{activity_log.os.getpid()}.live"
    live_tmp.write_text("in progress", encoding="utf-8")

    activity_log.archive_directory(log_dir, today="2026-06-21")

    assert live_tmp.exists()


def test_archive_directory_cleans_stale_tmpfile_before_nothing_to_archive(
    tmp_path, monkeypatch
):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    stale_tmp = log_dir / "archive.zip.tmp.123456.dead"
    stale_tmp.write_text("stale", encoding="utf-8")

    def dead_process(_pid, _signal):
        raise ProcessLookupError

    monkeypatch.setattr(activity_log.os, "kill", dead_process)

    result = activity_log.archive_directory(log_dir, today="2026-06-21")

    assert result.message == "nothing to archive"
    assert not stale_tmp.exists()


def test_jsonl_files_returns_rollover_parts_once(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    base = log_dir / "2026-06-20.jsonl"
    part = log_dir / "2026-06-20.part1.jsonl"
    base.write_text("", encoding="utf-8")
    part.write_text("", encoding="utf-8")

    files = activity_log._jsonl_files(log_dir)

    assert files == [part, base] or files == [base, part]
    assert len(files) == len({file.name for file in files})


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


def test_append_record_locks_target_selection_and_write(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    lock_state = {"held": False}
    original_target_path = activity_log._append_target_path
    original_flock = activity_log.fcntl.flock

    def tracking_flock(fd, operation):
        if operation & activity_log.fcntl.LOCK_EX:
            lock_state["held"] = True
        return original_flock(fd, operation)

    def checking_target_path(target_dir, line_len):
        assert lock_state["held"] is True
        return original_target_path(target_dir, line_len)

    monkeypatch.setattr(activity_log.fcntl, "flock", tracking_flock)
    monkeypatch.setattr(activity_log, "_append_target_path", checking_target_path)

    path = activity_log.append_record(
        activity_log.compose_record(summary="locked append"),
        log_dir=log_dir,
    )

    assert path.exists()
    assert (log_dir / ".append.lock").exists()


def test_append_record_runs_when_fcntl_unavailable(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    monkeypatch.setattr(activity_log, "fcntl", None)

    path = activity_log.append_record(
        activity_log.compose_record(summary="portable append"),
        log_dir=log_dir,
    )

    assert path.exists()


def test_compose_record_reads_documented_alfred_env(monkeypatch):
    monkeypatch.setenv("ALFRED_SESSION_ID", "session-123")
    monkeypatch.setenv("ALFRED_AGENT_VERSION", "agent-9")

    record = activity_log.compose_record(summary="env")

    assert record["session_id"] == "session-123"
    assert record["agent_version"] == "agent-9"


def test_compose_record_generates_session_id_when_missing(monkeypatch):
    monkeypatch.delenv("ALFRED_SESSION_ID", raising=False)
    monkeypatch.delenv("AF_SESSION_ID", raising=False)

    record = activity_log.compose_record(summary="env")

    assert re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        record["session_id"],
    )


def test_iter_records_skips_archive_member_when_loose_file_exists(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    loose = log_dir / "2026-06-20.jsonl"
    loose.write_text(
        json.dumps(activity_log.compose_record(summary="loose")) + "\n",
        encoding="utf-8",
    )
    with ZipFile(log_dir / "archive.zip", "w") as zf:
        zf.writestr(
            "2026-06-20.jsonl",
            json.dumps(activity_log.compose_record(summary="archived")) + "\n",
        )

    records = list(activity_log.iter_records(log_dir))

    assert len(records) == 1
    assert records[0][2]["summary"] == "loose"


def test_archive_directory_replaces_existing_member_once(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    old_file = log_dir / "2026-06-20.jsonl"
    old_file.write_text(
        json.dumps(activity_log.compose_record(summary="new")) + "\n",
        encoding="utf-8",
    )
    with ZipFile(log_dir / "archive.zip", "w") as zf:
        zf.writestr(
            "2026-06-20.jsonl",
            json.dumps(activity_log.compose_record(summary="old")) + "\n",
        )

    activity_log.archive_directory(log_dir, today="2026-06-21")

    with ZipFile(log_dir / "archive.zip") as zf:
        assert zf.namelist() == ["2026-06-20.jsonl"]
        payload = json.loads(zf.read("2026-06-20.jsonl"))
    assert payload["summary"] == "new"


def test_archive_directory_treats_unlink_failure_as_best_effort(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    old_file = log_dir / "2026-06-20.jsonl"
    old_file.write_text(
        json.dumps(activity_log.compose_record(summary="old")) + "\n",
        encoding="utf-8",
    )
    original_unlink = type(old_file).unlink

    def flaky_unlink(self, *args, **kwargs):
        if self.name.endswith(".jsonl"):
            raise PermissionError("leftover raw file")
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(type(old_file), "unlink", flaky_unlink)

    result = activity_log.archive_directory(log_dir, today="2026-06-21")

    assert result.archived_files == ["2026-06-20.jsonl"]
    assert old_file.exists()
    with ZipFile(log_dir / "archive.zip") as zf:
        assert zf.namelist() == ["2026-06-20.jsonl"]


def test_log_dir_resolution_uses_project_rules_log_when_project_exists(sample_project):
    assert activity_log.resolve_log_dir(root=sample_project) == (
        sample_project / "rules" / "logs"
    )


def test_log_dir_resolution_honors_explicit_empty_rules_root(tmp_path):
    (tmp_path / "rules").mkdir()

    assert activity_log.resolve_log_dir(root=tmp_path) == tmp_path / "rules" / "logs"


def test_log_dir_resolution_honors_explicit_root_without_rules_dir(tmp_path):
    assert activity_log.resolve_log_dir(root=tmp_path) == tmp_path / "rules" / "logs"


def test_log_dir_resolution_falls_back_to_user_home_when_no_project_discovered(
    tmp_path,
):
    assert (
        activity_log.resolve_log_dir(root=tmp_path, explicit_root=False)
        == activity_log.user_log_dir()
    )


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
    log_dir.mkdir(parents=True)
    (log_dir / "2026-06-21.jsonl").write_text(
        json.dumps(
            {
                "schema": "alfred.activity/v1",
                "ts": "2026-06-21T00:00:00Z",
                "agent": "other",
                "agent_name": "native-emitter",
                "agent_version": "unknown",
                "event": "note",
                "summary": "plan",
                "session_id": "session",
                "command": "plan",
                "usage_kind": "plan_explicit",
                "refs": ["TST-6101", "TST-6101"],
                "result_count": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    with (log_dir / "2026-06-21.jsonl").open("a", encoding="utf-8") as fh:
        fh.write("{bad json\n")
        fh.write(
            json.dumps(
                {
                    "schema": "alfred.activity/v1",
                    "ts": "2026-06-21T00:01:00Z",
                    "agent": "other",
                    "agent_name": "native-emitter",
                    "agent_version": "unknown",
                    "event": "not-real",
                    "summary": "invalid row must not count",
                    "session_id": "session",
                    "command": "guide",
                    "usage_kind": "routing_docs",
                    "refs": ["TST-6102"],
                    "result_count": 1,
                }
            )
            + "\n"
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
