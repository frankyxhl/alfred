# CHG-2174: Define Review Gate And Align Scoring

**Applies to:** FXA project
**Last updated:** 2026-04-01
**Last reviewed:** 2026-04-01
**Status:** Proposed
**Date:** 2026-04-01
**Requested by:** —
**Priority:** Medium
**Change Type:** Normal

---

## What

S1: Add "review gate" definition to Prohibited Actions in FXA-2148 and FXA-2149 — both reviewers (Codex + Gemini) score >= 9.0 per applicable rubric (COR-1608/1609/1610).

S2: Align FXA-2100 scoring dimensions with COR-1610 — replace 4 custom dimensions (Correctness, Code Quality, Test Coverage, Packaging) with COR-1610's 5 weighted dimensions (Correctness 25%, Test Coverage 25%, Code Style 15%, Security 15%, Simplicity 20%). Update Pass Criteria to weighted average >= 9.0. Update Review Prompt Template.

PRP: FXA-2173 (Codex 9.5, Gemini 9.3).

## Why

"review gate" was used in both evolve SOPs' Prohibited Actions but never defined — agents could not determine pass/fail criteria. FXA-2100 defined 4 scoring dimensions that conflicted with the COR-1610 standard it referenced, creating ambiguous review expectations.

## Impact Analysis

- **Systems affected:** FXA-2148, FXA-2149, FXA-2100 (text only, no code)
- **Rollback plan:** `git revert <commit>`

## Implementation Plan

1. Add review gate definition as sub-bullet under "Must not bypass" in FXA-2148 Prohibited Actions
2. Same edit in FXA-2149 Prohibited Actions
3. Replace FXA-2100 Step 5 scoring table with COR-1610 5-dimension weighted table
4. Update FXA-2100 Pass Criteria to weighted average >= 9.0
5. Update FXA-2100 Review Prompt Template to reference COR-1610
6. Update Change History in all three files

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-01 | Initial version | — |
