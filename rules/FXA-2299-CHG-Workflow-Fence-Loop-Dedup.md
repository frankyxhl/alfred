# CHG-2299: Workflow Fence Loop Dedup

**Applies to:** FXA project
**Last updated:** 2026-06-11
**Last reviewed:** 2026-06-11
**Status:** In Progress
**Date:** 2026-06-11
**Requested by:** Frank Xu (FXA-2294 R1 MiniMax advisory; follow-up batch 2026-06-11)
**Priority:** Medium
**Change Type:** Normal
**Targets:** src/fx_alfred/core/workflow.py; tests/test_architecture.py

---

## What

Replace the two remaining inline CommonMark fence-tracking loops in `core/workflow.py` (branch validation: sub-step presence/position scan and Rule-5 sibling-contiguity scan) with the shared `parser.iter_lines_with_fence_state` helper introduced by CHG-2294. Add an architecture guard to `tests/test_architecture.py`: the implementation fingerprint `fence_char` may appear only in `core/parser.py`, so inline fence loops cannot silently reappear.

**Scope constraint (semantic):** only the fence-tracking boilerplate is replaced. Each site keeps its own step-line regex (`^(?:###\s+)?(\d+)([a-z])?\.\s+` on the raw line, both forms counted, no text-capture requirement). The renderers' `iter_step_lines` is deliberately NOT used here — it applies heading-form preference (CHG-2294 R2), which is rendering-side semantics; validation stays permissive so loop/branch references against either step form keep validating.


## Why

CHG-2294 consolidated fence tracking for `extract_section` and both `steps.py` parsers, deferring `workflow.py` ("correct code, follow-up dedupe" — MiniMax located both sites at workflow.py:439-460 and 546-566 during the FXA-2294 R1 panel). Three duplicated implementations of the same CommonMark discipline (opener run ≥ 3 backticks/tildes; closer same char, run ≥ opener) means a future rule fix lands in one place and silently misses the others — exactly the failure shape that caused the original CHG-2294 bug (downstream defense, upstream hole). This completes the consolidation: one implementation, one guard.


## Out of Scope

- Any behavior change to branch/loop validation (existing tests are the contract and must pass unmodified).
- Migrating these sites to `iter_step_lines` (would change validation semantics via heading-form preference).
- Unifying the sites' local regex with `steps._STEP_LINE_RE` (differs deliberately: no text-capture group).
- plan_cmd/renderer surfaces.


## Acceptance Criteria

- A1: `grep -rn "fence_char" src/fx_alfred/ | grep -v core/parser.py` returns 0 matches; enforced by the new guard test (RED on current code, GREEN after).
- A2: All existing workflow/branch/loop validation tests pass unmodified (behavior-preservation proof).
- A3: Full gates: pytest, ruff check, ruff format --check, pyright, `af validate`.


## Implementation Plan

1. **RED:** add `test_fence_tracking_implementation_lives_only_in_parser` to `tests/test_architecture.py` (fails: workflow.py contains `fence_char` at two sites).
2. **GREEN:** both workflow.py sites iterate `iter_lines_with_fence_state(section)` and `continue` on fenced lines; local matching logic unchanged.
3. Verify A1–A3.
4. Trinity triad review (glm, deepseek, minimax), COR-1610, all ≥ 9.0; fix convergent findings.
5. PR per COR-1505.

---

## Change History

| Date       | Change                                                                              | By               |
|------------|-------------------------------------------------------------------------------------|------------------|
| 2026-06-11 | Initial version — complete the CHG-2294 fence-tracking consolidation in workflow.py | Claude (Fable 5) |
