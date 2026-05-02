# SOP-1206: Emit Agent Activity

**Applies to:** All projects using the COR document system
**Last updated:** 2026-05-02
**Last reviewed:** 2026-05-02
**Status:** Active
**Related:** COR-1205 (Agent Activity Log Format — data contract), COR-1200 (Session Retrospective — log consumer), PRP-2230 (originating proposal)

---

## What Is It?

The implementation guide for the cross-agent activity log protocol. Tells every coding agent (Claude Code, GitHub Copilot, Cursor, Cline, Aider, Codex CLI, Gemini CLI, …) **when to emit**, **how to emit**, and **how to map native lifecycle events** onto the canonical schema defined in COR-1205. Also defines the **scanner-skip contract** that protects `rules/logs/` from `af` document-walk commands.

This document defines the **emit protocol**. The **format** lives in COR-1205. The **CLI surfaces** are `af log` (writer), `af log-validate` (schema checker), `af log-archive` (explicit archival), all shipped in fx-alfred v1.9.0.

---

## Why

Without explicit emit-trigger rules, each agent integrates differently and `COR-1200` retrospectives can't rely on the log being populated. Mandating triggers at the SOP level ensures every compliant integration produces interoperable records.

---

## When to Use

- Implementing a new agent integration (per-agent recipe — see §Per-Agent Mapping below).
- Writing a hook script that calls `af log`.
- Reviewing whether an existing integration is COR-1206-compliant.

---

## When NOT to Use

- Document validation — see COR-0002 (Document Format Contract).
- Retrospective consumption of the log — see COR-1200 step 1.
- v1 schema details — see COR-1205.

---

## Mandatory Triggers

Every agent MUST emit at minimum:

1. **One `session.start`** per agent session.
2. **One `session.end`** per agent session.
3. **At least one `task.done`** (or `task.aborted` / `note`) per user-facing turn that resulted in non-trivial action.
4. **One `doc.created`** per Alfred document created via `af create`.
5. **One `doc.updated`** per Alfred document updated via `af update` / `af fmt`.

---

## Optional Triggers

Agents MAY emit:

- `task.start` for long-running tasks (useful for traceability when paired with `task.done` via `parent_event` correlation id).
- `decision` for material decisions: D-item resolutions, PRP convergences, scope cuts, retrospective conclusions.
- `note` for anything that doesn't fit elsewhere (debugging breadcrumbs, free-form annotations).

---

## Per-Agent Mapping Table

The v1 whitelist for the `agent` field is `claude-code`, `copilot`, `cursor`, `cline`, `aider`, `codex-cli`, `gemini-cli`, `other`. Adding a new entry requires a follow-on PRP.

| Agent | Native lifecycle hook | Emit mechanism |
|---|---|---|
| **Claude Code** | `settings.json` `Stop` and `PostToolUse` hooks | `hooks/emit-activity.sh` reads `$CLAUDE_*` env vars and invokes `af log "<turn-summary>" --event task.done --agent claude-code --agent-version "${CLAUDE_VERSION:-unknown}" \|\| true` |
| **GitHub Copilot (VS Code)** | No native lifecycle hook | Companion VS Code extension listening to `chat.acceptResponse` events; extension shells out to `af log --agent copilot ... \|\| true` |
| **Cursor** | `.cursorrules` directive | Rule instructs the model to call `af log --agent cursor ... \|\| true` after each turn |
| **Cline / Roo Code** | Custom MCP tool | Expose `af log` as an MCP tool; rules instruct usage |
| **Aider** | `--cmd-stop` callback OR git post-commit hook | Shell script invokes `af log --agent aider ... \|\| true` |
| **Codex CLI / Gemini CLI** | Each SDK's lifecycle event hook | Shell script writes JSONL via `af log --agent {codex,gemini}-cli ... \|\| true` |
| **Universal fallback** | None — direct shell-out | Any tool that can shell out invokes `af log` directly with appropriate `--agent` value (or `--agent other --agent-name <id>` for unrecognized harnesses) |

### Example: Claude Code reference hook

The reference Stop hook ships under `hooks/emit-activity.sh` (Phase 5 of CHG-2231). Conceptual form:

```bash
#!/usr/bin/env bash
# Claude Code Stop hook — emits one task.done per turn.
af log "${CLAUDE_TURN_DESCRIPTION:-claude-code turn complete}" \
  --event task.done \
  --agent claude-code \
  --agent-version "${CLAUDE_VERSION:-unknown}" \
  || true     # fail-open: emit failure MUST NOT break the session
```

Wire-up in `~/.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {"hooks": [{"type": "command", "command": "/path/to/hooks/emit-activity.sh"}]}
    ]
  }
}
```

---

## Compliance Test (mandatory before adding to mapping table)

Every implementation MUST pass `af log-validate <one-session-log.jsonl>` on its emitted output for at least one full session before being added to the mapping table above. The test must cover, at minimum:

- One `session.start`, one `session.end`.
- At least three `task.done` records across the session.
- All required fields populated correctly.
- `summary` ≤ 500 chars; line ≤ 4096 bytes.
- No forbidden content (secrets, full prompts, etc.) per COR-1205 §Privacy.

---

## Scanner-Skip Enforcement (`rules/logs/` is reserved)

**All `af` document scanners — present (`af list`, `af search`, `af status`, `af validate`) and any future scanner — MUST hard-skip the `rules/logs/` subtree.**

- Implementations enforce this at the `core/scanner.py` directory-walk layer (mirroring how `__pycache__` and `.git` are skipped) so the rule applies uniformly to every command that walks `rules/`.
- Only `*.jsonl`, `*.partN.jsonl`, `archive.zip`, and `archive.zip.tmp.*` are allowed inside `rules/logs/` per COR-1205 §Storage location.
- A regression test in CHG-2231 Phase 4 asserts that placing a `rules/logs/2026-05-02.jsonl`, a `rules/logs/archive.zip`, and even a misplaced `rules/logs/FXA-9999-PRP-Test.md` does not affect the output of any scanner-based command and produces no warnings.

This skip is implemented at the walk layer (not per-command) so future scanners inherit the rule automatically. Without this enforcement, future scanner improvements (e.g. "warn on unknown files in `rules/`") could interact badly with the activity log subtree.

---

## .gitignore Snippet

Activity logs are per-machine artifacts and SHOULD be gitignored. Add this single line to your project root `.gitignore`:

```
rules/logs/
```

Projects MAY commit logs deliberately (some teams do this for shared session memory across machines), but that is a project-level choice and not the protocol default.

---

## Fail-Open Hook Boundary

`af log` MUST NOT block or error a calling agent's user-visible operation. **Hook scripts SHOULD invoke it with `af log ... || true`** so an emit failure cannot cascade into a session break. `af log` itself returns non-zero on failure for diagnostic visibility, but the caller swallows that exit code.

This is the same fail-open posture as the rest of `af` (per FXA-2230 §Decisions §"`af log` is fail-open at the hook boundary").

Callers that find per-invocation warnings noisy can redirect stderr (`af log ... 2>/dev/null` or `2>>~/.alfred/logs/.warn.log`).

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-02 | Initial version. Implements PRP-2230 (Agent Activity Log Protocol v1) §"COR-1206-SOP-Emit-Agent-Activity" + scanner-skip enforcement rule (3/4 trinity advisory R5) + per-agent integration recipes for the 7-agent mapping table + `.gitignore` snippet + fail-open hook boundary. | Frank + Claude |
