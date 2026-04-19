# CHG-2211: Close three edge-arm coverage gaps with tests

**Applies to:** FXA project
**Last updated:** 2026-04-19
**Last reviewed:** 2026-04-19
**Status:** Proposed
**Date:** 2026-04-19
**Requested by:** Frank (FXA-2149 automated evolve-CLI run FXA-2209)
**Priority:** Medium
**Change Type:** Normal
**PRP:** FXA-2210 (approved R3: Codex 9.9 / Gemini 10.0)

---

## What

Add three narrow tests (no production code changes) that close the highest-confidence coverage gaps
identified by FXA-2209:

1. `tests/test_list_cmd.py::test_list_json_empty_result` — asserts `af list --json` with no-match
   filter outputs exactly `[]\n` and JSON-parses to `[]`.
2. `tests/test_helpers.py::test_atomic_write_double_failure_preserves_original_error` — patches
   both `os.replace` and `os.unlink` to raise; asserts the original `os.replace` exception propagates
   (not the unlink one). Closes `_helpers.py:86-87`.
3. `tests/test_validate_cmd.py::test_validate_history_header_early_return_arms` — unit tests the
   `_validate_history_header` helper directly on `""` (hits line 60) and on a multi-line input with
   no `|` line (hits line 70). Asserts exact diagnostic strings.

## Why

Automated evolve-CLI output per FXA-2149 run FXA-2209. Each test locks either a public contract
(Gap 1 — JSON shape for consumers), a failure-path invariant (Gap 2 — which error an operator sees
during atomic-write double-failure), or exact user-facing diagnostic strings (Gap 3). PRP FXA-2210
documents problem, solution, and risks in full.

## Impact Analysis

- **Systems affected:** test suite only (no production code changes).
- **Public CLI surface:** unchanged (no command / flag / output / JSON shape mutation).
- **Production source:** unchanged (`src/fx_alfred/**/*.py` not modified).
- **Rollback plan:** revert the three test additions; no further cleanup needed.
- **Review gate:** COR-1602 strict — both Codex and Gemini must score ≥ 9.0 on COR-1610 rubric.
- **Hard gate:** `pytest` 100% pass + `ruff check` 0 issues.

## Implementation Plan

### Step 1 — TDD Red: mutation verification per test

Since all three tests target code that is currently correct, standard Red is vacuous. Instead, for
each test we verify the test genuinely exercises the target code path by mutation testing:

| Test | Mutation applied in source | Expected Red |
|------|----------------------------|--------------|
| list-cmd JSON empty      | `list_cmd.py:66` — change `click.echo("[]")` to `click.echo("no results")` | test asserts `[]\n`, mutation makes it fail |
| atomic_write double-fail | `_helpers.py:88` — replace `raise` with `pass` (swallow the error entirely) | test asserts `pytest.raises(OSError)`, mutation makes it fail |
| validate history arms    | `validate_cmd.py:60` — return `[]` instead of the diagnostic                | test asserts exact string, mutation makes it fail |

Mutation runs are manual (revert before commit). Record each Red → Green cycle in the run log FXA-2209.

### Step 2 — TDD Green: implement all three tests

Test implementations must follow the PRP spec exactly:
- Test 1: `CliRunner().invoke(cli, ["list", "--json", "--type", "ZZ"], catch_exceptions=False)` with
  `sample_project` fixture, assert `result.output == "[]\n"` and `json.loads(result.output) == []`.
- Test 2: two `unittest.mock.patch` decorators/context managers stacked on `os.replace` and
  `os.unlink`, both raising `OSError` with distinct messages. Assert
  `pytest.raises(OSError, match="replace failed")`.
- Test 3: import `_validate_history_header` from `fx_alfred.commands.validate_cmd` (treat as
  module-level helper), call with `""` and assert
  `== ["Change History table header is missing or incomplete"]`; call with
  `"Trailing text only\nMore text\n"` and assert `== ["Change History table header is missing"]`.

### Step 3 — TDD Refactor: none needed

No refactor step — the tests are additive and minimal.

### Step 4 — Hard gate

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
```

Both must exit 0. Coverage for the three target modules must strictly improve:
- `_helpers.py` — 86–87 covered
- `list_cmd.py` — 66 covered
- `validate_cmd.py` — 60, 70 covered

### Step 5 — Trinity code review (COR-1610)

Dispatch Codex + Gemini in parallel on the CHG implementation diff. Both must score ≥ 9.0.

### Step 6 — Commit + push + PR

Single commit "evolve: close three edge-arm coverage gaps with tests" referencing issue #51,
PRP FXA-2210, CHG FXA-2211, run log FXA-2209.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-19 | Initial version | — |
| 2026-04-19 | Fill What / Why / Impact / Plan from approved PRP FXA-2210 (R3: Codex 9.9 / Gemini 10.0) | Frank + Claude |
