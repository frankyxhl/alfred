# CHG-2326: Loop Declaration Regression Guard

**Applies to:** FXA project
**Last updated:** 2026-08-12
**Last reviewed:** 2026-08-12
**Status:** Completed
**Date:** 2026-08-12
**Requested by:** Frank Xu (session request: add the regression guard test for the COR-1005 retrofit campaign)
**Priority:** Medium
**Change Type:** Normal
**Targets:** tests/test_bundled_loop_declarations.py (new)

---

## What

One data-driven test module pinning the outcome of the COR-1005 retrofit
campaign (PRs #320–#323) for all eight loop-declaring bundled docs:

- **Loop signatures, in declaration order** — `(id, from, to, max_iterations)`
  per doc. Order is load-bearing for COR-1617: `iterate-round` must stay last
  so it survives the `--todo` same-from-step collapse (issue #324).
- **Step extraction** — each doc keeps a parser-visible Steps section whose
  top-level indices are exactly `1..N` (contiguous).
- **Coverage closure** — any bundled doc that starts declaring
  `Workflow loops:` without being pinned here fails CI, so the table cannot
  silently rot.

Pattern follows `tests/test_cor1402_literal_drift.py` (per-doc drift guard);
marker `docs` per the existing test-marker governance.

## Why

The 1500-test engine suite asserts nothing about specific bundled documents'
loop structure. Both extraction defects fixed during the campaign — COR-1617's
fenced list (zero steps extracted) and COR-1802's phantom sub-list steps —
shipped unnoticed precisely because no test would fail. A re-fenced list, a
heading rename back to `### Step N —`, a budget edit, or a loop reorder in
COR-1617 would today regress silently; with this guard each fails the first CI
run.

## Impact Analysis

- **Systems affected:** tests only (one new file, 17 tests). No runtime code,
  no docs content.
- **Consumers:** future doc PRs touching loop declarations must update the
  expectation table — that is the point (a conscious, reviewed change).
- **Rollback plan:** delete the test file, set this CHG to Rolled Back,
  re-run `af index`.

## Implementation Plan

1. Author `tests/test_bundled_loop_declarations.py` with the expectation table
   for the eight docs; non-COR-format bundled files (INIT.md) are skipped in
   the coverage sweep.
2. Validate: new module 17/17, full `make check` green (1523 passed).
3. PR; COR-1615 bot loop to merge-ready.

---

## Change History

| Date       | Change          | By          |
|------------|-----------------|-------------|
| 2026-08-12 | Initial version | Claude Code |
| 2026-08-12 | Implemented: 17 guard tests green, full suite 1523 passed | Claude Code |
