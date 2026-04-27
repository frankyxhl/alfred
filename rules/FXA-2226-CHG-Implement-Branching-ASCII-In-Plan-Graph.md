# CHG-2226: Implement Branching ASCII In Plan Graph

**Applies to:** FXA project (`af plan --graph` ASCII renderer + sub-step parser)
**Last updated:** 2026-04-27
**Last reviewed:** 2026-04-27
**Status:** Proposed
**Date:** 2026-04-27
**Requested by:** Frank Xu
**Priority:** Medium (no production-blocking issue; quality-of-life improvement for branchy SOPs)
**Change Type:** Normal
**Targets:** PRP-2225 implementation
**Depends on:** PRP-2225 (must merge before this CHG executes)

---

## What

Implement PRP-2225 (Branching ASCII In Plan Graph) end-to-end across parser, validator, renderer, and CLI surfaces. Ship as **v1.8.0** (feature release; new metadata schema + renderer behavior; not patch).

This CHG is the execution plan derived from PRP-2225. The PRP is the *what and why*; this CHG is the *how* — concrete files, function signatures, test enumeration, and the order operations land.

## Why

PRP-2225 was approved 2026-04-27 via COR-1602 multi-model review (Codex 9.2 PASS, Gemini 9.30 PASS, both ≥ 9.0). The PRP enumerates the design decisions; this CHG schedules the work and defines the TDD sequence. Filing the CHG separately (per COR-1101) keeps the PRP reusable as the design reference while letting the implementation evolve through its own review cycle (COR-1500 TDD + COR-1610 code review).

## Impact

### Files to be modified

Direct edits (10 files):

| File | Nature | Estimated LOC |
|---|---|---|
| `src/fx_alfred/core/steps.py` | Extend regex `(\d+)\.` → `(\d+[a-z]?)\.`; drop `int()` cast on line 47; `parse_top_level_step_indices` returns `frozenset[str]` | ~30 |
| `src/fx_alfred/core/phases.py` | `StepDict.index: int` → `str` | ~5 |
| `src/fx_alfred/core/workflow.py` | `_parse_step_indices` returns `frozenset[str]`; `CROSS_SOP_REF` regex extends to `\d+[a-z]?`; `LoopSignature.from_step` / `to_step` typed `int → str`; `parse_workflow_loops` accepts both legacy int and new str; new `parse_workflow_branches` parser; new `BranchSignature` dataclass; new `validate_branches` for the validator | ~80 |
| `src/fx_alfred/core/branch_geometry.py` | **New file** — shared primitive for branch+convergence rendering. Functions: `compute_column_offsets`, `render_branch_connector`, `render_label_row`, `render_sibling_boxes`, `render_join_connector`, `render_dangling_tails` | ~100 |
| `src/fx_alfred/core/dag_graph.py` | `step_row_index` tuple key uses `str`; integrate `branch_geometry` primitives inside phase-box wrapping | ~40 |
| `src/fx_alfred/core/ascii_graph.py` | `step_idx` and `step_indices` audit per Migration Impact Table (signature lines 134/360/397; iteration sites 173, 219, 265); accept `str` step IDs throughout | ~30 |
| `src/fx_alfred/core/mermaid.py` | `step_idx` accepts `str`; emit `S2_3a` style node IDs for sub-steps | ~10 |
| `src/fx_alfred/commands/plan_cmd.py` | `_classify_step(step_idx: str)`; dict-key changes at lines 191/208/209/278/283/344 | ~20 |
| `src/fx_alfred/commands/validate_cmd.py` | New cross-checks for `Workflow branches` (per PRP §7); call site at line 324 already string-vs-string after steps.py change | ~30 |
| `src/fx_alfred/commands/plan_cmd.py` (`--json`) | Add `--json-legacy-step-ids` shim emitting `int` step IDs + `{"id": 3, "branch_letter": "a"}` for sub-steps | ~25 |

New files (2):

| File | Purpose | Estimated LOC |
|---|---|---|
| `src/fx_alfred/core/branch_geometry.py` | Shared branch primitive (above) | ~100 |
| `tests/test_workflow_branches.py` | Unit tests for parser, validator, geometry primitive | ~250 |

Sample SOP fixtures added under `tests/fixtures/`:
- `branches_2way.md` — 2-way branch + auto-convergence
- `branches_3way.md` — 3-way branch + auto-convergence (motivating Audit Ledger example from PRP)
- `branches_4way.md` — 4-way branch (renderer hard cap)
- `branches_dangling.md` — terminal branch (no next-sequential integer)
- `branches_cjk.md` — CJK labels exercising `wcwidth` truncation
- `branches_invalid_skipped.md` — `3a/3b/3c/5` (skipped 4) → validator rejects
- `branches_invalid_noncontiguous.md` — `3a/4/3b` → validator rejects
- `branches_loops_combined.md` — branch + loop in same SOP

Indirect (no edits expected, but covered by test sweep):
- All existing SOP test fixtures (parser regression — every legacy all-integer SOP must keep parsing identically)

### Dependencies

- New runtime dep: `wcwidth` (pure-Python, MIT, ~2KB). Add to `pyproject.toml` `dependencies = [...]`.

