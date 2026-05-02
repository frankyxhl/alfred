# REF-1205: Agent Activity Log Format

**Applies to:** All projects using the COR document system
**Last updated:** 2026-05-02
**Last reviewed:** 2026-05-02
**Status:** Active
**Related:** COR-1206 (Emit Agent Activity SOP), COR-1200 (Session Retrospective — log consumer), PRP-2230 (originating proposal)

---

## What Is It?

The canonical data contract for the Alfred activity log protocol. Defines the on-disk format, schema (`alfred.activity/v1`), required + optional fields, event enum, file rotation, archival procedure, and operational constraints. Any coding agent — Claude Code, GitHub Copilot, Cursor, Cline, Aider, Codex CLI, Gemini CLI, or any future tool — emits structured events to this format so "what was done in this session" becomes machine-readable across tools.

This document defines the **format**. The **emit protocol** (mandatory triggers, per-agent integration recipes, scanner-skip enforcement) lives in COR-1206. The **CLI surfaces** that read and write this format are `af log`, `af log-validate`, `af log-archive` (shipped in fx-alfred v1.9.0).

---

## Why

Without a stable cross-tool format, each agent's session work lives in a private store and `COR-1200` step 1 reduces to chat-history recollection. Standardizing the format unlocks:
- Shared session memory across agents (Claude Code morning, Cursor afternoon, Copilot evening — one trail).
- Replay-not-recall retrospectives (`COR-1200` step 1 reads the log).
- Forensic auditability of agent behavior (append-only, schema-validated, line-atomic).

---

## Storage Location

- **PRJ layer**: `./rules/logs/YYYY-MM-DD.jsonl` (one file per UTC day in the project)
- **USR layer fallback**: `~/.alfred/logs/YYYY-MM-DD.jsonl` when no project context resolves

