# CHG-2298: CI Python Matrix And Pyright Gate

**Applies to:** FXA project
**Last updated:** 2026-06-11
**Last reviewed:** 2026-06-11
**Status:** In Progress
**Date:** 2026-06-11
**Requested by:** Frank Xu (session review finding 2026-06-10; follow-up batch 2026-06-11)
**Priority:** Medium
**Change Type:** Normal
**Targets:** .github/workflows/ci.yml

---

## What

Close the three CI gaps found in the 2026-06-10 review:

1. **Python version matrix:** `pyproject.toml` declares `requires-python = ">=3.10"` but CI tests only 3.12. New matrix: `['3.10', '3.12', '3.14']` — declared minimum, previous pin, and the version the maintainer develops on locally (3.14.5). `fail-fast: false` so one version's failure still reports the others.
2. **pyright gate:** `make typecheck` exists and `pyright src/` is clean (0 errors), but CI never runs it — the clean state can silently regress. Added as a CI step (pyright ships in the `dev` extra; `pyrightconfig.json` pins `pythonVersion: "3.10"`, so type-checking enforces min-version semantics regardless of host interpreter).
3. **format gate:** `make lint` runs both `ruff check` and `ruff format --check`, but CI only ran `ruff check` — an unformatted file could merge green. Added `ruff format --check .`.


## Why

The review flagged: "CI 只测 Python 3.12（声明支持 3.10+）；pyright 在 Makefile 里有但 CI 不跑". The 3.10 claim was never exercised anywhere — verified for real before this change: a fresh uv-managed Python 3.10.20 venv runs the full suite green (979 passed, 2 skipped — the skips are `build`-module-not-installed, identical to current CI behavior, not version-related). The pyright and format gates exist in the Makefile contract but were unenforced in CI; both are clean today, and gates are cheapest to add while they pass.


## Out of Scope

- Branch-protection / required-check configuration (repo has none — verified via API 404 — so matrix check renaming `test` → `test (3.10)` etc. breaks nothing).
- Adding `build` to dev extras to un-skip the two packaging tests (pre-existing, identical before/after).
- Caching/pip-speedup optimizations for the now-3x job (suite runs ~4s; install dominates but stays acceptable).
- docs.yml / publish.yml workflows.
- Upper-bounding `requires-python` in pyproject.


## Acceptance Criteria

- A1: CI workflow defines `strategy.matrix.python-version: ['3.10', '3.12', '3.14']` with `fail-fast: false`, and steps run ruff check, ruff format --check, pyright src/, and the existing coverage-gated pytest, in that order.
- A2: Local proxy verification: full suite green on a real Python 3.10 environment (executed: 979 passed, 2 skipped on 3.10.20); `pyright src/` and `ruff format --check .` clean on the dev machine.
- A3: The PR's own CI run is green on all three matrix versions (the workflow exercising itself is the real test).
- A4: Full local gates: pytest, ruff check, ruff format --check, pyright, `af validate`.


## Implementation Plan

1. Edit `.github/workflows/ci.yml`: add matrix + fail-fast false; add format and pyright steps.
2. Verify A2 locally (3.10 venv via uv; gates on dev machine).
3. Trinity triad review (glm, deepseek, minimax), COR-1610, all ≥ 9.0; fix convergent findings.
4. PR per COR-1505; A3 confirmed by the PR's checks before merge.

---

## Change History

| Date       | Change                                                                                      | By               |
|------------|---------------------------------------------------------------------------------------------|------------------|
| 2026-06-11 | Initial version — CI matrix (3.10/3.12/3.14) + pyright + format gates per 2026-06-10 review | Claude (Fable 5) |
