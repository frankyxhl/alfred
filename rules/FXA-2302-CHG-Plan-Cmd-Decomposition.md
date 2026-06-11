# CHG-2302: Plan Cmd Decomposition

**Applies to:** FXA project
**Last updated:** 2026-06-11
**Last reviewed:** 2026-06-11
**Status:** In Progress
**Date:** 2026-06-11
**Requested by:** Frank Xu (session review finding 2026-06-10; final backlog item)
**Priority:** Medium
**Change Type:** Normal
**Targets:** src/fx_alfred/commands/plan_cmd.py; tests/test_architecture.py

---

## What

Decompose `plan_cmd.py`'s 376-line main function into named single-purpose module-level helpers, and merge the near-duplicate todo builders onto one classification path. Pure refactor — zero observable behavior change.

1. **Todo-builder merge:** `_build_todo_items` (48 lines) and `_build_todo_json` (78 lines) share extraction → fallback handling → loop-map building → per-step classification verbatim, differing only in final rendering. New `_classify_todo_entries(phase_num, body, loops) -> list[_TodoEntry]` (frozen dataclass: dotted index, text, gate, loop signatures) becomes the single classification source; both builders shrink to thin renderers over it. Fallback entries (no Steps section / no parsed steps) take the uniform path — `_apply_text_markers` is a no-op for unmarked entries. Public names and signatures unchanged.
2. **Main-function decomposition** along its 8 natural sections, each a module-level function with explicit parameters (no closures): `_validate_option_coupling` (--graph-format/--graph-layout/--with-skills coupling), `_resolve_sop_ids` (--task auto-composition + CompositionError boundary + usage checks), `_collect_phase_info` (first-pass parse loop) with `_enforce_branches_gate` split out (the 35-line FXA-2226 gate block), `_validate_composition` (signature validation + composition edges), `_validate_cross_sop_loops` (FXA-2218 D4 back-edge checks), `_emit_todo_text`, `_emit_json_output`, `_emit_phased_text`. `plan_cmd()` becomes ≤ ~80 lines of orchestration.
3. **Structure guard** (tests/test_architecture.py): AST-based assertion that no function in `commands/` exceeds 150 lines — operationalizes this CHG so the grab-bag cannot silently regrow (376-line precedent; current second-largest is 99).


## Why

The 2026-06-10 review's last open finding: plan_cmd.py at 918 lines with a 376-line main function of 3–4-level nested mode branching and two near-duplicate builders was the repo's largest maintenance liability — every plan feature (loops, branches, graphs, skills, provenance) has been layering into one function. Eight PRs of this cleanup cycle have touched it; each was harder to review than necessary because diffs land inside a monolith.


## Refactor Contract

Zero behavior change. **The existing suite is the characterization contract**: 999 tests including 100+ plan-surface tests (text/json/todo/graph/human modes, loops, branches, provenance, skills) must pass **unmodified** — same discipline as FXA-2295/2299. No new behavior exists to RED-test; the new structure guard is the only test addition.


## Out of Scope

- Moving anything to `core/` (e.g. the D4 loop validation) — core API changes deserve their own focused CHG (FXA-2295 precedent).
- Behavior changes of any kind, including output ordering, exit codes, warning text.
- Splitting plan_cmd.py into a package.
- Decomposing the three other oversized command functions (create_cmd 230 / update_cmd 283 / validate_cmd 325 lines) — grandfathered in the structure guard as a RATCHET (may shrink, may not grow; new functions get the 150 cap); recorded follow-up work.
- The renderer-readiness gate's logic (CHG-2227 owns its lifecycle; it only moves into a named function verbatim).


## Acceptance Criteria

- A1: `plan_cmd()` ≤ 80 lines; no function in commands/ > 150 lines (guard-enforced); todo builders share one classification path (duplication eliminated).
- A2: Full suite passes with zero test modifications.
- A3: Byte-identical CLI output spot-checks: `af plan COR-1612`, `af plan --task` zero-match (exit 2), `af plan COR-1612 --todo`, `--json`, `--json --todo`, `--graph` — captured before/after and diffed.
- A4: Full gates: pytest, ruff check, ruff format --check, pyright, `af validate`.


## Implementation Plan

1. Capture before-outputs for A3 (golden files in /tmp).
2. Merge todo builders via `_TodoEntry` + `_classify_todo_entries`.
3. Extract the 8 main-body sections; `plan_cmd()` becomes orchestration.
4. Add the function-length structure guard (RED against pre-refactor code verified conceptually — 376 > 150; GREEN after).
5. Diff before/after outputs (A3); run full gates (A2/A4).
6. Trinity triad review (glm, deepseek, minimax), COR-1610, all ≥ 9.0; fix convergent findings.
7. PR per COR-1505.

---

## Change History

| Date       | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | By               |
|------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------|
| 2026-06-11 | Initial version — decompose plan_cmd main function; merge duplicate todo builders; function-length guard                                                                                                                                                                                                                                                                                                                                                                                                                                           | Claude (Fable 5) |
| 2026-06-11 | Todo-builder merge landed (commit 1): _TodoEntry + _classify_todo_entries; 999 unmodified-green; 7 golden outputs byte-identical. Decomposition landed (commit 2): plan_cmd 376 → 76 lines, 8 named sections, largest function 108; golden outputs byte-identical again. Structure guard initially swept all commands/ and tripped on three pre-existing oversized functions (create 230 / update 283 / validate 325) — converted to a ratchet with grandfathered caps (shrink-only) rather than scope-creeping their decomposition into this CHG. | Claude (Fable 5) |
