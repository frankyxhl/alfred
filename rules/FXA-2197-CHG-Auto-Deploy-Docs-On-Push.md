# CHG-2197: Auto-Deploy-Docs-On-Push

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

Add `push to main` trigger to `.github/workflows/docs.yml` with path filter, so COR document changes auto-deploy without waiting for a release.

## Why

Currently docs only deploy on release. COR documents change more frequently than releases (e.g., evolve-sop runs, new SOPs). Manual `mkdocs gh-deploy` is needed in between, which is easy to forget.

## Impact Analysis

- **Systems affected:** `.github/workflows/docs.yml` (1 file)
- **Rollback plan:** Revert the trigger change; release-only deploy is restored

## Implementation Plan

1. Add `push` trigger to `.github/workflows/docs.yml` with path filters:
   - `src/fx_alfred/rules/COR-*.md`
   - `mkdocs.yml`
   - `scripts/build_docs.py`
2. Keep existing `release` trigger unchanged
3. Test by pushing a COR doc change to main

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-04 | Initial version | — |
