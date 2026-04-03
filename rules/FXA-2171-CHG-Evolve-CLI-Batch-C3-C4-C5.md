# CHG-2171: Evolve CLI Batch C3 C4 C5

**Applies to:** FXA project
**Last updated:** 2026-04-01
**Last reviewed:** 2026-04-01
**Status:** Proposed
**Date:** 2026-04-01
**Requested by:** —
**Priority:** Medium
**Change Type:** Normal

---

## What

Three small code quality improvements from Evolve-Run FXA-2167:
- C3: Simplify parser.py HistoryRow redundant branch into single unconditional construction
- C4: Remove dead code guards in fmt_cmd.py (num_cols always 3)
- C5: Add tests for status_cmd empty docs JSON path

PRP: FXA-2170.

## Why

"Compression as Intelligence" (FXA-2146): remove dead/redundant code, close coverage gaps.

## Impact Analysis

- **Systems affected:** `core/parser.py`, `commands/fmt_cmd.py`, `tests/test_status_cmd.py`
- **Rollback plan:** `git revert <commit>`

## Implementation Plan

1. C3: Replace dual-branch HistoryRow parsing with single safe-default construction. Add edge-case test.
2. C4: Remove `while` padding loops and `if num_cols > N` guards. Add assertion test that num_cols is 3.
3. C5: Add tests for empty docs with and without `--json`.
4. Hard gate: pytest 100%, ruff clean.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-01 | Initial version | — |
