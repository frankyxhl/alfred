# CHG-2331: Explicit Project Registration And Worktree Pruning

**Applies to:** FXA project
**Last updated:** 2026-10-02
**Last reviewed:** 2026-10-02
**Status:** Approved
**Date:** 2026-10-02
**Requested by:** Frank Xu
**Priority:** Medium (risk: Low — removes read-path writes and sharpens registry cleanup)
**Change Type:** Normal

---

## What

Refine the FXA-2330 Project SOP Registry so registration is explicit and
worktree roots do not enter the machine-wide catalog.

- Remove implicit registration from `af guide`, `af list`, `af read`, and
  `af status`.
- Keep `af register` as the sole registration entry point.
- Refuse registration when the target root's `.git` is a regular file, and
  direct the user to the main repository.
- Extend `af projects --prune` to remove linked-worktree roots as well as
  dead roots, report the removed count, and emit only surviving rows from
  `af projects --json`.

## Why

Read commands must not create or rewrite machine-level state. A linked
worktree is a checkout of one repository rather than a separate project;
cataloging it duplicates the repository's SOP map. Explicit registration and
worktree-aware pruning keep the registry deterministic and small.

## Impact Analysis

- **Systems affected:** `fx_alfred.commands`, `fx_alfred.core.registry`,
  and local Alfred documentation.
- **Rollback plan:** restore implicit registry maintenance and the previous
  directory-only pruning predicate from the pre-change commit.
- **Compatibility:** existing explicit registrations remain readable. Reads
  no longer refresh document counts or last-seen dates; rerun `af register`
  when those values should be refreshed.

## Implementation Plan

1. Delete the read-command registry trigger and its per-command rescans.
2. Add the `.git`-file worktree guard to `af register`.
3. Classify linked-worktree roots during registry pruning.
4. Cover behavior with `tests/test_project_registry_scenarios.py` and `tests/test_registry.py`.

---

## Change History

| Date       | Change                             | By     |
|------------|------------------------------------|--------|
| 2026-10-02 | Initial implementation | alfred |
