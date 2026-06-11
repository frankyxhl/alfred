# FXA-2298 Review Pack — CI Python Matrix + Pyright Gate

## Review request

Review this CI-config diff with the COR-1610 rubric pinned below. The unit is the branch diff vs main (one workflow file + CHG doc). Cross-reference pyproject.toml, pyrightconfig.json, and Makefile at HEAD to verify claims.

## What & why

pyproject declares `requires-python = ">=3.10"` but CI tested only 3.12 — the 3.10 claim was never exercised anywhere. `make typecheck` (pyright) and `ruff format --check` exist in the Makefile contract but never ran in CI, so their clean states could silently regress. (2026-06-10 review findings.)

Change to .github/workflows/ci.yml: matrix ['3.10','3.12','3.14'] (declared min / previous pin / maintainer's local 3.14.5), fail-fast: false; adds `ruff format --check .` and `pyright --pythonpath "$(which python)" src/` steps. The --pythonpath flag is load-bearing: pyrightconfig.json resolves third-party packages via the local `.venv`, which does not exist on CI runners — verified locally that the flag correctly resolves against an arbitrary interpreter (0 errors against a real 3.10 env).

Verification executed before this change: fresh uv-managed Python 3.10.20 venv runs the FULL suite green (979 passed, 2 skipped — skips are `build`-module-not-installed, identical to current CI, version-unrelated). Repo has NO branch protection (API 404), so matrix check renaming (`test` → `test (3.10)` etc.) breaks no required checks. The PR's own checks complete the verification (A3).

NOT in scope (do not deduct per COR-1610 rule 4): branch-protection setup; adding `build` to dev extras; pip caching for the 3x matrix; docs.yml/publish.yml; upper-bounding requires-python.

## Pinned rubric — COR-1610 (use EXACTLY these dimensions and weights)

| Dimension | Weight |
|-----------|--------|
| Correctness | 25% |
| Test Coverage | 25% |
| Code Style | 15% |
| Security | 15% |
| Simplicity | 20% |

Rules: deductions cite file:line; BLOCKING vs ADVISORY; no out-of-scope deductions; weighted average rounded to one decimal; >= 9.0 PASS. Recompute arithmetic before printing. Required output: Decision Matrix + weighted average + verdict + findings.

Special attention: (a) any GitHub Actions semantic error in the matrix/steps (expression syntax, quoting of '3.10' vs 3.1 float-trap, fail-fast placement)? (b) is `pyright --pythonpath "$(which python)"` correct on ubuntu runners (which python resolves to the setup-python interpreter)? (c) for Test Coverage, assess the VERIFICATION STRATEGY (local 3.10 proxy + PR-self-exercising CI) since workflow YAML has no unit tests.

## The diff (vs main)

diff --git a/.github/workflows/ci.yml b/.github/workflows/ci.yml
index da4fee2..9aaf5e1 100644
--- a/.github/workflows/ci.yml
+++ b/.github/workflows/ci.yml
@@ -8,11 +8,24 @@ on:
 jobs:
   test:
     runs-on: ubuntu-latest
+    strategy:
+      # Report every version's result even when one fails (CHG-2298).
+      fail-fast: false
+      matrix:
+        # Declared minimum (pyproject requires-python >=3.10), previous
+        # CI pin, and the maintainer's local development version.
+        python-version: ['3.10', '3.12', '3.14']
     steps:
       - uses: actions/checkout@v4
       - uses: actions/setup-python@v5
         with:
-          python-version: '3.12'
+          python-version: ${{ matrix.python-version }}
       - run: pip install -e '.[dev]'
       - run: ruff check .
+      - run: ruff format --check .
+      # pyrightconfig.json pins pythonVersion 3.10, so types are checked
+      # against the minimum supported version on every matrix host.
+      # --pythonpath overrides the config's local-.venv package resolution
+      # (no .venv exists on CI; verified locally against a 3.10 env).
+      - run: pyright --pythonpath "$(which python)" src/
       - run: pytest --tb=short --cov=src/fx_alfred --cov-report=term-missing --cov-fail-under=95
diff --git a/rules/FXA-0000-REF-Document-Index.md b/rules/FXA-0000-REF-Document-Index.md
index e5d426c..63c821e 100644
--- a/rules/FXA-0000-REF-Document-Index.md
+++ b/rules/FXA-0000-REF-Document-Index.md
@@ -208,6 +208,7 @@
 | 2295 | CHG | Compose Domain Exceptions |
 | 2296 | CHG | Validate Unknown Type Warning |
 | 2297 | CHG | CLAUDE Md Refresh And Drift Guard |
+| 2298 | CHG | CI Python Matrix And Pyright Gate |
 
 ---
 
diff --git a/rules/FXA-2298-CHG-CI-Python-Matrix-And-Pyright-Gate.md b/rules/FXA-2298-CHG-CI-Python-Matrix-And-Pyright-Gate.md
new file mode 100644
index 0000000..0d6387b
--- /dev/null
+++ b/rules/FXA-2298-CHG-CI-Python-Matrix-And-Pyright-Gate.md
@@ -0,0 +1,59 @@
+# CHG-2298: CI Python Matrix And Pyright Gate
+
+**Applies to:** FXA project
+**Last updated:** 2026-06-11
+**Last reviewed:** 2026-06-11
+**Status:** In Progress
+**Date:** 2026-06-11
+**Requested by:** Frank Xu (session review finding 2026-06-10; follow-up batch 2026-06-11)
+**Priority:** Medium
+**Change Type:** Normal
+**Targets:** .github/workflows/ci.yml
+
+---
+
+## What
+
+Close the three CI gaps found in the 2026-06-10 review:
+
+1. **Python version matrix:** `pyproject.toml` declares `requires-python = ">=3.10"` but CI tests only 3.12. New matrix: `['3.10', '3.12', '3.14']` — declared minimum, previous pin, and the version the maintainer develops on locally (3.14.5). `fail-fast: false` so one version's failure still reports the others.
+2. **pyright gate:** `make typecheck` exists and `pyright src/` is clean (0 errors), but CI never runs it — the clean state can silently regress. Added as a CI step (pyright ships in the `dev` extra; `pyrightconfig.json` pins `pythonVersion: "3.10"`, so type-checking enforces min-version semantics regardless of host interpreter).
+3. **format gate:** `make lint` runs both `ruff check` and `ruff format --check`, but CI only ran `ruff check` — an unformatted file could merge green. Added `ruff format --check .`.
+
+
+## Why
+
+The review flagged: "CI 只测 Python 3.12（声明支持 3.10+）；pyright 在 Makefile 里有但 CI 不跑". The 3.10 claim was never exercised anywhere — verified for real before this change: a fresh uv-managed Python 3.10.20 venv runs the full suite green (979 passed, 2 skipped — the skips are `build`-module-not-installed, identical to current CI behavior, not version-related). The pyright and format gates exist in the Makefile contract but were unenforced in CI; both are clean today, and gates are cheapest to add while they pass.
+
+
+## Out of Scope
+
+- Branch-protection / required-check configuration (repo has none — verified via API 404 — so matrix check renaming `test` → `test (3.10)` etc. breaks nothing).
+- Adding `build` to dev extras to un-skip the two packaging tests (pre-existing, identical before/after).
+- Caching/pip-speedup optimizations for the now-3x job (suite runs ~4s; install dominates but stays acceptable).
+- docs.yml / publish.yml workflows.
+- Upper-bounding `requires-python` in pyproject.
+
+
+## Acceptance Criteria
+
+- A1: CI workflow defines `strategy.matrix.python-version: ['3.10', '3.12', '3.14']` with `fail-fast: false`, and steps run ruff check, ruff format --check, pyright src/, and the existing coverage-gated pytest, in that order.
+- A2: Local proxy verification: full suite green on a real Python 3.10 environment (executed: 979 passed, 2 skipped on 3.10.20); `pyright src/` and `ruff format --check .` clean on the dev machine.
+- A3: The PR's own CI run is green on all three matrix versions (the workflow exercising itself is the real test).
+- A4: Full local gates: pytest, ruff check, ruff format --check, pyright, `af validate`.
+
+
+## Implementation Plan
+
+1. Edit `.github/workflows/ci.yml`: add matrix + fail-fast false; add format and pyright steps.
+2. Verify A2 locally (3.10 venv via uv; gates on dev machine).
+3. Trinity triad review (glm, deepseek, minimax), COR-1610, all ≥ 9.0; fix convergent findings.
+4. PR per COR-1505; A3 confirmed by the PR's checks before merge.
+
+---
+
+## Change History
+
+| Date       | Change                                                                                      | By               |
+|------------|---------------------------------------------------------------------------------------------|------------------|
+| 2026-06-11 | Initial version — CI matrix (3.10/3.12/3.14) + pyright + format gates per 2026-06-10 review | Claude (Fable 5) |
