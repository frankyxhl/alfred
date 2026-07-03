"""Tests for the append-only activity ledger (FXA-2307)."""

from __future__ import annotations

import json
import os
import re
import threading
from zipfile import ZipFile

import pytest

from fx_alfred.core import activity_log
from fx_alfred.core.scanner import scan_documents


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers for archive-merge tests (FXA-264)
# ---------------------------------------------------------------------------


def _make_test_record(summary, ts="2026-06-20T12:00:00Z", session_id="test-session-1"):
    """Build a minimal valid record with deterministic fields for merge tests."""
    return {
        "schema": "alfred.activity/v1",
        "ts": ts,
        "agent": "other",
        "agent_name": "af",
        "agent_version": "test",
        "event": "note",
        "summary": summary,
        "session_id": session_id,
    }


def _record_line(record):
    """Serialize one record to its JSONL line bytes (with trailing newline).

    Matches the format produced by ``activity_log._line_bytes``.
    """
    return (
        json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")


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
    # Dir fd first (archiver-vs-archiver), then .append.lock (appender
    # mutual exclusion, issue #263).
    append_lock = activity_log._append_lock_path(log_dir)
    assert locked_inodes == [log_dir.stat().st_ino, append_lock.stat().st_ino]
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


def test_iter_records_unions_shadowed_archive_member(tmp_path):
    """PR #290 R2: a shadowed member yields rows the loose file lacks.

    After a merge-then-failed-unlink (or a restore before re-archive), the
    member can hold rows that exist only in the archive; hiding the whole
    member behind the loose file would lose them from every reader.
    """
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    shared_line = json.dumps(activity_log.compose_record(summary="loose")) + "\n"
    loose = log_dir / "2026-06-20.jsonl"
    loose.write_text(shared_line, encoding="utf-8")
    with ZipFile(log_dir / "archive.zip", "w") as zf:
        zf.writestr(
            "2026-06-20.jsonl",
            shared_line
            + json.dumps(activity_log.compose_record(summary="archived"))
            + "\n",
        )

    records = list(activity_log.iter_records(log_dir))

    summaries = [rec[2]["summary"] for rec in records]
    assert sorted(summaries) == ["archived", "loose"]


def test_iter_records_does_not_double_count_shadowed_identical_member(tmp_path):
    """Guard: loose row also present in the member is yielded exactly once."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    shared_line = json.dumps(activity_log.compose_record(summary="loose")) + "\n"
    loose = log_dir / "2026-06-20.jsonl"
    loose.write_text(shared_line, encoding="utf-8")
    with ZipFile(log_dir / "archive.zip", "w") as zf:
        zf.writestr("2026-06-20.jsonl", shared_line)

    records = list(activity_log.iter_records(log_dir))

    assert len(records) == 1
    assert records[0][2]["summary"] == "loose"


def test_iter_records_best_effort_unions_shadowed_archive_member(tmp_path):
    """PR #290 R2: best-effort reader also unions shadowed members."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    shared_line = json.dumps(activity_log.compose_record(summary="loose")) + "\n"
    loose = log_dir / "2026-06-20.jsonl"
    loose.write_text(shared_line, encoding="utf-8")
    with ZipFile(log_dir / "archive.zip", "w") as zf:
        zf.writestr(
            "2026-06-20.jsonl",
            shared_line
            + json.dumps(activity_log.compose_record(summary="archived"))
            + "\n",
        )

    records = list(activity_log._iter_records_best_effort(log_dir))

    summaries = [rec[2]["summary"] for rec in records]
    assert sorted(summaries) == ["archived", "loose"]


def test_merge_preserves_existing_member_duplicate_rows(tmp_path):
    """PR #290 R2: existing member's duplicate identical rows survive a merge.

    Byte-identical rows are a legitimate ledger state (second-resolution ts,
    env-pinned session_id); the merge must not collapse the archive's own
    multiplicity — only suppress loose copies already covered by existing.
    """
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    row = json.dumps(activity_log.compose_record(summary="dup")) + "\n"
    with ZipFile(log_dir / "archive.zip", "w") as zf:
        zf.writestr("2026-06-20.jsonl", row + row)
    loose = log_dir / "2026-06-20.jsonl"
    loose.write_text(row, encoding="utf-8")

    activity_log.archive_directory(log_dir, today="2026-06-21")

    with ZipFile(log_dir / "archive.zip") as zf:
        assert zf.namelist() == ["2026-06-20.jsonl"]
        payload = zf.read("2026-06-20.jsonl")
    assert payload == row.encode("utf-8") * 2


def test_archive_directory_merges_existing_member_once(tmp_path):
    """Colliding member + loose file → both rows preserved, member listed once."""
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
        payload = zf.read("2026-06-20.jsonl")
    # Merge contract (FXA-264): both "old" and "new" rows preserved,
    # existing-member-first order, member appears exactly once.
    lines = payload.decode("utf-8").splitlines()
    summaries = [json.loads(line)["summary"] for line in lines]
    assert summaries == ["old", "new"]


# ---------------------------------------------------------------------------
# FXA-264: archive merge-member tests (RED on current unfixed code)
# ---------------------------------------------------------------------------


def test_archive_directory_merges_divergent_rows(tmp_path):
    """archive.zip[r1,r2] + reappeared-loose[r2,r3] → merged r1,r2,r3 (deduped)."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    r1 = _make_test_record("row1")
    r2 = _make_test_record("row2")
    r3 = _make_test_record("row3")
    r1_line = _record_line(r1)
    r2_line = _record_line(r2)
    r3_line = _record_line(r3)

    with ZipFile(log_dir / "archive.zip", "w") as zf:
        zf.writestr("2026-06-20.jsonl", r1_line + r2_line)

    loose = log_dir / "2026-06-20.jsonl"
    loose.write_bytes(r2_line + r3_line)

    result = activity_log.archive_directory(log_dir, today="2026-06-21")

    assert result.archived_files == ["2026-06-20.jsonl"]
    assert not loose.exists()

    with ZipFile(log_dir / "archive.zip") as zf:
        assert zf.namelist() == ["2026-06-20.jsonl"]
        payload = zf.read("2026-06-20.jsonl")

    # Must contain r1,r2,r3 in existing-first order, each exactly once.
    lines = payload.splitlines()
    summaries = [json.loads(line)["summary"] for line in lines]
    assert summaries == ["row1", "row2", "row3"]


def test_archive_directory_noop_on_identical_restore(tmp_path):
    """Byte-identical loose file → content unchanged, rows NOT duplicated.

    On current (unfixed) code the existing member is replaced with the
    identical loose-file bytes, so this test passes today.  It is kept as a
    contract guard to ensure the merge path does not accidentally duplicate.
    """
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    r1 = _make_test_record("row1")
    r2 = _make_test_record("row2")
    r3 = _make_test_record("row3")
    content = _record_line(r1) + _record_line(r2) + _record_line(r3)

    with ZipFile(log_dir / "archive.zip", "w") as zf:
        zf.writestr("2026-06-20.jsonl", content)

    loose = log_dir / "2026-06-20.jsonl"
    loose.write_bytes(content)

    activity_log.archive_directory(log_dir, today="2026-06-21")

    assert not loose.exists()
    with ZipFile(log_dir / "archive.zip") as zf:
        payload = zf.read("2026-06-20.jsonl")

    lines = payload.splitlines()
    assert len(lines) == 3
    summaries = [json.loads(line)["summary"] for line in lines]
    assert summaries == ["row1", "row2", "row3"]


def test_archive_directory_handles_missing_trailing_newline_in_existing_member(
    tmp_path,
):
    """Existing member without trailing newline still merges — no concatenated row."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    r_old = _make_test_record("old-row")
    r_new = _make_test_record("new-row")

    # Write existing member payload WITHOUT trailing newline via zipfile.
    old_bytes = json.dumps(r_old, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    with ZipFile(log_dir / "archive.zip", "w") as zf:
        zf.writestr("2026-06-20.jsonl", old_bytes)

    loose = log_dir / "2026-06-20.jsonl"
    loose.write_bytes(_record_line(r_new))

    activity_log.archive_directory(log_dir, today="2026-06-21")

    assert not loose.exists()

    archive_path = log_dir / "archive.zip"
    records = list(activity_log.iter_records(archive_path))
    summaries = {r[2]["summary"] for r in records}

    assert len(records) == 2
    assert summaries == {"old-row", "new-row"}
    for _, _, rec in records:
        assert activity_log.validate_record(rec) == []


def test_archive_directory_merged_records_pass_validation(tmp_path):
    """Every record yielded by iter_records on merged archive passes validate_record."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    r1 = _make_test_record("row1")
    r2 = _make_test_record("row2")
    r3 = _make_test_record("row3")

    with ZipFile(log_dir / "archive.zip", "w") as zf:
        zf.writestr("2026-06-20.jsonl", _record_line(r1) + _record_line(r2))

    loose = log_dir / "2026-06-20.jsonl"
    loose.write_bytes(_record_line(r2) + _record_line(r3))

    activity_log.archive_directory(log_dir, today="2026-06-21")

    archive_path = log_dir / "archive.zip"
    records = list(activity_log.iter_records(archive_path))

    assert len(records) == 3
    for _, _, rec in records:
        assert activity_log.validate_record(rec) == []


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


# ---------------------------------------------------------------------------
# FXA-263: unify append/archive locking — contention + no-lost-record tests
# ---------------------------------------------------------------------------


def test_archive_directory_acquires_append_lock_for_mutual_exclusion(
    tmp_path, monkeypatch
):
    """Prove archiver acquires .append.lock — RED on current code.

    An external thread holds an exclusive flock on .append.lock.
    The archiver must attempt to acquire it and block.  On current
    (unfixed) code the archiver never touches .append.lock, so the
    ``archiver_blocked`` Event is never set and the test fails.
    """
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    old_file = log_dir / "2026-06-20.jsonl"
    old_file.write_text(
        json.dumps(activity_log.compose_record(summary="old")) + "\n",
        encoding="utf-8",
    )

    # Open the append-lock file ourselves so we can detect when the
    # archiver tries to flock it (by matching inode).
    append_lock_path = activity_log._append_lock_path(log_dir)
    append_lock_fd = os.open(str(append_lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    append_lock_ino = os.fstat(append_lock_fd).st_ino

    archiver_blocked = threading.Event()
    archiver_done = threading.Event()
    archiver_running = threading.Event()
    result_container: list = []

    original_flock = activity_log.fcntl.flock

    def instrumented_flock(fd, operation):
        # Only flag the archiver's own call — not the external holder's.
        if archiver_running.is_set() and (operation & activity_log.fcntl.LOCK_EX):
            try:
                if os.fstat(fd).st_ino == append_lock_ino:
                    archiver_blocked.set()
            except OSError:
                pass
        return original_flock(fd, operation)

    monkeypatch.setattr(activity_log.fcntl, "flock", instrumented_flock)

    # Hold an exclusive flock on .append.lock from a separate thread.
    external_lock_held = threading.Event()
    release_lock = threading.Event()

    def hold_lock():
        activity_log._flock(append_lock_fd, activity_log._lock_ex())
        external_lock_held.set()
        release_lock.wait(timeout=5)
        activity_log._flock(append_lock_fd, activity_log.fcntl.LOCK_UN)

    holder = threading.Thread(target=hold_lock, daemon=True)
    holder.start()
    assert external_lock_held.wait(timeout=2), "external lock holder did not start"

    # Run archive_directory in a background thread.
    def do_archive():
        archiver_running.set()
        result_container.append(
            activity_log.archive_directory(log_dir, today="2026-06-21")
        )
        archiver_done.set()

    archiver = threading.Thread(target=do_archive)
    archiver.start()

    # The archiver must block on .append.lock — on current code it
    # never touches that file, so this wait times out → RED.
    blocked = archiver_blocked.wait(timeout=2)
    assert blocked, (
        "archiver should attempt to acquire .append.lock — "
        "on unfixed code it never touches it"
    )
    assert not archiver_done.is_set(), (
        "archiver should not complete while append lock is held externally"
    )

    # Release the external lock; archiver should now proceed.
    release_lock.set()
    assert archiver_done.wait(timeout=2), "archiver did not complete after unlock"
    result = result_container[0]
    assert result.archived_files == ["2026-06-20.jsonl"]

    os.close(append_lock_fd)
    holder.join(timeout=2)
    archiver.join(timeout=2)


def test_append_during_archive_is_not_lost(tmp_path, monkeypatch):
    """A record appended during archival must survive somewhere.

    On current (unfixed) code the archiver and appender use disjoint
    lock domains.  An append that lands between ``os.replace`` and the
    ``unlink`` loop is written to the loose file and then deleted —
    the record is lost.  This test injects a concurrent append at
    exactly that point and asserts the record is found in either the
    archive or a loose file afterward.

    On the fixed code the archiver holds ``.append.lock`` across its
    critical section, so the appender blocks until the archiver
    releases, then writes a fresh loose file.
    """
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    # Closed-day file with one pre-existing record.
    closed_file = log_dir / "2026-06-20.jsonl"
    closed_file.write_text(
        json.dumps(activity_log.compose_record(summary="existing")) + "\n",
        encoding="utf-8",
    )

    # Make append_record target the same closed-day file being archived.
    monkeypatch.setattr(activity_log, "_today_utc", lambda: "2026-06-20")

    go_appender = threading.Event()
    appender_done = threading.Event()
    appender_path: list[str] = []

    # Instrument os.replace so the appender is triggered AFTER the
    # real atomic replace but BEFORE the archiver's unlink loop.
    original_replace = activity_log.os.replace

    def instrumented_replace(src, dst):
        original_replace(src, dst)
        go_appender.set()
        # Wait for the appender to finish (or block on the lock,
        # which on fixed code means this times out).
        appender_done.wait(timeout=2)

    monkeypatch.setattr(activity_log.os, "replace", instrumented_replace)

    def run_appender():
        go_appender.wait(timeout=2)
        path = activity_log.append_record(
            activity_log.compose_record(summary="concurrent-append"),
            log_dir=log_dir,
        )
        appender_path.append(str(path))
        appender_done.set()

    appender = threading.Thread(target=run_appender, daemon=True)
    appender.start()

    # Run the archiver in the main thread.
    result = activity_log.archive_directory(log_dir, today="2026-06-21")
    assert result.archived_files == ["2026-06-20.jsonl"]

    appender.join(timeout=2)

    # The concurrent record must be discoverable somewhere.
    found = False

    # Check any loose file that still exists.
    for candidate in sorted(log_dir.glob("*.jsonl")):
        for _src, _lineno, rec in activity_log.iter_records(candidate):
            if rec.get("summary") == "concurrent-append":
                found = True
                break
        if found:
            break

    # Check archive.zip members.
    if not found:
        archive = log_dir / "archive.zip"
        if archive.exists():
            for _src, _lineno, rec in activity_log.iter_records(archive):
                if rec.get("summary") == "concurrent-append":
                    found = True
                    break

    assert found, (
        "concurrent-append record must exist in archive.zip or a loose file — "
        "on unfixed code it was written to the loose file before the unlink "
        "and is now lost"
    )


def test_archive_and_append_succeed_when_fcntl_unavailable(tmp_path, monkeypatch):
    """Guard: both archive and append succeed on fcntl-None platforms.

    This is expected to pass on both current and fixed code — the fix
    does not change the no-op locking behaviour when fcntl is absent.
    """
    monkeypatch.setattr(activity_log, "fcntl", None)

    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    closed_file = log_dir / "2026-06-20.jsonl"
    closed_file.write_text(
        json.dumps(activity_log.compose_record(summary="old")) + "\n",
        encoding="utf-8",
    )

    # Archive must succeed.
    result = activity_log.archive_directory(log_dir, today="2026-06-21")
    assert result.archived_files == ["2026-06-20.jsonl"]
    assert not closed_file.exists()

    # Append must succeed (targets today's file — let it write normally).
    path = activity_log.append_record(
        activity_log.compose_record(summary="portable-append"),
        log_dir=log_dir,
    )
    assert path.exists()

    # Verify both records are readable.
    records = list(activity_log.iter_records(log_dir))
    summaries = {r[2]["summary"] for r in records}
    assert "old" in summaries
    assert "portable-append" in summaries
