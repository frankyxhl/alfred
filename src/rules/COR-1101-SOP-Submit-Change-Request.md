# SOP-1101: Submit Change Request

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-12
**Last reviewed:** 2026-03-12

---

## What Is It?

A Change Request (CHG) documents a proposed change to a system, configuration, or architecture. It captures the reason, impact, plan, and approval before the change is made, and records the outcome after execution.

---

## When to Use

- Configuration changes to shared systems (relay, launchd, Discord bot)
- Architecture or design changes
- Dependency upgrades or migrations
- Any change that could affect other channels or sessions

## When NOT to Use

- Routine operations covered by an existing SOP
- Bug fixes (use INC instead; if the fix requires a system or configuration change, also file a CHG)
- New feature planning (use PLN instead)

---

## Change Types

| Type | Approval | Use When |
|------|----------|----------|
| **Standard** | Pre-approved, no review needed | Low-risk, routine changes covered by an existing SOP (e.g., adding a new channel per ALF-2000) |
| **Normal** | Requires review and approval | Changes with potential impact on shared systems |
| **Emergency** | Post-approval acceptable | Critical fixes that cannot wait for normal review |

**Approval flow for Normal changes:** The requestor submits the CHG for review. The project lead (or designated reviewer listed in the Approval section) reviews the impact analysis and implementation plan, then marks it Approved. Do not begin implementation until approval is recorded.

**Approval flow for Standard changes:** Standard changes are pre-approved by the referenced SOP. In the Approval section, check the box and note the SOP number (e.g., "Pre-approved per COR-1100 or ALF-2000"). No additional reviewer is required.

**Approval flow for Emergency changes:** Post-approval must be completed by the project lead within 24 hours of execution. If the post-review determines the change was inappropriate or harmful, the change must be rolled back as soon as safely feasible and an INC record created to document the incident.

**Standard vs. "When NOT to Use":** A Standard change still requires a CHG document — it is simply pre-approved and does not need a review cycle. "Routine operations covered by an existing SOP" in "When NOT to Use" refers to operations that are already fully described by an SOP and require no change record (e.g., restarting a service per COR-1100 or ALF-2000). If the operation modifies configuration or architecture, even if low-risk, use a Standard CHG.

---

## Naming Convention

```
ALF-<NNNN>-CHG-<Short-Description>.md
```

Examples:
- `ALF-4001-CHG-Add-File-Upload-To-Relay.md`
- `ALF-4002-CHG-Upgrade-Python-To-3.14.md`

---

## CHG Template

```markdown
# ALF-NNNN-CHG: <Short Description>

- **Date:** YYYY-MM-DD
- **Requested by:** <who>
- **Status:** Proposed | Approved | In Progress | Completed | Rolled Back
- **Priority:** Low | Medium | High | Critical
- **Change Type:** Standard | Normal | Emergency
- **Scheduled:** YYYY-MM-DD HH:MM (or ASAP)
- **Related:** <ALF-NNNN, ALF-NNNN, ...>

---

## What

<1-2 sentences: what exactly is being changed.>

---

## Why

<Why is this change needed? What problem does it solve or what value does it add?>

---

## Impact Analysis

- **Systems affected:** <list>
- **Channels affected:** <list or "none">
- **Downtime required:** Yes / No
- **Rollback plan:** <how to undo if it goes wrong>

---

## Implementation Plan

1. Step 1
2. Step 2
3. Step 3

---

## Testing / Verification

- How will you verify the change works?
- What does success look like?
- How will you verify the rollback works?

---

## Approval

- [ ] Reviewed by: <name/channel>
- [ ] Approved on: YYYY-MM-DD

---

## Execution Log

| Date | Action | Result |
|------|--------|--------|
| YYYY-MM-DD | <what was done> | <outcome> |

---

## Post-Change Review

- Did the change achieve its goal?
- Any unexpected side effects?
- Any follow-up actions needed?

---

## Change History

| Date | Change | By |
|------|--------|----|
| YYYY-MM-DD | Initial version | Author |
```

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-12 | Initial version | Claude Code |
| 2026-03-12 | Added Change Type (Standard/Normal/Emergency), Scheduled field, Related field, rollback verification, fixed header (per GPT-5.2 review) | Claude Code |
| 2026-03-12 | Added approval flow clarification, Standard vs SOP boundary, emergency denial handling (per GPT-5.2 second review) | Claude Code |
| 2026-03-12 | Added per-type approval flows, INC+CHG dual-filing guidance, softened emergency rollback language (per GPT-5.2 third review) | Claude Code |
| 2026-03-14 | PDCA + Johnny Decimal migration: renamed from ALF-4000 to COR-1001 | Claude Code |