The `rules/logs/` subtree is **reserved**: all `af` document scanners — present (`af list`, `af search`, `af status`, `af validate`) and any future scanner — MUST hard-skip it (see COR-1206 for enforcement at `core/scanner.py` walk layer). Only these files are allowed under `rules/logs/`:
- `*.jsonl` (today's loose file)
- `*.partN.jsonl` (rolled-over segments when today exceeds 8 MiB)
- `archive.zip` (closed-day archive)
- `archive.zip.tmp.*` (per-process unique tmpfile during archival; see §Archival)

---

## Encoding

UTF-8, LF line terminator, one JSON object per line, no embedded newlines, no trailing comma, **append-only**.

---

## Required Fields (every record)

| Field | Type | Constraint |
|---|---|---|
| `ts` | string | RFC 3339 UTC timestamp, e.g. `"2026-05-02T14:23:11Z"` |
| `agent` | string | One of v1 whitelist: `claude-code`, `copilot`, `cursor`, `cline`, `aider`, `codex-cli`, `gemini-cli`, `other`. Whitelist is hardcoded in the validator constant. Adding a new entry requires a new PRP. |
| `agent_version` | string | 1–64 ASCII chars, no whitespace, no newlines. Auto-filled by `af log` from `$ALFRED_AGENT_VERSION` env var, or the literal sentinel `"unknown"` if neither flag nor env var is set. |
| `session_id` | string | 1–128 chars, no whitespace. Auto-filled by `af log` from `$ALFRED_SESSION_ID` env var, or generated UUIDv4 if absent. |
| `event` | string | One of v1 enum (see §Event Enum below) |
| `summary` | string | UTF-8, 1–500 characters, no newlines, no NUL bytes |
| `schema` | string | Exact literal `"alfred.activity/v1"` |

---

## Optional Fields

| Field | Type | Constraint |
|---|---|---|
| `refs` | array of string | `PREFIX-ACID` strings, deduplicated, ≤ 16 entries |
| `files` | array of string | Repo-relative POSIX paths, deduplicated, ≤ 32 entries |
| `duration_ms` | integer | Non-negative, ≤ 86_400_000 (one day) |
| `parent_event` | string | Same format as `session_id`; correlation id |
| `agent_name` | string | **Required when `agent: "other"`**, MUST be omitted otherwise. 1–64 chars; identifies the unrecognized harness (e.g. `"qodo"`, `"continue"`). |
| `summary_truncated` | boolean | `true` only when `af log` truncated `summary` or trimmed `files`/`refs` to fit the 4 KiB line cap. MUST be omitted otherwise. `false` is **not allowed** in v1 (absence implies no truncation). |

---

## v1 Event Enum

| Event | Meaning |
|---|---|
| `session.start` | Agent session begins |
| `session.end` | Agent session ends |
| `task.start` | Long-running task begins (optional, for traceability) |
| `task.done` | User-facing turn completed with non-trivial action (mandatory per turn — see COR-1206) |
| `task.aborted` | Task abandoned mid-execution |
| `doc.created` | Alfred document created via `af create` (`refs` SHOULD be set) |
| `doc.updated` | Alfred document updated via `af update` / `af fmt` (`refs` SHOULD be set) |
| `decision` | Material decision: D-item resolution, PRP convergence, scope cut |
| `note` | Free-form fallback when no other event applies |

---

## Per-Record Line Size Cap (4 KiB)

Each JSONL line (including the trailing `\n`) MUST be ≤ **4096 bytes**.

This bound enables the multi-process atomicity guarantee: on Linux/macOS/BSD, `O_APPEND` provides per-write atomicity for regular files at the kernel level (inode lock); `PIPE_BUF` (≥ 4096) is the related guarantee for pipes/FIFOs that motivates the conservative line-size cap. The 4 KiB cap is well within atomicity windows on every supported OS.

When a record would exceed the cap, `af log` truncates `summary` and trims `files` / `refs` from the end to fit, then sets the optional `summary_truncated: true` field on that record so downstream readers can detect partial data.

---

## Rotation (8 MiB Pre-condition)

- New file per UTC calendar day.
- The 8 MiB per-file cap is enforced as a **pre-condition** check on every append: before writing, `af log` checks `current_file_size + len(new_record_line) > 8 MiB`. If so, it rolls over to `YYYY-MM-DD.partN.jsonl` (N starts at 1, smallest unused) **before** writing.
- As a result, no file ever exceeds 8 MiB by even one byte.
- A purely post-condition check (the early-draft bug) would let a file grow past the cap whenever the last record straddles the boundary — that is forbidden.

---

## Archival (5-step procedure, atomic-replace + eventually-consistent cleanup)

All closed days (any `YYYY-MM-DD.jsonl` or `YYYY-MM-DD.partN.jsonl` whose date is < today UTC) are folded into a **single `archive.zip` per log directory**, so the directory holds at most today's loose files plus `archive.zip`. The current day's file MUST stay loose because zip does not support append-atomic writes — emitting directly into a zip would force file-locking and defeat the 4 KiB / `O_APPEND` multi-process atomicity guarantee.

Archival is performed by `af log` lazily (on the first invocation that detects ≥ 1 closed-day raw file) or on demand via `af log-archive`.

### Procedure (5 steps)

**Step 0 — Acquire archival lock (try-lock).** Acquire a POSIX advisory lock on the log directory. Reference Python form:

```python
fd = os.open(log_dir, os.O_RDONLY | os.O_DIRECTORY)
fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)  # raises BlockingIOError on contention
```

The builtin `open()` raises `IsADirectoryError` on a directory, so `os.open()` MUST be used. **If the lock is already held by another process** (`BlockingIOError` / `EWOULDBLOCK`), **skip this archival cycle entirely** and proceed with today's append (the other archiver completes the work; closed-day files remain on disk and will be archived on the next `af log` invocation that finds the lock free).

This serializes archival without blocking `af log` emit (which never touches `archive.zip` and acquires no lock). Lock holders MUST release in a `finally` clause and `os.close(fd)` after; POSIX advisory locks are released automatically on process exit (or when the last fd referencing the inode is closed), so SIGKILL is safe.

The lock prevents a race where Process A enumerates closed-day files at T0, Process B enumerates a superset at T1 and archives + unlinks at T2, then A's stale enumeration at T3 would have built a tmpfile missing the entries B added — leading to data loss when A's `os.replace` overwrites B's archive.

**Step 1 — Build tmpfile.** Build `archive.zip.tmp.<pid>.<rand6>` (PID + 6 random hex chars; per-process unique even in the unlikely event a misbehaving non-locked archiver runs concurrently). Contents: union of the existing archive's entries plus the closed-day raw files. Filename collisions inside the zip are deduplicated by entry name — same `<date>.jsonl` from disk overwrites the existing zip entry; this is harmless because raw files are immutable once their day closes.

**Step 2 — Atomic replace (linearization point).** `os.replace(archive.zip.tmp.<pid>.<rand6>, archive.zip)`. POSIX rename is atomic; this is the linearization point. Because step 0 serializes archivers via the directory lock, no concurrent racer can have produced a newer archive between step 1 enumeration and step 2 replace; the new `archive.zip` is the strict superset of the prior version.

**Step 3 — Unlink raw files.** `unlink` the closed-day raw files. **Partial-failure semantics:** if any unlink fails (permission denied, file already removed by a concurrent run, etc.), the affected raw files remain on disk. They are *not* lost — they exist in `archive.zip` already, and the next archival run will re-include them by entry name (overwriting the existing zip entry harmlessly) and re-attempt unlink. Readers that union loose + zip MUST deduplicate by `(filename, lineno)` — entries with the same key from both sources are the same record. The "atomic" label thus applies to step 2 (the visible archive state); steps 1 and 3 are best-effort with self-healing on retry.

**Step 4 — Tmpfile cleanup.** Before starting step 1 (in the next archival cycle), the archiver removes any `archive.zip.tmp.<pid>.<rand6>` whose `<pid>` no longer corresponds to a live process (interrupted prior run; the owning archiver is gone). Tmp files whose PID is still live are left alone (another archiver actively writing). PID liveness via `os.kill(pid, 0)` with explicit POSIX-correct exception handling:

| Exception | Interpretation | Action |
|---|---|---|
| `ProcessLookupError` (`ESRCH`) | Process is dead | Remove the tmpfile |
| `PermissionError` (`EPERM`) | Process exists but is owned by another user (shared host, container, sudo'd archiver) | Leave the tmpfile alone |
| Any other exception, or success | Process exists | Leave the tmpfile alone |

The `EPERM` branch is critical — treating it as "dead" would let one user's archiver delete another user's live tmpfile and corrupt their in-flight archive. Wall-clock-based age checks were rejected because backward NTP / VM-resume skew can mistakenly delete live tmpfiles.

Compression typically reduces 30 days of logs by 7–10× (raw 30–50 MiB → zip 4–7 MiB).

---

## File Permissions

Log files are created with mode `0644`; the `rules/logs/` directory (and any parent created on demand) is created with mode `0755`. Agents MUST NOT relax these permissions. Activity logs are not secrets per the privacy constraints below; they are designed to be auditable by the user.

---

## Default Git Policy

Activity logs are per-machine artifacts and SHOULD be gitignored by default. The exact `.gitignore` snippet (a single line: `rules/logs/`) is shipped in CHG-2231 Phase 0. Projects MAY commit logs deliberately; that is a project-level choice and not the protocol default.

---

## Privacy & Safety Constraints

**Forbidden content in any field:**
- API keys, OAuth tokens
- Full prompt text
- Full tool call arguments
- Raw file contents (file *paths* are fine)
- User PII
- Environment variable values

Agents are responsible for their own redaction; the validator does not detect secrets. The 500-character `summary` cap enforces concision.

---

## Retention Policy

- **Default retention**: keep activity log files (loose `*.jsonl` and entries inside `archive.zip`) for **30 days**; older entries MAY be deleted by the agent runtime or by user cron.
- **Aggregate disk-space soft cap**: **256 MiB per `rules/logs/` directory** (raw + zip combined). Beyond this the runtime SHOULD warn; deletion is user-driven, not automatic.
- **Compression policy**: closed days are stored only inside `archive.zip` (DEFLATE provides 7–10× on JSONL). No additional gzip layer in v1.

---

## Versioning

Schema version is fixed in the `schema` field as the literal string `"alfred.activity/v1"`. Breaking changes ship as `alfred.activity/v2` and require a new PRP. v1 readers MUST ignore unknown optional fields they encounter (forward compatibility); v1 writers MUST NOT emit fields not listed in v1.

---

## Out-of-Scope Substrates (v1)

Two filesystem classes are explicitly unsupported in v1:

- **Windows** — `O_APPEND` and `flock(2)` semantics differ; v1 is best-effort. Revisit if concrete need surfaces.
- **Network filesystems (NFS / SMB / fuse-based remote mounts)** for **either log root** — both PRJ `rules/logs/` and USR `~/.alfred/logs/` (which on enterprise / Kerberos / LDAP-managed Linux setups is frequently NFS-mounted via the user's `$HOME`). `O_APPEND` and `flock(2)` semantics are implementation-defined and may silently no-op, breaking both per-line atomicity and archival serialization. Local POSIX filesystems (`ext4`, `xfs`, `btrfs`, `apfs`, `hfs+`, `ufs`, `zfs`) are the v1 supported substrate.

The implementing CHG SHOULD detect the filesystem type of the resolved log directory at `af log` startup using the **OS-appropriate API**:
- **Linux**: `statfs(2)` `f_type` magic numbers — `NFS_SUPER_MAGIC = 0x6969`, `SMB_SUPER_MAGIC`, `CIFS_MAGIC_NUMBER`, `FUSE_SUPER_MAGIC` — accessed via `ctypes` to libc, OR parse `/proc/self/mountinfo`
- **macOS / BSD**: `statfs(2)` `f_fstypename` via `ctypes` to libc, or shell out to `stat -f "%T"`
- **Avoid `os.statvfs`** — it returns block/inode counts but does NOT expose filesystem type

On detection, emit a one-time stderr warning. Hard refusal is deferred to v2 to avoid breaking existing setups during rollout.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-02 | Initial version. Implements PRP-2230 (Agent Activity Log Protocol v1) §"Storage location" + §"Required/Optional fields" + §"v1 event enum" + §"Per-record line size cap" + §"Rotation" + §"Archival" + §"File permissions" + §"Default git policy" + §"Privacy & safety" + §"Versioning". Adds retention policy (30-day default + 256 MiB soft cap) and explicit OS-appropriate filesystem-type detection guidance per PRP-2230 R5+R7 advisories. | Frank + Claude |
