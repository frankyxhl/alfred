# CHG-2157: Extract Duplicated Helpers And Add Gate Detection Tests

**Applies to:** FXA project
**Last updated:** 2026-03-30
**Last reviewed:** 2026-03-30
**Status:** Proposed
**Date:** 2026-03-30
**Requested by:** —
**Priority:** Medium
**Change Type:** Normal

---

## What

**A)** Move `_render_section_content()` and `_validate_spec_status()` from `create_cmd.py` and `update_cmd.py` into `commands/_helpers.py`. Update imports in both files.

**B)** Add test cases for `_parse_steps_for_json()` in `plan_cmd.py` covering gate detection (`[GATE]`, `✓` markers), numbered steps, and empty input.

## Why

**A)** Identical functions duplicated across two modules. Maintenance risk: changes to validation or rendering logic must be applied in two places. Compression as Intelligence principle: same behavior, minimum code.

**B)** Gate detection logic (plan_cmd.py:54-69) has zero test coverage. This logic is user-facing (JSON output for workflow checklists) and should be verified.

Evidence: Evolve-CLI run FXA-2155 — source analysis + coverage report (85% plan_cmd.py).

## Impact Analysis

- **Systems affected:** `commands/_helpers.py`, `commands/create_cmd.py`, `commands/update_cmd.py`, `tests/test_plan_cmd.py`
- **Rollback plan:** `git revert <commit>` — no schema, data, or API change

## Implementation Plan

1. **TDD Red** — Write tests for `_parse_steps_for_json()` gate detection. Confirm tests pass against current code (these test existing untested code, so they should pass immediately — but they verify coverage, not new behavior).
2. **TDD Red** — Write import tests: `from fx_alfred.commands._helpers import render_section_content, validate_spec_status`. Confirm import fails (functions don't exist there yet).
3. **TDD Green** — Add `render_section_content()` and `validate_spec_status()` to `_helpers.py` with required imports.
4. **TDD Green** — Update `create_cmd.py`: remove local definitions, import from `_helpers`.
5. **TDD Green** — Update `update_cmd.py`: remove local definitions, import from `_helpers`.
6. **TDD Refactor** — Run full test suite + ruff. Clean up any unused imports.
7. **Hard gate** — `pytest` 100% pass + `ruff check` 0 issues

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-30 | Initial version | — |
