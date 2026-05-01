# FXA-2230 Review Pack

> **Self-contained review pack for COR-1602 strict mode 4-reviewer review of the `FXA-2230 — Agent Activity Log Protocol` PRP.**
> Reviewers should NOT need to open any other file in the repository to perform this review. Everything required to score the PRP is in this single document.

**Pack assembled:** 2026-05-02
**Artifact under review:** `rules/FXA-2230-PRP-Agent-Activity-Log-Protocol.md`
**Review mode:** COR-1602 strict (PRP — **all four** reviewers must score ≥ 9.0)
**Reviewer rubric:** COR-1608 (PRP scoring) + COR-1611 (reviewer calibration)
**Reviewers:** Codex, Gemini, GLM, DeepSeek (extended from the default 2-reviewer COR-1602 because this PRP defines a vendor-neutral protocol that will be consumed across multiple model families — cross-vendor validation is part of the value)
**Dispatch:** Identical pack delivered to all four reviewers in parallel via the user's `/trinity` Claude Code skill.

---

## 1. Reviewer Brief

FXA-2230 is a **PRP (proposal)** that defines an **agent-neutral, vendor-neutral activity log protocol** for Alfred. It introduces:

1. Two new PKG documents — `COR-1205-REF-Agent-Activity-Log-Format` (the data contract) and `COR-1206-SOP-Emit-Agent-Activity` (the implementation guide with a per-agent mapping table for Claude Code, GitHub Copilot, Cursor, Cline, Aider, Codex CLI, Gemini CLI).
2. Two new CLI surfaces — `af log` (universal writer; any agent can shell out) and `af log-validate` (schema checker so protocol compliance is externally testable).
3. A versioned event schema (`alfred.activity/v1`) with required fields (`ts`, `agent`, `agent_version`, `session_id`, `event`, `summary`, `schema`) and optional fields (`refs`, `files`, `duration_ms`, `parent_event`, `agent_name`).
4. A 9-value v1 event enum (`session.start/end`, `task.start/done/aborted`, `doc.created/updated`, `decision`, `note`).
5. A 4 KiB per-line cap so that POSIX `O_APPEND` writes are guaranteed atomic across processes (since `PIPE_BUF` ≥ 4096 on every supported OS — no locking needed).
6. A reference implementation requirement: at least one Claude Code `Stop` hook script must ship in the same release and pass `af log-validate`.
7. An explicit positioning vs FXA-2229: this is the **emit surface** (capture) counterpart to FXA-2229's **recall surface** (retrieval). The two PRPs are **independently implementable** — FXA-2230 does **not** depend on FXA-2229 shipping.

The PRP went through a **self-audit revision round on 2026-05-02 before this dispatch** (see the `## Change History` row dated 2026-05-02 in Section 2 lines 230). The first draft had three structural issues caught by self-review:
- Out-of-scope vs Acceptance Criteria contradictions (per-agent hooks excluded but Claude Code reference hook required; COR-1200 modifications excluded but the retrospective also required to consume the log).
- POSIX `O_APPEND` atomicity claimed without a line size bound — the spec now caps records at 4096 bytes which makes the claim provable from POSIX guarantees.
- `session_id` semantics deferred to Open Questions despite being a required field.

The revision converged the contradictions, added the size cap, lifted `session_id` and agent-whitelist-source policy from Open Questions into `## Decisions`, and trimmed Open Questions from 4 to 2. **Reviewers must score the post-revision artifact embedded in Section 2.**

This is a **strict** review. Per COR-1102 + COR-1602, a PRP requires **all four** reviewers (Codex, Gemini, GLM, DeepSeek) to return PASS (weighted score ≥ 9.0 **and** the Open Questions hard gate satisfied) before the PRP can advance to a CHG (COR-1101). If any reviewer fails or returns FIX, the orchestrator (Claude Code) will revise the PRP per their deductions and re-dispatch. The same review pack is sent to all reviewers — they must apply identical standards (COR-1611) and not coordinate.

What we want from each reviewer:

- **A weighted score table** populated against the six COR-1608 dimensions, with deductions cited by line number from the embedded PRP in Section 2.
- **A hard-gate verdict** on the `## Open Questions` section (lines 216–221 — 2 OQs remaining; both annotated with explicit CHG-stage default fallbacks).
- **A list of blocking deductions** vs **advisory notes** (the distinction matters — only blocking deductions affect the score).
- **A final PASS/FAIL verdict** at the end.

---

## 2. Artifact Under Review

PRP file path: `rules/FXA-2230-PRP-Agent-Activity-Log-Protocol.md`
Total length: **240 lines**
Status: **Draft**
Revision date: **2026-05-02** (post self-audit; first dispatch to strict review)

The full PRP content is embedded below **verbatim** with 1-based line numbers prefixed on each line in a `NNN | ` format. Reviewers **MUST** cite line numbers from this block for every deduction (e.g. "Line 130 — `O_APPEND` atomicity claim relies on PIPE_BUF ≥ 4096; correct given line 85 cap, but should cite POSIX § directly").

