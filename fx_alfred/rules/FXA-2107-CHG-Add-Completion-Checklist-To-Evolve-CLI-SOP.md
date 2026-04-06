# CHG-2107: Add-Completion-Checklist-To-Evolve-CLI-SOP

**Applies to:** FXA project
**Last updated:** 2026-04-06
**Last reviewed:** 2026-04-06
**Status:** Completed
**Date:** 2026-04-06
**Requested by:** Frank
**Priority:** Medium
**Change Type:** Normal

---

## What

Add a "Phase 7: Completion Checklist" section to FXA-2149-SOP-Evolve-CLI.md. After all phases complete (or on early exit), the agent must display a checklist covering every key gate and decision point in the run, making the process auditable at a glance.

## Why

In the 2026-04-06 evolve run, the README check (Step 23) was correctly evaluated as N/A but only stated verbally — no auditable record was left in the output. If the judgment had been wrong, there would be no way to catch it in review. A mandatory completion checklist forces every gate to be explicitly shown with its result, preventing silent skips.

## Impact Analysis

- **Systems affected:** FXA-2149-SOP-Evolve-CLI.md only (SOP text, no code change)
- **Rollback plan:** Revert the commit

## Implementation Plan

1. Add Phase 7 section to FXA-2149 after Phase 6, containing a checklist template
2. Checklist must cover: guard checks, run log, signals, candidate evaluation, PRP review, hard gate (pytest + ruff), README check (with reason if N/A), code review, commit/push/PR
3. Update Change History

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-06 | Initial version | — |
