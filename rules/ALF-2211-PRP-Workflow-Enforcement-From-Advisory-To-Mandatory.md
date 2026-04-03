# PRP-2211: Workflow Enforcement From Advisory To Mandatory

**Applies to:** ALF project
**Last updated:** 2026-03-22
**Last reviewed:** 2026-03-22
**Status:** Approved
**Reviewed by:** Codex 8.9, Gemini 9.8 (Round 3, Leader final call)
**Related:** COR-1103, FXA-2134, FXA-2137

---

## What Is It?

Transform Alfred's workflow system from advisory-only (SOPs that agents can ignore) to mandatory enforcement (tooling that blocks non-compliant actions). Introduces git hooks, `af commit` command, session state tracking, and expanded validation.

## Why

The current system relies entirely on the AI agent voluntarily reading `af guide`, creating CHGs, and running reviews. During a 2-day session, the agent (Claude Code Opus 4.6) repeatedly violated its own SOPs:
- Changed code without creating CHG first (multiple times)
- Committed without review (FXA-2132, FXA-2133)
- Skipped `af guide` routing
- Left ruff format changes uncommitted
- Created retroactive CHGs after being caught

The root cause is that every workflow step is advisory — nothing blocks the agent from skipping any step.

---

## Problem

1. **Zero enforcement** — `af guide`, `af plan`, `af setup` are purely informational. Skipping them has no consequence.
2. **No commit gate** — `git commit` bypasses Alfred entirely. No hook checks for CHG, review, or format compliance.
3. **No session state** — No record of whether `af guide` was run, which SOPs were routed, or whether review was completed.
4. **`af plan` broken for key SOPs** — COR-1101 has no `## Steps`, COR-1500 uses `## The Cycle`. `af plan` returns empty for both.
5. **CHG template incomplete** — Missing Testing/Verification, Approval, Post-Change Review sections that COR-1101 defines.
6. **COR-1103 sequence ambiguity** — Diagram says `Code → TDD → Review → Commit` but route text says `CHG → Review → TDD`.

## Scope

**In scope:**
- `af commit` command — replaces `git commit` with built-in checks
- Git `pre-commit` hook — blocks commits that fail checks
- Session state file (`.alfred/session.json`) — tracks routing, plan, review status
- Expand `af validate` — check CHG structural completeness (sections only, NOT lifecycle or review)
- Fix `af plan` — support COR-1101/COR-1500 section headings
- Fix CHG template — add missing sections
- Fix COR-1103 sequence ambiguity

**Out of scope:**
- Server-side enforcement (GitHub branch protection, CI gates)
- Removing direct `git commit` access from agents (platform limitation)
- Quality assessment of reviews (only presence check)

## Proposed Solution

### 1. `af commit` command

New CLI command that wraps `git commit` with pre-checks:

```bash
af commit -m "feat: add X" --chg FXA-2137
```

Before committing, checks:
- `af validate` passes (0 structural issues)
- `ruff format --check .` passes (no uncommitted format changes)
- CHG document exists and status is `Approved` OR `In Progress` (discrete check, not ordinal — lifecycle enforcement in af commit only, NOT af validate)
- All staged `.py` files have corresponding test changes (warning, not blocking)
- Session state shows `af guide` was run this session (warning if missing, not blocking)

**`af commit --force "reason"`** — Bypass all checks with mandatory reason string. Logged to `.alfred/audit.log` with timestamp, user, reason. For emergency use only.

**Review evidence model:** `af commit` checks for review scores in session state:
```json
"review_status": {"codex": 9.0, "gemini": 9.5}
```
If `review_status` is empty and staged files include `.py`:
- Standard CHG → warning only (pre-approved, review optional)
- Normal/Emergency CHG → **blocking**: "No review evidence found. Run code review first."

**Scope note:** `af commit --chg FXA-2137` verifies the CHG exists and is approved, but does NOT verify that staged files "belong" to that CHG (too complex for v1, would require file-to-CHG mapping). This is a known limitation.

If any check fails → abort with clear error message. Agent must fix before retrying.

### 2. Git pre-commit hook

Installed via `af setup --install-hooks`:

```bash
#!/bin/sh
# .git/hooks/pre-commit
af validate --root . || exit 1
ruff format --check . || { echo "Run: ruff format . && git add -u"; exit 1; }
```

**Installation behavior:** If `.git/hooks/pre-commit` already exists, append Alfred checks to the end (separated by comment). If not, create new file. Print confirmation message.

Catches the most common violations even if agent uses raw `git commit`.

### 3. Session state (`<project-root>/.alfred/session.json`)

Location: `<project-root>/.alfred/` (NOT `~/.alfred/` which is the USR layer). Add `.alfred/` to `.gitignore`.

```json
{
  "started_at": "2026-03-22T01:00:00Z",
  "guide_run": true,
  "routed_sops": ["COR-1102", "COR-1602", "COR-1101"],
  "plan_generated": true,
  "active_chg": "FXA-2137",
  "review_status": {"codex": 9.0, "gemini": 9.5}
}
```

`af guide` writes this file. `af plan` updates it. `af commit` reads it. Session expires after 4 hours (warning, not blocking).

### 4. Expand `af validate`

For CHG documents, check structural completeness only (NOT lifecycle status):
- Has What, Why, Impact Analysis, Implementation Plan sections
- Has a non-placeholder Rollback plan