### CHANGELOG

Add v1.8.0 entry to `src/fx_alfred/CHANGELOG.md` covering: `Workflow branches:` schema, sub-step IDs in `## Steps`, ASCII renderer branching + convergence + edge labels, `flat` layout parity, `--json-legacy-step-ids` shim deprecation timeline (v1.8.x → removed v1.9.0).

### Documentation

- `CLAUDE.md` (project root) — add a one-paragraph note on `Workflow branches:` syntax; reference PRP-2225
- `COR-1202` (in `src/fx_alfred/rules/`) — add a one-line mention that `af plan --graph` now renders branches when SOP metadata declares them; example in body remains valid (it's a linear flow)
- No new SOPs needed

### Rollback

Single commit boundary at "Migration Impact Table verified, all consumer sites green" — if reviewers reject after that point, revert the commit. The branch is reversible at every stage of the TDD sequence below.

---

## Plan

Per COR-1500 (TDD Development Workflow). Each phase has explicit Red → Green → Refactor cycles. **Tests first; implementation only after tests fail for the right reason.**

### Phase 1 — Schema + Parser (parser widening)

**RED:**
- `tests/test_workflow_branches.py::test_parse_branches_simple` — load `branches_3way.md`, assert `parse_workflow_branches(parsed)` returns the expected list of `BranchSignature(from_step="2", to=[("3a","pass"), ("3b","fail"), ("3c","escalate")])`
- `tests/test_workflow.py::test_step_indices_accepts_substeps` — assert `_parse_step_indices` on a sub-stepped fixture returns `frozenset[str]` containing `{"1","2","3a","3b","3c","4"}`
- `tests/test_workflow.py::test_legacy_int_step_indices_unchanged` — every existing all-integer fixture must produce string-form indices `{"1","2","3"}` with no behavioral surprise downstream

**GREEN:** Implement `BranchSignature` dataclass + `parse_workflow_branches` + step-ID parser widening in `core/steps.py`, `core/phases.py`, `core/workflow.py`. Run full test suite — all existing tests must stay green (this is the widening-refactor self-audit per MEMORY note).

**REFACTOR:** Sweep `git grep -nE "step_idx|step_indices|isinstance.*int.*step|range\(.*step"` over `src/fx_alfred/` and audit any consumer not in the Migration Impact Table.

**Exit:** parser tests pass; `pyright src/` clean; full suite (existing 720 + new ~5) green.

### Phase 2 — Validator (cross-checks per PRP §7)

**RED:**
- `tests/test_validate.py::test_branches_from_must_exist` — invalid metadata referencing nonexistent `from`/`to` rejected
- `tests/test_validate.py::test_branches_leading_int_must_match_from_plus_one` — `from: 2 to: [4a]` rejected
- `tests/test_validate.py::test_branches_siblings_contiguous` — `branches_invalid_noncontiguous.md` rejected
- `tests/test_validate.py::test_branches_label_cell_width_warns` — label > 12 cells via `wcwidth` produces warning (not error)
- `tests/test_validate.py::test_branches_orphan_substep_rejected` — `## Steps` mentions `3a` not in any `Workflow branches.to` → rejected

**GREEN:** Implement validator rules in `core/workflow.py::validate_branches` and wire into `commands/validate_cmd.py`.

**Exit:** validator tests pass; existing validator tests stay green.

### Phase 3 — Renderer (branch geometry primitive)

**RED:**
- `tests/test_branch_geometry.py::test_2way_simple` — golden ASCII for 2-way branch
- `tests/test_branch_geometry.py::test_3way_simple` — golden ASCII for 3-way branch (matches Audit Ledger output in PRP)
- `tests/test_branch_geometry.py::test_4way_capped` — golden ASCII for 4-way branch (renderer hard cap)
- `tests/test_branch_geometry.py::test_dangling_tails` — terminal branch (no next-sequential integer) renders without join
- `tests/test_branch_geometry.py::test_auto_convergence` — `3a/3b/3c/4` renders `└──┼──┘` join into step 4
- `tests/test_branch_geometry.py::test_cjk_labels_truncated` — labels > 12 cells via `wcwidth` truncated with `…`
- `tests/test_branch_geometry.py::test_label_centered_between_tees` — label position matches `(c_i + c_{i+1}) // 2` rule (PRP §4 geometry sketch)

**GREEN:** Implement `core/branch_geometry.py` per PRP §4 algorithm sketch.

**REFACTOR:** Verify primitive is renderer-agnostic (no phase-box assumptions baked in).

**Exit:** branch geometry tests pass; `dag_graph.py` integration deferred to Phase 4.

### Phase 4 — Renderer integration (`dag_graph.py` `nested` layout)

**RED:**
- `tests/test_dag_graph.py::test_nested_layout_with_branches` — full SOP → ASCII golden file matching the Audit Ledger example
- `tests/test_dag_graph.py::test_nested_layout_branches_plus_loops` — branch + loop in same SOP (no interaction; loops still render as right-side tracks)

**GREEN:** Wire `branch_geometry` primitive into `dag_graph.py`'s phase-box rendering.

**Exit:** nested-layout tests pass; existing v1.7.0 nested-layout tests stay green.

### Phase 5 — Renderer integration (`ascii_graph.py` `flat` layout)

**RED:**
- `tests/test_ascii_graph.py::test_flat_layout_with_branches` — same SOP renders branches via shared primitive without phase-box wrapping
- `tests/test_ascii_graph.py::test_flat_layout_legacy_unchanged` — every existing flat-layout test stays green

**GREEN:** Wire `branch_geometry` primitive into `ascii_graph.py` (without phase-box wrapping). Refactor any duplication between the two layouts into the primitive.

**Exit:** flat-layout tests pass; existing flat-layout tests stay green.

### Phase 6 — CLI surface (`plan_cmd.py` + `--json` shim)

**RED:**
- `tests/test_plan_cmd.py::test_todo_with_substeps` — flat TODO output preserves `3a`/`3b`/`3c` step IDs
- `tests/test_plan_cmd.py::test_json_default_emits_str_step_ids` — `--json` emits `"step": "3a"` (str)
- `tests/test_plan_cmd.py::test_json_legacy_shim_emits_int_with_branch_letter` — `--json --json-legacy-step-ids` emits `{"id": 3, "branch_letter": "a"}`

**GREEN:** Implement `--json-legacy-step-ids` flag in `plan_cmd.py`; update `_classify_step` signature; rekey loop dicts.

**Exit:** all CLI tests pass; full suite green.

### Phase 7 — Mermaid output

**RED:**
- `tests/test_mermaid.py::test_mermaid_with_substeps` — `graph TD\nS2_3a[...]` etc. for sub-stepped SOP

**GREEN:** Update `core/mermaid.py:117` `step_idx` typing; emit valid Mermaid IDs (replacing `.` with `_` already; add sub-step suffix).

**Exit:** Mermaid output tests pass.

### Phase 8 — Documentation + CHANGELOG + version bump

- Add v1.8.0 entry to `src/fx_alfred/CHANGELOG.md`
- Bump `pyproject.toml` version `1.7.1 → 1.8.0`
- Update `CLAUDE.md` with one-paragraph `Workflow branches:` note
- Update `COR-1202` with one-line branch-rendering mention
- Add `wcwidth` to `pyproject.toml` `dependencies`

### Phase 9 — Multi-model code review (COR-1602 + COR-1610)

Codex + Gemini in parallel against the implementation PR diff. Both must score ≥ 9.0 per COR-1611. If FIX, iterate per COR-1600 (Direct Review Loop) up to 3 rounds.

### Phase 10 — Release (FXA-2102)

Per FXA-2102 release SOP: tests + lint + pyright clean; `gh release create v1.8.0`; PyPI publish via GH Actions; `pipx upgrade fx-alfred` to verify.

---

## Test Plan Summary (per COR-1500)

| Phase | New tests | Total at end of phase |
|---|---:|---:|
| Pre-CHG baseline | — | 720 |
| Phase 1 (parser) | ~10 | ~730 |
| Phase 2 (validator) | ~8 | ~738 |
| Phase 3 (geometry) | ~12 | ~750 |
| Phase 4 (nested integration) | ~5 | ~755 |
| Phase 5 (flat integration) | ~5 | ~760 |
| Phase 6 (CLI + JSON shim) | ~6 | ~766 |
| Phase 7 (Mermaid) | ~2 | ~768 |

**Total estimated new tests: ~48.** All existing tests must stay green throughout.

Coverage gates (per COR-1610): every new public function has at least one test; every fixture in `tests/fixtures/branches_*.md` is exercised by at least one assertion; the Migration Impact Table's "test coverage" column is satisfied row-by-row.

---

## Risks & Mitigations

Risks already enumerated in PRP-2225 §"Risks" — not duplicated here. CHG-specific operational risks:

| Risk | Mitigation |
|---|---|
| Phase 5 (flat integration) reveals the shared primitive isn't actually extractable cleanly | Spike Phase 3 first; if primitive shape is wrong, restructure before Phase 4 commits to it |
| LOC estimate (~150-250) blows past during implementation | Each phase has its own commit boundary; if a phase exceeds 2× its budget, pause and flag (don't silently absorb) |
| TDD sequence assumes phases are independent; in practice Phase 1 widening blocks every later phase | Accepted — Phase 1 is the longest and must land first; subsequent phases parallelize less than the table suggests |
| `wcwidth` adds a runtime dep that some downstream environments lack | `wcwidth` is pure-Python with zero deps of its own; pip-installable in any environment that already runs `fx-alfred` |
| Multi-model review divergence on the implementation PR | Hard cap 3 rounds per FXA-2218 budget; if persistent disagreement, escalate per COR-1601 |

---

## Approval

- [ ] Approved by: <reviewer> on <date>

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-27 | Initial CHG drafted as execution plan derived from PRP-2225 (Approved 2026-04-27 via Codex 9.2 + Gemini 9.30 PASS). 10 phases, ~48 new tests, ~150-250 LOC + ~250 LOC tests. | Frank + Claude Code |
