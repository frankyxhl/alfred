# PRP-2173: Define Review Gate And Align Scoring

**Applies to:** FXA project
**Last updated:** 2026-04-01
**Last reviewed:** 2026-04-01
**Status:** Draft

---

## What Is It?

Two SOP text fixes: define undefined "review gate" term and align FXA-2100 scoring with COR-1610.

---

## Problem

**S1 — "review gate" undefined (FXA-2148 line 90, FXA-2149 line 96):**
Both evolve SOPs say "Must not bypass hard gate or review gate" in Prohibited Actions, but "review gate" is never defined. Agents cannot determine what constitutes a gate pass or fail.

**S2 — FXA-2100 scoring mismatch (lines 90, 94-99, 123):**
FXA-2100 (Leader Mediated Development) uses 4 scoring dimensions: Correctness, Code Quality, Test Coverage, Packaging. But the referenced COR-1610 (Code Review Scoring) defines 5 weighted dimensions: Correctness 25%, Test Coverage 25%, Code Style 15%, Security 15%, Simplicity 20%. Reviewers don't know which rubric to follow.

## Proposed Solution

**S1:** Add a definition line to the Prohibited Actions section of both FXA-2148 and FXA-2149:
> **review gate** = both reviewers (Codex + Gemini) score >= 9.0 per the applicable scoring rubric (COR-1608 for PRP, COR-1609 for CHG, COR-1610 for code)

**S2:** In FXA-2100, replace the 4-dimension table and references with COR-1610's 5 dimensions:

| Dimension | Weight |
|-----------|--------|
| Correctness | 25% |
| Test Coverage | 25% |
| Code Style | 15% |
| Security | 15% |
| Simplicity | 20% |

Update Step 5, the scoring table (lines 94-99), Pass Criteria (lines 103-104, 112-113), and Review Prompt Template (line 123) accordingly.

## Scope

**In scope:**
- `FXA-2148-SOP-Evolve-SOP.md` (S1 — add review gate definition)
- `FXA-2149-SOP-Evolve-CLI.md` (S1 — add review gate definition)
- `FXA-2100-SOP-Leader-Mediated-Development.md` (S2 — align scoring dimensions)

**Out of scope:** COR-1610 itself (unchanged). No CLI code changes.

## Risks

- **S1:** Text-only addition. No behavior change — just documenting existing practice.
- **S2:** Reviewers using FXA-2100 will now see 5 dimensions instead of 4. This is a deliberate alignment with the standard they were already supposed to follow.

## Open Questions

None.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-01 | Initial version | — |