**Note:** Status lifecycle enforcement (Proposed → Approved → In Progress) is handled by `af commit`, NOT `af validate`. `af validate` remains a structural scan. This avoids blocking all newly created "Proposed" CHGs globally.

### 5. Fix `af plan`

COR-1101 has no `## Steps` section — it is a template/reference SOP. Its procedural content is the CHG template itself. For SOPs like this, `af plan` should show the "When to Use" + "CHG Template" sections as the checklist.

Update `_STEP_HEADINGS` to include confirmed headings from actual SOPs:
```python
_STEP_HEADINGS = ("Steps", "The Cycle", "Rule", "Rules", "Concepts", "CHG Template")
```

COR-1101 uses `## CHG Template` (confirmed). COR-1500 uses `## The Cycle` (confirmed).

Add tests against real bundled COR SOPs (COR-1101, COR-1500), not just synthetic fixtures.

### 6. Fix CHG template

Add sections from COR-1101 to `templates/chg.md`. Also update COR-1101 SOP to reference the updated template, preventing future divergence.

```markdown
## Testing / Verification
## Approval
## Execution Log
## Post-Change Review
```

### 7. Fix COR-1103 sequence

Clarify the two different review types explicitly in the diagram and route text:
```
Pre-implementation:  CHG created → CHG approval review (COR-1602/1606)
Implementation:      TDD (COR-1500) → Code
Post-implementation: Code review (COR-1602/1606) → Commit
```

The current diagram conflates these. Update both the sequence diagram and the Branch 4 text.

## Risks

1. **Agent uses `--no-verify`** — Git allows bypassing hooks. Mitigated by: agent instructions explicitly forbid `--no-verify`.
2. **Over-enforcement friction** — Too many checks slow down simple tasks. Mitigated by: Standard CHGs (pre-approved) skip review check.
3. **Session state stale** — Long sessions may have outdated state. Mitigated by: `af commit` warns if session > 4 hours old.
4. **False positives** — `af validate` may block valid commits. Mitigated by: `af commit --force "reason"` escape hatch with logged justification.
5. **Shared session state** — Another agent or session could satisfy session checks. Mitigated by: session state is project-root scoped and includes timestamp.
6. **Staged-file-to-CHG scope not checked** — Agent could commit unrelated code under any approved CHG. Mitigated by: known v1 limitation, documented. Future enhancement could add file-to-CHG mapping.
7. **Hook manager conflicts** — Existing hook managers (husky, pre-commit) may conflict. Mitigated by: `af setup --install-hooks` appends to existing hooks, not overwrites.
8. **Stale review evidence** — Agent stages new edits after review scores are recorded. `af commit` sees passing scores that don't cover new changes. Mitigated by: `af commit` warns if staged files were modified after `review_status` timestamp.

## Open Questions

None. All design decisions resolved:
- Pre-commit hook: yes, with `af validate` + `ruff format --check`, append behavior
- `af commit`: yes, wraps `git commit` with full checks, `--force "reason"` escape
- Session state: yes, `<project-root>/.alfred/session.json` (not USR layer)
- CHG lifecycle enforcement: in `af commit` only (NOT in `af validate`)
- Staged-file scope: not checked in v1 (documented limitation)

---

## Round 1 Review Feedback (Codex 8.6, Gemini 8.9 — both FIX)

### Blocking issues to resolve in Round 2

1. **af validate + Proposed status conflict** (both) — validate is a global scan; rejecting all "Proposed" CHGs would break newly created CHGs. Fix: move lifecycle enforcement to `af commit` only, keep `af validate` structural.

2. **COR-1101 heading unknown** (Gemini) — PRP proposes adding "Flow" to `_STEP_HEADINGS` but never verifies what heading COR-1101 actually uses. Must check and confirm.

3. **--quiet flag doesn't exist** (Codex) — pre-commit hook example uses `af validate --quiet` which is not implemented. Must note as new feature or remove from example.

4. **.alfred/session.json location** (Codex) — `~/.alfred` is USR layer. Project-level session state needs explicit path (e.g., `.alfred/` in project root, add to `.gitignore`).

5. **Hook installation strategy** (Gemini) — `af setup --install-hooks` behavior when `.git/hooks/pre-commit` already exists is undefined.

6. **No staged-file-to-CHG scope check** (Gemini) — `af commit --chg FXA-2137` doesn't verify staged files relate to that CHG.

7. **Review evidence data model** (Codex) — "review evidence" mentioned without concrete format/storage.

8. **`af commit --force` contract** (Codex) — mentioned in Risks but behavior undefined.

9. **Missing risk: global validate blocking unrelated CHGs** (Codex) — not in Risks section.

10. **COR-1101 alignment with CHG template** (Codex) — should clarify if COR-1101 SOP is updated alongside chg.md.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-22 | Initial version based on Codex+Gemini process compliance analysis | Frank + Claude Code |
| 2026-03-22 | Round 1 feedback recorded: Codex 8.6 FIX, Gemini 8.9 FIX — 10 blocking issues | Claude Code |
| 2026-03-22 | Round 2 revision: all 10 blocking issues resolved — validate stays structural, af commit handles lifecycle, COR-1101 heading confirmed (CHG Template), session path clarified, hook append behavior, --force contract, review evidence model, scope limitation documented, 3 new risks added | Claude Code |
| 2026-03-22 | Round 3 revision: fixed scope/solution inconsistency (validate = structural only), review blocking for Normal CHGs, discrete status check wording, stale review evidence risk #8 | Claude Code |
