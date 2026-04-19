# CHG-2215: Bundle N2 N3 plan-cmd parser edge tests

**Applies to:** FXA project
**Last updated:** 2026-04-19
**Last reviewed:** 2026-04-19
**Status:** Completed
**Date:** 2026-04-19
**Requested by:** Frank (FXA-2149 automated evolve-CLI run FXA-2213)
**Priority:** Medium
**Change Type:** Normal
**PRP:** FXA-2214 (approved R2: Codex 9.8 / Gemini 9.9)

---

## What

Add two narrow tests (no production code change) that close edge-path coverage gaps identified
by FXA-2213:

1. `tests/test_plan_cmd.py::test_plan_todo_raw_section_text_fallback` — asserts that when a SOP's
   `## Steps` section has prose but no numbered items, `af plan <ACID> --todo` emits the raw
   section text attached to the `{phase}.1 [{sop_id}] ...` line. Closes `plan_cmd.py:276`.
2. `tests/test_parser.py::test_parse_metadata_change_history_heading_without_table` — unit test
   of `parse_metadata` with a document that has `## Change History` heading but no `|---|---|---|`
   separator. Asserts `history_header == ""`, `history_rows == []`, and the raw text lands in
   `body`. Closes `parser.py:194`.

C4 (the third candidate from FXA-2213's evaluator output) was dropped during PRP R1 review after
both reviewers caught that the proposed `area = str(area)` fix was empirically broken and any
correct repair fell outside evolve scope. See FXA-2214 / FXA-2213 for the full trail.

## Why

Automated evolve-CLI output per FXA-2149 run FXA-2213. Each test pins observable behaviour at a
documented edge — one for the CLI `--todo` output path, one for the parser's document contract.
Without these, a silent regression (e.g. refactor that drops the fallback and crashes instead,
or changes the empty-history sentinel) would escape detection. PRP FXA-2214 documents problem,
solution, and risks in full.

## Impact Analysis

- **Systems affected:** test suite only (no production code changes).
- **Public CLI surface:** unchanged.
- **Production source:** unchanged.
- **Rollback plan:** revert the two test additions; no further cleanup needed.
- **Review gate:** COR-1602 strict — both Codex and Gemini must score ≥ 9.0 on COR-1610 rubric.
- **Hard gate:** `pytest` 100% pass + `ruff check` 0 issues.

## Implementation Plan

### Step 1 — TDD Red: mutation verification per test

Since both tests target code that is currently correct, standard Red is vacuous. Verify each test
genuinely exercises the target path by mutation:

| Test | Mutation applied in source | Expected Red |
|------|----------------------------|--------------|
| plan-cmd raw-section fallback | `plan_cmd.py:276` — change `steps_section.strip()` to `"MUTATED"` | test asserts "TODO: fill in…" present, mutation makes it fail |
| parser no-table fallback      | `parser.py:192` — change `if table_header_end is None:` to `if False:` | test asserts `history_header == ""`, mutation makes it fail (parser takes the other branch and populates history_header) |

Mutation runs are manual (revert before commit). Record each Red → Green cycle in the run log
FXA-2213.

### Step 2 — TDD Green: implement both tests

Test implementations follow the PRP spec exactly:

- **Test 1:** build a tmp `rules/` with a minimal-valid SOP whose `## Steps` section contains
  `TODO: fill in the numbered steps.` (no `\d+. ` items). Invoke
  `af plan TST-2100 --todo --root <tmp>` via `CliRunner`; assert `exit_code == 0` and the
  output contains `[TST-2100] TODO: fill in the numbered steps.` (on a single TODO line).
- **Test 2:** call `parse_metadata(content)` directly where `content` has `## Change History`
  heading but no `|---|---|---|` separator line. Assert `parsed.history_header == ""`,
  `parsed.history_rows == []`, and `"Change History" in parsed.body`.

### Step 3 — TDD Refactor: none needed

No refactor step — the tests are additive and minimal.

### Step 4 — Hard gate

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
```

Both must exit 0. Coverage for the two target modules must strictly improve:
- `plan_cmd.py` — line 276 covered
- `parser.py` — line 194 covered

### Step 5 — Trinity code review (COR-1610)

Dispatch Codex + Gemini in parallel on the CHG implementation diff. Both must score ≥ 9.0.

### Step 6 — Commit + push + PR

Single commit "evolve: close two edge-path coverage gaps with tests" referencing issue #54,
PRP FXA-2214, CHG FXA-2215, run log FXA-2213.

---

## Change History

| Date       | Change                                                                       | By             |
|------------|------------------------------------------------------------------------------|----------------|
| 2026-04-19 | Initial version | — |
| 2026-04-19 | Fill What / Why / Impact / Plan from approved PRP FXA-2214 (R2 9.8/9.9 PASS) | Frank + Claude |
| 2026-04-19 | Shipped in v1.6.2 (PR #55 → PyPI 2026-04-19) | Frank + Claude |
