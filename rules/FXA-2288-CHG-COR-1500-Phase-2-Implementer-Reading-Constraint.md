# CHG-2288: COR-1500 Phase 2 Implementer Reading Constraint

**Applies to:** FXA project
**Last updated:** 2026-05-17
**Last reviewed:** 2026-05-17
**Status:** Approved
**Related:** PRP-1507 (Two-Worker TDD Dispatch — design source), GitHub issue #175, CHG-2287 (CHG-A — Phase 1 worker assignment, the rule this constraint pairs with), CHG-2289 (CHG-C1 — §Two-Worker TDD Dispatch handoff contract that consumes this rule in step 4), CHG-2291 (CHG-D — `<test-writer-worker-agent>` parameter the rule gates on)
**Date:** 2026-05-17
**Requested by:** @frankyxhl
**Priority:** Medium
**Change Type:** Normal
**Targets:** src/fx_alfred/rules/COR-1500-SOP-TDD-Development-Workflow.md §Phase 2 (GREEN)

---

## What

Append a new bullet to the §Phase 2 (GREEN) "Rules:" list in `src/fx_alfred/rules/COR-1500-SOP-TDD-Development-Workflow.md`. The bullet declares the implementer reading constraint that pairs with the §Phase 1 worker-assignment rule introduced in CHG-A: when the two-worker split is in effect, the implementer worker MUST NOT read the test-writer's structured report / prose commentary / session transcripts, and MAY read (a) the failing test files, (b) the CHG/PRP body, and (c) the existing production source tree. Content is the verbatim text of PRP-1507 §Proposed Solution line 89.

## Why

The implementer reading constraint is the operational half of the cross-validation the two-worker split exists to provide. Without it, the test-writer's commentary channel (structured report, scratchpad output, chain-of-thought-shaped text) can leak the test-writer's *intended implementation* into the implementer worker's prompt — defeating the bias-mitigation the split was designed to deliver. The rule names the three allowed input channels (failing tests = the spec; existing source = the substrate; CHG/PRP body = the human-authored brief) so the implementer has unambiguous reading guidance.

PRP-1507 R2 fix (DeepSeek P0) corrected an earlier draft that forbade reading production source — clarifying that the constraint forbids only the test-writer's *commentary channel*, not the codebase under change. The verbatim line 89 reflects that corrected form.

## Out of Scope

- Editing §Phase 1 (RED) — separate surface, lands as CHG-A / FXA-2287 (this CHG references but does not modify the Phase 1 sub-section).
- Editing COR-1619 §Two-Worker TDD Dispatch §C step 4 enforcement detail (the `git diff` check + violation handling) — lands as CHG-C1 / FXA-2289.
- Tooling-side enforcement of the reading constraint (deferred — orchestrator-trust-based per PRP-1507 §C step 1 enforcement-note class).
- Constraining the refactor-phase reading rules — PRP-1507 §C step 7 explicitly lifts this constraint during refactor only; that text lands in CHG-C1, not here.
- Renaming the inserted bullet or paraphrasing line 89 — text is the verbatim panel-approved PRP-1507 §Proposed Solution.

## Impact Analysis

- **Systems affected:** `src/fx_alfred/rules/COR-1500-SOP-TDD-Development-Workflow.md` only (one file, one bullet appended to one list; no other text touched).
- **Behavioural impact:** Adopters who leave `<test-writer-worker-agent>` unset see no behaviour change — the new bullet's leading conjunction ("When the two-worker split is in effect …") gates it on the Phase 1 sub-section's conditional, which only triggers when the parameter is set distinct. Adopters who set the parameter gain a clear reading guarantee for the implementer worker.
- **Compatibility:** Backwards-compatible. Existing Phase 2 rules (resist over-implementation; do not break other tests; transformation priority) are preserved verbatim.
- **Risk surface:** Low. Single new bullet; no other content in §Phase 2 changes. The verbatim text was scored to PASS by the full quintet panel.
- **Rollback plan:** Revert this commit. The bullet is purely additive; CHG-A's Phase 1 sub-section's text already contains an "off-state" branch that handles the case where the implementer constraint is also missing.

## Acceptance Criteria

- A1: `src/fx_alfred/rules/COR-1500-SOP-TDD-Development-Workflow.md` §Phase 2 (GREEN) "Rules:" list contains a new bullet appended after the existing three bullets (resist the urge to write more than needed; if you need to break another test to pass this one, stop and rethink; prefer simple transformations).
- A2: The new bullet's text matches PRP-1507 §Proposed Solution line 89 verbatim (no paraphrase, no truncation, no addition).
- A3: No other content in COR-1500 is modified by this CHG. (CHG-A's §Phase 1 sub-section insertion and CHG-A's Change History row are separate; the bundle PR includes both, but each CHG is independently atomic at its declared surface.)
- A4: `Last updated` and `Last reviewed` are updated to today's date (2026-05-17) once per file across the bundle PR (CHG-A and CHG-B share the file; one frontmatter update covers both).
- A5: `af validate --root /Users/frank/Projects/alfred` reports 0 issues after the edit.
- A6: This CHG document (`rules/FXA-2288-CHG-COR-1500-Phase-2-Implementer-Reading-Constraint.md`) exists, has `Status: Proposed` on creation and is moved to `Status: Completed` in the merge commit.

## Implementation Plan

1. Open `src/fx_alfred/rules/COR-1500-SOP-TDD-Development-Workflow.md`.
2. Locate §Phase 2 (GREEN) "**Rules:**" bullet list (the three bullets starting with "Resist the urge to write more than needed").
3. Append a new bullet matching PRP-1507 §Proposed Solution line 89 verbatim.
4. Confirm `Last updated` / `Last reviewed` are 2026-05-17 (set in the same editing pass that lands CHG-A, since both CHGs target the same file).
5. Add a Change History row dated 2026-05-17 referencing this CHG (FXA-2288) and PRP-1507.
6. Run `af validate --root /Users/frank/Projects/alfred`; expect 0 issues.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-17 | Initial version — drafted as CHG-B of PRP-1507 §Implementation Plan, bundled with CHG-A/C1/C2/D in PR closing issue #175 | Claude Opus 4.7 |
| 2026-05-17 | R1 plan-review panel (alfred triad, gemini substituted for minimax which hit usage limit): glm 9.94, deepseek 10.0, gemini 10.0 — PASS, blocking == []. No advisories on this CHG specifically. Status moved Proposed → Approved. | Claude Opus 4.7 |