```md
   1 | # PRP-2230: Agent Activity Log Protocol
   2 | 
   3 | **Applies to:** FXA project
   4 | **Last updated:** 2026-05-02
   5 | **Last reviewed:** 2026-05-02
   6 | **Status:** Draft
   7 | **Related:** FXA-2229 (Layered SOP Memory Model — recall surface; this PRP covers the complementary emit surface), COR-1200 (Session Retrospective), COR-1201 (Discussion Tracking)
   8 | 
   9 | ---
  10 | 
  11 | ## What Is It?
  12 | 
  13 | This PRP proposes a **vendor-neutral, agent-neutral activity log protocol** for Alfred. Any coding agent — Claude Code, GitHub Copilot, Cursor, Cline, Aider, Codex CLI, Gemini CLI, or any future tool — can emit structured events to a shared on-disk log so that "what was done in this session" becomes a first-class, machine-readable artifact instead of relying on the agent to remember.
  14 | 
  15 | The protocol itself is two pieces of documentation (`COR-1205` REF format contract + `COR-1206` SOP implementation guide) plus two minimal CLI surfaces (`af log` writer + `af log-validate` schema checker). The protocol does **not** mandate how each agent hooks into its own runtime — that is delegated to per-agent implementations following the SOP.
  16 | 
  17 | This is the **emit surface** counterpart to FXA-2229's **recall surface**. FXA-2229 defines how durable documents get retrieved into prompt context; FXA-2230 defines how runtime work gets captured in the first place.
  18 | 
  19 | ---
  20 | 
  21 | ## Problem
  22 | 
  23 | Today Alfred's short-term working memory (FXA-2229 layer 4) is captured **only** by the discussion tracker (`COR-1201`) and end-of-session retrospective (`COR-1200`). Both require the agent to **manually decide** what to write and **manually call** `af update` / `af create`. This has three concrete failure modes observable today:
  24 | 
  25 | 1. **Lossy retrospectives.** `COR-1200 step 1` ("List all actions taken this session") relies on the agent's recollection of the session. For long sessions or compaction events, the agent reconstructs from chat history rather than from a ground-truth log, and consistently under-reports.
  26 | 2. **No cross-tool continuity.** A user who runs Claude Code in the morning and Cursor in the afternoon has **no shared trail** of what happened. Each tool's session state is private to that tool. The discussion tracker only captures what one agent chose to write.
  27 | 3. **No forensics for agent behavior.** When an agent takes an unexpected action (wrong file edit, scope creep, missed SOP), there is no append-only artifact to review. The conversation transcript is private to the harness and not always exportable.
  28 | 
  29 | The natural fix — "make the agent emit a log line every time it finishes something" — is **not a single-agent problem**. Hardcoding it as a Claude Code `Stop` hook only solves it for Claude Code. Each coding agent has different lifecycle hooks (`Stop` events, MCP callbacks, VS Code extensions, shell commands, git hooks). What is missing is a **shared contract** they can all target.
  30 | 
  31 | Alfred is uniquely positioned to own this contract because Alfred is already document-first and framework-agnostic: `core/` has no Click dependency, `af` has no agent dependency, PKG documents are portable.
  32 | 
  33 | ## Scope
  34 | 
  35 | This proposal covers the protocol design and the minimum CLI surface needed to make the protocol **executable and verifiable**. Per-agent implementations (Claude Code hook scripts, VS Code extensions, etc.) are explicitly out of scope for this PRP — they will be follow-on CHGs, one per agent.
  36 | 
  37 | In scope:
  38 | 
  39 | - Define the on-disk format for activity log files (location, encoding, JSONL conventions, rotation rules).
  40 | - Define a versioned event schema (`alfred.activity/v1`) with required and optional fields.
  41 | - Define the minimum event enum (`session.start`, `session.end`, `task.start`, `task.done`, `task.aborted`, `doc.created`, `doc.updated`, `decision`, `note`).
  42 | - Define the per-agent implementation guidance: when to emit, how to map native lifecycle events, and the universal fallback (`af log`).
  43 | - Add `af log` as a thin writer that any agent can shell out to.
  44 | - Add `af log-validate` as a schema checker so protocol compliance is externally testable.
  45 | - Define privacy and size constraints (no secrets, no full prompts, summary length cap).
  46 | 
  47 | Out of scope:
  48 | 
  49 | - Per-agent hook implementations **beyond the single Claude Code reference implementation** listed in acceptance criteria. Copilot, Cursor, Cline, Aider, Codex CLI, Gemini CLI integrations are each follow-on CHGs with their own scope.
  50 | - Embedding generation, semantic search, or any analytics over the log (separate proposal if needed).
  51 | - Modifying the **core semantics** of `COR-1201` (D-item lifecycle) or `COR-1200` (the 6-step retrospective protocol). The retrospective gets a single additive bullet in step 1 directing the agent to read the activity log first; its 6-step protocol and outputs are unchanged.
  52 | - Changes to FXA-2229's `Recall` field or `af recall` command. Cross-references are added at the end of FXA-2229 implementation, not here.
  53 | - Encrypting log files at rest, log shipping to remote services, or multi-machine sync.
  54 | - Windows-specific atomicity guarantees for concurrent multi-process emit. v1 ships POSIX-correct behavior; Windows is best-effort and revisited if concrete need surfaces.
  55 | 
  56 | ## Proposed Solution
  57 | 
  58 | ### Two new PKG documents
  59 | 
  60 | **`COR-1205-REF-Agent-Activity-Log-Format`** — the canonical data contract. Defines:
  61 | 
  62 | - **Storage location.** `./logs/agent-activity/YYYY-MM-DD.jsonl` at PRJ layer; `~/.alfred/logs/agent-activity/YYYY-MM-DD.jsonl` at USR layer when no project context.
  63 | - **Encoding.** UTF-8, LF line terminator, one JSON object per line, no embedded newlines, no trailing comma, append-only.
  64 | - **Required fields per event:**
  65 | -   - `ts` — RFC 3339 UTC timestamp (`2026-05-02T14:23:11Z`).
  66 | -   - `agent` — short identifier from a v1 whitelist (`claude-code`, `copilot`, `cursor`, `cline`, `aider`, `codex-cli`, `gemini-cli`, `other`). The whitelist is hardcoded as a constant inside the validator (see Decisions). Adding a new entry requires a follow-on PRP that bumps the constant.
  67 |   - `agent_version` — agent's own version string. Constraints: 1–64 ASCII characters, no whitespace, no newlines. Not otherwise validated for semver shape.
  68 |   - `session_id` — string, 1–128 chars, no whitespace. Provided by the agent if available; auto-generated as UUIDv4 by `af log` when absent (see Decisions).
  69 |   - `event` — one of the v1 event enum values.
  70 |   - `summary` — UTF-8 string, 1–500 characters, no newlines, no NUL bytes.
  71 |   - `schema` — exact literal `"alfred.activity/v1"`.
  72 | - **Optional fields per event:**
  73 |   - `refs` — array of `PREFIX-ACID` strings, deduplicated, ≤ 16 entries.
  74 |   - `files` — array of repo-relative POSIX paths, deduplicated, ≤ 32 entries.
  75 |   - `duration_ms` — non-negative integer ≤ 86_400_000 (one day).
  76 |   - `parent_event` — optional event correlation id (string, same format as `session_id`).
  77 |   - `agent_name` — required when `agent: "other"`; free-form 1–64 chars to identify the unrecognized harness (e.g. `"qodo"`, `"continue"`). MUST be omitted otherwise.
  78 | - **v1 event enum.**
  79 |   - `session.start`, `session.end` — agent session lifecycle.
  80 |   - `task.start`, `task.done`, `task.aborted` — coarse task boundaries (one user turn or one logical sub-task).
  81 |   - `doc.created`, `doc.updated` — Alfred document write events; `refs` SHOULD be set.
  82 |   - `decision` — D-item decisions, PRP convergences, scope cuts.
  83 |   - `note` — free-form fallback when no other event applies.
  84 | - **Rotation.** New file each calendar day in UTC. If a single file exceeds 8 MiB, split into `YYYY-MM-DD.partN.jsonl` (N starts at 1 and increments).
  85 | - **Per-record line size cap.** Each JSONL line (including the trailing `\n`) MUST be ≤ 4096 bytes. This bound is required so that POSIX `O_APPEND` writes are atomic across processes (POSIX guarantees atomicity for writes ≤ `PIPE_BUF`, which is ≥ 4096 on every supported OS). `af log` truncates `summary` and trims `files` / `refs` from the end if needed to stay under the cap; the truncation flag `summary_truncated: true` is set when truncation occurs.
  86 | - **File permissions.** Log files are created with mode `0644`; the `logs/agent-activity/` directory is created with mode `0755`. Agents MUST NOT relax these permissions. (Activity logs are not secrets per the privacy constraints below; they are designed to be auditable by the user.)
  87 | - **Default git policy.** Activity logs are per-machine artifacts and SHOULD be gitignored by default. `COR-1206` provides the exact `.gitignore` snippet. Projects MAY commit logs deliberately; that is a project-level choice and not the protocol default.
  88 | - **Privacy & safety constraints.** Forbidden content in any field: API keys, OAuth tokens, full prompt text, full tool call arguments, raw file contents (file *paths* are fine), user PII, environment variable values. Agents are responsible for their own redaction; the validator does not detect secrets. `summary` ≤ 500 chars enforces concision.
  89 | - **Versioning.** Schema version is fixed in `schema` field. Breaking changes ship as `alfred.activity/v2` and require a new PRP. v1 readers MUST ignore unknown optional fields they encounter (forward compatibility); v1 writers MUST NOT emit fields not listed in v1.
  90 | 
  91 | **`COR-1206-SOP-Emit-Agent-Activity`** — the implementation guide. Defines:
  92 | 
  93 | - **Mandatory triggers** (every agent MUST emit at minimum):
  94 |   - One `session.start` per session.
  95 |   - One `session.end` per session.
  96 |   - At least one `task.done` (or `task.aborted` / `note`) per user-facing turn that resulted in non-trivial action.
  97 |   - One `doc.created` or `doc.updated` per Alfred document write.
  98 | - **Optional triggers** (agent MAY emit):
  99 |   - `task.start` for long-running tasks.
 100 |   - `decision` for material decisions surfaced in conversation.
 101 |   - `note` for anything that doesn't fit elsewhere.
 102 | - **Per-agent mapping table** (initial v1 entries, extensible by follow-on PRP):
 103 | 
 104 |   | Agent | Native hook / mechanism | How to emit |
 105 |   |---|---|---|
 106 |   | Claude Code | `settings.json` `Stop` and `PostToolUse` hooks | `hooks/emit-activity.sh` reads `$CLAUDE_*` env vars, writes JSONL |
 107 |   | GitHub Copilot (VS Code) | No native lifecycle hook → companion VS Code extension listening to chat events | extension calls `af log` |
 108 |   | Cursor | `.cursorrules` instructs the model to call `af log` after each turn | shell-out via `af log` |
 109 |   | Cline / Roo Code | Custom MCP tool exposing `af log`; rules instruct usage | tool call |
 110 |   | Aider | `--cmd-stop` callback or git post-commit hook | shell script writes JSONL |
 111 |   | Codex CLI / Gemini CLI | Each SDK's lifecycle event hook | shell script writes JSONL |
 112 |   | Universal fallback | `af log` subcommand (always available, agent-agnostic) | direct shell-out |
 113 | - **Compliance test.** Every implementation MUST pass `af log-validate <file>` on its emitted output for at least one full session before being added to the mapping table.
 114 | 
 115 | ### Two new CLI surfaces
 116 | 
 117 | **`af log`** — universal writer. Any agent that can shell out can use this as a fallback regardless of native hook availability.
 118 | 
 119 | ```
 120 | af log "FXA-2230 PRP draft created" --event task.done --refs FXA-2230 --files rules/FXA-2230-PRP-Agent-Activity-Log-Protocol.md --agent claude-code
 121 | ```
 122 | 
 123 | Behavior:
 124 | - **Layer resolution** (deterministic, in order):
 125 |   1. If `--root <DIR>` is given → write to `<DIR>/logs/agent-activity/<YYYY-MM-DD>.jsonl`.
 126 |   2. Else if cwd is inside a recognized project (`./rules/` exists at cwd or any ancestor) → write to `<project-root>/logs/agent-activity/<YYYY-MM-DD>.jsonl`.
 127 |   3. Else → write to `~/.alfred/logs/agent-activity/<YYYY-MM-DD>.jsonl`.
 128 | - **Auto-fills** `ts` (current UTC), `schema` (literal), and `session_id` (UUIDv4) when those flags / env vars are not provided. Reads `$ALFRED_SESSION_ID` if set, otherwise generates.
 129 | - **Validates** the resulting record against the v1 schema before writing; rejects with exit code 3 (validation error) on failure, printing the failing field and rule.
 130 | - **Atomic append** using `open(O_APPEND | O_CREAT, 0o644)` followed by a single `write()` of one line ≤ 4096 bytes. No read-modify-write. No locking required on POSIX given the size cap.
 131 | - **Rotation handoff.** If today's file already exceeds 8 MiB at append time, `af log` opens `<YYYY-MM-DD>.partN.jsonl` where N is the next integer (smallest unused).
 132 | - **Failure mode.** `af log` MUST NOT block or error a calling agent's user-visible operation. Hook scripts SHOULD invoke it with `af log ... || true` so an emit failure cannot cascade into a session break. `af log` itself returns non-zero on failure for diagnostic visibility.
 133 | - **Exit codes.** 0 = written, 2 = invalid CLI args, 3 = schema validation error, 4 = filesystem error.
 134 | 
 135 | **`af log-validate [PATH]`** — schema checker. The executable form of the protocol. Naming: hyphenated form preferred over `af validate-activity-log` (shorter, shares `af log` prefix) and over a `af log validate` subcommand (since `af log` itself takes a positional message argument and Click subcommand groups conflict awkwardly with positional dispatch). Kept separate from existing `af validate` (which validates document structure, not activity logs).
 136 | 
 137 | ```
 138 | af log-validate                              # validate today's PRJ log
 139 | af log-validate ./logs/agent-activity/       # validate every *.jsonl in directory
 140 | af log-validate path/to/2026-05-02.jsonl     # validate a specific file
 141 | ```
 142 | 
 143 | Behavior:
 144 | - **Default target** when `PATH` omitted: today's log file using the same layer resolution as `af log`.
 145 | - **Path semantics:** if `PATH` is a file → validate that file. If `PATH` is a directory → validate every file matching `*.jsonl` and `*.partN.jsonl` recursively at depth 1.
 146 | - **Per-line check:** required fields present, types correct, `agent` in v1 whitelist, `event` in v1 enum, `summary` length, `schema` literal match, `agent_name` present iff `agent == "other"`, line ≤ 4096 bytes.
 147 | - **Output:** one line per violation in the form `<path>:<lineno>: <field>: <reason>`. Quiet on success.
 148 | - **Exit codes:** 0 = all valid, 1 = schema violations found, 2 = invalid CLI args, 4 = file/dir not readable.
 149 | 
 150 | ### Acceptance Criteria
 151 | 
 152 | This proposal is complete when:
 153 | 
 154 | - `COR-1205-REF-Agent-Activity-Log-Format` exists in PKG with the v1 schema fully specified (fields, enum values, file format, rotation, line size cap, file permissions, gitignore policy, privacy constraints).
 155 | - `COR-1206-SOP-Emit-Agent-Activity` exists in PKG with mandatory triggers, optional triggers, and the per-agent mapping table covering at least: `claude-code`, `copilot`, `cursor`, `aider`, plus `other` as escape hatch.
 156 | - `af log` command writes a record that passes `af log-validate`, including: layer resolution per the 3-step rule, auto-fill of `ts`/`session_id`/`schema`, line size cap with `summary_truncated` flag, rotation handoff at 8 MiB, exit codes per spec.
 157 | - `af log-validate` correctly reports schema violations on a synthetic invalid file covering at least: missing required field, wrong type, `agent` not in whitelist, `agent: "other"` without `agent_name`, line > 4096 bytes, malformed `schema` literal.
 158 | - `COR-1200` (retrospective) gets a single additive bullet in step 1 directing the agent to read today's `logs/agent-activity/<today>.jsonl` before reconstructing actions. The 6-step protocol and outputs are otherwise unchanged.
 159 | - At least **one reference implementation** ships in the same release: a Claude Code `Stop` hook script (committed under `hooks/` in this repo) that emits `task.done` via `af log ... || true` and passes `af log-validate` over a real session log.
 160 | - No reverse dependency on FXA-2229 — this PRP must be independently implementable whether FXA-2229 is shipped or not.
 161 | 
 162 | ---
 163 | 
 164 | ## Decisions
 165 | 
 166 | The decisions below constrain implementation. Items still requiring discussion remain in `## Open Questions`.
 167 | 
 168 | ### Vendor-neutral protocol, not a single-agent feature
 169 | 
 170 | The protocol is owned by Alfred (a documentation system) rather than any specific harness. **Why:** matches Alfred's existing document-first / framework-agnostic posture (core/ is Click-free, `af` is agent-free, PKG documents are portable across projects). Hardcoding emit logic into a single agent's hook reproduces the very fragmentation the protocol is meant to fix.
 171 | 
 172 | ### Two-document split (REF + SOP)
 173 | 
 174 | Format contract (`COR-1205`, REF) is separated from implementation guidance (`COR-1206`, SOP). **Why:** the data contract is stable and rarely changes; the agent mapping table changes every time a new tool gets integrated. Putting them in one document would either freeze the table or thrash the contract. This split mirrors FXA-2229's static-vs-dynamic knowledge cut (REF = static facts, SOP = dynamic procedure).
 175 | 
 176 | ### `af log` is the universal fallback, not the only path
 177 | 
 178 | `af log` is the lowest-common-denominator writer for agents that cannot install a native hook. Native hooks (Claude Code `Stop`, VS Code extension, etc.) are **preferred** because they are zero-effort for the user, but `af log` is always available as the contract floor.
 179 | 
 180 | ### Schema versioning is strict
 181 | 
 182 | `schema` field is a literal string match (`"alfred.activity/v1"`), not a semver range. v2 ships under a different literal. v1 readers MUST ignore unknown optional fields (forward compat); breaking changes get a new version. **Why:** JSONL logs are append-only and may live for years; loose versioning leads to silent corruption.
 183 | 
 184 | ### `session_id`: agent-provided when available, UUIDv4 fallback
 185 | 
 186 | `af log` reads `$ALFRED_SESSION_ID` (set by the calling hook) and uses it as `session_id` when present. If absent, `af log` generates a UUIDv4 and emits it. **Why:** preserves cross-tool correlation when the harness exposes a stable session id (Claude Code, Cursor); does not break agents that do not. The emitted id is always written to the log so downstream readers can group records by session even when generation happened on the writer side.
 187 | 
 188 | ### Agent whitelist lives in code, not in a separate YAML
 189 | 
 190 | The v1 agent whitelist (`claude-code`, `copilot`, `cursor`, `cline`, `aider`, `codex-cli`, `gemini-cli`, `other`) is hardcoded as a Python constant in the validator module. **Why:** keeps schema enforcement self-contained — no separate parser for `COR-1206.agents.yaml`, no risk of doc/code drift. The cost of adding a new agent is one PRP that bumps the constant and updates `COR-1206`'s mapping table in the same change. v2 may revisit this if the whitelist starts changing more than once per quarter.
 191 | 
 192 | ### `agent: "other"` requires `agent_name`
 193 | 
 194 | When `agent` is `"other"`, the optional field `agent_name` becomes required and identifies the unrecognized harness (e.g. `"qodo"`). **Why:** prevents the `"other"` value from silently absorbing all unrecognized writers and erasing the cost signal that the whitelist needs an addition. A spike in `agent: "other"` log lines with the same `agent_name` is the explicit trigger for a follow-on whitelist PRP.
 195 | 
 196 | ### `af log` is fail-open at the hook boundary
 197 | 
 198 | `af log` exits non-zero on validation or filesystem errors, but per-agent hook scripts MUST invoke it with `af log ... || true` so a log emit failure cannot break the user's session. **Why:** observability is valuable, but not so valuable that we let it take down a coding session. Hooks are advisory; the fallback is graceful degradation, not failure.
 199 | 
 200 | ### Implementation Workflow
 201 | 
 202 | This PRP follows the standard meta-workflow:
 203 | 
 204 | `COR-1102 (PRP, current) → COR-1602 strict review (4 reviewers — Codex + Gemini + GLM + DeepSeek — all ≥ 9.0; extended from default 2 for cross-vendor protocol validation) → COR-1101 CHG → COR-1500 TDD per phase`
 205 | 
 206 | Implementation phases (detailed decomposition belongs in the CHG):
 207 | 
 208 | - Phase 0 — PRP cleanup
 209 | - Phase 1 — Documents (`COR-1205` REF, `COR-1206` SOP, update to `COR-1200` retrospective consuming the log)
 210 | - Phase 2 — `af log` command
 211 | - Phase 3 — `af log-validate` command (renamed from earlier draft `af validate-activity-log`)
 212 | - Phase 4 — Reference Claude Code `Stop` hook + tests + integration
 213 | 
 214 | ---
 215 | 
 216 | ## Open Questions
 217 | 
 218 | The remaining items are CHG-stage implementation details, not design questions. None block PRP approval; each is explicitly deferred to the implementing CHG with the noted constraint.
 219 | 
 220 | - **`--stdin` mode for `af log`.** Should `af log` accept a `--stdin` mode that reads a pre-built JSON object directly (for agents that already construct the record themselves), in addition to the flag-based form? Adds surface area but avoids round-tripping through CLI flags. *Deferred to CHG; default decision if CHG punts: no, flag-based is sufficient for v1.*
 221 | - **`outcome` enum on `task.done`.** Should `task.done` records optionally carry a coarse `outcome` enum (`success | partial | failure`)? Useful for retrospective signal but risks over-engineering v1. *Deferred to CHG; default decision if CHG punts: no, deferred to v2 schema if usage data shows demand.*
 222 | 
 223 | ---
 224 | 
 225 | ## Change History
 226 | 
 227 | | Date | Change | By |
 228 | |------|--------|----|
 229 | | 2026-05-01 | Initial version | Frank + Claude |
 230 | | 2026-05-02 | Self-audit revision pre-strict-review: split out-of-scope vs acceptance contradictions (Claude Code reference hook now in-scope as the sole reference impl; COR-1200 augmentation explicitly an additive bullet, not a semantic change); add 4 KiB line size cap to make POSIX O_APPEND atomicity provable; add explicit layer resolution algorithm; rename `af validate-activity-log` → `af log-validate`; add file permissions, gitignore, fail-open hook policy; tighten `agent_version` / `session_id` / `agent: other` rules; move `session_id` and agent-whitelist-source decisions from OQ into ## Decisions; trim OQs from 4 → 2 with explicit CHG default fallbacks; extend strict review to 4 reviewers (Codex + Gemini + GLM + DeepSeek). | Frank + Claude |
 231 | 
 232 | ---
 233 | 
 234 | ## References
 235 | 
 236 | - FXA-2229 (Layered SOP Memory Model) — defines the recall surface; this PRP covers the complementary emit surface.
 237 | - COR-1200 (Session Retrospective) — current consumer of session memory; will be updated to read the activity log.
 238 | - COR-1201 (Discussion Tracking) — D-item protocol; remains the human-curated short-term memory layer alongside the machine-emitted log.
 239 | - JSON Lines specification — https://jsonlines.org
 240 | - RFC 3339 — date and time format used for the `ts` field.
