"""Append-only activity ledger helpers.

Framework-agnostic implementation for the COR-1205 ``alfred.activity/v1``
record family. Click wrappers live in ``commands/log*_cmd.py``; command
telemetry uses ``append_usage_event()`` as a fail-open convenience boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import uuid
import zipfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from fx_alfred.core.document import Document, FILENAME_PATTERN

try:
    import fcntl
except ModuleNotFoundError:  # pragma: no cover - exercised on non-POSIX platforms.
    fcntl = None  # type: ignore[assignment]

SCHEMA_LITERAL = "alfred.activity/v1"
AGENT_WHITELIST = {
    "claude-code",
    "copilot",
    "cursor",
    "cline",
    "aider",
    "codex-cli",
    "gemini-cli",
    "other",
}
EVENT_ENUM = {
    "session.start",
    "session.end",
    "task.start",
    "task.done",
    "task.aborted",
    "doc.created",
    "doc.updated",
    "decision",
    "note",
}
COMMAND_ENUM = {"guide", "plan", "log", "log-validate", "log-archive"}
USAGE_KIND_ENUM = {
    "routing_docs",
    "plan_explicit",
    "plan_task",
    "plan_task_gap",
    "manual_log",
}
OPTIONAL_FIELDS = {
    "refs",
    "files",
    "duration_ms",
    "parent_event",
    "agent_name",
    "command",
    "usage_kind",
    "task_text",
    "task_text_sha256",
    "task_text_redacted",
    "result_count",
    "summary_truncated",
}
REQUIRED_FIELDS = {
    "schema",
    "ts",
    "agent",
    "agent_version",
    "event",
    "summary",
    "session_id",
}
ALLOWED_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS
RECORD_LINE_CAP_BYTES = 4096
FILE_SIZE_CAP_BYTES = 8 * 1024 * 1024
SUMMARY_CAP_CHARS = 500
REFS_CAP = 16
FILES_CAP = 32
TASK_TEXT_CAP_CHARS = 200

_SENSITIVE_RE = re.compile(
    r"""
    (
        (?:api[_-]?key|token|secret|password|authorization|bearer|
           aws[_-]?secret[_-]?access[_-]?key)\s*[:=]\s*\S+
        |
        \bbearer\s+\S+
        |
        \b(?:sk-[A-Za-z0-9_-]{8,}|ghp_[A-Za-z0-9_]{8,}|
           github_pat_[A-Za-z0-9_]{8,}|xox[baprs]-[A-Za-z0-9-]{8,}|
           AKIA[0-9A-Z]{12,})\b
        |
        \b[A-Z][A-Z0-9_]{2,}\s*=\s*\S+
        |
        [A-Za-z][A-Za-z0-9+.-]*://[^\s/:@]+:[^\s/@]+@
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)
_TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
_NO_WHITESPACE_RE = re.compile(r"\S+\Z")
_ASCII_NO_WHITESPACE_RE = re.compile(r"[\x21-\x7e]+\Z")
_DOC_REF_RE = re.compile(r"[A-Z]{3}-\d{4}\Z")


@dataclass(frozen=True)
class Violation:
    """One validation failure."""

    field: str
    reason: str


@dataclass(frozen=True)
class ArchiveResult:
    """Result from ``archive_directory``."""

    archived_files: list[str]
    skipped: bool = False
    message: str = ""


class ArchiveError(Exception):
    """Raised for archive failures the CLI maps to non-zero exits."""


class ActivityLogLineError(Exception):
    """Raised when a raw JSONL line violates ledger framing."""

    def __init__(self, source: str, lineno: int, reason: str) -> None:
        super().__init__(reason)
        self.source = source
        self.lineno = lineno
        self.reason = reason


def _flock(fd: int, operation: int) -> None:
    if fcntl is None:
        return
    fcntl.flock(fd, operation)


def _lock_ex() -> int:
    if fcntl is None:
        return 0
    return fcntl.LOCK_EX


