# CHG-2287: COR-1500 Phase 1 Worker Assignment Sub-Section

**Applies to:** FXA project
**Last updated:** 2026-05-17
**Last reviewed:** 2026-05-17
**Status:** Approved
**Related:** PRP-1507 (Two-Worker TDD Dispatch — design source), GitHub issue #175, CHG-2288 (CHG-B — Phase 2 implementer reading constraint, paired surface in COR-1500), CHG-2289 (CHG-C1 — COR-1619 handoff contract that consumes this rule), CHG-2291 (CHG-D — COR-1622 `<test-writer-worker-agent>` parameter the rule gates on)
**Date:** 2026-05-17
**Requested by:** @frankyxhl
**Priority:** Medium
**Change Type:** Normal
**Targets:** src/fx_alfred/rules/COR-1500-SOP-TDD-Development-Workflow.md §Phase 1 (RED)

---

## What

Insert a new `#### Worker assignment` sub-section in `src/fx_alfred/rules/COR-1500-SOP-TDD-Development-Workflow.md` §Phase 1 (RED), between the existing "Rules:" bullet block and "Test structure convention (Arrange-Act-Assert):". The new sub-section is CHG-A of PRP-1507 §Implementation Plan.

The inserted block declares the `test-writer ≠ implementer` rule for substantive code dispatches when the two-worker split is active (gated by the new `<test-writer-worker-agent>` parameter introduced in CHG-D / FXA-2291), states that the rule subsumes COR-1500 §AI-Assisted TDD Protocol Mandatory Rule #3, declares OFF behaviour for non-adopters, and enumerates a six-row opt-out table (trivial single-function fix below `<worker-min-loc>`; refactor with pre-existing coverage; config/metadata-only change; characterization tests on legacy code; generated test scaffolding; vendored code update). Content is the verbatim text of PRP-1507 §Proposed Solution lines 64–85 (Approved at R6 with all five panel reviewers at PASS).

## Why

PRP-1507 §Problem identifies three structural risks under single-worker TDD: implement-to-fit bias, weakened RED probing, and no cross-validation. Mandatory Rule #3 ("Agent must not write test and implementation simultaneously") is satisfied as long as the same agent writes them in two sequential turns — the single agent still holds the GREEN design in working memory throughout the RED phase. CHG-A introduces the stronger rule (distinct agent *instances*) and gates it on a new `<test-writer-worker-agent>` parameter so non-adopters see zero behaviour change.

Without CHG-A landing in COR-1500, the PRP-1507 design has no operative effect — adopters who set `<test-writer-worker-agent>` via CHG-D have no SOP text to follow at RED. The opt-out table is required by CHG-A (not deferred) so adopters do not have to read PRP-1507 itself to know which classes legitimately skip the split.

## Out of Scope

- Editing COR-1500 §Phase 2 (GREEN) — separate surface, lands as CHG-B / FXA-2288.
- Editing COR-1619 §Worker Dispatch Contract or §Decision Tree — separate surfaces, land as CHG-C1 / FXA-2289 and CHG-C2 / FXA-2290.
- Editing COR-1622 schema — separate surface, lands as CHG-D / FXA-2291.
- Setting alfred's `<test-writer-worker-agent>` value in FXA-2276 — alfred opt-in lands as CHG-E (separate PR, tracked in issue #176).
- Changing COR-1500 §AI-Assisted TDD Protocol Mandatory Rule #3 itself — the new rule subsumes it; Rule #3 stays as-is for non-adopters per PRP-1507 §Decisions.
- Tooling-side enforcement of the test-writer/implementer separation beyond `git diff` (deferred to Tier 2 human review per PRP-1507 §C step 7).
- Renaming the inserted sub-section or its opt-out classes — text is the verbatim panel-approved PRP-1507 §Proposed Solution.

## Impact Analysis