```

---

## 3. Scoring Rubric (COR-1608, embedded)

Source SOP: `src/fx_alfred/rules/COR-1608-SOP-PRP-Review-Scoring.md`. The rubric below is the canonical version reviewers must apply. PRP review is **strict**: the pass threshold is **≥ 9.0** weighted average **and** the OQ hard gate must be PASS.

### 3.1 Hard Gate — Open Questions

Before scoring any dimension, the reviewer **MUST** check:

> **Are all `## Open Questions` resolved (or explicitly deferred to the implementing CHG with justification)?**

- If any OQ remains unresolved with no justification → return **FIX** immediately, do not score.
- COR-1102 forbids approving a PRP with open questions unresolved.

For FXA-2230 specifically: see Section 2 lines **216–221** — 2 OQs remain, both annotated with explicit "Deferred to CHG; default decision if CHG punts: …". The reviewer must decide whether this annotation pattern satisfies the "explicitly deferred with justification" condition. Compare against the original 4-OQ list mentioned in the change history (line 230) — two were lifted into `## Decisions` (lines 184–190), two were trimmed with default fallbacks.

### 3.2 Six Weighted Dimensions

| # | Dimension | Weight | What to check |
|---|-----------|--------|---------------|
| 1 | **Problem Clarity** | 20% | Is the pain real, specific, observable today? Not aspirational? Does the PRP cite concrete failure modes? Lines 21–31 list 3 failure modes — verify they are concrete vs hand-wavy. |
| 2 | **Scope Precision** | 20% | Is `In scope` (lines 37–45) / `Out of scope` (lines 47–54) explicit? No ambiguity? Reference impl in scope is a deliberate exception (line 49) — confirm it is no longer contradictory with acceptance criteria (line 159). |
| 3 | **Solution Completeness** | 25% | Enough detail to implement (in a CHG) without guessing? Schema fields fully bounded (lines 64–77)? Layer resolution algorithm complete (lines 124–127)? Line size cap and atomicity reasoning sound (line 85, line 130)? Rotation algorithm specified (line 84, line 131)? |
| 4 | **Feasibility** | 15% | Compatible with existing architecture (`af` LazyGroup, Click subcommands, `core/` Click-free)? POSIX `O_APPEND` claim correct given the line size cap (line 130 vs 85)? Naming choice for `af log-validate` (line 135) sound vs alternatives discussed there? Windows explicitly punted (line 54). |
| 5 | **Necessity** | 10% | Should this change exist at all? Is there a simpler alternative (e.g., docs-only with `af log` as an existing-command extension; or just a Claude Code hook)? Is the cross-agent generality justified by the failure modes in lines 21–31? |
| 6 | **Risk Awareness** | 10% | Failure modes covered? Privacy constraints tight enough (line 88)? `agent: "other"` laundering risk acknowledged (line 192–194)? Fail-open hook policy explicit (line 196–198)? File permissions (line 86)? Default git policy (line 87)? Rotation disk-space exhaustion handled (line 84)? |

