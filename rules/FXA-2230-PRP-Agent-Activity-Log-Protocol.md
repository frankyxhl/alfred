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
- Add `af log` as a thin writer that any agent can shell out to.
- Add `af log-validate` as a schema checker so protocol compliance is externally testable.
- Define privacy and size constraints (no secrets, no full prompts, summary length cap).

Out of scope:

- Per-agent hook implementations **beyond the single Claude Code reference implementation** listed in acceptance criteria. Copilot, Cursor, Cline, Aider, Codex CLI, Gemini CLI integrations are each follow-on CHGs with their own scope.
- Embedding generation, semantic search, or any analytics over the log (separate proposal if needed).
- Modifying the **core semantics** of `COR-1201` (D-item lifecycle) or `COR-1200` (the 6-step retrospective protocol). The retrospective gets a single additive bullet in step 1 directing the agent to read the activity log first; its 6-step protocol and outputs are unchanged.
- Changes to FXA-2229's `Recall` field or `af recall` command. Cross-references are added at the end of FXA-2229 implementation, not here.
- Encrypting log files at rest, log shipping to remote services, or multi-machine sync.
- Windows-specific atomicity guarantees for concurrent multi-process emit. v1 ships POSIX-correct behavior; Windows is best-effort and revisited if concrete need surfaces.

## Proposed Solution

### Two new PKG documents

**`COR-1205-REF-Agent-Activity-Log-Format`** — the canonical data contract. Defines:

- **Storage location.** `./logs/agent-activity/YYYY-MM-DD.jsonl` at PRJ layer; `~/.alfred/logs/agent-activity/YYYY-MM-DD.jsonl` at USR layer when no project context.
- **Encoding.** UTF-8, LF line terminator, one JSON object per line, no embedded newlines, no trailing comma, append-only.
- **Required fields per event:**
  - `ts` — RFC 3339 UTC timestamp (`2026-05-02T14:23:11Z`).
  - `agent` — short identifier from a v1 whitelist (`claude-code`, `copilot`, `cursor`, `cline`, `aider`, `codex-cli`, `gemini-cli`, `other`). The whitelist is hardcoded as a constant inside the validator (see Decisions). Adding a new entry requires a follow-on PRP that bumps the constant.
  - `agent_version` — agent's own version string. Constraints: 1–64 ASCII characters, no whitespace, no newlines. Not otherwise validated for semver shape.
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
- **Rotation.** New file each calendar day in UTC. If a single file exceeds 8 MiB, split into `YYYY-MM-DD.partN.jsonl` (N starts at 1 and increments).
- **Per-record line size cap.** Each JSONL line (including the trailing `\n`) MUST be ≤ 4096 bytes. This bound is required so that POSIX `O_APPEND` writes are atomic across processes (POSIX guarantees atomicity for writes ≤ `PIPE_BUF`, which is ≥ 4096 on every supported OS). `af log` truncates `summary` and trims `files` / `refs` from the end if needed to stay under the cap; when this happens the optional `summary_truncated: true` field (see Optional fields above) is emitted on that record so downstream readers can detect partial data.
- **File permissions.** Log files are created with mode `0644`; the `logs/agent-activity/` directory is created with mode `0755`. Agents MUST NOT relax these permissions. (Activity logs are not secrets per the privacy constraints below; they are designed to be auditable by the user.)
- **Default git policy.** Activity logs are per-machine artifacts and SHOULD be gitignored by default. `COR-1206` provides the exact `.gitignore` snippet. Projects MAY commit logs deliberately; that is a project-level choice and not the protocol default.
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
  1. If `--root <DIR>` is given → write to `<DIR>/logs/agent-activity/<YYYY-MM-DD>.jsonl`.
  2. Else if cwd is inside a recognized project (`./rules/` exists at cwd or any ancestor) → write to `<project-root>/logs/agent-activity/<YYYY-MM-DD>.jsonl`.
  3. Else → write to `~/.alfred/logs/agent-activity/<YYYY-MM-DD>.jsonl`.
- **Auto-fills** `ts` (current UTC), `schema` (literal), and `session_id` (UUIDv4) when those flags / env vars are not provided. Reads `$ALFRED_SESSION_ID` if set, otherwise generates.
- **Validates** the resulting record against the v1 schema before writing; rejects with exit code 3 (validation error) on failure, printing the failing field and rule.
- **Atomic append** using `open(O_APPEND | O_CREAT, 0o644)` followed by a single `write()` of one line ≤ 4096 bytes. No read-modify-write. No locking required on POSIX given the size cap.
- **Rotation handoff.** If today's file already exceeds 8 MiB at append time, `af log` opens `<YYYY-MM-DD>.partN.jsonl` where N is the next integer (smallest unused).
- **Failure mode.** `af log` MUST NOT block or error a calling agent's user-visible operation. Hook scripts SHOULD invoke it with `af log ... || true` so an emit failure cannot cascade into a session break. `af log` itself returns non-zero on failure for diagnostic visibility.
- **Exit codes.** 0 = written, 2 = invalid CLI args, 3 = schema validation error, 4 = filesystem error.

**`af log-validate [PATH]`** — schema checker. The executable form of the protocol. Naming: hyphenated form preferred over `af validate-activity-log` (shorter, shares `af log` prefix) and over a `af log validate` subcommand (since `af log` itself takes a positional message argument and Click subcommand groups conflict awkwardly with positional dispatch). Kept separate from existing `af validate` (which validates document structure, not activity logs).

