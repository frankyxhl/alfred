# CHG-2139: Implement COR-1004 Create Routing Document SOP

**Applies to:** FXA project
**Last updated:** 2026-03-22
**Last reviewed:** 2026-03-22
**Status:** Completed
**Date:** 2026-03-22
**Requested by:** FXA-2138 (Approved PRP)
**Priority:** Medium
**Change Type:** Normal

---

## What

1. Create `COR-1004-SOP-Create-Routing-Document.md` in `fx_alfred/src/fx_alfred/rules/` (PKG layer)
2. Update `COR-1103` — reduce "Creating Routing Documents for USR/PRJ Layers" section to a pointer to COR-1004
3. Update `COR-0002` — add `## Language` section referencing COR-1401

## Why

FXA-2138 PRP approved (Codex 9.23/10, Gemini 10.0/10). No SOP currently governs how to write routing documents. This results in language violations (FXA-2125 in Chinese), inconsistent decision tree formats, and branches that don't resolve to concrete SOPs.

## Impact Analysis

- **Systems affected:** PKG layer (fx_alfred/src/fx_alfred/rules/): COR-1004 (new), COR-1103 (edit), COR-0002 (edit)
- **Rollback plan:** Delete COR-1004, revert COR-1103 and COR-0002 edits via git

## Implementation Plan

1. Create `COR-1004-SOP-Create-Routing-Document.md` per FXA-2138 spec
2. Edit `COR-1103` — replace "Creating Routing Documents for USR/PRJ Layers" section with pointer to COR-1004
3. Edit `COR-0002` — add `## Language` section after `## Section Rules`
4. Run `af validate --root fx_alfred` to confirm 0 issues

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-22 | Initial version | Frank + Claude Code |
| 2026-03-22 | 2026-03-22 \| Review passed: Codex 9.58/10, Gemini 9.9/10; fixed H1 identifier and Step 5 USR clarity \| Codex + Gemini | — |