### 3.3 Weighted Formula

```
score = 0.20 × ProblemClarity
      + 0.20 × ScopePrecision
      + 0.25 × SolutionCompleteness
      + 0.15 × Feasibility
      + 0.10 × Necessity
      + 0.10 × RiskAwareness
```

Round the final score to **one decimal**. **9.0 = PASS, 8.9 = FIX.**

### 3.4 Scoring Rules (mandatory)

1. Every deduction must cite a **specific line number from Section 2** or a specific section heading. Bare "Completeness: 7" with no citation is invalid.
2. **10/10 means zero improvements possible.** If you noted anything for a dimension, that dimension's max is 9.8 (advisory note) or 9.0 (blocking issue). See Section 4 for the calibration cap.
3. Distinguish **blocking** (affects score) vs **advisory** (noted, no deduction).
4. Do **NOT** deduct for issues explicitly listed in `Out of scope` (lines 47–54).
5. Cross-reference the source files cited in the PRP and summarized in Sections 5 and 6.
6. Check the artifact's own metadata compliance (COR-0002 — `Applies to`, `Last updated`, `Last reviewed`, `Status`, valid Status value for type `PRP`).
7. Scores rounded to one decimal.

---

## 4. Calibration Rules (COR-1611, embedded)

Source SOP: `src/fx_alfred/rules/COR-1611-SOP-Reviewer-Calibration-Guide.md`. These rules apply identically to all four reviewers — symmetric standards regardless of which model performs the review.

