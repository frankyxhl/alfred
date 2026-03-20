# SOP-1501: Create GitHub Issue

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-14
**Last reviewed:** 2026-03-14
**Status:** Active
**Last executed:** —

---

## What Is It?

A standardized process for creating GitHub issues as task tickets. Ensures every issue has clear context, acceptance criteria, and traceability.

---

## Prerequisites

- GitHub repo with remote configured
- `gh` CLI installed and authenticated (`gh auth status`)

---

## Issue Template

```markdown
## Summary

<1-2 sentences describing what needs to be done and why.>

## Context

- **Source:** <SOP number, session retrospective, or user request>
- **Related files:** <list of relevant files or paths>
- **Depends on:** <other issue numbers, if any>

## Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Technical Notes

<Optional: implementation hints, constraints, or relevant code references.>
```

---

## Steps

### 1. Determine issue type

| Label | Use when |
|-------|----------|
| `sop` | New or updated SOP needed |
| `automation` | Script, Makefile target, or command to create |
| `bug` | Something broken |
| `enhancement` | Improvement to existing feature |
| `docs` | Documentation only |

### 2. Write the issue

Use the template above. Keep the title short (<70 chars), put details in the body.

Title format: `[<label>] <short description>`

Examples:
- `[automation] Add make add-channel command`
- `[sop] Create SOP for launchd plist management`
- `[bug] Codex relay 401 when started via nohup`

### 3. Create via CLI

```bash
gh issue create \
  --title "[<label>] <title>" \
  --body "$(cat <<'EOF'
## Summary

<description>

## Context

- **Source:** ALF-NNNN / session retrospective / user request
- **Related files:** <paths>

## Acceptance Criteria

- [ ] ...

## Technical Notes

<notes>
EOF
)" \
  --label "<label>"
```

### 4. Verify

```bash
gh issue list
```

---

## Naming Conventions

| Field | Convention |
|-------|-----------|
| Title prefix | `[sop]`, `[automation]`, `[bug]`, `[enhancement]`, `[docs]` |
| Assignee | Channel/session that will work on it |
| Milestone | Optional, for grouping related work |

---

## Safety Notes

- One issue per task — don't bundle unrelated work
- Reference SOP numbers in issues for traceability
- Close issues with a comment explaining what was done

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-08 | Initial version | Claude Code |
| 2026-03-14 | PDCA + Johnny Decimal migration: renamed from ALF-1003 to ALF-2101 | Claude Code |
