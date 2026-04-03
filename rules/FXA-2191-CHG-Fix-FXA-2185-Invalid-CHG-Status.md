# CHG-2191: Fix-FXA-2185-Invalid-CHG-Status

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

Change FXA-2185 Status from "Implemented" to "Completed". "Implemented" is not a valid CHG status per COR-0002.

## Why

`af validate` reports FXA-2185 as invalid. COR-0002 allows CHG statuses: Proposed, Approved, In Progress, Completed, Rolled Back. The change described in FXA-2185 is done, so "Completed" is correct.

## Impact Analysis

- **Systems affected:** FXA-2185 metadata only
- **Rollback plan:** `git revert` the commit

## Implementation Plan

1. Edit FXA-2185 Status field from "Implemented" to "Completed"
2. Run `af validate` — must pass with 0 issues on FXA-2185

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-04 | Initial version | — |
