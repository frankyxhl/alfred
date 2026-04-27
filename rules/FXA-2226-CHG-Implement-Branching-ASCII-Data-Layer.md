# CHG-2226: Implement Branching ASCII — Data Layer

**Applies to:** FXA project (parser + validator + plan-builder type widening)
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

Land the **data-layer foundation** for PRP-2225 (Branching ASCII In Plan Graph) — `Workflow branches:` schema, sub-step ID parsing (`\d+[a-z]?`), validator cross-checks, and plan-builder type widening. **No renderer changes**, no version bump. Renderer work ships in CHG-2227 once this CHG's type contract has stabilized in main.

This CHG is the *Data Layer* half of a 2-CHG split, recommended by both Round 1 reviewers (Codex 8.5, Gemini 8.5) over the original 10-phase monolith. The split lets the breaking-change-prone parser/loop migration soak in main before the renderer geometry commits to the type contract.

## Why

PRP-2225 was approved 2026-04-27 (Codex 9.2 + Gemini 9.30 PASS). The original CHG-2226 attempted to ship the entire implementation (10 phases) as one PR; Round 1 review converged on splitting it because (1) Phase 1 widens types across 3 files which gates everything else; (2) renderer geometry (Phase 3) carries different review surface than parser widening; (3) the original "single commit boundary" rollback story didn't survive contact with the 12-file scope.

The split also surfaces a fact issue worth recording (see "Supersedes" below): PRP-2225 described the `--json` step-ID change as "int → str breaking" — but `af plan --json` already emits `"index"` as a string (e.g. `"1.1"`, `"2.1"`) since v1.6.x. There is no breaking change to public output; the int → str migration is purely internal type widening.

## JSON output schema delta (this CHG)

Round 2 review (Gemini) caught a factual defect in the prior "Supersedes" framing: `af plan --json` has **two distinct `index` fields**, not one, and they have different current types. Empirical verification on v1.7.1:

| JSON path | Current type (v1.7.1) | After this CHG |
|---|---|---|
| `phases[].steps[].index` | **`int`** (raw `StepDict.index`) | `int` for legacy SOPs (all integer steps); `str` for sub-stepped SOPs only — **shim at JSON emit boundary**, see below |
| `todo[].index` | `str` (e.g. `"1.1"`, dotted form) | `str` (format extended to `"2.3a"` for sub-stepped SOPs) |

`plan_cmd.py:322/334/369` emits `todo[].index` via `f"{phase_num}.{step_idx}"` — already a string. That field's behavior is unchanged.

`phases[].steps[].index` IS currently `int`. Naively widening the internal `StepDict.index` to `str` (Phase 1A) would cause `phases[].steps[].index` to flip type for legacy consumers, which IS a breaking change.

### Resolution: JSON-emit-boundary shim (preserves backward compatibility)