### 4.1 Mandatory Rules

1. **Cross-reference source files** mentioned in the artifact. Sections 5 and 6 below provide self-contained snapshots of the relevant existing SOPs and the existing CLI / code touch-points — confirm the PRP's claims against those.
2. **Cite line:N or section** for every deduction. **Unsupported deductions are not valid** — they do not affect the score and the orchestrator may discard them.
3. **Distinguish blocking vs advisory.** Blocking deductions reduce the score for that dimension. Advisory notes are flagged but do **not** reduce the score (max for that dimension drops from 10 → 9.8 only).
4. **Do NOT deduct** for issues explicitly listed as `Out of scope` (lines 47–54).
5. **The 10-point cap rule (HARD):**
   - Any **advisory** note on a dimension ⇒ that dimension's maximum is **9.8** (not 10).
   - Any **blocking** issue on a dimension ⇒ that dimension's maximum is **9.0** (not 10).
   - A weighted total of 10.0 is valid **only if every individual dimension is 10.0 with zero notes**.
6. **Check COR-0002 compliance** of the PRP itself (metadata format, required fields, Status value `Draft` is valid for PRP per `ALLOWED_STATUSES`).
7. **Flag unaddressed prior-round feedback** explicitly. This is the first dispatch of FXA-2230 to strict review; a self-audit round happened before dispatch (Change History line 230). If your prior advisory on a related concept (e.g. POSIX atomicity, OQ deferral pattern) was not addressed in the PRP, call it out at the top of your review.
8. **List at least one improvement suggestion** even on a passing review — advisory, no deduction.
9. **Round scores to one decimal.** 8.9 → FIX, 9.0 → PASS. No softening.
10. **Four-reviewer parity.** Codex, Gemini, GLM, and DeepSeek must apply identical standards. Disagreement is the **point** of the parallel review — do not anchor to what you imagine the other reviewers will say.

