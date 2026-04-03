# CHG-2154: Fix FXA-2100 Command Reference And Round Limit

**Applies to:** FXA project
**Last updated:** 2026-03-30
**Last reviewed:** 2026-03-30
**Status:** Completed
**Date:** 2026-03-30
**Requested by:** —
**Priority:** Medium
**Change Type:** Normal

---

## What

Fix two issues in FXA-2100 (Leader Mediated Development):
1. Replace `/ask codex` and `/ask gemini` with `/trinity codex "..." gemini "..."` in Step 4
2. Add round-limit guard to Step 8 referencing the 5-round maximum from Pass Criteria

## Why

Step 4 contradicts the Examples section which correctly uses `/trinity`. Step 8 has no exit condition for the review loop, though Pass Criteria states a 5-round max. PRP FXA-2152 approved (Codex 9.2, Gemini 9.4).

## Impact Analysis

- **Systems affected:** FXA-2100 only
- **Rollback plan:** `git revert` the commit

## Implementation Plan

1. Edit Step 4: replace `/ask` references with `/trinity` dispatch syntax
2. Edit Step 8: add "If 5 rounds reached without pass, Leader makes final call"
3. Run `af validate` to confirm 0 issues

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-30 | Initial version | — |
