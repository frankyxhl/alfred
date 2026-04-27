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

## Supersedes (PRP-2225 fact correction)

PRP-2225 §"Migration Impact Table" and §"Risks" describe the `--json` step-ID type change as a breaking output change requiring a `--json-legacy-step-ids` shim and a deprecation runway. **Empirical verification on v1.7.1 contradicts this:**

```
$ af plan --task "..." COR-1500 --todo --json
{"index": "1.1", "sop": "COR-1103", ...}
{"index": "2.1", "sop": "COR-1402", ...}
```

`plan_cmd.py:322/334/369` emits `"index"` via `f"{phase_num}.{step_idx}"` — already a string. After this CHG's type widening, sub-stepped plans emit `"index": "2.3a"` — still a string, format extended from `"phase.step"` to `"phase.stepLetter"`. **Any consumer correctly parsing the current string format auto-handles the new format.** No SemVer issue; no shim needed.

This CHG therefore drops the `--json-legacy-step-ids` shim entirely. v1.8.0 (CHG-2227 release) ships as a regular minor version with no breaking-change disclaimer.

The `StepDict.index: int → str` widening is real but it's an *internal* TypedDict field, not a JSON output contract. Migration Impact Table covers the internal sites; nothing leaks to the CLI surface.

## Impact

### Files to be modified

| File | Nature | Estimated LOC |
|---|---|---|
| `src/fx_alfred/core/steps.py` | Extend regex `(\d+)\.` → `(\d+[a-z]?)\.` (parser/storage form, optional suffix); drop `int()` cast on line 47; `parse_top_level_step_indices` returns `frozenset[str]` | ~30 |
| `src/fx_alfred/core/phases.py` | `StepDict.index: int → str` (internal TypedDict; not user-facing) | ~5 |
| `src/fx_alfred/core/workflow.py` | `_parse_step_indices` returns `frozenset[str]`; `CROSS_SOP_REF` regex extends to `\d+[a-z]?`; `LoopSignature.from_step` / `to_step` typed `int → str`; `parse_workflow_loops` accepts both legacy int and new str (canonicalizing to str internally); new `parse_workflow_branches` parser; new `BranchSignature` dataclass; new `validate_branches` for the validator | ~80 |
| `src/fx_alfred/commands/plan_cmd.py` | `_classify_step(step_idx: str)`; loop dict keys `dict[int, ...] → dict[str, ...]` at lines 191/208/209/278/283/344. **`--json` emit path unchanged** — `f"{phase_num}.{step_idx}"` already produces strings; sub-stepped output naturally extends to `"2.3a"` form. | ~25 |
| `src/fx_alfred/commands/validate_cmd.py` | New cross-checks for `Workflow branches` (per PRP §7); call site at line 324 already string-vs-string after steps.py change | ~30 |

**Not modified in this CHG** (deferred to CHG-2227):
- `core/dag_graph.py`, `core/ascii_graph.py`, `core/mermaid.py` — renderer-side `step_idx` audit
- New file `core/branch_geometry.py` — branch+convergence rendering primitive
- Any user-visible behavior change

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

### Phase 1B — Workflow + branches schema (`workflow.py`)

**RED:**
- `tests/test_workflow.py::test_step_indices_returns_frozenset_str` — sub-stepped fixture returns `{"1","2","3a","3b","4"}`
- `tests/test_workflow.py::test_legacy_int_step_indices_unchanged` — all-integer fixture returns `{"1","2","3"}` (str-form)
- `tests/test_workflow.py::test_loop_signature_accepts_str_steps` — `LoopSignature.from_step` / `to_step` round-trip through str
- `tests/test_workflow.py::test_cross_sop_ref_accepts_substep` — `CROSS_SOP_REF` regex matches `COR-1500.3a`
- `tests/test_workflow_branches.py::test_parse_simple_3way` — load `branches_3way.md`; `parse_workflow_branches(parsed)` returns `[BranchSignature(from_step="2", to=[("3a","pass"),("3b","fail"),("3c","escalate")])]`
- `tests/test_workflow_branches.py::test_branches_legacy_int_loops_unchanged` — SOPs without `Workflow branches:` parse identically; loop parsing unaffected

