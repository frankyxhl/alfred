# CHG-2202: Add COR 1612 Respond To PR Review Comments SOP

**Applies to:** FXA project
**Last updated:** 2026-04-05
**Last reviewed:** 2026-04-05
**Status:** In Progress
**Date:** 2026-04-04
**Requested by:** Frank
**Priority:** Medium
**Change Type:** Normal
**Related:** PR #29, COR-1612

---

## What

Add `COR-1612-SOP-Respond-To-PR-Review-Comments.md` to the PKG layer (`src/fx_alfred/rules/`) and register it in the bundled COR document index. The new SOP standardizes how agents fetch PR review feedback from GitHub, classify comments, batch code fixes into one commit, reply with commit references, wait for CI, and avoid self-resolving review threads. This change also adds the corresponding `FXA-2202` entry to the FXA document index.

## Why

PR review handling is currently implicit and inconsistent. Agents can miss review summary comments, fix issues without replying on GitHub, or resolve their own threads without reviewer confirmation. COR-1612 makes the review-response workflow explicit and reusable across COR-1600 through COR-1605.

## Impact Analysis

- **Systems affected:** `src/fx_alfred/rules/COR-1612-SOP-Respond-To-PR-Review-Comments.md`, `src/fx_alfred/rules/COR-0000-REF-Document-Index.md`, `rules/FXA-0000-REF-Document-Index.md`, and this CHG record
- **Rollback plan:** `git revert` the commit(s) that add COR-1612 and the associated index entries

## Implementation Plan

1. Create `src/fx_alfred/rules/COR-1612-SOP-Respond-To-PR-Review-Comments.md` with the standard SOP structure:
   - Fetch inline comments, review summaries, and top-level PR comments
   - Categorize feedback into blocking, advisory, question, and incorrect
   - Batch fixes into one commit, reply with commit references, wait for CI, and leave thread resolution to reviewers
2. Update `src/fx_alfred/rules/COR-0000-REF-Document-Index.md` to add the COR-1612 entry
3. Update `rules/FXA-0000-REF-Document-Index.md` to add the FXA-2202 entry
4. Run `af validate --root .` and relevant tests to confirm the docs are valid and the package still passes its test suite

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-04 | Initial version | — |
| 2026-04-04 | Start implementation: add COR-1612 SOP to PKG layer | Claude Code |
| 2026-04-05 | Fill CHG sections with the actual PR scope and verification plan | Codex |