### 4.2 Common Pitfalls to Avoid

| Pitfall | How to avoid |
|---------|--------------|
| Inflating scores to avoid conflict with other reviewers | If you noted issues, score accordingly. Disagreement is the **point** of multi-reviewer review. |
| Deducting for wording/style when meaning is clear | Focus on substance, not prose. |
| Requiring changes that contradict `Out of scope` | Read lines 47–54 first. |
| Over-indexing on minor issues while missing structural problems | Score structural issues higher; minor wording is advisory. |
| Giving 10/10 as default | 10 means "I cannot improve this." Prove it. Any noted advisory ⇒ max 9.8. |
| Asymmetric standards between models | Apply this guide identically regardless of which model you are. |
| Cross-vendor anchoring | Don't soften because you're "the GLM reviewer alongside Codex" or vice versa — the rubric is identical. |

---

## 5. Related SOP Snapshots

Reviewers do **not** need to open these files; the bullets below capture each SOP's current behavior and the change FXA-2230 proposes for it. If the PRP's claims appear inconsistent with these snapshots, that is a **Solution Completeness** deduction.

### 5.1 COR-1200 — Session Retrospective
Source: `src/fx_alfred/rules/COR-1200-SOP-Session-Retrospective.md` (Active).
- Today: 6-step end-of-session protocol — (0) close all D items → (1) list all actions taken this session → (2) identify repeated patterns → (3) identify undocumented processes → (4) identify SOP gaps → (5) record findings as a REF doc → (6) execute improvements. Step 1 today relies entirely on the agent's recollection from chat history.
- FXA-2230 proposes (PRP line 158): add a **single additive bullet** in step 1 directing the agent to read today's `logs/agent-activity/<today>.jsonl` before reconstructing actions. The 6-step protocol structure and outputs are otherwise unchanged. Reviewers should weigh whether "single additive bullet" is precise enough for `Solution Completeness`, or whether the PRP should pin the exact wording.

