# CHG-2181: Add-AF-Tool-Context-To-Review-Dispatch-Template

**Applies to:** FXA project
**Last updated:** 2026-04-01
**Last reviewed:** 2026-04-01
**Status:** Completed
**Date:** 2026-04-01
**Requested by:** Evolve-SOP (FXA-2175)
**Priority:** Medium
**Change Type:** Normal

---

## What

Added optional Tool Context block to FXA-2100's Review Prompt Template. When dispatching reviews for projects with specialized CLIs (e.g., `af` for alfred_ops), the Leader includes tool instructions so reviewers can access referenced documents.

## Why

During the 2026-04-01 evolve-sop run, Gemini's agent couldn't find FXA-2165 because it didn't know to use `af read`. This caused a false -4 score deduction. Adding tool context to the template prevents this class of failure.

## Impact Analysis

- **Systems affected:** FXA-2100 Review Prompt Template section only
- **Rollback plan:** `git checkout HEAD -- rules/FXA-2100-*.md`

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-01 | Initial version | — |
