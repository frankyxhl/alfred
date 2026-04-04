# CHG-2196: MkDocs-Material-PKG-Documentation-Site

**Applies to:** FXA project
**Last updated:** 2026-04-04
**Last reviewed:** 2026-04-04
**Status:** Proposed
**Date:** 2026-04-04
**Requested by:** —
**Priority:** Medium
**Change Type:** Normal

---

## What

Add a MkDocs Material documentation site for PKG layer COR documents, deployed to `frankyxhl.github.io/fx-alfred` via GitHub Pages. Includes:

1. `mkdocs.yml` configuration with Material theme and search
2. Build script to organize `src/fx_alfred/rules/*.md` (41 COR docs) by type (SOP/REF/ADR) into `docs/`
3. GitHub Actions workflow triggered on release to auto-deploy

## Why

COR documents are growing (41+). `af search` works locally but there's no browsable/searchable web UI for quick reference. A hosted documentation site provides instant full-text search and structured navigation without CLI access.

## Impact Analysis

- **Systems affected:** GitHub Pages (new), GitHub Actions (new workflow `docs.yml`), `pyproject.toml` (new dev dependency `mkdocs-material`), repo root (new `mkdocs.yml`, `scripts/build_docs.py`)
- **Rollback plan:**
  1. Delete `gh-pages` branch: `git push origin --delete gh-pages`
  2. Disable GitHub Pages in repo Settings
  3. Remove files: `.github/workflows/docs.yml`, `mkdocs.yml`, `scripts/build_docs.py`
  4. Remove `.gitignore` entries (`docs/`, `site/`)
  5. Remove `mkdocs-material` from dev dependencies in `pyproject.toml`, regenerate `uv.lock`

## Implementation Plan

1. Add `mkdocs-material` to dev dependencies in `pyproject.toml`, regenerate `uv.lock`
2. Create `scripts/build_docs.py` — filters only `COR-*.md` from `src/fx_alfred/rules/`, cleans `docs/` before copying, copies files flat (no subdirectories) to preserve any future cross-links, generates nav index grouped by type (SOP, REF, ADR, etc.)
3. Create `mkdocs.yml` with Material theme, search plugin, nav structure
4. Create `.github/workflows/docs.yml`:
   - Triggered on release (published)
   - `permissions: contents: write` (required for gh-pages push)
   - Steps: checkout, setup Python 3.12, `pip install -e ".[dev]"`, run build script, `mkdocs gh-deploy --force`
5. Add `docs/` and `site/` to `.gitignore` (both are generated)
6. Enable GitHub Pages in repo Settings → Pages → Source: `Deploy from a branch`, Branch: `gh-pages` / `/ (root)`
7. Test locally: `python scripts/build_docs.py && mkdocs serve`
8. Verify with `mkdocs build --strict` (catch broken links/warnings)

## Scope

| In scope | Out of scope |
|----------|-------------|
| PKG layer COR-* files only | USR layer (`~/.alfred/`) |
| 41 COR documents | PRJ layer (`rules/`), non-COR files (INIT.md etc.) |
| GitHub Actions on release | Manual deploy |
| H1 as-is (`# SOP-1103: ...`) | Custom title rewriting |
| Site URL: `frankyxhl.github.io/fx-alfred` | Custom domain |

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-04 | Initial version | — |
| 2026-04-04 | R2: Fix rollback plan, add workflow details, COR-* filter, site/ gitignore (Codex 8.1, Gemini 7.8) | Claude Code |
| 2026-04-04 | R3: Unify URL to fx-alfred, add GitHub Pages enable step (Codex 8.8, Gemini 9.9) | Claude Code |
| 2026-04-04 | R4: Flat copy to avoid cross-link breakage (Codex 9.9, Gemini 8.8) | Claude Code |