def _lock_nb() -> int:
    if fcntl is None:
        return 0
    return fcntl.LOCK_NB


def _is_json_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_repo_relative_posix_path(value: str) -> bool:
    if not value or value.startswith(("/", "~")):
        return False
    if "\\" in value or "\n" in value or "\x00" in value:
        return False
    parts = value.split("/")
    return all(part not in {"", ".", ".."} for part in parts)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _today_utc() -> str:
    return _utc_now().date().isoformat()


def _rfc3339(dt: datetime) -> str:
    return (
        dt.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def user_log_dir() -> Path:
    """Return the user-layer telemetry ledger directory."""

    return Path.home() / ".alfred" / "logs"


def _is_project_root(root: Path) -> bool:
    rules_dir = root / "rules"
    if not rules_dir.is_dir():
        return False
    try:
        return any(
            entry.is_file()
            and FILENAME_PATTERN.match(entry.name)
            and not entry.name.startswith("COR-")
            for entry in rules_dir.iterdir()
        )
    except OSError:
        return False


def resolve_log_dir(root: Path | None = None, *, explicit_root: bool = True) -> Path:
    """Resolve public ``af log*`` storage using COR-1205 layer semantics."""

    if root is not None and (explicit_root or _is_project_root(root)):
        return root / "rules" / "logs"
    return user_log_dir()


def log_file_for_dir(log_dir: Path, day: str | None = None) -> Path:
    """Return the active loose JSONL file for ``day``."""

    return log_dir / f"{day or _today_utc()}.jsonl"


def sanitize_task_text(raw: str) -> dict[str, Any]:
    """Return safe task-text fields for an activity row."""

    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    collapsed = " ".join(raw.replace("\x00", " ").split())
    if _SENSITIVE_RE.search(collapsed):
        return {"task_text_sha256": digest, "task_text_redacted": True}
    if len(collapsed) > TASK_TEXT_CAP_CHARS:
        collapsed = collapsed[:TASK_TEXT_CAP_CHARS]
        return {
            "task_text": collapsed,
            "task_text_sha256": digest,
            "task_text_redacted": True,
        }
    return {"task_text": collapsed, "task_text_sha256": digest}


def compose_record(
    *,
    summary: str,
    event: str = "note",
    agent: str = "other",
    agent_name: str | None = None,
    agent_version: str | None = None,
    session_id: str | None = None,
    refs: list[str] | tuple[str, ...] | None = None,
    files: list[str] | tuple[str, ...] | None = None,
    command: str | None = None,
    usage_kind: str | None = None,
    task_text: str | None = None,
    result_count: int | None = None,
) -> dict[str, Any]:
    """Compose one canonical activity record."""

    summary_text = " ".join(summary.split())
    summary_truncated = len(summary_text) > SUMMARY_CAP_CHARS
    if summary_truncated:
        summary_text = summary_text[:SUMMARY_CAP_CHARS]

    record: dict[str, Any] = {
        "schema": SCHEMA_LITERAL,
        "ts": _rfc3339(_utc_now()),
        "agent": agent,
        "agent_version": agent_version
        or os.environ.get("ALFRED_AGENT_VERSION")
        or os.environ.get("AF_AGENT_VERSION")
        or "unknown",
        "event": event,
        "summary": summary_text,
        "session_id": session_id
        or os.environ.get("ALFRED_SESSION_ID")
        or os.environ.get("AF_SESSION_ID")
        or str(uuid.uuid4()),
    }
    if agent_name is not None or agent == "other":
        record["agent_name"] = agent_name or "af"
    if summary_truncated:
        record["summary_truncated"] = True
    if refs:
        record["refs"] = list(dict.fromkeys(refs))[:REFS_CAP]
    if files:
        record["files"] = list(dict.fromkeys(files))[:FILES_CAP]
    if command:
        record["command"] = command
    if usage_kind:
        record["usage_kind"] = usage_kind
    if task_text is not None:
        record.update(sanitize_task_text(task_text))
    if result_count is not None:
        record["result_count"] = result_count
    return record


def _line_bytes(record: dict[str, Any]) -> bytes:
    return (
        json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _fit_record_line(record: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    fitted = dict(record)
    line = _line_bytes(fitted)
    while len(line) > RECORD_LINE_CAP_BYTES:
        fitted["summary_truncated"] = True
        files = fitted.get("files")
        refs = fitted.get("refs")
        summary = str(fitted.get("summary", ""))
        if isinstance(files, list) and files:
            files.pop()
            if not files:
                fitted.pop("files", None)
        elif isinstance(refs, list) and refs:
            refs.pop()
            if not refs:
                fitted.pop("refs", None)
        elif "task_text" in fitted:
            fitted.pop("task_text", None)
            fitted["task_text_redacted"] = True
        elif len(summary) > 1:
            fitted["summary"] = summary[: max(1, len(summary) // 2)]
        else:
            raise ValueError("activity record cannot fit within line cap")
        line = _line_bytes(fitted)
    return fitted, line


def _append_target_path(log_dir: Path, line_len: int) -> Path:
    base = log_file_for_dir(log_dir)
    if not base.exists() or base.stat().st_size + line_len <= FILE_SIZE_CAP_BYTES:
        return base
    part = 1
    while True:
        candidate = log_dir / f"{base.stem}.part{part}.jsonl"
        if (
            not candidate.exists()
            or candidate.stat().st_size + line_len <= FILE_SIZE_CAP_BYTES
        ):
            return candidate
        part += 1


def _append_lock_path(log_dir: Path) -> Path:
    return log_dir / ".append.lock"


def append_record(record: dict[str, Any], *, log_dir: Path | None = None) -> Path:
    """Append ``record`` to the active loose JSONL file."""

    target_dir = log_dir or user_log_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    _record, line = _fit_record_line(record)
    with _append_lock_path(target_dir).open("w", encoding="utf-8") as lock_fh:
        _flock(lock_fh.fileno(), _lock_ex())
        path = _append_target_path(target_dir, len(line))
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            os.write(fd, line)
        finally:
            os.close(fd)
    return path


def append_usage_event(
    *,
    command: str,
    usage_kind: str,
    refs: list[str] | tuple[str, ...] | None = None,
    task_text: str | None = None,
    result_count: int | None = None,
) -> Path | None:
    """Append first-party command telemetry to the user-layer ledger."""

    record = compose_record(
        summary=f"af {command} {usage_kind}",
        command=command,
        usage_kind=usage_kind,
        refs=refs,
        task_text=task_text,
        result_count=result_count,
    )
    if validate_record(record):
        return None
    return append_record(record, log_dir=user_log_dir())


def validate_record(record: dict[str, Any]) -> list[Violation]:
    """Validate one activity record."""

    violations: list[Violation] = []
    for field in sorted(REQUIRED_FIELDS - record.keys()):
        violations.append(Violation(field, "required field missing"))
    for field in sorted(record.keys() - ALLOWED_FIELDS):
        violations.append(Violation(field, "unknown field"))
    if record.get("schema") != SCHEMA_LITERAL:
        violations.append(Violation("schema", f"must be {SCHEMA_LITERAL}"))
    ts = record.get("ts")
    if not isinstance(ts, str) or not _TS_RE.fullmatch(ts):
        violations.append(Violation("ts", "must be RFC 3339 UTC timestamp"))
    else:
        try:
            datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            violations.append(Violation("ts", "must be valid UTC timestamp"))
    summary = record.get("summary")
    if (
        not isinstance(summary, str)
        or not summary
        or len(summary) > SUMMARY_CAP_CHARS
        or "\n" in summary
        or "\x00" in summary
    ):
        violations.append(Violation("summary", "invalid summary"))
    agent_version = record.get("agent_version")
    if (
        not isinstance(agent_version, str)
        or not (1 <= len(agent_version) <= 64)
        or not _ASCII_NO_WHITESPACE_RE.fullmatch(agent_version)
    ):
        violations.append(Violation("agent_version", "invalid agent version"))
    session_id = record.get("session_id")
    if (
        not isinstance(session_id, str)
        or not (1 <= len(session_id) <= 128)
        or not _NO_WHITESPACE_RE.fullmatch(session_id)
    ):
        violations.append(Violation("session_id", "invalid session id"))
    if record.get("agent") not in AGENT_WHITELIST:
        violations.append(Violation("agent", "unknown agent"))
    agent_name = record.get("agent_name")
    if record.get("agent") == "other" and not agent_name:
        violations.append(Violation("agent_name", "required when agent is other"))
    if record.get("agent") != "other" and "agent_name" in record:
        violations.append(
            Violation("agent_name", "must be omitted unless agent is other")
        )
    if "agent_name" in record and (
        not isinstance(agent_name, str)
        or not (1 <= len(agent_name) <= 64)
        or not _ASCII_NO_WHITESPACE_RE.fullmatch(agent_name)
    ):
        violations.append(Violation("agent_name", "invalid agent name"))
    if record.get("event") not in EVENT_ENUM:
        violations.append(Violation("event", "unknown event"))
    if "command" in record and record["command"] not in COMMAND_ENUM:
        violations.append(Violation("command", "unknown command"))
    if "usage_kind" in record and record["usage_kind"] not in USAGE_KIND_ENUM:
        violations.append(Violation("usage_kind", "unknown usage kind"))
    if "task_text" in record:
        task_text = record["task_text"]
        if not isinstance(task_text, str) or len(task_text) > TASK_TEXT_CAP_CHARS:
            violations.append(Violation("task_text", "invalid task text"))
        elif (
            "\n" in task_text or "\x00" in task_text or _SENSITIVE_RE.search(task_text)
        ):
            violations.append(Violation("task_text", "unsafe task text"))
    if "task_text_sha256" in record:
        digest = record["task_text_sha256"]
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            violations.append(Violation("task_text_sha256", "invalid digest"))
    if "task_text_redacted" in record and record["task_text_redacted"] is not True:
        violations.append(Violation("task_text_redacted", "must be true if present"))
    if "summary_truncated" in record and record["summary_truncated"] is not True:
        violations.append(Violation("summary_truncated", "must be true if present"))
    if "result_count" in record:
        count = record["result_count"]
        if not _is_json_integer(count) or count < 0:
            violations.append(Violation("result_count", "must be non-negative integer"))
    if "duration_ms" in record:
        duration = record["duration_ms"]
        if not _is_json_integer(duration) or not (0 <= duration <= 86_400_000):
            violations.append(
                Violation("duration_ms", "must be integer between 0 and 86400000")
            )
    if "parent_event" in record:
        parent_event = record["parent_event"]
        if (
            not isinstance(parent_event, str)
            or not (1 <= len(parent_event) <= 128)
            or not _NO_WHITESPACE_RE.fullmatch(parent_event)
        ):
            violations.append(Violation("parent_event", "invalid correlation id"))
    for list_field, cap in (("refs", REFS_CAP), ("files", FILES_CAP)):
        if list_field not in record:
            continue
        value = record[list_field]
        if not isinstance(value, list) or len(value) > cap:
            violations.append(Violation(list_field, f"must be list of at most {cap}"))
        elif not all(isinstance(item, str) for item in value):
            violations.append(Violation(list_field, "must contain strings"))
        elif list_field == "refs" and not all(
            _DOC_REF_RE.fullmatch(item) for item in value
        ):
            violations.append(Violation("refs", "must contain canonical document ids"))
        elif list_field == "files" and not all(
            _is_repo_relative_posix_path(item) for item in value
        ):
            violations.append(Violation("files", "must contain repo-relative paths"))
    return violations


def _jsonl_files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.glob("*.jsonl") if p.is_file())


def _merge_jsonl_payloads(existing: bytes, loose: bytes) -> bytes:
    """Multiset-union two JSONL payloads, existing rows first, by raw line bytes.

    Existing rows are preserved verbatim (including byte-identical
    duplicates — a legitimate ledger state given second-resolution ``ts``
    and env-pinned ``session_id``); each loose row suppresses at most one
    matching existing occurrence, so per-row multiplicity is
    ``max(existing_count, loose_count)``.  Identity is byte-level
    (``splitlines()`` content), so a restored byte-identical file merges to
    an unchanged member and CRLF/LF variants of one row count as the same
    row.
    """
    rows = [row for row in existing.splitlines() if row.strip()]
    remaining = Counter(rows)
    for row in loose.splitlines():
        if not row.strip():
            continue
        if remaining[row] > 0:
            remaining[row] -= 1
            continue
        rows.append(row)
    if not rows:
        return b""
    return b"\n".join(rows) + b"\n"


def _shadow_line_counts(payload: bytes) -> Counter[bytes]:
    """Count non-blank raw lines (terminator-stripped)."""

    return Counter(row for row in payload.splitlines() if row.strip())


def _iter_member_lines(
    zf: zipfile.ZipFile, member: str, suppress: Counter[bytes] | None
) -> Iterator[tuple[int, bytes]]:
    """Yield ``(lineno, raw)`` member rows, skipping blanks and shadowed rows.

    ``suppress`` counts rows a same-named loose file already yielded; each
    match consumes one occurrence so only rows the loose copy lacks remain
    (merge-then-failed-unlink or restore-before-re-archive states).
    """

    with zf.open(member) as fh:
        for lineno, raw in enumerate(fh, start=1):
            if not raw.strip():
                continue
            if suppress is not None and suppress[raw.rstrip(b"\r\n")] > 0:
                suppress[raw.rstrip(b"\r\n")] -= 1
                continue
            yield lineno, raw


def _iter_zip_members(
    zf: zipfile.ZipFile, shadow: dict[str, Counter[bytes]]
) -> Iterator[tuple[str, Counter[bytes] | None]]:
    """Yield each ``.jsonl`` member once, with its shadow-suppression counts."""

    seen: set[str] = set()
    for member in sorted(zf.namelist()):
        if not member.endswith(".jsonl") or member in seen:
            continue
        seen.add(member)
        yield member, shadow.get(member)


def _iter_zip_records(
    path: Path, *, shadowed: dict[str, Counter[bytes]] | None = None
) -> Iterator[tuple[str, int, dict[str, Any]]]:
    with zipfile.ZipFile(path) as zf:
        for member, suppress in _iter_zip_members(zf, shadowed or {}):
            source = f"{path}::{member}"
            for lineno, raw in _iter_member_lines(zf, member, suppress):
                yield (source, lineno, _parse_jsonl_record(source, lineno, raw))


def _iter_jsonl_payload_records(
    source: str, payload: bytes, *, best_effort: bool = False
) -> Iterator[tuple[str, int, dict[str, Any]]]:
    for lineno, raw in enumerate(payload.splitlines(keepends=True), start=1):
        if not raw.strip():
            continue
        try:
            yield (source, lineno, _parse_jsonl_record(source, lineno, raw))
        except ActivityLogLineError:
            if best_effort:
                continue
            raise


def _parse_jsonl_record(source: str, lineno: int, raw: bytes) -> dict[str, Any]:
    if len(raw) > RECORD_LINE_CAP_BYTES:
        raise ActivityLogLineError(source, lineno, "JSONL line exceeds 4096 bytes")
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ActivityLogLineError(source, lineno, f"invalid UTF-8: {exc}") from exc
    try:
        record = json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise ActivityLogLineError(source, lineno, f"invalid JSONL: {exc}") from exc
    if not isinstance(record, dict):
        raise ActivityLogLineError(source, lineno, "JSONL record must be an object")
    return record


def _archive_tmp_is_stale(path: Path) -> bool:
    match = re.fullmatch(r"archive\.zip\.tmp\.(\d+)\..+", path.name)
    if match is None:
        return False
    pid = int(match.group(1))
    if pid == os.getpid():
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    except OSError:
        return False
    return False


def _cleanup_stale_archive_tmps(log_dir: Path) -> None:
    for stale in log_dir.glob("archive.zip.tmp.*"):
        if _archive_tmp_is_stale(stale):
            try:
                stale.unlink()
            except OSError:
                pass


def iter_records(path: Path) -> Iterator[tuple[str, int, dict[str, Any]]]:
    """Yield ``(source, line_number, record)`` from a file, dir, or zip archive."""

    if not path.exists():
        return
    if path.is_dir():
        loose_files = _jsonl_files(path)
        shadowed: dict[str, Counter[bytes]] = {}
        for file_path in loose_files:
            try:
                payload = file_path.read_bytes()
            except FileNotFoundError:
                continue
            shadowed[file_path.name] = _shadow_line_counts(payload)
            yield from _iter_jsonl_payload_records(str(file_path), payload)
        archive = path / "archive.zip"
        if archive.exists():
            yield from _iter_zip_records(archive, shadowed=shadowed)
        return
    if path.suffix == ".zip":
        yield from _iter_zip_records(path)
        return
    with path.open("rb") as fh:
        for lineno, raw in enumerate(fh, start=1):
            if raw.strip():
                yield (
                    str(path),
                    lineno,
                    _parse_jsonl_record(str(path), lineno, raw),
                )


def _iter_zip_records_best_effort(
    path: Path, *, shadowed: dict[str, Counter[bytes]] | None = None
) -> Iterator[tuple[str, int, dict[str, Any]]]:
    try:
        with zipfile.ZipFile(path) as zf:
            for member, suppress in _iter_zip_members(zf, shadowed or {}):
                source = f"{path}::{member}"
                for lineno, raw in _iter_member_lines(zf, member, suppress):
                    try:
                        yield (source, lineno, _parse_jsonl_record(source, lineno, raw))
                    except ActivityLogLineError:
                        continue
    except (OSError, zipfile.BadZipFile):
        return


def _iter_records_best_effort(
    path: Path,
) -> Iterator[tuple[str, int, dict[str, Any]]]:
    """Yield parseable records while skipping corrupt ledger rows."""

    if not path.exists():
        return
    if path.is_dir():
        loose_files = _jsonl_files(path)
        shadowed: dict[str, Counter[bytes]] = {}
        for file_path in loose_files:
            try:
                payload = file_path.read_bytes()
            except OSError:
                continue
            shadowed[file_path.name] = _shadow_line_counts(payload)
            yield from _iter_jsonl_payload_records(
                str(file_path), payload, best_effort=True
            )
        archive = path / "archive.zip"
        if archive.exists():
            yield from _iter_zip_records_best_effort(archive, shadowed=shadowed)
        return
    if path.suffix == ".zip":
        yield from _iter_zip_records_best_effort(path)
        return
    try:
        with path.open("rb") as fh:
            for lineno, raw in enumerate(fh, start=1):
                if not raw.strip():
                    continue
                try:
                    yield (
                        str(path),
                        lineno,
                        _parse_jsonl_record(str(path), lineno, raw),
                    )
                except ActivityLogLineError:
                    continue
    except OSError:
        return


def archive_directory(
    log_dir: Path, *, today: str | None = None, force: bool = False
) -> ArchiveResult:
    """Move closed-day loose JSONL files into ``archive.zip`` atomically."""

    day = today or _today_utc()
    log_dir.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(log_dir, os.O_RDONLY) if fcntl is not None else None
    append_lock_fd: int | None = None
    try:
        try:
            if lock_fd is not None:
                _flock(lock_fd, _lock_ex() | _lock_nb())
        except BlockingIOError:
            return ArchiveResult(
                [], skipped=True, message="another archiver is running, skipping"
            )

        if lock_fd is not None:
            append_lock_fd = os.open(
                _append_lock_path(log_dir), os.O_WRONLY | os.O_CREAT, 0o644
            )
            _flock(append_lock_fd, _lock_ex())

        _cleanup_stale_archive_tmps(log_dir)
        archive = log_dir / "archive.zip"
        existing: dict[str, bytes] = {}
        archive_was_corrupt = False
        if archive.exists():
            try:
                with zipfile.ZipFile(archive) as zf:
                    existing = {name: zf.read(name) for name in zf.namelist()}
            except zipfile.BadZipFile as exc:
                if not force:
                    raise ArchiveError(
                        "corrupt archive.zip; rerun with --force"
                    ) from exc
                archive_was_corrupt = True

        closed = [p for p in _jsonl_files(log_dir) if p.name.split(".")[0] < day]
        if not closed and not archive_was_corrupt:
            return ArchiveResult([], message="nothing to archive")

        fd, tmp_name = tempfile.mkstemp(
            prefix=f"archive.zip.tmp.{os.getpid()}.", dir=log_dir
        )
        has_fchmod = hasattr(os, "fchmod")
        if has_fchmod:
            os.fchmod(fd, 0o644)
        os.close(fd)
        if not has_fchmod:
            os.chmod(tmp_name, 0o644)
        tmp_path = Path(tmp_name)
        try:
            with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                closed_names = {file_path.name for file_path in closed}
                closed_by_name = {file_path.name: file_path for file_path in closed}
                merged_names: set[str] = set()
                for name, payload in sorted(existing.items()):
                    if name in closed_names:
                        loose_payload = closed_by_name[name].read_bytes()
                        zf.writestr(name, _merge_jsonl_payloads(payload, loose_payload))
                        merged_names.add(name)
                        continue
                    zf.writestr(name, payload)
                for file_path in closed:
                    if file_path.name in merged_names:
                        continue
                    zf.write(file_path, arcname=file_path.name)
            os.replace(tmp_path, archive)
            for file_path in closed:
                try:
                    file_path.unlink()
                except OSError:
                    pass
        finally:
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass

        _cleanup_stale_archive_tmps(log_dir)
        return ArchiveResult([p.name for p in closed])
    finally:
        if append_lock_fd is not None:
            os.close(append_lock_fd)
        if lock_fd is not None:
            os.close(lock_fd)


def _in_date_window(
    record: dict[str, Any], since: str | None, until: str | None
) -> bool:
    day = str(record.get("ts", ""))[:10]
    if since is not None and day < since:
        return False
    if until is not None and day > until:
        return False
    return True


def collect_evolve_signals(
    docs: list[Document],
    *,
    log_dir: Path | None = None,
    since: str | None = None,
    until: str | None = None,
) -> dict[str, Any]:
    """Aggregate activity-ledger signals consumed by the Evolve SOP."""

    target = log_dir or user_log_dir()
    sop_ids = {f"{doc.prefix}-{doc.acid}" for doc in docs if doc.type_code == "SOP"}
    usage_counts: dict[str, int] = {}
    plan_task_gaps: list[dict[str, Any]] = []

    if target.exists():
        for _source, _lineno, record in _iter_records_best_effort(target):
            if not _in_date_window(record, since, until):
                continue
            if validate_record(record):
                continue
            command = record.get("command")
            usage_kind = record.get("usage_kind")
            if command in {"guide", "plan"}:
                for ref in dict.fromkeys(record.get("refs", [])):
                    if ref in sop_ids:
                        usage_counts[ref] = usage_counts.get(ref, 0) + 1
            if command == "plan" and usage_kind == "plan_task_gap":
                plan_task_gaps.append(
                    {
                        key: record[key]
                        for key in (
                            "ts",
                            "task_text",
                            "task_text_sha256",
                            "task_text_redacted",
                            "result_count",
                        )
                        if key in record
                    }
                )

    never_used = sorted(sop_ids - usage_counts.keys())
    return {
        "usage_counts": dict(sorted(usage_counts.items())),
        "plan_task_gaps": plan_task_gaps,
        "never_used_sops": never_used,
    }
