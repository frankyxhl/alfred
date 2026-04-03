# CHG-2190: Fix-FXA-2125-Stale-Alfred-Ops-Refs

**Applies to:** FXA project
**Last updated:** 2026-04-04
**Last reviewed:** 2026-04-04
**Status:** Completed
**Date:** 2026-04-04
**Requested by:** —
**Priority:** Medium
**Change Type:** Normal

---

## What

Remove two stale references in FXA-2125 (Workflow Routing PRJ) left from the alfred_ops merge (FXA-2186):
1. Decision tree item 9 referencing deprecated FXA-2127 (Commit Alfred Ops)
2. Golden rule claiming "no remote (local git only)" when fx_alfred has a GitHub remote

## Why

FXA-2186 step 10 explicitly required updating FXA-2125 to remove FXA-2127 references. This was not completed. The routing doc currently sends users to a deprecated SOP and contains a factually incorrect golden rule.

## Impact Analysis

- **Systems affected:** FXA-2125 (Workflow Routing PRJ) — document content only
- **Rollback plan:** `git revert` the commit

## Implementation Plan

1. Remove decision tree item 9 ("End of session? → FXA-2127") from the `## Project Decision Tree` code block in FXA-2125
2. Replace golden rule `fx_alfred: Documents live in rules/ (PRJ layer), document changes, no remote (local git only)` with `fx_alfred: Documents live in rules/ (PRJ layer), document changes committed with code`
3. Run `af validate` — must pass with 0 issues on FXA-2125

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-04 | Initial version | — |
