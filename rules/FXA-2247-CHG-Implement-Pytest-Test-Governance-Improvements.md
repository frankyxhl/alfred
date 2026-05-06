# CHG-2247: Implement Pytest Test Governance Improvements

**Applies to:** FXA project
**Last updated:** 2026-05-06
**Last reviewed:** 2026-05-06
**Status:** Approved
**Date:** 2026-05-06
**Requested by:** Frank Xu
**Priority:** Medium
**Change Type:** Normal
**Related:** FXA-2244, FXA-2245, FXA-2246, COR-1101, COR-1500, COR-1602, COR-1609, COR-1610
**Tags:** pytest, tests, coverage, ci

---

## What

Implement the three latest pytest-focused Draft PRPs as one coordinated test
governance change:

- **FXA-2244:** define and apply custom pytest markers for test categorization.
- **FXA-2245:** convert repeated assertion families into parametrized pytest
  cases where that improves clarity without hiding scenario-specific setup.
- **FXA-2246:** enforce a pytest coverage threshold in the normal developer and
  CI validation paths.

The target implementation is test/configuration focused. It should not change
runtime CLI behavior except where tests expose an existing defect that must be
fixed under COR-1500.

## Why

The current project test suite is broad, but the test execution contract is
implicit:

- `pyproject.toml` has `testpaths = ["tests"]` but no marker taxonomy or strict
  marker validation.
- CI runs `pytest --tb=short` with no coverage enforcement.
- `pytest-cov` is available only through the `evolve` optional extra, so a
  default `pip install -e '.[dev]'` environment cannot run coverage gates.
- Some tests use repeated assertion patterns where parametrization would make
  intent, failure IDs, and future additions easier to review.

This change makes the suite easier to slice, keeps CI from accepting accidental
coverage regressions, and improves test readability without changing public
product behavior.

## PRP Readout

As of 2026-05-06, the referenced PRPs exist locally but are still Drafts with
placeholder body sections:

| PRP | Title | Status | Readout |
|-----|-------|--------|---------|
| FXA-2244 | Add Custom Pytest Markers for Test Categorization | Draft | Title is actionable; marker taxonomy still needs final confirmation. |
| FXA-2245 | Add Parametrized Tests for Repeated Assertions | Draft | Title is actionable; exact test targets must be discovered during implementation. |
| FXA-2246 | Enforce Pytest Coverage Thresholds | Draft | Title is actionable; threshold must be set from measured baseline and CI cost. |

This CHG is therefore a proposed execution plan based on the latest available
PRP titles, not evidence that those PRPs have completed COR-1602 approval.

## Impact Analysis

- **Systems affected:**
  - `pyproject.toml` pytest configuration and optional dependencies.
  - `.github/workflows/ci.yml` and `.github/workflows/publish.yml` test commands.
  - `uv.lock` if dependency metadata is regenerated.
  - `tests/` marker annotations and selected parametrized test refactors.
  - `README.md` or a new contributor/testing section if marker usage needs a
    durable local reference.
- **Not affected:** packaged runtime modules, CLI commands, bundled COR rules,
  and public command output unless tests reveal an existing bug that requires a
  separate scoped fix.
- **Risk:** coverage enforcement can block unrelated PRs if the threshold is set
  above the real baseline or if CI installs a dev environment without
  `pytest-cov`. Mitigation: measure baseline first, add `pytest-cov` to the
  same dependency path used by CI, and set the initial threshold at or slightly
  below measured current coverage.
- **Rollback plan:** revert the implementation commit, commit range, or merge
  commit that lands this CHG. If rollback is partial, first remove
  coverage-enforcing pytest/CI flags, then remove marker strictness, then revert
  test refactors. Verify rollback with `pip install -e '.[dev]'`,
  `pytest --tb=short`, `ruff check .`, and `af validate --root .`.

## Implementation Plan

1. **Preflight and approval gate**
   - Confirm whether FXA-2244, FXA-2245, and FXA-2246 need PRP body backfill and
     COR-1602 approval before implementation starts.
   - Run the current baseline checks:
     `pytest --tb=short`, `ruff check .`, and `af validate --root .`.
   - Confirm coverage tooling is missing from the default dev path, then decide
     whether to add `pytest-cov` to `dev` or introduce a separate CI extra.

2. **FXA-2244 marker taxonomy**
   - Add pytest marker definitions under `[tool.pytest.ini_options]`.
   - Enable strict marker validation so unknown markers fail fast.
   - Initial taxonomy default:
     - `unit`: pure function/unit tests with no project-level filesystem setup.
     - `cli`: Click `CliRunner` or `af` command surface tests.
     - `integration`: tests that exercise project-root, filesystem, packaging,
       subprocess, or cross-module behavior.
     - `docs`: documentation or bundled-rule rendering/validation tests.
     - `slow`: intentionally slower tests that may be excluded from tight local
       loops.
   - Apply markers at module level where most tests share a category; use
     function-level markers only for mixed modules.

