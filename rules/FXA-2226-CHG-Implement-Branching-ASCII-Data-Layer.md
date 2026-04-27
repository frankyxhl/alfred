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
| `src/fx_alfred/core/steps.py` | Add **second regex** for sub-steps `^(?:###\s+)?(\d+)([a-z])\.\s+(.+)` matched alongside the existing integer regex; `extract_steps_section` produces `StepDict` with `sub_branch="a"` for matched sub-steps and **omits `sub_branch` entirely** for plain steps (the key is absent — never set to `None` or any sentinel). This convention is required for deterministic `todo[].index` formatting at Phase 3: `step.get('sub_branch', '')` must return `""` for plain steps so `f"{phase_num}.{step_idx}{step.get('sub_branch', '')}"` produces `"1.1"` (not `"1.1None"`). Phase 1 RED includes a test asserting `"sub_branch" not in step` for every plain step. **`index` stays int**. The original cast on line 47 is unchanged. | ~25 |
| `src/fx_alfred/core/phases.py` | Refactor `StepDict` to use the **`_StepRequired + total=False`** pattern matching the repo's existing `_PhaseRequired + PhaseDict(total=False)` precedent at `phases.py:47-75`. Required keys (`index: int`, `text: str`, `gate: bool`) move to `_StepRequired`; new optional `sub_branch: str` lives on the `total=False` subclass. Avoids adding `typing_extensions` as a runtime dep (the `NotRequired` alternative would require it; the `total=False` precedent is already battle-tested per FXA-2206 `reportTypedDictNotRequiredAccess` history in `src/fx_alfred/CHANGELOG.md:80`). | ~10 |
| `src/fx_alfred/core/workflow.py` | (a) **Update `_parse_step_indices`** at `workflow.py:332` to include sub-stepped lines — a `3a.` line contributes parent integer `3` to the returned `frozenset[int]`. Implementation choice: extend `_STEP_INDEX_RE` at `workflow.py:181` to `^(?:###\s+)?(\d+)[a-z]?\.\s+` (single regex captures both forms; sub-step suffix discarded by the int cast) OR add a parallel sub-step scan that injects parent ints. Phase 1 RED test `test_step_indices_legacy_unchanged` enforces `{1,2,3,4}` for SOP `1, 2, 3a, 3b, 4`. (b) New `parse_workflow_branches` parser; new `BranchSignature` dataclass (fields: `from_step: int`, `to: list[BranchTarget]` where `BranchTarget = NamedTuple("BranchTarget", [("parent", int), ("branch", str), ("label", str)])`); new `validate_branches` validator. **`LoopSignature.from_step / to_step` and `CROSS_SOP_REF` regex remain unchanged.** Sub-step IDs in `Workflow branches.to` are validated against the new sub-step parser output. | ~85 |
| `src/fx_alfred/commands/plan_cmd.py` | Format-extension changes at the **actual sites verified by `grep -n 'dotted = f' src/fx_alfred/commands/plan_cmd.py`**: (1) `plan_cmd.py:286` — `dotted = f"{phase_num}.{step_idx}"` → `dotted = f"{phase_num}.{step_idx}{step.get('sub_branch', '')}"`. (2) `plan_cmd.py:352` — same pattern. Note: lines 322/334 are no-Steps-found fallback paths with no `step_idx` in scope (untouched); the prior CHG draft cited 322/334/369 incorrectly. **`phases[].steps[].index` JSON emit path unchanged** (still int). Loop dict keys unchanged. | ~10 |
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