The internal type widening is needed (sub-step IDs like `"3a"` can't fit in `int`). But the JSON emit path can preserve `int` output for legacy step IDs:

```python
# In plan_cmd.py, where StepDict.index is serialized to JSON:
def _emit_step_index(idx: str) -> int | str:
    return int(idx) if idx.isdigit() else idx
```

Result:
- Legacy SOPs (all integer steps `1`, `2`, `3`) emit `phases[].steps[].index = 1` (int) — **identical to v1.7.1**
- Sub-stepped SOPs (introducing `3a`/`3b`) emit `phases[].steps[].index = "3a"` (str) — **only paths newly capable of producing sub-step IDs see strings**

Since no SOP currently uses `Workflow branches:` (the schema doesn't exist yet until this CHG), no existing consumer ever sees a string in `phases[].steps[].index` until it explicitly opts into the new schema. Backward-compatible by construction.

CHG-2227 (Presentation Layer) keeps this shim through v1.8.0 release; v1.9.0 (or later) can remove it once consumers migrate.

This CHG therefore does NOT introduce a breaking change to `--json` output. v1.8.0 (CHG-2227 release) ships as a regular minor version. PRP-2225's original "int → str breaking" framing was located on the wrong field (`todo[].index` is unchanged); this CHG corrects the location and adds the boundary shim.

## Supersedes / corrects PRP-2225

| PRP-2225 said | Corrected here |
|---|---|
| `--json` step-ID change is breaking, requires shim + deprecation runway | Two distinct fields. `todo[].index` is unchanged. `phases[].steps[].index` is preserved-int for legacy SOPs via emit-boundary shim; only sub-stepped SOPs (which require explicit opt-in via new `Workflow branches:` schema) see new string form. No breaking change for existing consumers. |
| Migration Impact Table marks JSON output as a breaking surface | Migration Impact Table is correct on internal type widening; JSON output preserves backward compat via shim. |

## Impact

### Files to be modified

| File | Nature | Estimated LOC |
|---|---|---|
| `src/fx_alfred/core/steps.py` | Extend regex `(\d+)\.` → `(\d+[a-z]?)\.` (parser/storage form, optional suffix); drop `int()` cast (line `:48` on main HEAD); `parse_top_level_step_indices` returns `frozenset[str]` | ~30 |
| `src/fx_alfred/core/phases.py` | `StepDict.index: int → str` (internal TypedDict; backward-compat preserved at JSON emit boundary — see "JSON output schema delta" above) | ~5 |
| `src/fx_alfred/core/workflow.py` | `_parse_step_indices` returns `frozenset[str]`; `CROSS_SOP_REF` regex extends to `\d+[a-z]?`; new `parse_workflow_branches` parser; new `BranchSignature` dataclass; new `validate_branches` for the validator. **`LoopSignature.from_step / to_step` REMAIN `int`** in this CHG — Codex Round 2 caught that widening them would break renderer call sites at `dag_graph.py:189`, `mermaid.py:153`, `ascii_graph.py:266` that filter loops via `isinstance(int)` or numeric comparison. The `Workflow branches:` schema and sub-step IDs are independent of the loop schema, so this CHG can ship branches support without touching loops. CHG-2227 widens loop types alongside the renderer touches that consume them. | ~60 |
| `src/fx_alfred/commands/plan_cmd.py` | `_classify_step(step_idx: str)` for plain-step parameter typing; loop dict keys remain `dict[int, ...]` (loop types unchanged in this CHG). **JSON emit path:** add `_emit_step_index(idx)` shim at `phases[].steps[].index` serialization point — preserves `int` for legacy step IDs, emits `str` only for sub-step IDs (which can only exist when `Workflow branches:` is declared, opt-in by definition). `todo[].index` field unchanged (already string via `f"{phase_num}.{step_idx}"`). | ~25 |
| `src/fx_alfred/commands/validate_cmd.py` | New cross-checks for `Workflow branches` (per PRP §7); call site at line 324 already string-vs-string after steps.py change | ~30 |

**Not modified in this CHG** (deferred to CHG-2227):
- `core/dag_graph.py`, `core/ascii_graph.py`, `core/mermaid.py` — renderer-side `step_idx` audit AND `LoopSignature.to_step` consumer migration (`dag_graph.py:189`, `mermaid.py:153`, `ascii_graph.py:266` — three call sites that currently use `isinstance(int)` or numeric comparison)
- `LoopSignature.from_step` / `to_step` widening — moves to CHG-2227 alongside the renderer touches that consume them (avoids the silent loop-rendering regression Codex Round 2 caught)
- New file `core/branch_geometry.py` — branch+convergence rendering primitive
- Any user-visible behavior change to loop or branch rendering

### New files

| File | Purpose | Estimated LOC |
|---|---|---|
| `tests/test_workflow_branches.py` | Unit tests for `parse_workflow_branches`, `BranchSignature`, validator rules | ~150 |
| `tests/fixtures/branches_2way.md` | 2-way branch fixture for parser+validator | small |
| `tests/fixtures/branches_3way.md` | 3-way branch fixture (Audit Ledger from PRP) | small |
| `tests/fixtures/branches_invalid_skipped.md` | `3a/3b/3c/5` (skipped 4) — validator rejects | small |
| `tests/fixtures/branches_invalid_noncontiguous.md` | `3a/4/3b` — validator rejects | small |
| `tests/fixtures/branches_invalid_orphan.md` | sub-step in `## Steps` not in any `branches.to` — validator rejects | small |
| `tests/fixtures/branches_loops_combined.md` | Branch + loop in same SOP — parser test | small |

### Dependencies

**No new runtime deps in this CHG.** `wcwidth` is needed by the renderer (CHG-2227), not the parser/validator.

### CHANGELOG

**No CHANGELOG entry yet.** This CHG ships nothing user-visible; the v1.8.0 entry lands with CHG-2227 once the renderer is green.

### Documentation

- No CLAUDE.md / COR-1202 changes in this CHG (renderer-facing docs land with CHG-2227)
- Internal docstrings in new `parse_workflow_branches` / `validate_branches` cover the schema

### Rollback

**Per-phase commit boundaries** (replaces the original "single commit boundary" framing). Each phase below ends with a green-tests commit; reviewers and the author can `git revert` any single phase without unwinding earlier ones. If Phase 2 fails after Phase 1 lands, Phase 1 stays — it's behavior-neutral until something consumes the new types (which only happens in this CHG's own Phase 6 + CHG-2227).

---

## Plan

Per COR-1500 (TDD Development Workflow). Phase 1 split into 1A/1B per Codex Round 1 feedback to limit blast radius.

### Phase 1A — Step-ID parser widening (`steps.py` + `phases.py`)

**RED:**
- `tests/test_steps.py::test_extract_step_substep_format` — `## Steps` containing `3a. Foo` parses to step with `index="3a"`, `gate=False`
- `tests/test_steps.py::test_legacy_int_steps_unchanged` — every existing all-integer fixture parses identically (with string-form indices `"1"`, `"2"` instead of `1`, `2`)
- `tests/test_steps.py::test_substep_with_gate` — `3a. Foo [GATE]` correctly detects gate while preserving sub-step ID
- `tests/test_phases.py::test_stepdict_index_is_str` — typed-dict accepts `index: str`, rejects `index: int` at type-check time (pyright)

**GREEN:** Extend `_TOP_LEVEL_STEP_RE` to `(\d+[a-z]?)`; drop `int(m.group(1))` cast on line 47; widen `StepDict.index` to `str`. Run full existing test suite — all 720 tests stay green (this is the widening-refactor self-audit per MEMORY note `feedback_widening_refactor_self_audit.md`).

**REFACTOR:** Run `git grep -nE "step_idx|step_indices|isinstance.*int.*step|range\(.*step"` over `src/fx_alfred/core/steps.py` and `src/fx_alfred/core/phases.py`; audit any consumer not in this phase's plan.

**Exit:** All tests pass; `pyright src/` clean; commit boundary: `parser: widen step IDs to str (1A)`.

### Phase 1B — Workflow branches schema + step-indices widening (`workflow.py`)

**RED:**
- `tests/test_workflow.py::test_step_indices_returns_frozenset_str` — sub-stepped fixture returns `{"1","2","3a","3b","4"}`
- `tests/test_workflow.py::test_legacy_int_step_indices_unchanged` — all-integer fixture returns `{"1","2","3"}` (str-form)
- `tests/test_workflow.py::test_cross_sop_ref_accepts_substep` — `CROSS_SOP_REF` regex matches `COR-1500.3a`
- `tests/test_workflow.py::test_loop_signature_unchanged` — `LoopSignature.from_step` / `to_step` types and parsing unchanged from v1.7.1 (path A constraint)
- `tests/test_workflow.py::test_existing_loop_rendering_regression_suite` — full nested + flat + Mermaid loop fixtures stay byte-identical to pre-CHG output
- `tests/test_workflow_branches.py::test_parse_simple_3way` — load `branches_3way.md`; `parse_workflow_branches(parsed)` returns `[BranchSignature(from_step="2", to=[("3a","pass"),("3b","fail"),("3c","escalate")])]`
- `tests/test_workflow_branches.py::test_branches_legacy_int_loops_unchanged` — SOPs without `Workflow branches:` parse identically; loop parsing unaffected

**GREEN:** Implement `BranchSignature` dataclass; `parse_workflow_branches`; update `_parse_step_indices` to return `frozenset[str]`; extend `CROSS_SOP_REF` regex to `\d+[a-z]?`. **Do NOT widen `LoopSignature.from_step` / `to_step`** — they remain `int` per Codex Round 2. Loop parsing, validation, and renderer consumption are byte-identical to v1.7.1.

**REFACTOR:** Sweep `src/fx_alfred/core/workflow.py` for `int(step` and `isinstance(.*step.*int)` patterns; audit any consumer not in the plan. Confirm no `LoopSignature` field types changed.

**Exit:** All tests pass; existing nested/flat/Mermaid loop fixtures byte-identical; commit boundary: `workflow: widen step indices to str + add branches parser (1B; loop types unchanged)`.

### Phase 2 — Validator (`validate_cmd.py` + `workflow.py::validate_branches`)

**RED:**
- `test_branches_from_must_exist` — `Workflow branches.from = 99` (no such step) → rejected
- `test_branches_to_must_exist` — `to: [3a]` when `## Steps` has no `3a` → rejected
- `test_branches_leading_int_must_match_from_plus_one` — `from: 2 to: [4a]` rejected (must be `3a`)
- `test_branches_substep_id_well_formed` — `to: [3aa]` rejected (regex `\d+[a-z]` not `\d+[a-z]+`)
- `test_branches_siblings_contiguous_in_steps` — `branches_invalid_noncontiguous.md` (`3a, 4, 3b`) rejected
- `test_branches_orphan_substep_rejected` — `branches_invalid_orphan.md` rejected
- `test_branches_skipped_integer_rejected` — `branches_invalid_skipped.md` (`3a/3b/3c/5` no step 4) rejected with clear error

**GREEN:** Implement `validate_branches(parsed, branches) -> list[ValidationError]` in `core/workflow.py`; wire into `commands/validate_cmd.py`.

**Exit:** All tests pass; existing 720 + ~7 new = ~727 green; commit boundary: `validate: add Workflow branches cross-checks`.

### Phase 6 (renamed from original) — Plan-builder + JSON-emit-boundary shim (`plan_cmd.py`)

`plan_cmd.py` consumes the widened `StepDict.index: str` and the new `BranchSignature` type. **Loop dict keys remain `dict[int, ...]`** since `LoopSignature` step types are unchanged in this CHG. `--json` output preserves backward compatibility via the JSON-emit-boundary shim documented in §"JSON output schema delta".

**RED:**
- `tests/test_plan_cmd.py::test_classify_step_accepts_str_idx` — `_classify_step(step_idx: str)` parameter typing
- `tests/test_plan_cmd.py::test_loop_to_steps_int_keys_unchanged` — `loop_to_steps.get(3)` (int key) still works (LoopSignature unchanged)
- `tests/test_plan_cmd.py::test_emit_step_index_int_for_legacy` — `_emit_step_index("1")` returns `1` (int, backward-compat for legacy SOPs)
- `tests/test_plan_cmd.py::test_emit_step_index_str_for_substep` — `_emit_step_index("3a")` returns `"3a"` (str, only for sub-step IDs)
- `tests/test_plan_cmd.py::test_json_output_legacy_byte_identical` — all-integer plans emit `phases[].steps[].index` as `int` AND `todo[].index` as `str` (`"1.1"`) — byte-identical to v1.7.1 snapshot
- `tests/test_plan_cmd.py::test_json_output_substep_index` — sub-stepped plan emits `phases[].steps[].index = "3a"` (str) AND `todo[].index = "2.3a"` (str)

**GREEN:** Update `_classify_step` parameter typing; add `_emit_step_index(idx: str) -> int | str` helper at the JSON serialization point. Loop dicts unchanged.

**Exit:** Full test suite green (~735 total); commit boundary: `plan: step-index parameter typing + JSON-emit shim (legacy-compat preserved)`.

### No Phase 8/9/10 in this CHG

Documentation, CHANGELOG, version bump, multi-model code review of renderer changes, and PyPI release all happen in CHG-2227. This CHG ships the data layer to main with no user-visible behavior change.

---

## Test Plan Summary

| Phase | New tests | Total at end of phase |
|---|---:|---:|
| Pre-CHG baseline | — | 720 |
| Phase 1A (parser) | ~4 | ~724 |
| Phase 1B (workflow + branches schema) | ~6 | ~730 |
| Phase 2 (validator) | ~7 | ~737 |
| Phase 6 (plan-builder) | ~4 | ~741 |

**Total estimated new tests in this CHG: ~21.** All existing tests must stay green throughout. No new runtime deps. No version bump.

Coverage gates: every new public function has at least one test; every fixture in `tests/fixtures/branches_*.md` is exercised by at least one assertion; every site in PRP-2225 §"Migration Impact Table" that this CHG touches (`steps.py`, `phases.py`, `workflow.py`, `plan_cmd.py`, `validate_cmd.py`) has type-check + unit-test coverage.

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Phase 1A widening breaks existing tests due to `int → str` ripple beyond enumerated sites | Self-audit grep (per MEMORY note `feedback_widening_refactor_self_audit.md`) before commit boundary: `git grep -nE "step_idx\|step_indices\|isinstance.*int.*step\|range\(.*step"` over `src/fx_alfred/`; audit any consumer not in the enumerated plan. Existing test suite is the secondary safety net. |
| Phase 1B widening of `step_indices` to `frozenset[str]` breaks call-site behavior | Phase 1B specifically does NOT widen `LoopSignature.from_step` / `to_step` (kept as `int`) per Codex Round 2 — would otherwise break `dag_graph.py:189`, `mermaid.py:153`, `ascii_graph.py:266` consumers. Loop typing migration moves to CHG-2227 alongside the renderer touches. The Phase 1B regression test (`test_existing_loop_rendering_regression_suite`) asserts byte-identical loop output before/after this CHG. |
| `phases[].steps[].index` JSON output type changes from `int` to `str` (Gemini Round 2) | JSON-emit-boundary shim in Phase 6: `_emit_step_index(idx)` returns `int(idx)` for legacy `\d+` IDs, `str` for sub-step IDs (only emitted when `Workflow branches:` opted in — schema doesn't exist for legacy SOPs). Existing consumers see byte-identical JSON; test `test_json_output_legacy_byte_identical` asserts this. Shim removable in v1.9.0+ once consumers migrate. |
| CHG-2227 (renderer) needs the data-layer types but lands on a different schedule | Per-phase commit boundaries in this CHG mean main always has a coherent type contract; CHG-2227 picks up `LoopSignature` widening + renderer touches in one coordinated change |
| Phase 2 validator surfaces invalid SOPs in the existing corpus | None expected (no SOP currently uses `Workflow branches:` since it doesn't exist yet); validator strict-mode default could miss edge cases — fix is to add the surfaced fixture to test suite |
| Test-suite size grows ~22 tests; CI time creeps up | Negligible (existing 720 tests run in 5.7s; ~22 more is < 0.5s) |

---

## Approval

- [ ] Approved by: <reviewer> on <date>

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-27 | Initial CHG drafted as 10-phase execution plan derived from PRP-2225. | Frank + Claude Code |
| 2026-04-27 | Round 1 review: Codex 8.5 FIX, Gemini 8.5 FIX. Both reviewers independently endorsed splitting the 10-phase monolith into Data Layer + Presentation Layer CHGs. Empirical verification of `af plan --json` output on v1.7.1 also revealed PRP-2225's "int → str breaking" framing was based on an incorrect premise: `--json` already emits string `"index"` (e.g. `"1.1"`), so sub-stepped extension to `"2.3a"` is non-breaking. CHG rewritten as Data Layer only (Phases 1A, 1B, 2, 6); SemVer/disclaimer/JSON-shim discussion removed entirely. Phase 1 split into 1A/1B per Codex feedback. Per-phase commit boundaries replace original "single commit boundary" framing. Renderer + release deferred to CHG-2227. | Frank + Claude Code |
| 2026-04-27 | Round 2 review: Codex 8.4 FIX, Gemini 6.7 FIX. Two factual defects caught (the second of which dropped Gemini's score by -1.8): (1) Gemini — Round 1's "Supersedes" overcorrection: `phases[].steps[].index` IS currently `int` (only `todo[].index` was already string); naive widening IS breaking. (2) Codex — Phase 1B widening `LoopSignature.from_step / to_step` to `str` would break 3 renderer call sites NOT modified in this CHG (`dag_graph.py:189`, `mermaid.py:153`, `ascii_graph.py:266` use `isinstance(int)` or numeric comparison) — silent loop-rendering regression between Phase 1B landing and CHG-2227 shipping. **Round 3 fixes (this revision):** (a) "Supersedes" rewritten as "JSON output schema delta" with both fields documented and a JSON-emit-boundary shim (`_emit_step_index`) in Phase 6 that preserves `int` for legacy step IDs and emits `str` only for sub-step IDs (which require explicit `Workflow branches:` opt-in). Backward-compatible by construction. (b) `LoopSignature` widening REMOVED from this CHG — moves to CHG-2227 alongside the renderer touches that consume it. Phase 1B test list adds `test_loop_signature_unchanged` and `test_existing_loop_rendering_regression_suite` to enforce the constraint. Risk table rewritten. Should fail self-audit grep WAS THE ROUND 1 PROCESS BUG (per MEMORY `feedback_widening_refactor_self_audit.md`); Phase 1A REFACTOR step now mandates the grep. Line-drift fix: `steps.py:47` → `:48`. | Frank + Claude Code |