3. **FXA-2245 parametrization pass**
   - Audit repeated assertion families with `rg` and targeted file review.
   - Convert suitable tests to `@pytest.mark.parametrize(..., ids=[...])`.
   - Preserve separate tests where the setup, failure diagnosis, or scenario
     narrative would become less clear after parametrization.
   - Keep refactors behavior-preserving: no production code changes in this
     phase unless an existing test defect is exposed.

4. **FXA-2246 coverage gate**
   - Add `pytest-cov` to the dependency path used by local dev and CI
     verification. Keep `pytest-cov` in the `evolve` extra as well; this CHG
     intentionally accepts duplicate optional-extra membership rather than
     changing the extra dependency model.
   - Measure current coverage with:
     `pytest --cov=fx_alfred --cov-report=term-missing --cov-report=xml --cov-fail-under=0`.
   - Set the initial fail-under threshold to the measured baseline rounded down
     to a stable integer, with a conservative default of **95%** if the measured
     baseline remains at or above historical FXA reports.
   - Update CI and publish workflows to run the same coverage-enforcing command.
     CI should continue running the full test suite by default; marker filters
     are for local quick loops unless a later CHG creates a separate slow-test
     CI lane.
   - Keep local quick-loop guidance available via marker selection, for example
     `pytest -m "not slow" --tb=short`.

5. **Documentation**
   - Add a concise testing section documenting the marker taxonomy, common
     selection commands, and coverage gate command.
   - Mention that unknown markers are rejected by strict marker validation.

6. **Verification**
   - `pytest --tb=short`
   - `pytest -m "not slow" --tb=short`
   - `pytest --cov=fx_alfred --cov-report=term-missing --cov-fail-under=<threshold>`
   - `ruff check .`
   - `pyright src/`
   - `af validate --root .`
   - `git diff --check`

## Acceptance Criteria

- [ ] Pytest marker taxonomy is defined in `pyproject.toml`.
- [ ] Unknown pytest markers fail under the default test configuration.
- [ ] Existing tests are categorized with module-level markers where practical.
- [ ] Repeated assertion families that benefit from table-driven testing are
  converted to parametrized tests with readable IDs.
- [ ] Tests that become less diagnosable when parametrized are left separate and
  not force-converted.
- [ ] `pytest-cov` is available through the same install path used by CI.
- [ ] CI and publish validation fail when coverage drops below the chosen
  threshold.
- [ ] The chosen threshold is justified by a measured baseline recorded in this
  CHG's execution log.
- [ ] `pytest`, coverage pytest, `ruff`, `pyright`, `af validate`, and
  `git diff --check` pass before PR.

## Open Questions / Defaults

- **Can implementation start while all three PRPs are Draft placeholders?**
  Resolved: yes, by Frank's explicit approval on 2026-05-06. This CHG is the
  implementation authority unless a later review requires PRP body backfill.
- **Initial coverage threshold?** Default: measured baseline rounded down, capped
  at a conservative first gate of 95% unless the fresh baseline is lower.
- **Marker granularity?** Default: module-level marker coverage first; avoid
  noisy per-test annotations unless a module is mixed.
- **Dependency path?** Default: add `pytest-cov` to `dev` because CI installs
  `.[dev]`; keep it in `evolve` because the evolve workflow also consumes
  coverage reports.

## Testing / Verification

Pre-implementation:

- [ ] `pytest --tb=short`
- [ ] `ruff check .`
- [ ] `af validate --root .`

Implementation:

- [ ] `pytest --tb=short`
- [ ] `pytest -m "not slow" --tb=short`
- [ ] `pytest --cov=fx_alfred --cov-report=term-missing --cov-fail-under=<threshold>`
- [ ] `ruff check .`
- [ ] `pyright src/`
- [ ] `af validate --root .`
- [ ] `git diff --check`

## Approval

- [x] PRP approval or explicit override recorded.
- [x] CHG reviewed under COR-1609.
- [x] Approved for implementation.

## Execution Log

| Date | Action | Result |
|------|--------|--------|
| 2026-05-06 | Created CHG from FXA-2244/2245/2246 titles. | PRPs are Draft placeholders; CHG remains Proposed pending approval/backfill. |
| 2026-05-06 | Checked local coverage command in existing `.venv`. | `pytest-cov` is not installed in default `.venv`; coverage flags are currently unavailable without dependency-path changes. |
| 2026-05-06 | Trinity CHG review R1 using GLM and DeepSeek under COR-1609. | PASS: GLM 9.1/10, DeepSeek 9.0/10. Folded in low-risk advisories for Related metadata, optional-extra policy, CI marker policy, and rollback wording. |
| 2026-05-06 | Frank approved explicit override and requested PR. | Status moved to Approved; PRP placeholder status remains documented as a known constraint. |

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-06 | Initial version | Codex |
| 2026-05-06 | Marked Approved after Trinity PASS and Frank explicit approval. | Codex |