### 5.2 COR-1201 — Discussion Tracking
Source: `src/fx_alfred/rules/COR-1201-SOP-Discussion-Tracking.md` (Active).
- Today: D-item lifecycle protocol (D new / list / start / done / defer / archive / reopen). Tracker is a per-day REF document; D items are persisted in real time via `af update`.
- FXA-2230 declares (PRP line 51): COR-1201's D-item lifecycle semantics are **out of scope**. The activity log is a parallel artifact that augments but does not replace D items. Reviewers should check the boundary holds — e.g. is there any acceptance criterion that implicitly modifies COR-1201?

### 5.3 COR-1102 — PRP Lifecycle (gate rules)
Source: `src/fx_alfred/rules/COR-1102-SOP-Submit-PRP.md` (Active).
- Today: PRPs require all `## Open Questions` resolved or explicitly deferred to the implementing CHG before approval. The OQ hard gate (Section 3.1) is the codification of this rule.
- FXA-2230 retains 2 OQs (lines 220–221), both annotated with `*Deferred to CHG; default decision if CHG punts: …*`. Reviewers should decide whether this annotation pattern is sufficient ("deferred with justification") or insufficient ("still unresolved, return FIX").

### 5.4 COR-1602 — Multi-Model Parallel Review
Source: `src/fx_alfred/rules/COR-1602-SOP-Multi-Model-Parallel-Review.md` (Active).
- Today: default 2-reviewer parallel review (Codex + Gemini); strict mode requires both ≥ 9.0.
- FXA-2230 extends to 4 reviewers (PRP line 204). This extension is described as "extended from default 2 for cross-vendor protocol validation" and is not itself the subject of this review — it is a meta-decision about how to review this specific PRP. Reviewers should NOT score for or against this extension; just apply the same rubric.

---

## 6. Code Touch-Point Summary

The PRP is currently a planning artifact, but its acceptance criteria (lines 152–160) and Phase decomposition (lines 208–212) imply specific code changes for **Phase 2 (`af log`)**, **Phase 3 (`af log-validate`)**, and **Phase 4 (Claude Code Stop hook)**. The table below maps each claim to the existing module and the symbol(s) reviewers should verify against.

| Module | Current state | Phase impact (per FXA-2230) |
|--------|---------------|------------------------------|
| `src/fx_alfred/cli.py` | `LazyGroup` registers all subcommands by lazy import — current entries: `changelog`, `create`, `fmt`, `guide`, `index`, `list`, `plan`, `read`, `search`, `setup`, `status`, `update`, `validate`, `where`. | **Phase 2:** add `log`. **Phase 3:** add `log-validate`. Both follow the existing LazyGroup pattern (one new command module per command). Click hyphenation: registered name with hyphen is fine — `af log-validate` is a single command, not a group. |
| `src/fx_alfred/commands/log_cmd.py` (NEW) | Does not exist today. | **Phase 2:** new Click command. Inputs per PRP line 117–133: positional message, `--event`, `--refs`, `--files`, `--agent`, `--session-id`, `--root`. Layer resolution: 3-step rule per line 124–127. Atomic append: `os.open(path, O_APPEND \| O_CREAT \| O_WRONLY, 0o644)` then single `os.write()` per line 130. Schema validation before write: in-process check using the constants from `log_validate_cmd`. |
| `src/fx_alfred/commands/log_validate_cmd.py` (NEW) | Does not exist today. | **Phase 3:** new Click command. Inputs per PRP line 135–148: optional positional `PATH`, defaults to today's PRJ log. File-vs-directory dispatch per line 145. Per-line schema check per line 146. Output format per line 147. Exit codes per line 148. Hardcoded constants: `AGENT_WHITELIST` (line 66 + line 188), `EVENT_ENUM` (line 78–83), `SCHEMA_LITERAL = "alfred.activity/v1"` (line 71). |
| `src/fx_alfred/core/` (no changes) | `core/` is Click-free per CLAUDE.md. | Per PRP "framework-agnostic" principle, the v1 schema constants and validation logic could optionally live in a new `core/activity_log.py` rather than in `commands/log_validate_cmd.py`, so library users can validate without Click. PRP does not specify; reviewers may flag as a `Solution Completeness` advisory. |
| `pyproject.toml` | `fx-alfred` v1.8.0; entry point `af = fx_alfred.cli:cli`. | No changes required for these phases. Version bump (to v1.9.0) happens at release time per FXA-2102. |
| Reference hook script (NEW) | Does not exist today. | **Phase 4:** new shell script under `hooks/` (project-level) or installed by `claude-code-skill` (out of scope). Script reads `$CLAUDE_*` env vars per line 106, calls `af log ... \|\| true` per line 132 to satisfy fail-open. Must pass `af log-validate` against a real session log per acceptance criterion line 159. |
| `.gitignore` | Does not contain `logs/agent-activity/` today. | **Phase 1 / 4:** add `logs/agent-activity/` (per PRP line 87 default git policy). Exact snippet to ship as part of `COR-1206`. |

Reviewers should verify this table against the PRP's claims and flag any discrepancies as `Solution Completeness` (if a behavior is implied but not specified) or `Feasibility` (if the change is impossible against the listed symbols) deductions.

