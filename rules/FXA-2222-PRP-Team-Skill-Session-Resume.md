# PRP-2222: Team Skill Session Resume

**Applies to:** FXA project
**Last updated:** 2026-03-22
**Last reviewed:** 2026-03-20
**Status:** Rejected
**Related:** ALF-2202 (USR), ALF-2204 (USR)

---

## What Is It?

Add session resume capability to the /team skill. When a background agent is accidentally stopped, the underlying CLI session (codex/gemini/glm) is still alive. This PRP designs how to resume that session instead of starting fresh.

---

## Problem

During this session, the user accidentally stopped background agents 4+ times (wrong key press). Each time:

1. The Claude Code agent is killed
2. The underlying CLI session (stored in `.team/sessions.json`) is still valid
3. A fresh agent is dispatched with a new session → previous work lost
4. Codex API is slow (~5-10 min per review) → re-doing costs significant time

`.team/sessions.json` already tracks session IDs per provider:
```json
{
  "codex": {"session_id": "019d...", "last_used": "2026-03-20T13:31:54", "task_summary": "..."},
  "gemini": {"session_id": "4d49...", "last_used": "2026-03-20T14:08:13", "task_summary": "..."}
}
```

But the /team skill never checks this file before dispatching — it always creates new sessions.

## Scope

**In scope:**
- Add `/team resume <provider>` command to resume a stopped session
- Auto-detect resumable sessions on `/team <provider> "task"` dispatch
- Update `.team/sessions.json` with session status (active/stopped/completed)
- Update team skill SKILL.md with resume syntax and behavior

**Out of scope:**
- Changing Claude Code's agent stop behavior (platform limitation)
- Restoring the Claude Code agent's internal context (only CLI session is resumable)
- Multi-session support per provider (one active session per provider)

## Proposed Solution

### Enhanced session state

Update `.team/sessions.json` schema to track session status:

```json
{
  "codex": {
    "session_id": "019d...",
    "last_used": "2026-03-20T13:31:54",
    "task_summary": "COR-1602 review of FXA-2221",
    "status": "stopped"
  }
}
```

Status values:
- `active` — agent is currently running
- `stopped` — agent was stopped but CLI session is resumable
- `completed` — agent finished normally

### `/team resume <provider>` command

```bash
/team resume codex          # resume most recent codex session
/team resume gemini         # resume most recent gemini session
```

Behavior:
1. Read `.team/sessions.json` for the provider
2. If status = `stopped` and `last_used` < 30 minutes ago:
   - Dispatch new Claude agent with prompt: "Resume CLI session `<session_id>`. The previous task was: `<task_summary>`. Continue where the session left off."
   - The agent uses the CLI's session resume flag (e.g., `codex exec -s <session_id>`)
3. If status = `completed` or `last_used` > 30 minutes:
   - Report: "No resumable session for codex. Use `/team codex \"task\"` to start a new one."
4. Update status to `active`

### Auto-detect on dispatch

When `/team codex "task"` is called:
1. Check `.team/sessions.json` for existing codex session
2. If status = `stopped` and `last_used` < 30 minutes ago and task summary matches:
   - Ask user: "Found a stopped codex session (task: ...). Resume it? [Y/n]"
   - If Y → resume instead of fresh dispatch
   - If n → create new session, overwrite old
3. If no resumable session → dispatch fresh (current behavior)

### Status tracking

Update the agent dispatch flow to set status:
- On dispatch → `active`
- On agent completion → `completed`
- On agent stop (detected via notification) → `stopped`

### 30-minute window

CLI sessions may expire or become stale. 30 minutes is a reasonable window for:
- Codex: sessions persist for hours
- Gemini: sessions persist for the duration of the CLI process
- GLM (droid): sessions persist for hours

If the session is older than 30 minutes, treat as expired and start fresh.

## Open Questions

1. Can we detect "agent stopped" vs "agent completed" reliably from the task notification? (The notification includes `status: killed` vs `status: completed`)
2. Should the 30-minute window be configurable?
3. Should `/team status` show the session status (active/stopped/completed)?

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version based on D1 discussion | Frank + Claude Code |
| 2026-03-22 | /team skill replaced by /trinity; session resume is built into /trinity via .claude/trinity.json | Frank |
