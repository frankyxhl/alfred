# CHG-2123: Migrate Existing Documents To Format Contract

**Applies to:** FXA project
**Last updated:** 2026-03-20
**Last reviewed:** 2026-03-20
**Status:** Completed
**Date:** 2026-03-20
**Requested by:** Frank
**Priority:** Medium
**Change Type:** Normal
**Related:** FXA-2116, FXA-2119, FXA-2120, FXA-2122

---

## What

Migrate all existing non-compliant documents in `alfred_ops/rules/` and `~/.alfred/` to comply with the Document Format Contract (COR-0002). Five sub-tasks:

1. **Normalize metadata prefix** — Convert `- **Key:** Value` to `**Key:** Value` (FXA-2101, FXA-2103, others)
2. **Clean Status annotations** — Remove parenthetical text (e.g., FXA-2104: `Draft (revised after COR-1602 review)` → `Draft`)
3. **Add missing Status fields** — Defaults per type:
   - SOP → `Active`
   - PRP → `Draft`
   - CHG → infer from document content (e.g., has Execution Log with results → `Completed`; otherwise `Proposed`)
   - ADR → manually review each: check if decision was already accepted/superseded (do not blanket-assign `Proposed`)
   - PLN → infer from content (has completed milestones → `Completed`; active work → `Active`; otherwise `Draft`)
   - INC → infer from content (has Resolution filled → `Resolved`; otherwise `Open`)
   - REF → `Active`
4. **Add missing required fields** — Backfill `Applies to`, `Last updated`, `Last reviewed` on CHG/INC/PLN documents that lack them
5. **Normalize Date field** — Existing CHG/INC documents that have `Date` but not `Last updated`: add `Last updated` using the most recent date from Change History table; add `Last reviewed` with same date

### Backfill rules

| Field | Default value |
|-------|--------------|
| `Applies to` | `<PREFIX> project` (e.g., `FXA project`) |
| `Last updated` | Most recent date from Change History table, or file's `Date` field, or today's date as last resort |
| `Last reviewed` | Same as `Last updated` |

**Fallback rule:** If a document has neither a Change History table nor a `Date` field, use today's date (2026-03-20) for both `Last updated` and `Last reviewed`.

### Acceptance criteria

`af validate --root /Users/frank/Projects/alfred/alfred_ops` returns 0 issues across all layers (PRJ + USR). CHG-2122 must be implemented first so ACID=0000 exemption is active.

## Why

After CHG-2122 enhances `af validate` with per-type rules, all existing non-compliant documents will fail validation. This migration brings the entire document corpus to zero issues.

## Impact Analysis

- **Systems affected:** `alfred_ops/rules/` (~14 documents), `~/.alfred/` (ALF documents)
- **Rollback plan:**
  - `alfred_ops/rules/` (git-tracked): Create backup branch before migration (`git checkout -b backup/pre-format-contract`), then `git revert` if needed
  - `~/.alfred/` (not git-tracked): Create a tarball backup before migration (`tar czf ~/.alfred-backup-pre-format-contract.tar.gz ~/.alfred/`)

## Implementation Plan

1. Create backup branch: `git checkout -b backup/pre-format-contract`
2. Switch back to working branch
3. Run `af validate` to get the full issue list
4. Fix each category (prefix normalization → status cleanup → missing Status → missing fields → Date normalization)
5. Use `af update --field` where possible, manual edits where needed
6. Run `af validate` — expect 0 issues
7. Commit

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version | Claude Code |
| 2026-03-20 | Round 1 revision: added compliant metadata, ADR default Status, PLN Last reviewed backfill, backfill rules table, acceptance criteria, backup branch rollback | Claude Code |
| 2026-03-20 | Round 2 revision: context-based ADR/CHG/PLN/INC status defaults, fallback date rule, USR layer rollback strategy, acceptance criteria covers all layers | Claude Code |