**No int → str type changes anywhere.** Adding the optional `sub_branch` field is additive; existing consumers ignore it. Format extension on `todo[].index` is string→string but **schema-breaking for strict numeric-regex consumers** (`^\d+\.\d+$` would reject `"2.3a"`); see §Risks for mitigation (gated by renderer-readiness flag; v1.8.0 release notes must call it out under fx-alfred's documented versioning policy).

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
- `tests/test_steps.py::test_legacy_int_steps_unchanged` — every existing all-integer fixture parses identically with `sub_branch` absent (optional key via `total=False`)
- `tests/test_steps.py::test_substep_with_gate` — `3a. Foo [GATE]` correctly detects gate while preserving `sub_branch="a"`
- `tests/test_phases.py::test_stepdict_sub_branch_optional` — type-check fixture confirms `sub_branch` is optional via the `_StepRequired + total=False` subclass pattern (existing call sites pass without `sub_branch` and continue to type-check; `step.get("sub_branch")` returns `None` for plain steps)
- `tests/test_workflow.py::test_step_indices_with_bare_parent` — sub-stepped fixture `1, 2, 3, 3a, 3b, 4` (with bare `3.` parent line — see authoring convention below) returns `frozenset[int] = {1, 2, 3, 4}` (sub-step lines also contribute their parent int; suffix lives in separate field)
- `tests/test_workflow.py::test_step_indices_substeps_only` — sub-stepped fixture `1, 2, 3a, 3b, 4` (without bare `3.` line) ALSO returns `{1, 2, 3, 4}` (parser injects parent int from each sub-step)
- `tests/test_workflow_branches.py::test_parse_simple_3way` — load `branches_3way.md`; `parse_workflow_branches(parsed)` returns `[BranchSignature(from_step=2, to=[BranchTarget(parent=3, branch="a", label="pass"), BranchTarget(parent=3, branch="b", label="fail"), BranchTarget(parent=3, branch="c", label="escalate")])]`
- `tests/test_workflow_branches.py::test_branches_legacy_loops_unchanged` — SOPs without `Workflow branches:` parse identically; `LoopSignature` round-trip byte-identical to v1.7.1
- `tests/test_workflow.py::test_existing_loop_rendering_regression_suite` — every existing loop test in the suite stays byte-identical (existing assertion suites enumerated below) for `nested`, `flat`, and Mermaid layouts

   *Authoring convention (locked here per Gemini Round 1 issue 3):* a SOP authoring `Workflow branches: from: 2; to: [3a, 3b, 3c]` MAY OR MAY NOT include a bare `3.` parent line in `## Steps`. Either form is valid; the parser injects the parent integer (`3`) into `step_indices` from the sub-step lines themselves so `step_indices` is the same `{1, 2, 3, 4}` regardless. Validator does not require the bare parent line. Documented in Phase 1 GREEN.

   *Enumerated regression suite:* the project does NOT have a `tests/fixtures/` directory; loop fixtures are defined inline in `tests/test_workflow_loops.py`, `tests/test_validate_cmd.py`, `tests/test_mermaid.py`, and the existing `test_*` modules under `tests/`. Phase 1 RED for the regression suite means: every existing test in those modules that exercises `Workflow loops:` rendering (collected at Phase 1 start via `git grep -l 'Workflow loops' tests/`) must run unchanged after Phase 1 GREEN. Snapshot-test idiom is in-process: capture pre-CHG output (commit before the parser change) by running `pytest -k 'workflow_loop or mermaid' --tb=no -q` and saving to a baseline; re-run after Phase 1 GREEN; assert no diffs. No new fixture directory is created.

**GREEN:** Add second regex in `core/steps.py` for sub-step parsing. Refactor `StepDict` in `core/phases.py` to `_StepRequired + total=False` pattern (matching `phases.py:47-75` precedent); add `sub_branch: str` on the `total=False` subclass. Add `BranchSignature`/`BranchTarget`/`parse_workflow_branches` to `core/workflow.py`. Update `_parse_step_indices` at `workflow.py:332` (extending `_STEP_INDEX_RE` at `:181` to `^(?:###\s+)?(\d+)[a-z]?\.\s+`) so sub-step lines contribute their parent int. **No existing code path changes** — every existing site reads `step["index"]` as int, ignores absent `sub_branch`, sees no behavioral change.

**REFACTOR — full-corpus self-audit grep with explicit tabulation** (per MEMORY note `feedback_widening_refactor_self_audit.md` AND Gemini Round 1 issue 4):

```
git grep -nE "step_idx|step_indices|isinstance.*int.*step|range\(.*step|StepDict|index.*int" src/fx_alfred/
```

Tabulate **every hit** in a table at the bottom of the implementation PR description with three columns: `file:line`, `pattern`, `decision` (one of: `int-only-read-safe`, `reads-sub-branch-explicitly`, `requires-CHG-2227-attention`). Acceptance: every row has decision filled in by the implementer; reviewer audits the table during code review. "Expected zero touches" without per-hit tabulation is not acceptable.

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
- `test_branches_blocked_until_renderer_ships` — **intermediate-state guardrail** (per Codex Round 1 issue 3): until CHG-2227 lands, **`af validate` errors with `"Workflow branches: schema is parsed but renderer support is not yet shipped (CHG-2227 pending). Production SOPs MUST NOT author this field until CHG-2227 lands."`** Test SOP carrying `Workflow branches:` triggers this error. The error is gated by a feature flag (`_BRANCHES_RENDERER_READY = False` in `core/workflow.py`); CHG-2227 flips it to `True` as one of its commit-boundary deliverables. Existing test fixtures without `Workflow branches:` are unaffected.

**GREEN:** Implement `validate_branches(parsed, branches) -> list[ValidationError]` in `core/workflow.py`; wire into `commands/validate_cmd.py`. Include the renderer-readiness gate (`_BRANCHES_RENDERER_READY = False` flag).

**Exit:** All tests pass; existing + ~18 new = ~738 green; commit boundary: `validate: add Workflow branches cross-checks + renderer-readiness gate (Phase 2)`.

### Phase 3 — Plan-builder `todo[].index` formatting (`plan_cmd.py`)

This is the smallest user-visible surface change in this CHG: the dotted form in `todo[].index` extends from `"phase.step"` to `"phase.stepLetter"` for sub-stepped plans. Format extension is string→string but **breaks consumers using strict numeric regex** (`^\d+\.\d+$` would reject `"2.3a"`). Output cannot appear until both CHG-2226 and CHG-2227 ship (renderer-readiness flag gated); CHG-2227 Phase 8's v1.8.0 release notes must call this out as a breaking surface under fx-alfred's documented versioning policy.

**RED:**
- `tests/test_plan_cmd.py::test_todo_index_legacy_unchanged` — all-integer plan emits `todo[].index = "1.1"`, `"2.1"`, etc., byte-identical to v1.7.1 snapshot
- `tests/test_plan_cmd.py::test_todo_index_substep_format` — sub-stepped plan emits `todo[].index = "2.3a"` for sub-step
- `tests/test_plan_cmd.py::test_phases_steps_index_int_unchanged` — `phases[].steps[].index` remains int for both legacy and sub-stepped plans (sub-step shares parent's int)
- `tests/test_plan_cmd.py::test_phases_steps_sub_branch_emitted` — sub-stepped plan emits `phases[].steps[].sub_branch = "a"` (additive new field)

**GREEN:** Update `plan_cmd.py:286` and `:352` formatting (the actual `dotted = f"..."` sites verified by `grep -n 'dotted = f' src/fx_alfred/commands/plan_cmd.py`): `f"{phase_num}.{step_idx}{step.get('sub_branch', '')}"` instead of `f"{phase_num}.{step_idx}"`. JSON `phases[].steps[].index` emit path is unchanged (still emits int from `step["index"]`). Add `sub_branch` to the emitted dict if present.

**Exit:** Full test suite green (~741 total); commit boundary: `plan: extend todo[].index format for sub-steps + emit sub_branch (Phase 3)`.

### No Phase 4+ in this CHG

Documentation, CHANGELOG, version bump, multi-model code review of renderer changes, and PyPI release all happen in CHG-2227. This CHG ships the data layer to main with no user-visible behavior change beyond the backward-compatible `todo[].index` format extension and the additive `sub_branch` field.

---

## Test Plan Summary

| Phase | New tests | Total at end of phase |
|---|---:|---:|
| Pre-CHG baseline | — | 720 |
| Phase 1 (parser + schema) | ~10 | ~730 |
| Phase 2 (validator + renderer-readiness gate) | ~8 | ~738 |
| Phase 3 (plan-builder format) | ~4 | ~742 |

**Total estimated new tests in this CHG: ~21.** All existing tests must stay green throughout. No new runtime deps. No version bump.

Coverage gates: every new public function has at least one test; every fixture in `tests/fixtures/branches_*.md` is exercised by at least one assertion; the regression suite enumerated in Phase 1 RED enforces byte-identical loop rendering across every existing loop fixture.

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Phase 1 self-audit grep surfaces an unexpected consumer that behaves differently when `sub_branch` is set | Path B's additivity means consumers reading `step["index"]` are unaffected. Any consumer that *also* reads `sub_branch` is opting in. Worst case: log + defer to CHG-2227. The grep is mandatory before commit. |
| `StepDict.sub_branch` optional TypedDict field — pyright behavior on the boundary | `_StepRequired + total=False` is the repo's established idiom for backward-compatible optional TypedDict fields (matches `_PhaseRequired + PhaseDict(total=False)` precedent at `phases.py:47-75`; battle-tested per FXA-2206 `reportTypedDictNotRequiredAccess` history in `src/fx_alfred/CHANGELOG.md:80`). No new runtime dep needed. Existing call sites that don't pass `sub_branch` keep type-checking; `step.get("sub_branch")` returns `None` for plain steps. |
| Sub-stepped SOPs share parent's int in `step_indices`, which collapses sibling identity | This is intentional. `step_indices` is a *workflow-loops contract* — cross-SOP loops target integer steps. Sibling identity for branches is tracked in the new `Workflow branches` schema, not in `step_indices`. The two schemas are orthogonal. |
| Phase 3 `todo[].index` format extension (`"2.3a"`) is a **schema-breaking change** for consumers using strict numeric regex | **Acknowledged as breaking** for any consumer validating `todo[].index` with a strict pattern like `^\d+\.\d+$` (numeric-only step token); such consumers will reject `"2.3a"` until they update to `^\d+\.\d+[a-z]?$`. Mitigation: (a) the breaking surface is gated by the renderer-readiness flag (`_BRANCHES_RENDERER_READY = False` in this CHG; flipped by CHG-2227 Phase 4) — sub-stepped output cannot appear until both CHGs ship; (b) v1.8.0 release notes (CHG-2227 Phase 8) MUST list this as an explicit "⚠ Breaking — `todo[].index` format" entry under fx-alfred's documented versioning policy (per the disclaimer in `src/fx_alfred/CHANGELOG.md`). The earlier framing of "any consumer auto-handles" was overconfident; strict numeric validators are a reasonable practice and would not auto-handle. |
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
| 2026-04-27 | **Path B rearchitecture** (initial revision). Eliminates the type-widening migration entirely. New `StepDict.sub_branch: NotRequired[str]` field is purely additive. Three phases (was four). Reframed as fresh review (architecture changed; not Round 4). | Frank + Claude Code |
| 2026-04-27 | Path B fresh review: Codex 8.3 FIX, Gemini 8.5 FIX. **Both reviewers endorsed the architecture** ("Path B is the right architecture", "trust restored"); concerns were CHG drafting gaps, not architectural problems. This revision applies all 7 combined fixes: (1) line citations corrected `plan_cmd.py:322/334/369 → :286, :352` (Gemini Issue 1); (2) `_parse_step_indices` regex update added to Phase 1 GREEN — current regex skips `3a.` lines (Codex defect 1); (3) `StepDict` refactor uses repo's `_StepRequired + total=False` precedent at `phases.py:47-75` instead of `NotRequired` (avoids new `typing_extensions` dep — Codex defect 2); (4) regression suite rewritten — `tests/fixtures/` doesn't exist; loop tests are inline in `tests/test_workflow_loops.py`/`test_validate_cmd.py`/`test_mermaid.py`; collected via `git grep -l 'Workflow loops' tests/` at Phase 1 start (Gemini Issue 2); (5) parent-step authoring convention locked — bare `3.` line is OPTIONAL; parser injects parent integer from sub-step lines so `step_indices` is correct either way (Gemini Issue 3); (6) Phase 2 adds renderer-readiness gate (`_BRANCHES_RENDERER_READY = False`) — `af validate` errors on `Workflow branches:` until CHG-2227 flips the flag (Codex defect 3); (7) Phase 1 REFACTOR audit grep now mandates explicit per-hit tabulation in implementation PR description (Gemini Issue 4). | Frank + Claude Code |
