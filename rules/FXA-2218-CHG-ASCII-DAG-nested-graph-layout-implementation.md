# CHG-2218: ASCII DAG nested graph layout implementation

**Applies to:** FXA project
**Last updated:** 2026-04-19
**Last reviewed:** 2026-04-19
**Status:** Completed
**Date:** 2026-04-19
**Requested by:** Frank (manually-driven PRP after FXA-2213 Evolve-CLI cold-discarded FXA-2212 at 6.05)
**Priority:** Medium
**Change Type:** Normal
**PRP:** FXA-2217 (approved R3: Codex 9.30 / Gemini 10.0)
**Issue:** #58
**Branch:** `feat/fxa-2212-dag-graph-layout`

---

## What

Implement the ASCII DAG nested graph layout spec'd in FXA-2217. Delivers:

- `Workflow loops.to` metadata widening to accept `int` (intra-SOP, unchanged) or
  `"PREFIX-ACID.step"` (cross-SOP, new) — with parser regex validation, validator gating, and
  output-contract branching.
- Three-layer validation (parser/`af validate`/`af plan`) with 4 new error diagnostics.
- New `core/dag_graph.py` renderer implementing nested phase-box + step-box layout with
  cross-SOP track routing.
- `--graph-layout={nested,flat}` flag on `af plan --graph`, default `nested`.
- `core/mermaid.py` defensive edit: skip cross-SOP loops, emit one-time omission comment.
- Mechanical refactor: `_parse_steps_for_json` moves from `commands/plan_cmd.py:129` to new
  `core/steps.py` module to avoid `commands → commands` imports.

## Why

PRP FXA-2217 was approved at R3 by both trinity reviewers. Implementation is the direct delivery
of that design. No scope change from PRP.

## Impact Analysis

- **Systems affected:** `core/workflow.py`, `core/steps.py` (new), `core/dag_graph.py` (new),
  `core/mermaid.py`, `core/phases.py`, `commands/plan_cmd.py`, `commands/validate_cmd.py`, tests.
- **Public CLI surface:** new `--graph-layout` flag; default-on behaviour change to nested ASCII.
  `--graph-layout=flat` preserves legacy. JSON `loops[].to` is a polymorphic string (adds new
  lexical form `"PREFIX-ACID.step"` alongside existing `"{phase}.{step}"`).
- **Metadata surface:** `Workflow loops.to` accepts `int` (unchanged) or `"PREFIX-ACID.step"` (new).
  All existing SOPs use `int`; zero SOP file edits required.
- **Rollback plan:** revert the entire PR. No data migration; no persisted state changes. The
  `--graph-layout=flat` escape hatch also offers a runtime rollback for anyone pinned on legacy
  output without reverting code.
- **Review gate:** COR-1602 strict — both Codex and Gemini must score ≥ 9.0 on COR-1610 rubric
  against the full diff.
- **Hard gate:** `pytest -q` passes all, `ruff check .` clean, `ruff format --check .` clean,
  `pyright src/` 0 errors/warnings, `af validate` 0 issues.

## Implementation Plan

Eight ordered commits, each independently green on pytest. The commit order keeps the type
widening contained to isolated commits so any reviewer can bisect cleanly.

### Commit 1 — `refactor: extract _parse_steps_for_json to core/steps.py`

Mechanical. Move `_parse_steps_for_json` from `commands/plan_cmd.py:129` into a new module
`src/fx_alfred/core/steps.py`. Re-export from `plan_cmd.py` via `from fx_alfred.core.steps
import _parse_steps_for_json` so existing call sites continue unchanged. Zero behaviour change.

### Commit 2 — `feat: widen LoopSignature.to_step for cross-SOP references`

Core metadata change:

- `core/workflow.py` — add module-level `CROSS_SOP_REF` regex constant.
- `core/workflow.py:192` — `LoopSignature.to_step: int | str`.
- `core/workflow.py` — add `LoopSignature.is_cross_sop()` and `cross_sop_target()` methods.
- `core/workflow.py:263-266` — loosen `to_step` int guard in `parse_workflow_loops`; reject quoted
  digit strings (`"27"`) and strings that don't match `CROSS_SOP_REF`.
- `core/workflow.py:315-380` — gate `validate_loops` intra-SOP membership + back-edge checks on
  `isinstance(loop.to_step, int)`.
- `core/phases.py:28-43` — widen documentation-only `LoopDict.to_step` to `int | str` + docstring
  note.

New tests: `tests/test_workflow.py` covering each new parser branch, each new validator gate,
and the `CROSS_SOP_REF` regex edge cases (valid, malformed prefix, malformed ACID, quoted
digits, missing step).

### Commit 3 — `feat: af validate cross-SOP reference pass (D2/D3)`

- `commands/validate_cmd.py` — add post-scan cross-reference pass that iterates every SOP's
  cross-SOP loops, resolves `(prefix, acid)` against the corpus scan, and checks step index
  range via `core/steps.py::_parse_steps_for_json`.
