# CHG-2328: Semantic Release Automation

**Applies to:** FXA project
**Last updated:** 2026-08-16
**Last reviewed:** 2026-08-16
**Status:** Proposed
**Date:** 2026-08-16
**Requested by:** Frank Xu (session request: automate releases; borrow fx_bin's cd-release.yml pattern)
**Priority:** Medium
**Change Type:** Normal
**Targets:** .github/workflows/cd-release.yml (new), pyproject.toml, rules/FXA-2102-SOP-Release-To-PyPI.md, src/fx_alfred/CHANGELOG.md, rules/FXA-0000-REF-Document-Index.md

---

## What

Adopt fx_bin's two-stage auto-release shape, adapted for fx-alfred:

1. **New `.github/workflows/cd-release.yml`** — on every push to `main`,
   `python-semantic-release@v9` parses conventional commits, decides the next
   version (feat → minor; fix/perf/docs → patch), bumps
   `pyproject.toml:project.version`, commits `chore(release): ...`, tags
   `v{version}`, and creates the GitHub Release using
   `secrets.SEMANTIC_RELEASE_PAT`. Guards: skip when actor is
   `github-actions[bot]` or the head commit message contains
   `chore(release):` (recursion), plus a `release` concurrency group.
2. **`pyproject.toml` `[tool.semantic_release]`** — version source
   `project.version` (PEP 621, not poetry); `docs` mapped to **patch** because
   bundled SOP documents ship in the wheel (a docs change IS a shippable
   change for this package); changelog generation **disabled** (the action's
   `changelog: false`) — `src/fx_alfred/CHANGELOG.md` stays hand-curated and
   `af changelog` keeps reading it.
3. **Existing `publish.yml` untouched** — the PAT-created GitHub Release
   fires its `release: [published]` trigger, so the tested path (pytest
   cov≥95 / ruff / pyright → build → Trusted Publishing) is reused verbatim.
4. **FXA-2102 SOP updated** — manual steps 1–3 collapse into "merge a
   conventional-commit PR to main"; manual `gh release create` becomes the
   fallback path.

Not borrowed from fx_bin: its changelog auto-generation (conflicts with the
curated narrative CHANGELOG), poetry version plumbing, and the PyPI
existence-check/publish job (publish.yml already covers it).


## Why

FXA-2102 is a 7-step manual procedure (bump, CHANGELOG, README, release
notes, create release, watch CI, verify). fx_bin has run the semantic-release
shape successfully; every fx-alfred commit already follows conventional
format, so version decisions are mechanically derivable. Automation removes
the human-bump errors (stale versions, forgotten tags) and makes "merge to
main" the single release action.


## Impact Analysis

- **Systems affected:** CI only (one new workflow + one pyproject section +
  SOP doc). No `af` runtime code changes.
- **Release cadence:** every merged PR containing feat/fix/perf/docs commits
  produces a release. test/chore/ci/refactor commits do not.
- **One-time operator action:** create a classic PAT with `repo` scope and
  save it as the `SEMANTIC_RELEASE_PAT` repository secret. Without it the
  workflow fails at checkout; the default `GITHUB_TOKEN` cannot be used
  because releases it creates do not trigger `publish.yml`.
- **Branch protection caveat:** semantic-release pushes the version-bump
  commit directly to `main`; if branch protection later forbids direct
  pushes, the PAT owner needs bypass permission.
- **README "NEW in vX" (FXA-2136):** stays a manual, in-PR editorial step;
  no longer blocks the release mechanics.
- **Rollback plan:** delete cd-release.yml, remove the pyproject section,
  revert the FXA-2102 edit, set this CHG to Rolled Back. Manual FXA-2102
  flow keeps working throughout (it is the documented fallback).


## Implementation Plan

1. Add `.github/workflows/cd-release.yml` (adapted from fx_bin, poetry and
   changelog steps removed).
2. Add `[tool.semantic_release]` + parser options to pyproject.toml.
3. Update FXA-2102: automated primary path + manual fallback.
4. CHANGELOG Unreleased entry; validate (pytest, af validate, actionlint if
   available); PR under `ryosaeba1985`; COR-1615 loop to closure.
5. Operator creates `SEMANTIC_RELEASE_PAT`; first real merge validates the
   chain end-to-end.

---

## Change History

| Date       | Change                                                                                                                                                                                                                                                                                                                                                                   | By          |
|------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------|
| 2026-08-16 | Initial version                                                                                                                                                                                                                                                                                                                                                          | Claude Code |
| 2026-08-16 | R1 (codex P2 on PR #329): cd-release.yml gains a pre-tag CHANGELOG promotion step — computes the next version with `semantic-release --noop version --print`, promotes `## Unreleased` to `## v{version} (date)` (skip when empty), commits before semantic-release tags, so wheels ship correct version boundaries and Unreleased no longer accumulates shipped changes | Claude Code |