```
af log-validate                              # validate today's PRJ log
af log-validate ./logs/agent-activity/       # validate every *.jsonl in directory
af log-validate path/to/2026-05-02.jsonl     # validate a specific file
```

Behavior:
- **Default target** when `PATH` omitted: today's log file using the same layer resolution as `af log`.
- **Path semantics:** if `PATH` is a file → validate that file. If `PATH` is a directory → validate every file matching `*.jsonl` and `*.partN.jsonl` recursively at depth 1.
- **Per-line check:** required fields present, types correct, `agent` in v1 whitelist, `event` in v1 enum, `summary` length, `schema` literal match, `agent_name` present iff `agent == "other"`, `summary_truncated` (if present) is the literal boolean `true` and the record is at or near the 4096-byte cap, line ≤ 4096 bytes.
- **Output:** one line per violation in the form `<path>:<lineno>: <field>: <reason>`. Quiet on success.
- **Exit codes:** 0 = all valid, 1 = schema violations found, 2 = invalid CLI args, 4 = file/dir not readable.

### Acceptance Criteria

This proposal is complete when:

- `COR-1205-REF-Agent-Activity-Log-Format` exists in PKG with the v1 schema fully specified (fields, enum values, file format, rotation, line size cap, file permissions, gitignore policy, privacy constraints).
- `COR-1206-SOP-Emit-Agent-Activity` exists in PKG with mandatory triggers, optional triggers, and the per-agent mapping table covering at least: `claude-code`, `copilot`, `cursor`, `aider`, plus `other` as escape hatch.
- `af log` command writes a record that passes `af log-validate`, including: layer resolution per the 3-step rule, auto-fill of `ts`/`session_id`/`schema`, line size cap with `summary_truncated` flag, rotation handoff at 8 MiB, exit codes per spec.
- `af log-validate` correctly reports schema violations on a synthetic invalid file covering at least: missing required field, wrong type, `agent` not in whitelist, `agent: "other"` without `agent_name`, `summary_truncated: false` (must be omitted, not set to false in v1), line > 4096 bytes, malformed `schema` literal.
- `COR-1200` (retrospective) gets a single additive bullet in step 1 directing the agent to read today's `logs/agent-activity/<today>.jsonl` before reconstructing actions. The 6-step protocol and outputs are otherwise unchanged.
- At least **one reference implementation** ships in the same release: a Claude Code `Stop` hook script (committed under `hooks/` in this repo) that emits `task.done` via `af log ... || true` and passes `af log-validate` over a real session log.
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

### `session_id`: agent-provided when available, UUIDv4 fallback

`af log` reads `$ALFRED_SESSION_ID` (set by the calling hook) and uses it as `session_id` when present. If absent, `af log` generates a UUIDv4 and emits it. **Why:** preserves cross-tool correlation when the harness exposes a stable session id (Claude Code, Cursor); does not break agents that do not. The emitted id is always written to the log so downstream readers can group records by session even when generation happened on the writer side.

### Agent whitelist lives in code, not in a separate YAML

The v1 agent whitelist (`claude-code`, `copilot`, `cursor`, `cline`, `aider`, `codex-cli`, `gemini-cli`, `other`) is hardcoded as a Python constant in the validator module. **Why:** keeps schema enforcement self-contained — no separate parser for `COR-1206.agents.yaml`, no risk of doc/code drift. The cost of adding a new agent is one PRP that bumps the constant and updates `COR-1206`'s mapping table in the same change. v2 may revisit this if the whitelist starts changing more than once per quarter.

### `agent: "other"` requires `agent_name`

When `agent` is `"other"`, the optional field `agent_name` becomes required and identifies the unrecognized harness (e.g. `"qodo"`). **Why:** prevents the `"other"` value from silently absorbing all unrecognized writers and erasing the cost signal that the whitelist needs an addition. A spike in `agent: "other"` log lines with the same `agent_name` is the explicit trigger for a follow-on whitelist PRP.

### `af log` is fail-open at the hook boundary

`af log` exits non-zero on validation or filesystem errors, but per-agent hook scripts MUST invoke it with `af log ... || true` so a log emit failure cannot break the user's session. **Why:** observability is valuable, but not so valuable that we let it take down a coding session. Hooks are advisory; the fallback is graceful degradation, not failure.

### Implementation Workflow

This PRP follows the standard meta-workflow:

`COR-1102 (PRP, current) → COR-1602 strict review (4 reviewers — Codex + Gemini + GLM + DeepSeek — all ≥ 9.0; extended from default 2 for cross-vendor protocol validation) → COR-1101 CHG → COR-1500 TDD per phase`

Implementation phases (detailed decomposition belongs in the CHG):

- Phase 0 — PRP cleanup
- Phase 1 — Documents (`COR-1205` REF, `COR-1206` SOP, update to `COR-1200` retrospective consuming the log)
- Phase 2 — `af log` command
- Phase 3 — `af log-validate` command (renamed from earlier draft `af validate-activity-log`)
- Phase 4 — Reference Claude Code `Stop` hook + tests + integration

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

---

## References

- FXA-2229 (Layered SOP Memory Model) — defines the recall surface; this PRP covers the complementary emit surface.
- COR-1200 (Session Retrospective) — current consumer of session memory; will be updated to read the activity log.
- COR-1201 (Discussion Tracking) — D-item protocol; remains the human-curated short-term memory layer alongside the machine-emitted log.
- JSON Lines specification — https://jsonlines.org
- RFC 3339 — date and time format used for the `ts` field.
