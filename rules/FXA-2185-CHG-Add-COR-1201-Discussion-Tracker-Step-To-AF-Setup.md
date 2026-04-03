# CHG-2185: Add COR-1201 Discussion Tracker Step To AF Setup

**Applies to:** FXA project
**Last updated:** 2026-04-04
**Last reviewed:** 2026-04-03
**Status:** Completed
**Date:** 2026-04-03
**Requested by:** Frank
**Priority:** Medium
**Change Type:** Standard

---

## What

Add the COR-1201 Discussion Tracker session-start step to all three `af setup` options (A, B, C) in `setup_cmd.py`. Currently `af setup` only mentions `af guide` and `af plan` but omits the mandatory Discussion Tracker loading step that COR-1103 ALWAYS block requires.

## Why

COR-1201 was added to the COR-1103 ALWAYS block in v1.2.1, making Discussion Tracker loading mandatory at every session start. However, `af setup` — the onboarding prompt that agents copy into their configuration — does not mention this step. Agents configuring themselves via `af setup` will miss the Discussion Tracker requirement.

## Impact Analysis

- **Systems affected:** `src/fx_alfred/commands/setup_cmd.py` (text-only change)
- **Rollback plan:** Revert the `_SETUP_TEXT` string to previous version

## Implementation Plan

1. Edit `_SETUP_TEXT` in `setup_cmd.py`:
   - **Option A (Minimal)**: Add "Load today's Discussion Tracker per COR-1201" after `af guide`
   - **Option B (With routing)**: Add step between `af guide` and task routing for Discussion Tracker
   - **Option C (Full)**: Add step between `af guide` and task routing for Discussion Tracker
2. Run tests to verify no regressions
3. Version bump and release

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-03 | Initial version | Frank + Claude Code |