**GREEN:** Implement `BranchSignature` dataclass; `parse_workflow_branches`; widen `LoopSignature` step types to `str`; canonicalize int → `str(int)` on parse. Update `_parse_step_indices` and `CROSS_SOP_REF`.

**REFACTOR:** Sweep `src/fx_alfred/core/workflow.py` for `int(step` and `isinstance(.*step.*int)` patterns; audit any consumer not in the plan.

**Exit:** All tests pass; commit boundary: `workflow: widen step types + add branches parser (1B)`.

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

### Phase 6 (renamed from original) — Plan-builder type widening (`plan_cmd.py`)

This is **not** a CLI surface change — `plan_cmd.py` consumes the new `LoopSignature` types and re-keys its internal dicts. `--json` output's `"index"` field is unchanged (already a string per `f"{phase_num}.{step_idx}"`); sub-stepped plans naturally produce `"2.3a"` form.

**RED:**
- `tests/test_plan_cmd.py::test_classify_step_accepts_str_idx` — function signature accepts `step_idx: str`
- `tests/test_plan_cmd.py::test_loop_to_steps_str_keys` — `loop_to_steps.get("3a")` works after re-keying
- `tests/test_plan_cmd.py::test_json_output_substep_index` — `--json` emits `{"index": "2.3a", "sop": "...", ...}` for sub-stepped plan
- `tests/test_plan_cmd.py::test_json_output_legacy_unchanged` — all-integer plans emit `{"index": "1.1", ...}` unchanged from v1.7.1

**GREEN:** Update `_classify_step` signature; rekey loop dicts at `plan_cmd.py:191/208/209/278/283/344`.

**Exit:** Full test suite green (~735 total); commit boundary: `plan: widen step idx to str through plan-builder`.

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
| Phase 1A widening breaks existing tests due to `int → str` ripple beyond enumerated sites | Self-audit grep before commit boundary; existing test suite is the safety net (any silent int-vs-str comparison surfaces as a failure) |
| `LoopSignature.from_step` type change breaks FXA-2218 cross-SOP loop validator | Unit tests in Phase 1B cover `LoopSignature.cross_sop_target()` round-trip + cross-SOP membership check at `workflow.py:393` |
| CHG-2227 (renderer) needs the data-layer types but lands on a different schedule | Per-phase commit boundaries in this CHG mean main always has a coherent type contract; CHG-2227 simply consumes whatever has merged |
| Phase 2 validator surfaces invalid SOPs in the existing corpus | None expected (no SOP currently uses `Workflow branches:` since it doesn't exist yet); validator strict-mode default could miss edge cases — fix is to add the surfaced fixture to test suite |
| Test-suite size grows ~21 tests; CI time creeps up | Negligible (existing 720 tests run in 5.7s; ~21 more is < 0.5s) |

---

## Approval

- [ ] Approved by: <reviewer> on <date>

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-27 | Initial CHG drafted as 10-phase execution plan derived from PRP-2225. | Frank + Claude Code |
| 2026-04-27 | Round 1 review: Codex 8.5 FIX, Gemini 8.5 FIX. Both reviewers independently endorsed splitting the 10-phase monolith into Data Layer + Presentation Layer CHGs. Empirical verification of `af plan --json` output on v1.7.1 also revealed PRP-2225's "int → str breaking" framing was based on an incorrect premise: `--json` already emits string `"index"` (e.g. `"1.1"`), so sub-stepped extension to `"2.3a"` is non-breaking. CHG rewritten as Data Layer only (Phases 1A, 1B, 2, 6); SemVer/disclaimer/JSON-shim discussion removed entirely. Phase 1 split into 1A/1B per Codex feedback. Per-phase commit boundaries replace original "single commit boundary" framing. Renderer + release deferred to CHG-2227. | Frank + Claude Code |