- **Systems affected:** `src/fx_alfred/rules/COR-1500-SOP-TDD-Development-Workflow.md` only (one file, one section inserted between two existing sections; no other section text touched).
- **Behavioural impact:** Adopters who leave `<test-writer-worker-agent>` unset (or equal to `<worker-agent>`) see zero behaviour change — the new sub-section explicitly states "Rule #3 alone applies" in that branch. Adopters who set the parameter distinct gain a stronger TDD discipline at RED, with six declared opt-out classes covering deterministic / coverage-already-exists / no-bias-mode scenarios.
- **Compatibility:** Backwards-compatible. Existing CHGs / PRs that ran under Mandatory Rule #3 alone remain valid; the new rule applies prospectively to dispatches under projects that opt in.
- **Risk surface:** Low. The insertion is a single new sub-section; the surrounding "Rules:" bullets and "Test structure convention" content are untouched. The verbatim text was scored to PASS by the full quintet panel (GLM 9.9, DeepSeek 9.0, MiniMax 9.55, Codex 9.6, Gemini 9.9) over six review rounds.
- **Rollback plan:** Revert this commit. The sub-section is purely additive; no other section depends on it textually, and the gate parameter (CHG-D) has no other consumer if all five CHGs land in the same PR and are reverted together.

## Acceptance Criteria

- A1: `src/fx_alfred/rules/COR-1500-SOP-TDD-Development-Workflow.md` §Phase 1 (RED) contains a new `#### Worker assignment` sub-section inserted between the existing "Rules:" bullet block (ending at "Each test must be independent — no shared mutable state, no ordering dependencies") and the existing "Test structure convention (Arrange-Act-Assert):" heading.
- A2: The inserted sub-section's prose, opt-out table (6 rows), Rule #3 subsumption sentence, parameter-unset fallback sentence, and opt-out Rule #3 clarification match PRP-1507 §Proposed Solution lines 64–85 verbatim (no paraphrase, no reordering).
- A3: No other content in COR-1500 is modified — Phase 2, Phase 3, Worked Example, Characterization Tests, AI-Assisted TDD Protocol, Test Execution Strategy, Definition of Done, Progress Tracker, Commit Strategy, Common Pitfalls, Integration with CI/CD, Safety Notes, References, and the existing Change History rows all remain byte-for-byte identical except for the new Change History row added at the bottom of the file referencing this CHG and PRP-1507.
- A4: `Last updated` and `Last reviewed` fields in COR-1500 frontmatter are updated to today's date (2026-05-17).
- A5: `af validate --root /Users/frank/Projects/alfred` reports 0 issues after the edit.
- A6: This CHG document (`rules/FXA-2287-CHG-COR-1500-Phase-1-Worker-Assignment-Sub-Section.md`) exists, has `Status: Proposed` on creation and is moved to `Status: Completed` in the merge commit; CHG `Change History` records the iteration cycle (R1 + each plan-review round) per the bundle PR's actual review trace.

## Implementation Plan

1. Open `src/fx_alfred/rules/COR-1500-SOP-TDD-Development-Workflow.md`.
2. Locate the line containing "Each test must be independent — no shared mutable state, no ordering dependencies" — this is the last bullet of the §Phase 1 (RED) "Rules:" block.
3. Insert a blank line, then the new `#### Worker assignment` sub-section verbatim from PRP-1507 §Proposed Solution lines 64–85, then another blank line before the existing `**Test structure convention (Arrange-Act-Assert):**` heading.
4. Update `Last updated` and `Last reviewed` to 2026-05-17.
5. Add a Change History row dated 2026-05-17 referencing this CHG (FXA-2287) and PRP-1507.
6. Run `af validate --root /Users/frank/Projects/alfred`; expect 0 issues.
7. CHG-B (FXA-2288) edits the same file at §Phase 2 (GREEN). Coordinate the two edits in one editing pass per Implementation Plan of the bundle PR, but document them as separate CHGs per CLD-1802 atomicity.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-17 | Initial version — drafted as CHG-A of PRP-1507 §Implementation Plan, bundled with CHG-B/C1/C2/D in PR closing issue #175 | Claude Opus 4.7 |
| 2026-05-17 | R1 plan-review panel (alfred triad, gemini substituted for minimax which hit usage limit): glm 9.91, deepseek 10.0, gemini 10.0 — PASS, blocking == []. P3 advisories all cosmetic / by-design (mermaid quote-add required for valid syntax; bundle-revert coupling acknowledged in rollback plan). Convergence Case A per `<convergence-severity>` = advisory; not folded. Status moved Proposed → Approved. | Claude Opus 4.7 |
