# CHG-2294: Fence Aware Extract Section

**Applies to:** FXA project
**Last updated:** 2026-06-10
**Last reviewed:** 2026-06-10
**Status:** Approved
**Date:** 2026-06-10
**Requested by:** Frank Xu (session review finding, 2026-06-10)
**Priority:** High
**Change Type:** Normal
**Targets:** src/fx_alfred/core/parser.py; src/fx_alfred/core/steps.py; src/fx_alfred/commands/plan_cmd.py; tests/test_parser.py; tests/test_steps.py; tests/test_plan_cmd.py

---

## What

Make `core/parser.py::extract_section` fence-aware: section-boundary detection (both the section heading match and the next-heading terminator search) must ignore lines inside fenced code blocks. Hoist the CommonMark fence-tracking discipline that already exists in `core/steps.py::parse_top_level_step_indices` into a shared `parser.py` helper, and refactor the two duplicated fence loops in `steps.py` to use it.

R2 scope expansion (codex bot P1 on PR #190): align the two plan-step renderers — `steps._parse_steps_for_json` (JSON/todo modes) and `plan_cmd._parse_numbered_items` (text mode) — with the flush-left + fence-aware discipline already enforced by `parse_top_level_step_indices` / `has_top_level_substep_lines`. Without this pairing, un-truncated sections expose the renderers' loose stripped-line matching: nested numbered list items and fenced numbered lines render as top-level steps (COR-1612: 21 rendered vs 8 authored, with duplicate `1.` indices), violating A5's plain reading.


## Why

`extract_section` finds the end of a section with `^#{1,level}\s+` (parser.py:313), which also matches `#`-prefixed lines inside fenced code blocks — e.g. bash comments at column 0. Any SOP whose Steps section contains such a fence is silently truncated.

User-visible failure: `af plan COR-1612` renders **1 step**; the SOP authors **8 numbered steps**. The plan output says "Do not skip any step" while the tool dropped 7 of 8. 10 real SOPs across PKG/USR/PRJ are affected (measured extracted vs actual section chars): COR-1612 (269/27,336), COR-1200 (824/8,256), COR-1502 (30/364), COR-1501 (2,941/4,433), COR-1623 (3,035/6,590), COR-1618 (7,678/7,780), FXA-2102 (1,434/2,532), FXA-2148 (5,731/6,824), FXA-2149 (5,359/6,575), WUK-2007 (7/784).

Blast radius: `steps.py::extract_steps_section` (→ `af plan` checklists), `workflow.py` Steps extraction at 2 call sites (→ loop/branch cross-SOP validation sees truncated sections), `plan_cmd.py:876` ("What Is It?" phase summaries). Downstream `steps.py` already implements fence tracking (PR #59 review hardening), but the upstream truncation happens before that defense runs.


## Out of Scope

- A `validate` rule asserting plan-rendered step count == authored step count (worth doing; separate CHG).
- Fence handling changes in `parse_metadata` / Change History parsing (different surface; no observed failure).
- `workflow.py` internals beyond what already flows through `extract_section` (its own step-index parser already tracks fences).
- Loosening or changing the flush-left Path B sub-step contract itself (FXA-2226); renderers only converge onto it.


## Impact Analysis

- **Systems affected:** `core/parser.py` (`extract_section` + new shared fence helper), `core/steps.py` (dedupe two fence loops onto the helper), `af plan` / `af validate` output for the 10 affected SOPs (sections now complete).
- **Behavioral impact:** Docs without `#`-at-column-0 inside fences: byte-identical extraction. Affected docs: sections now extend to the true next heading. One deliberate semantic change: a heading-shaped line *inside* a fence no longer matches as the section start either (previously could anchor a section inside a code sample).
- **Risk surface:** Low-medium. `af plan` output for affected SOPs grows (correctly); any consumer that accidentally depended on truncated output will see more steps — that is the bug being fixed.
- **Rollback plan:** Single PR; revert the merge commit. CHG stays as historical record.


## Acceptance Criteria

- A1: `extract_section` returns the full section when fenced blocks contain `#`-at-column-0 lines (backtick and tilde fences; closer must be same char with run ≥ opener per CommonMark, matching `steps.py` discipline).
- A2: A heading-shaped line inside a fence is neither a section start nor a section terminator.
- A3: `steps.py` fence loops (`parse_top_level_step_indices`, `has_top_level_substep_lines`) delegate to the shared parser helper with unchanged behavior (existing tests stay green).
- A4: New `af plan` CLI regression: an SOP fixture whose step 1 contains a fenced bash comment renders **all** authored steps.
- A5: `af plan COR-1612` renders 8 numbered steps; re-running the affected-docs scan reports 0 truncated SOPs.
- A6: Full gates: pytest, ruff check, ruff format --check, pyright, `af validate`.
- A7 (R2): `_parse_steps_for_json` and `_parse_numbered_items` emit only flush-left, unfenced step lines (same notion of "step" as `parse_top_level_step_indices`); indented nested numbered items and numbered lines inside fences are excluded. `af plan COR-1612` emits exactly the 8 authored top-level steps with no duplicate indices.


## Implementation Plan

1. **RED:** Add failing tests — `tests/test_parser.py` (fence-aware extraction: backtick/tilde fences, longer-closer rule, fenced pseudo-headings as non-boundaries and non-starts), `tests/test_steps.py` (steps survive fenced bash comments end-to-end), `tests/test_plan_cmd.py` (CLI: all authored steps render). Confirm RED.
2. **GREEN:** Add shared fence-state helper to `parser.py` (hoisted from `steps.py`, same CommonMark rules); rewrite `extract_section` boundary detection on top of it; refactor `steps.py` to consume the helper.
3. Verify A1–A6; update CHANGELOG.
4. Trinity triad review (glm, deepseek, minimax) of the full diff per COR-1602, COR-1610 weights, all ≥ 9.0 to pass; fix real findings before PR.
5. PR per COR-1505.

---

## Change History

| Date       | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | By               |
|------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------|
| 2026-06-10 | Initial version — fence-aware extract_section per session review finding                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Claude (Fable 5) |
| 2026-06-10 | RED (7 failing tests) + GREEN (shared fence helper; steps.py dedupe) landed; all gates green; af plan COR-1612 renders 8/8 steps; 0 truncated docs across layers                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Claude (Fable 5) |
| 2026-06-10 | R1 code-review panel [glm, deepseek, minimax] per COR-1602/COR-1610: glm 9.8 PASS, deepseek 9.8 PASS, minimax 10.0 PASS — gate met, blocking empty. Convergent advisory (glm+deepseek): direct unit tests for iter_lines_with_fence_state — addressed (+9 tests, 953 total); deepseek advisory: CommonMark closer deviations documented in helper docstring. Status → Approved                                                                                                                                                                                                                                                                                                                                                                                                           | Claude (Fable 5) |
| 2026-06-10 | R2: codex bot P1 (PR #190, parser.py:388 thread) — renderers' loose stripped-line matching corrupts checklists once sections are no longer truncated; A5 plain reading ("renders 8 steps") not met (21 rendered). Scope expanded into §What R2: align `_parse_steps_for_json` + `_parse_numbered_items` to flush-left + fence-aware discipline (the same one the PR #68 R4 gate workaround already cites as authoritative). A7 added.                                                                                                                                                                                                                                                                                                                                                    | Claude (Fable 5) |
| 2026-06-10 | R2 implementation: corpus scan showed the COR-1612 pollution comes from FLUSH-LEFT bare numbered body lists (not indentation) — only 2/62 SOPs mix `### N.` and bare forms (COR-1612, COR-1200), both with bare lines as body content. Added heading-form preference to new shared `steps.iter_step_lines`: if a section authors any `### N.` step line, only heading-form lines render; all-bare sections keep legacy form. Rendering-side only — `parse_top_level_step_indices` stays permissive (rendered ⊆ indexed verified corpus-wide, 0 violations). Both renderers rebuilt on the shared iterator. `af plan COR-1612` → exactly 8 steps; COR-1200 → 7. 961 tests; all gates green.                                                                                               | Claude (Fable 5) |
| 2026-06-10 | R2 code-review panel [glm, deepseek, minimax] per COR-1602/COR-1610 on the delta diff: glm 9.3 PASS, deepseek 9.6 PASS, minimax 9.8 PASS — gate met twice, blocking empty. Convergent advisory (glm+deepseek): direct iter_step_lines unit tests incl. bare-form + fenced intersection — addressed (+4 tests, 965 total). MiniMax: docstring corpus denominator clarified ("62 step-bearing SOPs across all three layers"); cross-ref comment added on `_TOP_LEVEL_STEP_RE`. GLM forward-risk advisory (no diagnostic when mixed-form bare steps are suppressed) deferred to follow-up CHG alongside the validate step-parity rule. GitHub codex P1 thread: author reply verified RESOLVED by clearance verifier; no codex re-review in quiescence window; clearance Stage 3 on R2 head. | Claude (Fable 5) |
