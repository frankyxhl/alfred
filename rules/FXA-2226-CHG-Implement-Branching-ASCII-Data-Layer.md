# CHG-2226: Implement Branching ASCII — Data Layer (Path B / Two-Field)

**Applies to:** FXA project (parser + validator + plan-builder additive schema)
**Last updated:** 2026-04-27
**Last reviewed:** 2026-04-27
**Status:** Proposed
**Date:** 2026-04-27
**Requested by:** Frank Xu
**Priority:** Medium (no production-blocking issue; foundation for FXA-2225 / FXA-2227)
**Change Type:** Normal
**Targets:** PRP-2225 implementation — first of two staged CHGs
**Depends on:** PRP-2225 (merged via PR #65)
**Followed by:** CHG-2227 (Presentation Layer — branch geometry, nested/flat integration, Mermaid, docs, release)

---

## What

Land the **data-layer foundation** for PRP-2225 (Branching ASCII In Plan Graph) using a **two-field architecture** that avoids any type-widening migration:

- `StepDict.index: int` — **UNCHANGED** for legacy SOPs (1, 2, 3) and parent step of branch siblings (3 in `3a/3b/3c`).
- `StepDict.sub_branch: str | None` — **NEW additive optional field**. `None` for plain steps; set to `"a"`/`"b"`/etc. for sub-stepped siblings.

Sub-step `3a` parses to `StepDict(index=3, sub_branch="a", text="...", gate=False)`. No int → str migration. No consumer audit needed. No JSON schema break.

Plus: `Workflow branches:` schema parser + validator cross-checks.

## Why this architecture (path B)

Round 1 review converged on splitting the original 10-phase monolith. Rounds 2-3 attempted to land a Data Layer scoped around `StepDict.index: int → str` widening. That migration kept finding new consumer sites (`dag_graph.py:189/233`, `mermaid.py:117/153`, `ascii_graph.py:174/176/266/360`, `workflow.py:220` `cross_sop_target`); each round narrowed scope but each narrowing missed sites that broke on commit. The MEMORY note `feedback_widening_refactor_self_audit.md` exists for exactly this failure mode. Three rounds of partial success.

Path B sidesteps the migration. The new `sub_branch: str | None` field is **purely additive**:

| Property | Before | After |
|---|---|---|
| `StepDict.index` type | `int` | `int` (unchanged) |
| `step_indices` return type | `frozenset[int]` | `frozenset[int]` (unchanged — sub-steps share parent's int index) |
| `LoopSignature.from_step / to_step` | `int` | `int` (unchanged) |
| `CROSS_SOP_REF` regex | `\d+` | `\d+` (unchanged — cross-SOP refs target integer steps only; sub-step targeting is a future feature, out of scope) |
| `--json phases[].steps[].index` type | `int` | `int` (unchanged) |
| `--json todo[].index` format | `"phase.step"` (str) | `"phase.step"` for plain; `"phase.stepLetter"` (e.g. `"2.3a"`) for sub-stepped — string→string, format extension only |
| Renderer call sites at `dag_graph.py:189/233`, `mermaid.py:117/153`, `ascii_graph.py:174/176/266/360`, `workflow.py:220` | int-typed | **untouched** — they don't see sub_branch unless they explicitly read it |
| New: `StepDict.sub_branch` | (didn't exist) | `str | None` — additive optional |
| New: `parse_workflow_branches`, `BranchSignature` | (didn't exist) | New module-level functions; new dataclass |

Renderers that care about siblings opt in by reading `sub_branch`. Renderers that don't (every existing code path) stay byte-identical.

## Impact

### Files to be modified

| File | Nature | Estimated LOC |
|---|---|---|
| `src/fx_alfred/core/steps.py` | Add **second regex** for sub-steps `^(?:###\s+)?(\d+)([a-z])\.\s+(.+)` matched alongside the existing integer regex; `extract_steps_section` produces `StepDict` with `sub_branch="a"` for matched sub-steps and omits `sub_branch` (or sets `None`) for plain steps. **`index` stays int**. The original cast on line 47 is unchanged. | ~25 |
| `src/fx_alfred/core/phases.py` | Add `sub_branch: NotRequired[str]` to `StepDict` TypedDict (NotRequired = backward-compat; existing call sites don't break). | ~5 |
| `src/fx_alfred/core/workflow.py` | New `parse_workflow_branches` parser; new `BranchSignature` dataclass (fields: `from_step: int`, `to: list[BranchTarget]` where `BranchTarget = NamedTuple("BranchTarget", [("parent", int), ("branch", str), ("label", str)])`); new `validate_branches` validator. **`step_indices`, `LoopSignature`, `CROSS_SOP_REF` all unchanged.** Sub-step IDs in `Workflow branches.to` are validated against the new field, not against `step_indices`. | ~70 |
| `src/fx_alfred/commands/plan_cmd.py` | One additive change: when emitting `todo[].index` for a step with `sub_branch`, format as `f"{phase_num}.{step_idx}{sub_branch}"` instead of `f"{phase_num}.{step_idx}"`. **`phases[].steps[].index` JSON emit path unchanged** (still int). Loop dict keys unchanged (LoopSignature unchanged). | ~10 |
| `src/fx_alfred/commands/validate_cmd.py` | New cross-checks for `Workflow branches` (per PRP §7). | ~25 |

**Not modified in this CHG** (deferred to CHG-2227):
- `core/dag_graph.py`, `core/ascii_graph.py`, `core/mermaid.py` — renderer touches happen alongside the geometry primitive
- New file `core/branch_geometry.py` — branch+convergence rendering primitive
- Any user-visible behavior change

### New files

| File | Purpose | Estimated LOC |
|---|---|---|
| `tests/test_workflow_branches.py` | Unit tests for `parse_workflow_branches`, `BranchSignature`, `validate_branches` | ~120 |
| `tests/fixtures/branches_2way.md` | 2-way branch fixture for parser+validator | small |
| `tests/fixtures/branches_3way.md` | 3-way branch fixture (Audit Ledger from PRP) | small |
| `tests/fixtures/branches_invalid_skipped.md` | `3a/3b/3c/5` (skipped 4) — validator rejects | small |
| `tests/fixtures/branches_invalid_noncontiguous.md` | `3a/4/3b` — validator rejects | small |
| `tests/fixtures/branches_invalid_orphan.md` | sub-step in `## Steps` not in any `branches.to` — validator rejects | small |
| `tests/fixtures/branches_loops_combined.md` | Branch + loop in same SOP — parser test (loop rendering byte-identical) | small |

### Dependencies

**No new runtime deps in this CHG.** `wcwidth` is needed by the renderer (CHG-2227), not the parser/validator.

### CHANGELOG

**No CHANGELOG entry yet.** This CHG ships nothing user-visible; the v1.8.0 entry lands with CHG-2227 once the renderer is green.

### `--json` output schema delta

| JSON path | Before this CHG | After this CHG |
|---|---|---|
| `phases[].steps[].index` | `int` | `int` (unchanged for legacy; sub-steps share parent's int — both `3a` and `3b` emit `index: 3`) |
| `phases[].steps[].sub_branch` | (absent) | absent for plain; `"a"`/`"b"`/etc. for sub-steps (additive new field) |
| `todo[].index` | `"phase.step"` (str, e.g. `"1.1"`, `"2.3"`) | `"phase.step"` for plain; `"phase.stepLetter"` for sub-stepped (e.g. `"2.3a"`) — string→string, format extension only |
| Cross-SOP loop refs `"COR-1500.3"` | unchanged | unchanged (sub-step cross-SOP targeting is out of scope; future PRP) |

**No int → str type changes anywhere.** Adding the optional `sub_branch` field is additive; existing consumers ignore it. Format extension on `todo[].index` is string→string, non-breaking.

### Documentation

- No CLAUDE.md / COR-1202 changes in this CHG (renderer-facing docs land with CHG-2227)
- Internal docstrings on new `parse_workflow_branches` / `validate_branches` cover the schema

### Rollback

Per-phase commit boundaries. Each phase ends with green tests; reviewers and the author can `git revert` any single phase without unwinding earlier ones. Path B's additivity makes per-phase revert genuinely safe — no inter-phase type contracts that break in the middle.

---

## Plan

Per COR-1500 (TDD Development Workflow). Three phases (was four; LoopSignature widening eliminated; original Phase 1A and 1B re-merged since both are additive and don't conflict).

### Phase 1 — Schema + Parser (`steps.py` + `phases.py` + `workflow.py`)

**RED:**
- `tests/test_steps.py::test_extract_step_substep_format` — `## Steps` containing `3a. Foo` parses to step with `index=3`, `sub_branch="a"`, `gate=False`
- `tests/test_steps.py::test_legacy_int_steps_unchanged` — every existing all-integer fixture parses identically with `sub_branch` absent (NotRequired key)
- `tests/test_steps.py::test_substep_with_gate` — `3a. Foo [GATE]` correctly detects gate while preserving `sub_branch="a"`
- `tests/test_phases.py::test_stepdict_sub_branch_optional` — type-check fixture confirms `sub_branch: NotRequired[str]` (existing call sites pass without `sub_branch` and continue to type-check)
- `tests/test_workflow.py::test_step_indices_legacy_unchanged` — sub-stepped fixture `1, 2, 3a, 3b, 4` returns `frozenset[int] = {1, 2, 3, 4}` (siblings share parent's int; sub-step suffix lives in separate field, not in step_indices)
- `tests/test_workflow_branches.py::test_parse_simple_3way` — load `branches_3way.md`; `parse_workflow_branches(parsed)` returns `[BranchSignature(from_step=2, to=[BranchTarget(parent=3, branch="a", label="pass"), BranchTarget(parent=3, branch="b", label="fail"), BranchTarget(parent=3, branch="c", label="escalate")])]`
- `tests/test_workflow_branches.py::test_branches_legacy_loops_unchanged` — SOPs without `Workflow branches:` parse identically; `LoopSignature` round-trip byte-identical to v1.7.1
- `tests/test_workflow.py::test_existing_loop_rendering_regression_suite` — full nested + flat + Mermaid loop fixtures (enumerated below) stay byte-identical

   *Enumerated regression fixtures:* every existing fixture under `tests/fixtures/` matched by `git grep -l "Workflow loops" tests/fixtures/` (currently includes `tests/fixtures/sop_intra_sop_loop.md`, cross-SOP loop fixtures, gate+loop combinations, and multi-loop SOPs). Each fixture gets a snapshot test asserting byte-identical pre/post-CHG output for `nested`, `flat`, and Mermaid layouts. The actual fixture list is collected at the start of Phase 1 implementation (one `git grep` invocation) so it stays accurate to whatever ships in main.

**GREEN:** Add second regex in `core/steps.py` for sub-step parsing. Add `sub_branch: NotRequired[str]` to `StepDict` in `core/phases.py`. Add `BranchSignature`/`BranchTarget`/`parse_workflow_branches` to `core/workflow.py`. **No existing code path changes** — every existing site reads `step["index"]` as int, ignores absent `sub_branch`, sees no behavioral change.

**REFACTOR:** Run **full-corpus self-audit grep** per MEMORY note `feedback_widening_refactor_self_audit.md`:
```
git grep -nE "step_idx|step_indices|isinstance.*int.*step|range\(.*step|StepDict|index.*int" src/fx_alfred/
```
Audit any consumer not in the enumerated plan; expected = zero new touches needed since path B is additive (no type changes). If grep surfaces any consumer that reads `index` and would behave differently when `sub_branch` is set — log it for CHG-2227 attention; do NOT modify in this CHG.

**Exit:** All tests pass; existing 720 + ~10 new = ~730 green; commit boundary: `parser+workflow: add sub_branch field + Workflow branches schema (Phase 1)`.

### Phase 2 — Validator (`validate_cmd.py` + `workflow.py::validate_branches`)

**RED:**
- `test_branches_from_must_exist` — `Workflow branches.from = 99` (no such step) → rejected
- `test_branches_to_must_exist` — `to: [{id: 3a, label: pass}]` when `## Steps` has no `3a` → rejected
- `test_branches_to_parent_matches_from_plus_one` — `from: 2 to: [{id: 4a, ...}]` rejected (parent must be `from + 1`)
- `test_branches_substep_well_formed` — `to.id` regex matches `\d+[a-z]` only; `to: [{id: 3aa, ...}]` rejected
- `test_branches_siblings_contiguous_in_steps` — `branches_invalid_noncontiguous.md` (`3a, 4, 3b`) rejected
- `test_branches_orphan_substep_rejected` — `branches_invalid_orphan.md` rejected (sub-step in `## Steps` not in any `branches.to`)
- `test_branches_skipped_integer_rejected` — `branches_invalid_skipped.md` (`3a/3b/3c/5` no step 4) rejected with clear error

**GREEN:** Implement `validate_branches(parsed, branches) -> list[ValidationError]` in `core/workflow.py`; wire into `commands/validate_cmd.py`.

**Exit:** All tests pass; existing + ~17 new = ~737 green; commit boundary: `validate: add Workflow branches cross-checks (Phase 2)`.

### Phase 3 — Plan-builder `todo[].index` formatting (`plan_cmd.py`)

This is the smallest user-visible surface change in this CHG: the dotted form in `todo[].index` extends from `"phase.step"` to `"phase.stepLetter"` for sub-stepped plans. Pure format extension; existing consumers parsing `"1.1"` auto-handle `"2.3a"` (string→string, no type change).

**RED:**
- `tests/test_plan_cmd.py::test_todo_index_legacy_unchanged` — all-integer plan emits `todo[].index = "1.1"`, `"2.1"`, etc., byte-identical to v1.7.1 snapshot
- `tests/test_plan_cmd.py::test_todo_index_substep_format` — sub-stepped plan emits `todo[].index = "2.3a"` for sub-step
- `tests/test_plan_cmd.py::test_phases_steps_index_int_unchanged` — `phases[].steps[].index` remains int for both legacy and sub-stepped plans (sub-step shares parent's int)
- `tests/test_plan_cmd.py::test_phases_steps_sub_branch_emitted` — sub-stepped plan emits `phases[].steps[].sub_branch = "a"` (additive new field)

**GREEN:** Update `plan_cmd.py:322/334/369` formatting: `f"{phase_num}.{step_idx}{step.get('sub_branch', '')}"` instead of `f"{phase_num}.{step_idx}"`. JSON `phases[].steps[].index` emit path is unchanged (still emits int from `step["index"]`). Add `sub_branch` to the emitted dict if present.

**Exit:** Full test suite green (~741 total); commit boundary: `plan: extend todo[].index format for sub-steps + emit sub_branch (Phase 3)`.

### No Phase 4+ in this CHG

Documentation, CHANGELOG, version bump, multi-model code review of renderer changes, and PyPI release all happen in CHG-2227. This CHG ships the data layer to main with no user-visible behavior change beyond the backward-compatible `todo[].index` format extension and the additive `sub_branch` field.

---

## Test Plan Summary

| Phase | New tests | Total at end of phase |
|---|---:|---:|
| Pre-CHG baseline | — | 720 |
| Phase 1 (parser + schema) | ~10 | ~730 |
| Phase 2 (validator) | ~7 | ~737 |
| Phase 3 (plan-builder format) | ~4 | ~741 |

**Total estimated new tests in this CHG: ~21.** All existing tests must stay green throughout. No new runtime deps. No version bump.

Coverage gates: every new public function has at least one test; every fixture in `tests/fixtures/branches_*.md` is exercised by at least one assertion; the regression suite enumerated in Phase 1 RED enforces byte-identical loop rendering across every existing loop fixture.

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Phase 1 self-audit grep surfaces an unexpected consumer that behaves differently when `sub_branch` is set | Path B's additivity means consumers reading `step["index"]` are unaffected. Any consumer that *also* reads `sub_branch` is opting in. Worst case: log + defer to CHG-2227. The grep is mandatory before commit. |
| `StepDict.sub_branch: NotRequired[str]` (TypedDict) — pyright behavior on the boundary | `NotRequired[str]` is the standard idiom for backward-compatible optional TypedDict fields (Python 3.11+; we use 3.10+ via `typing_extensions`). Existing call sites that don't pass `sub_branch` keep type-checking. |
| Sub-stepped SOPs share parent's int in `step_indices`, which collapses sibling identity | This is intentional. `step_indices` is a *workflow-loops contract* — cross-SOP loops target integer steps. Sibling identity for branches is tracked in the new `Workflow branches` schema, not in `step_indices`. The two schemas are orthogonal. |
| Phase 3 `todo[].index` format extension (`"2.3a"`) breaks downstream consumers parsing string IDs | The format was always documented as opaque string in `plan_cmd.py`. Any consumer regex-matching `^\d+\.\d+$` would be tolerant (the new form `^\d+\.\d+[a-z]?$` is a strict superset that still parses fine for legacy input). Sub-stepped output only appears for SOPs that opted in via `Workflow branches:` (none today). |
| Branch + loop combined SOP exercises new schema and old schema together | `tests/fixtures/branches_loops_combined.md` covers; Phase 1 regression suite asserts loop rendering byte-identical. |
| Test-suite size grows ~21 tests; CI time creeps up | Negligible (existing 720 tests run in 5.7s; ~21 more is < 0.5s). |

---

## Approval

- [ ] Approved by: <reviewer> on <date>

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-27 | Initial CHG drafted as 10-phase execution plan derived from PRP-2225. | Frank + Claude Code |
| 2026-04-27 | Round 1 review: Codex 8.5 FIX, Gemini 8.5 FIX. Both reviewers independently endorsed splitting the 10-phase monolith into Data Layer + Presentation Layer CHGs. CHG rewritten as Data Layer only. | Frank + Claude Code |
| 2026-04-27 | Round 2 review: Codex 8.4 FIX, Gemini 6.7 FIX. Two factual defects caught: `phases[].steps[].index` IS currently `int` (widening it IS breaking); `LoopSignature` widening would silently break renderer call sites. | Frank + Claude Code |
| 2026-04-27 | Round 3 review: Codex 8.6 FIX, Gemini 6.6 FIX (-0.1 — regressed). Round 3 attempted Path A (narrow-scope widening + JSON-emit shim) but introduced two new defects in the same family the MEMORY note `feedback_widening_refactor_self_audit.md` exists to prevent: Phase 1A breaks renderers (`ascii_graph.py:266` `int < str < int` runtime TypeError; `mermaid.py:117` pyright fail; etc.); Phase 1B regex extension to `\d+[a-z]?` breaks `cross_sop_target` int-cast. Self-audit grep was scoped only to `steps.py + phases.py`, missed full-corpus consumer audit. Three rounds of partial success; FXA-2218 3-round cap reached. | Frank + Claude Code |
| 2026-04-27 | **Path B rearchitecture** (this revision). Eliminates the type-widening migration entirely. New `StepDict.sub_branch: NotRequired[str]` field is purely additive; `index` stays `int`; `step_indices` stays `frozenset[int]`; `LoopSignature` stays `int`; `CROSS_SOP_REF` regex stays `\d+`. No consumer audit needed since no types change. Three phases (was four — Phase 1A/1B re-merged since both are additive). Per-phase commit boundaries genuinely safe due to additivity. Phase 1 REFACTOR step now mandates **full-corpus self-audit grep** over `src/fx_alfred/` (was only `steps.py + phases.py` in R3). Loop rendering regression suite enumerated explicitly. Reframed as fresh review (architecture changed; not Round 4). | Frank + Claude Code |
