# CHG-2111: Add-Post-Push-Review-Loop-To-Evolve-SOPs

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

Insert a "Phase 6.5: Post-Push Review Loop" into both FXA-2148 (Evolve-SOP) and FXA-2149 (Evolve-CLI). After the PR is opened, the agent waits for CI and automated reviews (e.g. GitHub Copilot), categorizes comments, fixes actionable items, re-runs the hard gate, pushes, and repeats — up to 3 iterations. Renumber Phase 7 (Completion Checklist) accordingly.

## Why

PR #36 received 4 Copilot review comments that were valid but required a manual follow-up cycle. The agent had already moved on to the completion checklist. An automated review loop closes this gap: the agent self-iterates until CI passes and all actionable review comments are resolved, before presenting the final checklist to the human.

## Impact Analysis

- **Systems affected:** FXA-2148-SOP-Evolve-SOP.md, FXA-2149-SOP-Evolve-CLI.md
- **Rollback plan:** Revert the commit

## Implementation Plan

1. Add Phase 6.5 to FXA-2149 with steps: wait, check CI + comments, categorize, fix, re-gate, push, loop (max 3)
2. Add Phase 6.5 to FXA-2148 with same structure, adapted for SOP gates
3. Renumber Phase 7 → Phase 8 in both files
4. Update Change History in both SOPs

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-06 | Initial version | Frank + Claude |