- New diagnostics emitted as issues on the source SOP.

New tests: `tests/test_validate_cmd.py` covering D2 (target SOP missing) and D3 (step index out
of range) happy/error paths.

### Commit 4 — `feat: af plan cross-SOP runtime checks + output-contract fixes (D4)`

- `commands/plan_cmd.py` — after compose, enforce (a) target SOP in composed plan (b) target
  SOP precedes source in composition order.
- `commands/plan_cmd.py:249-250` — branch the human TODO text interpolation on
  `isinstance(loop_from_sig.to_step, int)`.
- `commands/plan_cmd.py:279, :343` — filter `loop_to_steps` dict comprehensions:
  `if isinstance(loop.to_step, int)` to preserve the `dict[int, LoopSignature]` contract at
  line 201.
- `commands/plan_cmd.py:651-657` — branch JSON `loops[].to` emission on the same isinstance.

New tests: D4 runtime errors + human TODO suffix + JSON loops array for cross-SOP cases.

### Commit 5 — `feat: mermaid skip cross-SOP loops with omission comment`

- `core/mermaid.py:131-136` — add `if lp.is_cross_sop(): continue` before `_node_id` call.
- `core/mermaid.py` — track whether any cross-SOP loop was encountered per render; emit exactly
  one `%% (cross-SOP loops omitted — Mermaid layout is ASCII-only in this release)` comment
  immediately before the back-edges block if so.

New tests: `tests/test_mermaid.py` confirming (a) cross-SOP loop skipped, (b) omission comment
emitted exactly once per render (not per loop), (c) intra-SOP loops still render unchanged.

### Commit 6 — `feat: core/dag_graph.py ASCII DAG renderer (new module)`

Largest piece. New `core/dag_graph.py`:

- `render_dag(phases, provenance_map) -> str` — top-level entry.
- `_render_phase(phase, cross_sop_targets) -> list[str]` — nested phase box with inner step
  boxes.
- `_allocate_track_columns(loops) -> dict[loop_id, col]` — non-overlapping loops share columns.
- `_draw_cross_sop_track(lines, source_row, target_row, col) -> None` — track extending across
  phase boundaries.
- Reused helpers from `core/ascii_graph.py`: `_visual_width`, `_pad_visual`, `_truncate_visual`.

New tests: `tests/test_dag_graph.py` with snapshot coverage for single-SOP linear, two-SOP with
intra-SOP loop, two-SOP with cross-SOP loop, multi-loop column allocation, narrow-terminal
degradation to inline fallback.

### Commit 7 — `feat: --graph-layout flag + dispatch; route flat snapshots`

- `commands/plan_cmd.py` — add `--graph-layout` Click option; dispatch to `render_dag` or
  `render_ascii` based on flag.
- `tests/test_ascii_graph.py` — keep as-is (but every test that exercises the graph gets
  `--graph-layout=flat` to preserve today's output as the legacy baseline).
- Or rename to `tests/test_ascii_graph_flat.py` — decide during implementation based on which is
  less churn.

### Commit 8 — `test: regenerate nested-layout snapshots`

Run the full `pytest -q` suite with `--graph-layout=nested` default active. Any snapshot that
now fails gets regenerated, but each diff is **individually inspected** against the golden-case
checklist from PRP section "Snapshot regeneration protocol":

1. Outer phase-box borders intact?
2. Inner step-boxes aligned?
3. Intra-SOP tracks render at correct column?
4. Cross-SOP tracks (if any) leave the right phase-box and re-enter at correct row?
5. No trailing whitespace drift?
6. Visual width within the assumed terminal budget?

Trinity code review in Step 9 includes explicit sign-off on snapshot regeneration.

### Commit 9 — `docs: update CHANGELOG for v1.7.0 / v1.6.3`

Defer version bump to the release PR following this merge (per FXA-2102). This commit only adds
an `## Unreleased` entry in `src/fx_alfred/CHANGELOG.md` summarising the feature + behaviour
change + escape hatch.

### Review gate (after Commit 9)

- Hard gate: `pytest -q`, `ruff check .`, `ruff format --check .`, `pyright src/`, `af validate`
- Trinity code review: Codex + Gemini parallel on full diff via COR-1602 strict (both ≥ 9.0 on
  COR-1610)

### Open PR + CI loop

Per FXA-2149 Phase 7 pattern (though this is a feature PRP, not evolve): push branch, open PR
referencing #58, monitor CI + automated reviewers up to 3 iterations.

---

## Change History

| Date       | Change                                                 | By             |
|------------|--------------------------------------------------------|----------------|
| 2026-04-19 | Initial version | — |
| 2026-04-19 | Fill from approved PRP FXA-2217 (R3 9.30 / 10.0 PASS) | Frank + Claude |
| 2026-04-19 | Shipped in v1.7.0 (PR #59 → PR #60 release → PyPI 2026-04-19) | Frank + Claude |
