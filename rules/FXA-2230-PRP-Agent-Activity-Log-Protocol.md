# PRP-2230: Agent Activity Log Protocol

**Applies to:** FXA project
**Last updated:** 2026-05-02
**Last reviewed:** 2026-05-02
**Status:** Approved
**Related:** FXA-2229 (Layered SOP Memory Model — recall surface; this PRP covers the complementary emit surface), COR-1200 (Session Retrospective), COR-1201 (Discussion Tracking)

---

## What Is It?

This PRP proposes a **vendor-neutral, agent-neutral activity log protocol** for Alfred. Any coding agent — Claude Code, GitHub Copilot, Cursor, Cline, Aider, Codex CLI, Gemini CLI, or any future tool — can emit structured events to a shared on-disk log so that "what was done in this session" becomes a first-class, machine-readable artifact instead of relying on the agent to remember.

The protocol itself is two pieces of documentation (`COR-1205` REF format contract + `COR-1206` SOP implementation guide) plus two minimal CLI surfaces (`af log` writer + `af log-validate` schema checker). The protocol does **not** mandate how each agent hooks into its own runtime — that is delegated to per-agent implementations following the SOP.

This is the **emit surface** counterpart to FXA-2229's **recall surface**. FXA-2229 defines how durable documents get retrieved into prompt context; FXA-2230 defines how runtime work gets captured in the first place.

---

## Problem

Today Alfred's short-term working memory (FXA-2229 layer 4) is captured **only** by the discussion tracker (`COR-1201`) and end-of-session retrospective (`COR-1200`). Both require the agent to **manually decide** what to write and **manually call** `af update` / `af create`. This has three concrete failure modes observable today:

1. **Lossy retrospectives.** `COR-1200 step 1` ("List all actions taken this session") relies on the agent's recollection of the session. For long sessions or compaction events, the agent reconstructs from chat history rather than from a ground-truth log, and consistently under-reports.
2. **No cross-tool continuity.** A user who runs Claude Code in the morning and Cursor in the afternoon has **no shared trail** of what happened. Each tool's session state is private to that tool. The discussion tracker only captures what one agent chose to write.
3. **No forensics for agent behavior.** When an agent takes an unexpected action (wrong file edit, scope creep, missed SOP), there is no append-only artifact to review. The conversation transcript is private to the harness and not always exportable.

The natural fix — "make the agent emit a log line every time it finishes something" — is **not a single-agent problem**. Hardcoding it as a Claude Code `Stop` hook only solves it for Claude Code. Each coding agent has different lifecycle hooks (`Stop` events, MCP callbacks, VS Code extensions, shell commands, git hooks). What is missing is a **shared contract** they can all target.

Alfred is uniquely positioned to own this contract because Alfred is already document-first and framework-agnostic: `core/` has no Click dependency, `af` has no agent dependency, PKG documents are portable.

## Scope

This proposal covers the protocol design and the minimum CLI surface needed to make the protocol **executable and verifiable**. Per-agent implementations (Claude Code hook scripts, VS Code extensions, etc.) are explicitly out of scope for this PRP — they will be follow-on CHGs, one per agent.

In scope:

- Define the on-disk format for activity log files (location, encoding, JSONL conventions, rotation rules).
- Define a versioned event schema (`alfred.activity/v1`) with required and optional fields.
- Define the minimum event enum (`session.start`, `session.end`, `task.start`, `task.done`, `task.aborted`, `doc.created`, `doc.updated`, `decision`, `note`).
- Define the per-agent implementation guidance: when to emit, how to map native lifecycle events, and the universal fallback (`af log`).
- Add `af log` as a thin writer that any agent can shell out to (with built-in lazy archival of closed days).
- Add `af log-validate` as a schema checker so protocol compliance is externally testable (transparently reads loose `.jsonl` and `archive.zip` entries).
- Add `af log-archive` as an explicit archival command for ops/cron use.
- Define privacy and size constraints (no secrets, no full prompts, summary length cap).

Out of scope:

- Per-agent hook implementations **beyond the single Claude Code reference implementation** listed in acceptance criteria. Copilot, Cursor, Cline, Aider, Codex CLI, Gemini CLI integrations are each follow-on CHGs with their own scope.
- Embedding generation, semantic search, or any analytics over the log (separate proposal if needed).
- Modifying the **core semantics** of `COR-1201` (D-item lifecycle) or `COR-1200` (the 6-step retrospective protocol). The retrospective gets a single additive bullet in step 1 directing the agent to read the activity log first; its 6-step protocol and outputs are unchanged.
- Changes to FXA-2229's `Recall` field or `af recall` command. Cross-references are added at the end of FXA-2229 implementation, not here.
- Encrypting log files at rest, log shipping to remote services, or multi-machine sync.
- Windows-specific atomicity guarantees for concurrent multi-process emit. v1 ships POSIX-correct behavior; Windows is best-effort and revisited if concrete need surfaces.
- Network filesystems (NFS / SMB / fuse-based remote mounts) for **either log root** — both the PRJ-layer `rules/logs/` and the USR-layer `~/.alfred/logs/` (which on enterprise / Kerberos / LDAP-managed Linux setups is frequently NFS-mounted via the user's `$HOME`). `O_APPEND` and `flock(2)` semantics on these substrates are implementation-defined and may silently no-op, breaking both the per-line atomicity guarantee and the archival serialization mutex regardless of which log root is active. Local POSIX filesystems (ext4, xfs, btrfs, apfs, hfs+, ufs, zfs) are the v1 supported substrate. The implementing CHG SHOULD `os.statvfs` the resolved log directory at `af log` startup and emit a one-time stderr warning if it detects a network mount; a hard refusal is deferred to v2 to avoid breaking existing setups during rollout.

## Proposed Solution

### Two new PKG documents

**`COR-1205-REF-Agent-Activity-Log-Format`** — the canonical data contract. Defines:

- **Storage location.** `./rules/logs/YYYY-MM-DD.jsonl` at PRJ layer; `~/.alfred/logs/YYYY-MM-DD.jsonl` at USR layer when no project context. The `rules/logs/` subtree is **reserved**: **all** `af` document scanners — present (`af list`, `af search`, `af status`, `af validate`) **and any future scanner** — MUST hard-skip it. Implementations enforce this at the `core/scanner.py` directory-walk layer (mirroring how `__pycache__` and `.git` are skipped) so the rule applies uniformly to every command that walks `rules/`. Only `*.jsonl`, `*.partN.jsonl`, `archive.zip`, and any `archive.zip.tmp.*` (the per-process unique tmpfile glob defined under §Archival) are allowed inside.
- **Encoding.** UTF-8, LF line terminator, one JSON object per line, no embedded newlines, no trailing comma, append-only.
- **Required fields per event:**
  - `ts` — RFC 3339 UTC timestamp (`2026-05-02T14:23:11Z`).
  - `agent` — short identifier from a v1 whitelist (`claude-code`, `copilot`, `cursor`, `cline`, `aider`, `codex-cli`, `gemini-cli`, `other`). The whitelist is hardcoded as a constant inside the validator (see Decisions). Adding a new entry requires a follow-on PRP that bumps the constant.
  - `agent_version` — agent's own version string. Constraints: 1–64 ASCII characters, no whitespace, no newlines. Not otherwise validated for semver shape. Auto-filled by `af log` when neither `--agent-version` nor `$ALFRED_AGENT_VERSION` is supplied — see Decisions and `af log` behavior. The literal sentinel `"unknown"` is permitted but indicates the caller did not declare a version; hook scripts SHOULD export `$ALFRED_AGENT_VERSION` to avoid this.
  - `session_id` — string, 1–128 chars, no whitespace. Provided by the agent if available; auto-generated as UUIDv4 by `af log` when absent (see Decisions).
  - `event` — one of the v1 event enum values.
  - `summary` — UTF-8 string, 1–500 characters, no newlines, no NUL bytes.
  - `schema` — exact literal `"alfred.activity/v1"`.
- **Optional fields per event:**
  - `refs` — array of `PREFIX-ACID` strings, deduplicated, ≤ 16 entries.
  - `files` — array of repo-relative POSIX paths, deduplicated, ≤ 32 entries.
  - `duration_ms` — non-negative integer ≤ 86_400_000 (one day).
  - `parent_event` — optional event correlation id (string, same format as `session_id`).
  - `agent_name` — required when `agent: "other"`; free-form 1–64 chars to identify the unrecognized harness (e.g. `"qodo"`, `"continue"`). MUST be omitted otherwise.
  - `summary_truncated` — boolean. MUST be `true` when `af log` truncated `summary` or trimmed `files` / `refs` to stay under the per-record line size cap. MUST be omitted otherwise (an absent field implies no truncation; emitting `false` is not allowed in v1).
- **v1 event enum.**
  - `session.start`, `session.end` — agent session lifecycle.
  - `task.start`, `task.done`, `task.aborted` — coarse task boundaries (one user turn or one logical sub-task).
  - `doc.created`, `doc.updated` — Alfred document write events; `refs` SHOULD be set.
  - `decision` — D-item decisions, PRP convergences, scope cuts.
  - `note` — free-form fallback when no other event applies.
- **Rotation.** New file each calendar day in UTC. The 8 MiB per-file cap is enforced as a **pre-condition** check on every append: if writing the next record would push the active file past 8 MiB, `af log` rolls over to `YYYY-MM-DD.partN.jsonl` (N starts at 1 and increments) **before** writing. As a result, no file ever exceeds 8 MiB. (A purely post-condition check would let a file grow past the cap whenever the last record straddles the boundary; that is forbidden.)
- **Archival.** All closed days (any `YYYY-MM-DD.jsonl` or `YYYY-MM-DD.partN.jsonl` whose date is < today UTC) are folded into a **single `archive.zip` per log directory**, so the directory holds at most today's loose files plus `archive.zip`. The current day's file MUST stay loose because zip does not support append-atomic writes — emitting directly into a zip would force file-locking and defeat the 4 KiB / `O_APPEND` multi-process atomicity guarantee. Archival is performed by `af log` lazily (on the first invocation that detects ≥ 1 closed-day raw file) or on demand via `af log-archive`. **Procedure** — atomic for the archive replacement, eventually-consistent for raw-file cleanup:
  0. **Acquire archival lock (try-lock semantics).** Acquire a POSIX advisory lock on the log directory. Reference Python form: `fd = os.open(<dir>, os.O_RDONLY | os.O_DIRECTORY); fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)` — the builtin `open()` raises `IsADirectoryError` on a directory, so `os.open()` MUST be used to obtain the directory fd. **If the lock is already held by another process** (`fcntl.flock` raises `BlockingIOError` / `EWOULDBLOCK`), **skip this archival cycle entirely and proceed with today's append** (the other archiver will complete the work; closed-day files remain on disk and will be archived on the next `af log` invocation that finds the lock free). This serializes archival without blocking `af log` emit (which never touches `archive.zip` and acquires no lock). Lock holders MUST release in a `finally` clause and `os.close(fd)` after; POSIX advisory locks are released automatically when the holding process exits (or when its last fd referencing the inode is closed), so even SIGKILL is safe. The lock prevents a race where Process A enumerates closed-day files at T0, Process B enumerates a superset at T1 and archives + unlinks at T2, then A's stale enumeration at T3 would have built a tmpfile missing the entries B added — leading to data loss when A's `os.replace` overwrites B's archive. **Filesystem caveat (out of scope for v1):** `flock(2)` semantics on **NFS / SMB / other network filesystems** are implementation-defined and may silently no-op — the archival serialization guarantee holds only on local POSIX filesystems (`ext4`, `xfs`, `btrfs`, `apfs`, `hfs+`, `ufs`, `zfs`). Hosting `rules/logs/` on a network mount is unsupported in v1 and joins Windows in §Out of scope (line 55); v2 may revisit with a `flock`-fallback strategy if real demand surfaces.
  1. Build `archive.zip.tmp.<pid>.<rand6>` (PID + 6 random hex chars; per-process unique tmpfile so even a stray non-locked archiver from a misbehaving implementation does not corrupt a concurrent build) containing the union of the existing archive's entries plus the closed-day files. Filename collisions inside the zip are deduplicated by entry name — same `<date>.jsonl` from disk overwrites the existing zip entry; this is harmless because raw files are immutable once their day closes.
  2. `os.replace(archive.zip.tmp.<pid>.<rand6>, archive.zip)` — POSIX rename is atomic; this is the linearization point. Because step 0 serializes archivers via the directory lock, no concurrent racer can have produced a newer archive between step 1 enumeration and step 2 replace; the new `archive.zip` is the strict superset of the prior version.
  3. `unlink` the closed-day raw files. **Partial-failure semantics:** if any unlink fails (permission denied, file already removed by a concurrent run, etc.), the affected raw files remain on disk. They are *not* lost — they exist in `archive.zip` already, and the next archival run will re-include them by entry name (overwriting the existing zip entry harmlessly) and re-attempt unlink. Readers that union loose + zip MUST deduplicate by `(filename, lineno)` — entries with the same key from both sources are the same record. The "atomic" label thus applies to step 2 (the visible archive state); steps 1 and 3 are best-effort with self-healing on retry.
  4. **Tmpfile cleanup.** Before starting step 1, the archiver removes any `archive.zip.tmp.<pid>.<rand6>` whose `<pid>` no longer corresponds to a live process (interrupted prior run; the owning archiver is gone). Tmp files whose PID is still live are left alone (another archiver actively writing). PID liveness is checked via `os.kill(pid, 0)` with **explicit POSIX-correct exception handling**: `ProcessLookupError` (errno `ESRCH`) ⇒ process is dead ⇒ remove the tmpfile; `PermissionError` (errno `EPERM`) ⇒ process **exists but is owned by another user** (shared host, container, sudo'd archiver) ⇒ leave the tmpfile alone; any other exception (or success) ⇒ process exists ⇒ leave the tmpfile alone. The `EPERM` branch is critical — treating it as "dead" would let one user's archiver delete another user's live tmpfile and corrupt their in-flight archive. On rare PID reuse the worst case is leaving a dead tmpfile in place for one more cycle — harmless because the existing `archive.zip` is always authoritative and tmpfiles never participate in reads. (Wall-clock-based age checks were rejected because backward NTP / VM-resume skew can mistakenly delete live tmpfiles.)

  Compression typically reduces 30 days of logs by 7–10× (raw 30–50 MiB → zip 4–7 MiB).
- **Per-record line size cap.** Each JSONL line (including the trailing `\n`) MUST be ≤ 4096 bytes. This bound is required so that POSIX `O_APPEND` writes are atomic across processes (POSIX guarantees atomicity for writes ≤ `PIPE_BUF`, which is ≥ 4096 on every supported OS). `af log` truncates `summary` and trims `files` / `refs` from the end if needed to stay under the cap; when this happens the optional `summary_truncated: true` field (see Optional fields above) is emitted on that record so downstream readers can detect partial data.
- **File permissions.** Log files are created with mode `0644`; the `rules/logs/` directory (and any parent created on demand) is created with mode `0755`. Agents MUST NOT relax these permissions. (Activity logs are not secrets per the privacy constraints below; they are designed to be auditable by the user.)
- **Default git policy.** Activity logs are per-machine artifacts and SHOULD be gitignored by default. `COR-1206` provides the exact `.gitignore` snippet (a single line: `rules/logs/`). Projects MAY commit logs deliberately; that is a project-level choice and not the protocol default.
- **Privacy & safety constraints.** Forbidden content in any field: API keys, OAuth tokens, full prompt text, full tool call arguments, raw file contents (file *paths* are fine), user PII, environment variable values. Agents are responsible for their own redaction; the validator does not detect secrets. `summary` ≤ 500 chars enforces concision.
- **Versioning.** Schema version is fixed in `schema` field. Breaking changes ship as `alfred.activity/v2` and require a new PRP. v1 readers MUST ignore unknown optional fields they encounter (forward compatibility); v1 writers MUST NOT emit fields not listed in v1.

**`COR-1206-SOP-Emit-Agent-Activity`** — the implementation guide. Defines:

- **Mandatory triggers** (every agent MUST emit at minimum):
  - One `session.start` per session.
  - One `session.end` per session.
  - At least one `task.done` (or `task.aborted` / `note`) per user-facing turn that resulted in non-trivial action.
  - One `doc.created` or `doc.updated` per Alfred document write.
- **Optional triggers** (agent MAY emit):
  - `task.start` for long-running tasks.
  - `decision` for material decisions surfaced in conversation.
  - `note` for anything that doesn't fit elsewhere.
- **Per-agent mapping table** (initial v1 entries, extensible by follow-on PRP):

  | Agent | Native hook / mechanism | How to emit |
  |---|---|---|
  | Claude Code | `settings.json` `Stop` and `PostToolUse` hooks | `hooks/emit-activity.sh` reads `$CLAUDE_*` env vars, writes JSONL |
  | GitHub Copilot (VS Code) | No native lifecycle hook → companion VS Code extension listening to chat events | extension calls `af log` |
  | Cursor | `.cursorrules` instructs the model to call `af log` after each turn | shell-out via `af log` |
  | Cline / Roo Code | Custom MCP tool exposing `af log`; rules instruct usage | tool call |
  | Aider | `--cmd-stop` callback or git post-commit hook | shell script writes JSONL |
  | Codex CLI / Gemini CLI | Each SDK's lifecycle event hook | shell script writes JSONL |
  | Universal fallback | `af log` subcommand (always available, agent-agnostic) | direct shell-out |
- **Compliance test.** Every implementation MUST pass `af log-validate <file>` on its emitted output for at least one full session before being added to the mapping table.

### Two new CLI surfaces

**`af log`** — universal writer. Any agent that can shell out can use this as a fallback regardless of native hook availability.

```
af log "FXA-2230 PRP draft created" --event task.done --refs FXA-2230 --files rules/FXA-2230-PRP-Agent-Activity-Log-Protocol.md --agent claude-code
```

Behavior:
- **Layer resolution** (deterministic, in order):
  1. If `--root <DIR>` is given → write to `<DIR>/rules/logs/<YYYY-MM-DD>.jsonl`.
  2. Else if cwd is inside a recognized project (`./rules/` exists at cwd or any ancestor) → write to `<project-root>/rules/logs/<YYYY-MM-DD>.jsonl`.
  3. Else → write to `~/.alfred/logs/<YYYY-MM-DD>.jsonl`.
- **Auto-fills** `ts` (current UTC), `schema` (literal), `session_id`, and `agent_version` when those flags / env vars are not provided. Resolution rules:
  - `session_id` — read from `$ALFRED_SESSION_ID` if set; otherwise generate a UUIDv4.
  - `agent_version` — read from `$ALFRED_AGENT_VERSION` if set; otherwise fall back to the literal sentinel `"unknown"`. Hook scripts SHOULD export `$ALFRED_AGENT_VERSION` (or pass `--agent-version`) so this fallback is rare; the sentinel exists so that fail-open hooks (`af log ... || true`) cannot silently lose events when the caller forgets the flag.
  - All other required fields (`agent`, `event`, `summary`) MUST be supplied by the caller; their absence is a usage error, not a fail-open scenario.
- **Validates** the resulting record against the v1 schema before writing; rejects with exit code 3 (validation error) on failure, printing the failing field and rule.
- **Atomic append** using `open(O_APPEND | O_CREAT, 0o644)` followed by a single `write()` of one line ≤ 4096 bytes. No read-modify-write. No locking required on POSIX given the size cap.
- **Rotation handoff.** Before each append, `af log` checks `current_file_size + len(new_record_line) > 8 MiB`. If so, it opens `<YYYY-MM-DD>.partN.jsonl` (N = smallest unused integer ≥ 1) and writes the new record there instead. This is a strict pre-condition check — no file is ever permitted to exceed 8 MiB, even by a single byte.
- **Lazy archival on startup.** Before the first append in any invocation, `af log` scans the resolved log directory for any closed-day raw file (`YYYY-MM-DD.jsonl` or `YYYY-MM-DD.partN.jsonl` with date < today UTC). If found, it performs the atomic archival into `archive.zip` (see §Archival above) **before** writing today's record. This keeps the directory clean without requiring a daily cron.
  - **Failure handling.** If archival fails (filesystem error, corrupt existing archive, race lost), `af log` proceeds with today's append — observability MUST NOT block emit. Each failure emits exactly **one** stderr line per `af log` invocation (no in-process suppression — `af log` is a short-lived CLI process; suppressing within one process would not help looping callers since each invocation is a fresh process anyway). The closed-day raw files remain on disk and the next `af log` invocation will retry — this is the self-healing path. Callers that find the per-invocation warning too noisy can redirect stderr (`af log ... 2>>~/.alfred/logs/.warn.log` or `2>/dev/null`).
  - **Warning format (mandatory).** Every lazy-archival failure warning MUST follow this format so machine consumers and humans get the same minimum information:
    ```
    af log: lazy archival failed in <dir>: <error_class>: <message>. Recover: af log-archive --force
    ```
    The `<error_class>` token is a stable, low-cardinality string identifier from a fixed v1 enum: `filesystem` (any `OSError` not covered by other classes), `permission-denied` (`PermissionError` / `EACCES` / `EPERM` on directory or file ops), `corrupt-archive` (existing `archive.zip` is unreadable as zip — `BadZipFile` or equivalent), `race-lost` (two archivers raced and the loser's `os.replace` overwrite was preempted in a way that requires retry), `partial-cleanup` (archive replaced successfully but one or more raw-file unlinks failed). The `<message>` token is a human-readable detail (typically the OS error string). The `Recover: af log-archive --force` suffix is required so operators who only ever run `af log` see the explicit recovery command without having to read this PRP.

    **Mandatory sanitization (security-critical).** Both `<dir>` and `<message>` are interpolated from untrusted sources (filesystem paths can contain `\n`, `\r`, `\t`, and any byte except `/` and `\0`; OS error strings frequently embed paths). Before interpolation the writer MUST escape these tokens with the **JSON string-escape** ruleset: `\` → `\\`, `\n` → `\n` (literal two chars), `\r` → `\r`, `\t` → `\t`, all other control chars (0x00–0x1F) → either `\xNN` (hex byte) **or** `\u00NN` (Unicode escape) — implementations MAY pick either form; both preserve the single-physical-line guarantee, and the `json.dumps()` shortcut below produces `\u00NN` while still conforming. This guarantees the warning is a single physical line and prevents **log-injection attacks** where a path like `/tmp/evil\nRecover: rm -rf /` could otherwise spoof a fake `Recover:` directive on the next line. Implementations MAY use `json.dumps()` minus the surrounding quotes for `<message>` (this is the recommended path — it correctly handles all the rules above with one stdlib call). The `<error_class>` token is from a fixed enum and is not interpolated from untrusted input — no escaping needed.
  - **Lazy vs explicit corrupt-archive asymmetry (intentional).** When the existing `archive.zip` is corrupt, lazy archival inside `af log` falls back to "warn + skip + leave files for retry" (because emit must not break). The explicit `af log-archive` command, by contrast, exits with code 5 unless `--force` is passed (because the operator invoked it deliberately and a silent skip would mislead them). This asymmetry is by design: lazy = conservative, explicit = bold. Operators running `af log-archive --force` accept that the corrupt archive is overwritten with a fresh zip built from the closed-day raw files only (entries from the corrupt archive are unrecoverable).
- **Failure mode.** `af log` MUST NOT block or error a calling agent's user-visible operation. Hook scripts SHOULD invoke it with `af log ... || true` so an emit failure cannot cascade into a session break. `af log` itself returns non-zero on failure for diagnostic visibility.
- **Exit codes.** 0 = written, 2 = invalid CLI args, 3 = schema validation error, 4 = filesystem error.

**`af log-validate [PATH]`** — schema checker. The executable form of the protocol. Naming: hyphenated form preferred over `af validate-activity-log` (shorter, shares `af log` prefix) and over a `af log validate` subcommand (since `af log` itself takes a positional message argument and Click subcommand groups conflict awkwardly with positional dispatch). Kept separate from existing `af validate` (which validates document structure, not activity logs).

```
af log-validate                              # validate today's PRJ log
af log-validate ./rules/logs/                # validate every loose file + every entry inside archive.zip
af log-validate path/to/2026-05-02.jsonl     # validate a specific file
af log-validate ./rules/logs/archive.zip     # validate every entry inside the zip
```

Behavior:
- **Default target** when `PATH` omitted: today's log file using the same layer resolution as `af log`.
- **Path semantics:** if `PATH` is a `.jsonl` file → validate that file. If `PATH` ends in `.zip` → validate every member inside as a JSONL file. If `PATH` is a directory → validate every loose `*.jsonl` / `*.partN.jsonl` at depth 1 **and** every member inside `archive.zip` if present (the directory + zip view is unioned). The zip path inside violations is reported as `<dir>/archive.zip::<member>:<lineno>:` so callers can disambiguate. The `::` separator is chosen over `!` (Java JAR URL convention) because `!` triggers history expansion in interactive bash/zsh and would corrupt copy-pasted paths.
- **Deduplication of duplicate raw+zip records.** When the directory union view encounters the same `(filename, lineno)` from both a loose file and a zip member (the partial-cleanup self-healing state defined in §Archival step 3), the validator deduplicates by `(filename, lineno)` and validates each unique record exactly once. The two sources are guaranteed byte-identical because closed-day raw files are immutable; the dedup is correctness preservation, not lossy collapse.
- **Per-line check:** required fields present, types correct, `agent` in v1 whitelist, `event` in v1 enum, `summary` length, `schema` literal match, `agent_name` present iff `agent == "other"`, `summary_truncated` (if present) is the literal boolean `true` (the field MUST NOT be set to `false` in v1; absence implies no truncation regardless of the final record size), line ≤ 4096 bytes.
- **Output:** one line per violation in the form `<path>:<lineno>: <field>: <reason>`. Quiet on success.
- **Exit codes:** 0 = all valid, 1 = schema violations found, 2 = invalid CLI args, 4 = file/dir/zip not readable, 5 = corrupt zip.

**`af log-archive [PATH]`** — archive command. Atomically folds all closed-day `*.jsonl` and `*.partN.jsonl` files in the target directory into the directory's `archive.zip`, then deletes the raw closed-day files. The current day's file is never touched.

```
af log-archive                               # archive today's PRJ log directory
af log-archive ./rules/logs/                 # explicit path
```

Behavior:
- **Layer resolution**: same as `af log`. The default target is the directory, not a file.
- **Per-directory atomicity**: follows the §Archival 5-step procedure (step 0: acquire `fcntl.flock` directory lock with try-lock semantics — see §Archival caveat for `af log-archive`'s standalone behavior on contention; step 1: build `archive.zip.tmp.<pid>.<rand6>`; step 2: `os.replace`; step 3: unlink raw files with self-healing on partial failure; step 4: PID-liveness tmpfile cleanup). No partial states are observable to readers — the archive replacement at step 2 is the linearization point. **Standalone `af log-archive` lock-contention behavior:** unlike the lazy `af log` path which silently skips, the explicit `af log-archive` command MUST exit with code 0 and stderr "another archiver is running, skipping" when it cannot acquire the lock — this preserves try-lock-and-skip semantics consistently and avoids blocking cron/CI invocations indefinitely. Operators wanting blocking-wait semantics MAY wrap with their own retry loop.
- **Idempotent**: safe to invoke when there is nothing to archive (exit 0, no output). Safe to invoke concurrently — racing archivers produce a content-identical zip.
- **Tmpfile cleanup**: stale `archive.zip.tmp.<pid>.<rand6>` files whose `<pid>` no longer corresponds to a live process (per `os.kill(pid, 0)`) are removed at start (interrupted prior runs); tmp files with live PIDs are left alone (another archiver actively writing). The existing `archive.zip` is always authoritative. Wall-clock-based age checks are explicitly rejected because backward NTP / VM-resume skew can mistakenly delete live tmpfiles.

CLI options:

| Flag | Purpose |
|---|---|
| `--force` | Required when the existing `archive.zip` is corrupt and the operator wants to replace it. Without `--force`, exit code 5 is returned and the corrupt file is left untouched. With `--force`, the corrupt archive is replaced with a fresh zip built from the closed-day raw files only (entries inside the corrupt archive are unrecoverable). |
| `--root <DIR>` | Same semantics as `af log --root` for layer resolution. |

Exit codes:
- 0 = archived (or nothing to do)
- 2 = invalid CLI args
- 4 = filesystem error (cannot read directory, cannot write tmpfile, etc.)
- 5 = corrupt existing `archive.zip`; refuses to overwrite without `--force`

### Acceptance Criteria

This proposal is complete when:

- `COR-1205-REF-Agent-Activity-Log-Format` exists in PKG with the v1 schema fully specified (fields, enum values, file format, rotation, line size cap, archival policy, file permissions, gitignore policy, privacy constraints, scanner-skip rule for `rules/logs/`).
- `COR-1206-SOP-Emit-Agent-Activity` exists in PKG with mandatory triggers, optional triggers, the per-agent mapping table covering at least `claude-code`, `copilot`, `cursor`, `aider`, plus `other` as escape hatch, **and** the explicit `.gitignore` snippet (`rules/logs/`) and the scanner-skip enforcement rule.
- `af log` command writes a record that passes `af log-validate`, including: layer resolution per the 3-step rule, auto-fill of `ts`/`session_id`/`schema`/`agent_version`, line size cap with `summary_truncated` flag, rotation handoff at 8 MiB pre-condition, **lazy archival of closed days into `archive.zip` on startup**, and exit codes per spec.
- `af log-validate` correctly reports schema violations on a synthetic invalid file covering at least: missing required field, wrong type, `agent` not in whitelist, `agent: "other"` without `agent_name`, `summary_truncated: false` (must be omitted, not set to false in v1), line > 4096 bytes, malformed `schema` literal. The validator transparently reads both loose `*.jsonl` files and entries inside `archive.zip` when given a directory or a `.zip` path; violations inside the zip are reported with `<dir>/archive.zip::<member>:<lineno>:` notation.
- `af log-archive` performs the atomic archival per the §Archival **5-step procedure** (step 0: acquire `fcntl.flock(LOCK_EX | LOCK_NB)` advisory lock on the log directory — skip cycle if not free; step 1: build `archive.zip.tmp.<pid>.<rand6>`; step 2: `os.replace`; step 3: unlink raw closed-day files with self-healing on partial failure; step 4: tmpfile cleanup via PID liveness) and is interruptible-safe (a stray `archive.zip.tmp.<pid>.<rand6>` from a dead PID is unlinked on the next run; the authoritative `archive.zip` is never compromised; POSIX advisory locks auto-release on process exit so SIGKILL during step 0–4 cannot orphan the lock).
- `COR-1200` (retrospective) gets a single additive bullet in step 1 directing the agent to read today's `./rules/logs/<today>.jsonl` (and `archive.zip` if relevant) before reconstructing actions. The 6-step protocol and outputs are otherwise unchanged.
- At least **one reference implementation** ships in the same release: a Claude Code `Stop` hook script (committed under `hooks/` in this repo) that emits `task.done` via `af log ... || true` and passes `af log-validate` over a real session log.
- **All** `af` document scanners (present: `af list`, `af search`, `af status`, `af validate`) verifiably **skip** `rules/logs/` at the `core/scanner.py` directory-walk layer. A regression test asserts that placing `rules/logs/2026-05-02.jsonl`, `rules/logs/archive.zip`, and even a misplaced `rules/logs/FXA-9999-PRP-Test.md` does not affect the output of any scanner-based command and produces no warnings. The skip is implemented at the walk layer (not per-command) so future scanners inherit the rule automatically.
- No reverse dependency on FXA-2229 — this PRP must be independently implementable whether FXA-2229 is shipped or not.

---

## Decisions

The decisions below constrain implementation. Items still requiring discussion remain in `## Open Questions`.

### Vendor-neutral protocol, not a single-agent feature

The protocol is owned by Alfred (a documentation system) rather than any specific harness. **Why:** matches Alfred's existing document-first / framework-agnostic posture (core/ is Click-free, `af` is agent-free, PKG documents are portable across projects). Hardcoding emit logic into a single agent's hook reproduces the very fragmentation the protocol is meant to fix.

### Two-document split (REF + SOP)

Format contract (`COR-1205`, REF) is separated from implementation guidance (`COR-1206`, SOP). **Why:** the data contract is stable and rarely changes; the agent mapping table changes every time a new tool gets integrated. Putting them in one document would either freeze the table or thrash the contract. This split mirrors FXA-2229's static-vs-dynamic knowledge cut (REF = static facts, SOP = dynamic procedure).

### `af log` is the universal fallback, not the only path

`af log` is the lowest-common-denominator writer for agents that cannot install a native hook. Native hooks (Claude Code `Stop`, VS Code extension, etc.) are **preferred** because they are zero-effort for the user, but `af log` is always available as the contract floor.

### Schema versioning is strict

`schema` field is a literal string match (`"alfred.activity/v1"`), not a semver range. v2 ships under a different literal. v1 readers MUST ignore unknown optional fields (forward compat); breaking changes get a new version. **Why:** JSONL logs are append-only and may live for years; loose versioning leads to silent corruption.

### `session_id` and `agent_version`: agent-provided when available, sentinel fallback

`af log` reads `$ALFRED_SESSION_ID` (set by the calling hook) and uses it as `session_id` when present; if absent it generates a UUIDv4. `af log` reads `$ALFRED_AGENT_VERSION` and uses it as `agent_version` when present; if absent it falls back to the literal sentinel `"unknown"`. **Why:** preserves cross-tool correlation when the harness exposes a stable session id, and keeps `agent_version` a required (always-present) field for downstream readers without breaking the fail-open contract — without sentinel fallback, a caller that forgot `--agent-version` plus a `af log ... || true` hook would silently lose every event for that session. The sentinel is preferable to silent loss because it produces a visible signal ("this caller didn't declare a version") that downstream tooling can warn on.

### Agent whitelist lives in code, not in a separate YAML

The v1 agent whitelist (`claude-code`, `copilot`, `cursor`, `cline`, `aider`, `codex-cli`, `gemini-cli`, `other`) is hardcoded as a Python constant in the validator module. **Why:** keeps schema enforcement self-contained — no separate parser for `COR-1206.agents.yaml`, no risk of doc/code drift. The cost of adding a new agent is one PRP that bumps the constant and updates `COR-1206`'s mapping table in the same change. v2 may revisit this if the whitelist starts changing more than once per quarter.

### `agent: "other"` requires `agent_name`

When `agent` is `"other"`, the optional field `agent_name` becomes required and identifies the unrecognized harness (e.g. `"qodo"`). **Why:** prevents the `"other"` value from silently absorbing all unrecognized writers and erasing the cost signal that the whitelist needs an addition. A spike in `agent: "other"` log lines with the same `agent_name` is the explicit trigger for a follow-on whitelist PRP.

### Storage location: `rules/logs/` with hard scanner-skip rule

Activity logs live under `./rules/logs/` rather than the originally proposed `./logs/agent-activity/` or alternatives like `.alfred/logs/`. **Why:** co-locates with Alfred state so users have one place to look, and avoids cluttering the project root with another top-level directory. **Cost:** `rules/` is the `af` document scanner's working directory; today's scanner happens to ignore non-`*.md` files, but that is implementation behavior, not a contract. To prevent future scanner improvements (e.g. "warn on unknown files in rules/") from interacting badly with logs, `COR-1206` mandates that **all** `af` scanners — present (`list`, `search`, `status`, `validate`) and any future addition — MUST hard-skip the `rules/logs/` subtree at the `core/scanner.py` directory-walk layer — the directory is reserved exclusively for `*.jsonl`, `*.partN.jsonl`, `archive.zip`, and any `archive.zip.tmp.*` (the per-process unique tmpfile glob from §Archival). A regression test in the implementing CHG asserts this skip behavior.

### Hybrid storage: today raw, closed days zipped

Today's file is raw `.jsonl` (POSIX `O_APPEND` provides per-write atomicity for ≤ 4096-byte writes on regular files via the kernel inode lock; `PIPE_BUF` ≥ 4096 motivates the line-size cap as the conservative upper bound). Closed days are folded into a single `archive.zip` per directory. **Why:** zip does not support append-atomic writes — directly emitting into a zip would force file-locking and defeat the multi-process atomicity guarantee that motivated the 4 KiB line cap (and that Codex bot R3 review caught when the rotation check was post-condition rather than pre-condition). The hybrid keeps the hot path lock-free while compressing cold data 7–10× to control disk growth. `af log-validate` and consumer code transparently read both forms; the implementing CHG provides reader helpers that abstract the union.

### `af log` is fail-open at the hook boundary

`af log` exits non-zero on validation or filesystem errors, but per-agent hook scripts MUST invoke it with `af log ... || true` so a log emit failure cannot break the user's session. **Why:** observability is valuable, but not so valuable that we let it take down a coding session. Hooks are advisory; the fallback is graceful degradation, not failure.

### Implementation Workflow

This PRP follows the standard meta-workflow:

`COR-1102 (PRP, current) → COR-1602 strict review (4 reviewers — Codex + Gemini + GLM + DeepSeek — all ≥ 9.0; extended from default 2 for cross-vendor protocol validation) → COR-1101 CHG → COR-1500 TDD per phase`

Implementation phases (detailed decomposition belongs in the CHG):

- Phase 0 — PRP cleanup
- Phase 1 — Documents (`COR-1205` REF, `COR-1206` SOP, update to `COR-1200` retrospective consuming the log)
- Phase 2 — `af log` command
- Phase 3 — `af log-validate` command (renamed from earlier draft `af validate-activity-log`); transparently reads loose `.jsonl` and entries inside `archive.zip`
- Phase 4 — `af log-archive` command + scanner-skip enforcement test
- Phase 5 — Reference Claude Code `Stop` hook + integration test + v1.9.0 release

---

## Open Questions

The remaining items are CHG-stage implementation details, not design questions. None block PRP approval; each is explicitly deferred to the implementing CHG with the noted constraint.

- **`--stdin` mode for `af log`.** Should `af log` accept a `--stdin` mode that reads a pre-built JSON object directly (for agents that already construct the record themselves), in addition to the flag-based form? Adds surface area but avoids round-tripping through CLI flags. *Deferred to CHG; default decision if CHG punts: no, flag-based is sufficient for v1.*
- **`outcome` enum on `task.done`.** Should `task.done` records optionally carry a coarse `outcome` enum (`success | partial | failure`)? Useful for retrospective signal but risks over-engineering v1. *Deferred to CHG; default decision if CHG punts: no, deferred to v2 schema if usage data shows demand.*

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-01 | Initial version | Frank + Claude |
| 2026-05-02 | Self-audit revision pre-strict-review: split out-of-scope vs acceptance contradictions (Claude Code reference hook now in-scope as the sole reference impl; COR-1200 augmentation explicitly an additive bullet, not a semantic change); add 4 KiB line size cap to make POSIX O_APPEND atomicity provable; add explicit layer resolution algorithm; rename `af validate-activity-log` → `af log-validate`; add file permissions, gitignore, fail-open hook policy; tighten `agent_version` / `session_id` / `agent: other` rules; move `session_id` and agent-whitelist-source decisions from OQ into ## Decisions; trim OQs from 4 → 2 with explicit CHG default fallbacks; extend strict review to 4 reviewers (Codex + Gemini + GLM + DeepSeek). | Frank + Claude |
| 2026-05-02 | Strict 4-reviewer review (Codex+Gemini+GLM+DeepSeek) all PASS — Codex 9.9, GLM 9.9, Gemini 9.8, DeepSeek 9.8; OQ gate PASS for all four. 4/4 satellite advisories on L84 (long-term retention policy) and L85 (POSIX O_APPEND wording precision) to be addressed in the implementing CHG. Status: Draft → Approved. | Codex+Gemini+GLM+DeepSeek (strict review) |
| 2026-05-02 | Address PR #78 review (Codex bot, P1 inline at L85): add `summary_truncated` (boolean) to v1 optional fields list, resolving the self-contradiction where the spec required emitting `summary_truncated: true` on truncation while also forbidding writers from emitting unlisted fields. Validator updated: `summary_truncated: false` is invalid in v1 (omit instead). Acceptance criteria for af log-validate extended to cover this case. | Frank + Claude (PR #78 review fix) |
| 2026-05-02 | Address PR #78 R2 Codex review (2 blocking comments on commit 68e0011): (1) [P1 L147] Drop "at or near 4096-byte cap" qualifier from `summary_truncated` validator rule — when truncation is achieved by trimming `files`/`refs` rather than `summary`, the final record can sit well below the cap, and the qualifier would create false negatives. Validator now just checks the field is the literal boolean `true` if present (`false` still forbidden). (2) [P2 L130] `agent_version` is required but `af log` did not auto-fill it — combined with the fail-open hook contract (`af log ... \|\| true`), a hook that forgot `--agent-version` would silently drop every event. `af log` now reads `$ALFRED_AGENT_VERSION` (mirroring the existing `session_id` pattern) and falls back to the literal sentinel `"unknown"` when neither is supplied. Decision section updated, required-field constraint updated to permit the sentinel. | Frank + Claude (PR #78 R2 fix) |
| 2026-05-02 | Address PR #78 R3 Codex review (1 blocking comment on commit 009edbd): [P2→Blocking L135] Rotation threshold was a post-condition check ("already exceeds 8 MiB"), letting any record that straddles the boundary push the file past the cap. Changed to a strict pre-condition check on every append: if `current_file_size + new_record_line_len > 8 MiB`, rollover to next `.partN.jsonl` BEFORE writing. The cap is now an absolute upper bound (no file ever exceeds 8 MiB by even one byte). Both the COR-1205 rotation rule (L84) and the `af log` rotation handoff behavior (L132/L135) updated together so the contract is consistent. | Frank + Claude (PR #78 R3 fix) |
| 2026-05-02 | Amendment (in-place spec change, single PR, no version bump — schema literal stays `alfred.activity/v1`): (a) Storage location moved from `./logs/agent-activity/` to `./rules/logs/` per user direction; `COR-1206` mandates `af` document scanners hard-skip the `rules/logs/` subtree (regression test required in CHG). (b) Add hybrid archival: today's file stays raw `.jsonl` (POSIX append-atomicity preserved); closed days are atomically rolled into a single per-directory `archive.zip` via temp-file + os.replace + unlink. (c) Add `af log-archive` CLI surface and lazy archival on `af log` startup. (d) `af log-validate` extended to transparently read both loose `.jsonl` files and entries inside `archive.zip`. (e) Acceptance criteria + Decisions sections updated. (f) Phase decomposition extended from 4 → 5 (archive command + scanner-skip test as Phase 4, reference hook + release as Phase 5). | Frank + Claude (in-place amendment, route A) |
| 2026-05-02 | Address PR #80 R1 strict 4-reviewer review (Codex FAIL 8.8, DeepSeek FAIL 8.25, Gemini PASS 9.5, GLM PASS 9.5 with calibration anomaly): (1) [L89] Stale path `logs/agent-activity/` → `rules/logs/` in file-permissions clause (2/4 blocking; my own oversight from the path migration). (2) [L87] Atomic-procedure spec was misleading: archive replacement is atomic but raw-file unlink loop is not. Reframed as 'atomic for the archive replacement, eventually-consistent for raw-file cleanup' with explicit partial-failure semantics — affected raw files re-included on next run, readers dedupe by (filename, lineno) (4/4 vote). (3) [L87] Concurrent archival race: `archive.zip.tmp` → `archive.zip.tmp.<pid>.<rand6>` per-process unique tmp; race resolves via `os.replace` atomicity producing content-identical archive (3/4 blocking). (4) [L138] Lazy-archival fail-open now rate-limits stderr warnings to 'at most once per process per (directory, error_class)' to prevent looping callers from spam (Codex blocking + DeepSeek advisory). (5) [L138] Made the lazy-vs-explicit corrupt-archive asymmetry explicit ('lazy = conservative, explicit = bold'); previously implicit (DeepSeek advisory). (6) [L153, L161] `!` separator → `::` to avoid bash/zsh history expansion on copy-paste of violation paths (4/4 advisory). (7) [L173+] Added explicit CLI options table for `af log-archive` documenting `--force` flag (Codex blocking — flag promised in exit-code-5 description but never defined in CLI surface). (8) [L223, L226] Scanner-skip rule strengthened: 'all af scanners present and future' + implemented at `core/scanner.py` walk layer (not per-command) so future scanners inherit (GLM advisory). Plus tmpfile cleanup window (60s) for stale `archive.zip.tmp.*`. | Frank + Claude (PR #80 R1 fix) |
| 2026-05-02 | Address PR #80 R2 strict 4-reviewer review (Codex FAIL 8.9, DeepSeek/Gemini/GLM PASS — Codex was sole COR-1608-compliant reviewer and caught 3 R2-introduced contradictions): (1) [L63, L206, L248] Reserved-subtree allowlist + acceptance criteria + Decisions section updated to glob `archive.zip.tmp.*` (Codex blocking — R1 fix renamed tmpfile to suffixed form but allowlist still listed unsuffixed name, contradicting §Archival procedure). (2) [L183] `af log-archive` Tmpfile cleanup section synced to PID-based liveness check, removing stale 60s wording (Codex blocking + 4/4 advisory consensus). (3) [L91] §Archival step 4 changed from 60s wall-clock window to PID liveness check via `os.kill(pid, 0)`; rationale 'wall-clock-based age checks are explicitly rejected because backward NTP / VM-resume skew can mistakenly delete live tmpfiles' inline (3/4 advisory). (4) [L145] Lazy-archival warn rate-limit redesigned: removed unsound 'at most once per process' suppression (every `af log` is a fresh CLI process — per-process limit was meaningless to looping callers); now emits exactly one stderr line per invocation with the redirection escape hatch (`af log ... 2>/dev/null`) noted (Codex blocking). (5) [L146] Mandatory warning format defined: `af log: lazy archival failed in <dir>: <error_class>: <message>. Recover: af log-archive --force`. `<error_class>` is now a fixed v1 enum {filesystem, corrupt-archive, race-lost, partial-cleanup} — no longer informal (4/4 advisory). `Recover:` suffix mandatory so operators see the recovery command without reading the PRP (4/4 advisory). (6) [L161] `af log-validate` Behavior section now explicitly echoes the `(filename, lineno)` deduplication contract from §Archival, closing the gap between archival self-healing and validator behavior (3/4 advisory). | Frank + Claude (PR #80 R2 fix) |
| 2026-05-02 | Address PR #80 R3 strict 4-reviewer review (4/4 PASS but GLM raised 2 blocking, Codex+Gemini+DeepSeek raised same as advisory — true signal worth fixing pre-merge): (1) [L91] PID-liveness POSIX semantics fact-error fixed: `os.kill(pid, 0)` does NOT 'succeed iff process exists regardless of signal-permission' — `PermissionError`/EPERM means process EXISTS but is owned by another user (shared host, container). Spec now mandates explicit exception handling: `ProcessLookupError` (ESRCH) ⇒ dead ⇒ remove tmpfile; `PermissionError` (EPERM) ⇒ alive ⇒ leave alone; any other exception or success ⇒ alive ⇒ leave alone. The EPERM branch is critical — treating it as 'dead' would let one user's archiver delete another user's live tmpfile and corrupt their in-flight archive (3/4 reviewer signal — GLM blocking, Codex advisory, DeepSeek advisory). (2) [L150–151] Mandatory sanitization for warning format `<dir>` / `<message>` to prevent log-injection: filesystem paths can contain \n/\r/\t and any byte except / and \0; OS error strings frequently embed paths. Writer MUST apply JSON string-escape ruleset before interpolation (\\ → \\\\, \n → \\n literal, etc., control chars 0x00–0x1F → \\xNN). Without this, a path like `/tmp/evil\nRecover: rm -rf /` could spoof a fake `Recover:` directive on the next line (4/4 reviewer signal — GLM blocking, Codex+Gemini+DeepSeek advisory). Bonus: added `permission-denied` to error_class enum (Gemini advisory) so EACCES/EPERM gets a dedicated bucket separate from generic `filesystem`. | Frank + Claude (PR #80 R3 fix) |
| 2026-05-02 | Address PR #80 R4 strict 4-reviewer review (4/4 PASS — Codex 9.9, Gemini 10.0, GLM 10.0, DeepSeek 9.41 — 0 blocking, 0 required changes; this is housekeeping for a 2/4 advisory): [L152] Spec-implementation consistency gap noted by Codex + DeepSeek. Spec required `\xNN` for control chars 0x00–0x1F, but the recommended `json.dumps()` shortcut produces `\u00NN`. Both are safe (single-line preserved, injection blocked) but a literal-spec-following implementer would diverge from the shortcut-following one. Spec now accepts either form explicitly: '\xNN (hex byte) or \u00NN (Unicode escape) — implementations MAY pick either; both preserve the single-physical-line guarantee'. Also added 'this is the recommended path' to the json.dumps hint to make the implementation choice explicit. No behavior change; spec-as-written and json.dumps()-shortcut now provably converge. | Frank + Claude (PR #80 R4 housekeeping) |
| 2026-05-02 | Address PR #80 Codex bot inline review #3175617379 (P1 blocking on commit 5595d26): The R2 'concurrent archivers race resolves to content-identical' claim was incomplete — only true if both archivers enumerate the SAME closed-day file set. If Process A enumerates {f1,f2} at T0, Process B enumerates {f1,f2,f3} (a partN.jsonl rotated since T0) at T1, archives + unlinks at T2, then A's stale enumeration at T3 would build a tmpfile missing f3, and A's os.replace would drop f3 from archive AND f3's raw file is already unlinked → data loss. Fix: add archival 'step 0' acquiring fcntl.flock(LOCK_EX \| LOCK_NB) on the log directory with try-lock semantics — if locked, skip the archival cycle (next af log will retry); if free, hold for the duration of steps 1–4. POSIX advisory locks auto-release on process exit so SIGKILL is safe. The lock serializes archival but does NOT block af log emit (which never touches archive.zip). Step 2's race-content-identical claim is replaced with 'no concurrent racer can have produced a newer archive between step 1 enumeration and step 2 replace; new archive.zip is strict superset of prior version'. | Frank + Claude (PR #80 Codex bot P1 fix) |
| 2026-05-02 | Address PR #80 Codex bot inline review #3175814258 (P2, blocking-class self-contradiction): `af log-archive` acceptance criterion (L209) still called §Archival a '4-step procedure' after commit 9cd2aaa added step 0 (the lock). Implementers/tests following the L209 bullet would pass while omitting the lock and reintroduce the data-loss race that step 0 was added to prevent. Synced L209 to '5-step procedure' enumerating step 0 (lock) through step 4 (tmpfile cleanup); added explicit note about POSIX advisory lock auto-release on process exit so SIGKILL is safe. Same self-contradiction class Codex bot has reliably caught throughout this amendment series (PR #78 R1 summary_truncated, PR #80 R1 L89 stale path, PR #80 R2 L63 allowlist + L200 acceptance, PR #80 R3 60s wall-clock, now this). Bot continues to be the most reliable static-diff cross-reference checker. | Frank + Claude (PR #80 Codex bot L209 sync fix) |
| 2026-05-02 | Address PR #80 R5 strict 4-reviewer review (4/4 PASS — Codex 9.9, Gemini 9.9, GLM 9.9, DeepSeek 9.47 — but 3 convergent advisory worth fixing pre-merge per the 'no known bug to main' principle): (1) [L88, 4/4 advisory] NFS/SMB `flock` reliability not declared. Spec now explicitly carves out network filesystems from v1 scope (joins Windows in §Out of scope L55-56) — `flock(2)` semantics on NFS/SMB/fuse mounts are implementation-defined and may silently no-op, breaking both `O_APPEND` per-line atomicity AND archival serialization. Local POSIX FS (ext4/xfs/btrfs/apfs/hfs+/ufs/zfs) is the v1 substrate; v2 may revisit. (2) [L88, 2/4 advisory] CPython API correctness: `open(<dir>, O_DIRECTORY)` is invalid Python — builtin `open()` raises `IsADirectoryError` on a directory. Spec now uses correct `os.open(<dir>, os.O_RDONLY \| os.O_DIRECTORY)` pseudocode + explicit `fcntl.LOCK_EX \| fcntl.LOCK_NB` constants + `BlockingIOError`/`EWOULDBLOCK` exception name + `os.close(fd)` cleanup pattern. Implementers can now copy-paste safely. (3) [L184, 2/4 advisory — same self-contradiction class Codex bot catches every round] `af log-archive` Per-directory atomicity bullet listed only steps 1/2/3, missing step 0 (lock) + step 4 (PID cleanup). Now enumerates all 5 steps consistent with L209 acceptance criterion. Bonus: closed Gemini's separate advisory about `af log-archive` standalone lock-contention behavior — spec now mandates exit code 0 + stderr 'another archiver is running, skipping' (preserves try-lock-and-skip semantics consistent with lazy path; avoids blocking cron/CI). | Frank + Claude (PR #80 R5 fix) |
| 2026-05-02 | Address PR #80 R6 Codex bot inline #3175870539 + R6 trinity Gemini/GLM 2/4 advisory (3/4 collective signal): L56 NFS carve-out only mentioned `rules/logs/` — but `~/.alfred/logs/` USR fallback has the SAME O_APPEND + flock(2) issues on NFS-mounted home directories (common in enterprise Linux / Kerberos / LDAP-managed setups). Without scoping the carve-out to both log roots, USR-mode users on those setups silently break v1 guarantees. Spec now extends the §Out of scope NFS bullet to 'both log roots' and adds an implementing-CHG SHOULD: `os.statvfs` the resolved log directory at `af log` startup and emit a one-time stderr warning on network-mount detection (hard refusal deferred to v2 to avoid breaking existing setups during rollout). R6 trinity Codex + DeepSeek had argued 'no contradiction (USR is local by construction)' — the CHG runtime warning makes that interpretation testable and removes the ambiguity by making the deployment substrate observable at runtime. | Frank + Claude (PR #80 R6 Codex bot + 3/4 trinity advisory fix) |

---

## References

- FXA-2229 (Layered SOP Memory Model) — defines the recall surface; this PRP covers the complementary emit surface.
- COR-1200 (Session Retrospective) — current consumer of session memory; will be updated to read the activity log.
- COR-1201 (Discussion Tracking) — D-item protocol; remains the human-curated short-term memory layer alongside the machine-emitted log.
- JSON Lines specification — https://jsonlines.org
- RFC 3339 — date and time format used for the `ts` field.
