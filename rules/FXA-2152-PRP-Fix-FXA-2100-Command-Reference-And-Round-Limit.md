# PRP-2152: Fix FXA-2100 Command Reference And Round Limit

**Applies to:** FXA project
**Last updated:** 2026-03-30
**Last reviewed:** 2026-03-30
**Status:** Implemented

---

## What Is It?

Proposal to fix two issues in FXA-2100 (Leader Mediated Development): an incorrect command reference and a missing round-limit guard in the review loop.

---

## Problem

**Issue 1 — Command inconsistency**: Step 4 references `/ask codex` and `/ask gemini`, but the Examples section uses `/trinity codex "review" gemini "review"`. The correct dispatch mechanism for parallel review is `/trinity`.

**Issue 2 — Round limit gap**: Step 8 says "Repeat from step 4" without mentioning the 5-round maximum stated in Pass Criteria. An agent following steps linearly could loop indefinitely.

Both discovered during Evolve-SOP content analysis (FXA-2150 run log).

## Proposed Solution

**Fix 1**: In Step 4, replace `/ask codex` and `/ask gemini` with `/trinity codex "..." gemini "..."` to match the Examples section and COR-1602 parallel review pattern.

**Fix 2**: In Step 8, add a round-limit check: "If 5 rounds reached without pass, Leader makes final call (per Pass Criteria)."

## Open Questions

None — both fixes align with existing content in the same document.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-30 | Initial version | — |
