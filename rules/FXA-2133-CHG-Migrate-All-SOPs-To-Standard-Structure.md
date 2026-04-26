# CHG-2133: Migrate All SOPs To Standard Structure

**Applies to:** FXA project
**Last updated:** 2026-03-20
**Last reviewed:** 2026-03-20
**Status:** Completed
**Date:** 2026-03-20
**Requested by:** Frank
**Priority:** Medium
**Change Type:** Normal
**Related:** FXA-2223, FXA-2131, FXA-2132

---

## What

Backfill required sections (Why, When to Use, When NOT to Use, Examples where needed) to all existing SOP documents across PKG and PRJ layers.

## Why

After FXA-2132 enables section checking, all existing SOPs must comply or `af validate` will report issues.

## Impact Analysis

- **Systems affected:** 30+ SOP files in PKG layer (`fx_alfred/src/fx_alfred/rules/COR-*.md`), PRJ SOPs in `alfred_ops/rules/`
- **Rollback plan:** `git revert` per repo

## Implementation Plan

1. Run `af list --type SOP` to get full inventory
2. For each SOP, add missing required sections (Why, When to Use, When NOT to Use)
3. For complex SOPs (has Prerequisites or > 5 Steps), add Examples if missing
4. Preserve all existing custom sections (place between Steps and Examples)
5. Run `af validate` — expect 0 SOP section issues
6. Commit PKG layer (fx_alfred) + PRJ layer (alfred_ops)

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version | Claude Code |