---

## 7. Compatibility & Risk Notes

These are areas reviewers should weigh under `Feasibility` (15%) and `Risk Awareness` (10%). The PRP addresses some of them; others are gaps the reviewer may flag.

1. **POSIX `O_APPEND` atomicity** (PRP lines 85, 130). The claim "POSIX guarantees atomicity for writes ≤ `PIPE_BUF`, which is ≥ 4096" is technically correct for **regular file appends with `O_APPEND`** on Linux/macOS/BSD. Reviewers should verify the spec mention is precise — the actual POSIX guarantee for PIPE_BUF is on **pipes/FIFOs**; for regular files, atomicity comes from the kernel's `O_APPEND` implementation which on Linux uses an inode lock. The line-size cap is still the right shape but reviewers may flag a wording precision concern as advisory.
2. **Windows is explicitly out of scope** (PRP line 54). Reviewers should confirm this exclusion does not violate any project-level requirement — Alfred currently has no Windows support claim, so the punt is consistent.
3. **`af log` Click flag explosion** (PRP line 120 example). The example shows positional message + 4 flags. Reviewers should weigh whether a `--stdin` JSON mode (now an OQ at line 220) is the right path for power users, or whether the flag-based form is enough for v1.
4. **Schema versioning on long-lived JSONL** (PRP line 89). Strict literal `"alfred.activity/v1"` matching plus "v1 readers MUST ignore unknown optional fields, v1 writers MUST NOT emit unknown fields" is the right compatibility shape. Reviewers may probe: what happens when a v2 writer is misconfigured to emit `"alfred.activity/v1"` literal? The validator should reject unknown required fields.
5. **`agent: "other"` whitelist erosion** (PRP lines 66, 192–194). The `agent_name` requirement on `agent: "other"` is the explicit countermeasure. Reviewers should weigh whether this is observable in practice — `af log-validate` reports violation count but no aggregate "X% of records used `agent: other`" stat. May be a `Risk Awareness` advisory.
6. **`COR-1200` augmentation precision** (PRP line 158). "Single additive bullet" is the in-scope change. Reviewers should weigh whether the PRP should ship the exact bullet wording (it does not) or whether that level of detail belongs in the CHG.
7. **Reference implementation scope creep risk** (PRP line 159). The Claude Code `Stop` hook is in scope as the **single** reference implementation. Reviewers should confirm the PRP does not implicitly require multiple per-agent hooks (it does not — see line 49).
8. **Disk-space exhaustion** (PRP line 84). 8 MiB rotation per file but no aggregate cap. For a multi-month project, `logs/agent-activity/` could accumulate hundreds of MiB. The default gitignore policy (line 87) limits blast radius to per-machine, but no retention policy is specified. May be a `Risk Awareness` advisory.

---

## 8. Required Reviewer Output Format

Each reviewer must produce **exactly** the following structure. Headings, table format, gate label, and verdict label are pinned — do not reword. Replace `<Reviewer Name>` with `Codex`, `Gemini`, `GLM`, or `DeepSeek`. Use line numbers from Section 2 (the embedded PRP) for every citation.

````md
## Review by <Reviewer Name>

### Score Table
| Dimension | Weight | Score (0-10) | Weighted |
|---|---|---|---|
| Problem Clarity | 20% | X.X | X.XX |
| Scope Precision | 20% | X.X | X.XX |
| Solution Completeness | 25% | X.X | X.XX |
| Feasibility | 15% | X.X | X.XX |
| Necessity | 10% | X.X | X.XX |
| Risk Awareness | 10% | X.X | X.XX |
| **Total weighted** | — | — | **X.X / 10** |

### Open Questions Gate
PASS / FAIL — <reasoning, 2-3 lines citing PRP line numbers (e.g., "Lines 216-221 list 2 OQs; both carry explicit `*Deferred to CHG; default decision if CHG punts: …*` annotations; this is the deferral-with-justification pattern COR-1102 allows, so PASS")>.

### Deductions (cited)
- [Line N] <issue> → -X (blocking | advisory)
- [Line N] <issue> → -X (blocking | advisory)
- ...

### Strengths
- <one or more concrete strengths the PRP gets right>
- ...

### Required Changes Before Approval (if any)
- <bullet list of blocking changes; empty if PASS>
- ...

### Final Verdict
PASS (≥ 9.0 weighted **and** OQ gate PASS) | FAIL
````

Notes for the orchestrator parsing these reviews:
- The `Score Table` total row uses `**X.X / 10**` for one-decimal rounded weighted average.
- The `Final Verdict` line must be exactly `PASS (...)` or `FAIL` so the orchestrator can grep it.
- If `FAIL`, the `Required Changes Before Approval` section drives the next revision round.

---

## 9. Pass/Fail Gate

This PRP advances to a CHG **only when**:

1. **Codex** review meets **both**: weighted total ≥ 9.0 **and** Open Questions gate = PASS.
2. **Gemini** review meets **both**: weighted total ≥ 9.0 **and** Open Questions gate = PASS.
3. **GLM** review meets **both**: weighted total ≥ 9.0 **and** Open Questions gate = PASS.
4. **DeepSeek** review meets **both**: weighted total ≥ 9.0 **and** Open Questions gate = PASS.
5. **All four** reviewers' `Final Verdict` lines read `PASS (...)`.

If **any** of the above fails:

- The PRP returns to **Draft** state.
- The orchestrator (Claude Code) collates blocking deductions from all four reviews.
- A worker is dispatched to apply the required changes against `rules/FXA-2230-PRP-Agent-Activity-Log-Protocol.md`.
- The PRP's `## Change History` table is appended with a row describing the round and the changes made.
- This same review pack is regenerated (with the updated PRP embedded in Section 2) and re-dispatched to **all four** reviewers for the next round.
- COR-1602 default iteration cap is 3 rounds; beyond that the leader (Claude Code) makes the final call with explicit justification.

There is **no leader override** for PRP-stage strict review — this is the explicit COR-1102 invariant: all reviewers must pass independently. Any softening requires amending COR-1102, not amending this gate.
