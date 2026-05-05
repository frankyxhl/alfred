# CHG-2125: Create Code Review Checklist COR-1705-1709

**Applies to:** FXA project
**Last updated:** 2026-05-06
**Last reviewed:** 2026-05-06
**Status:** Proposed
**Date:** 2026-05-06
**Requested by:** Frank Xu
**Priority:** Medium
**Change Type:** Normal
**Related:** FXA-2124 (PRP), Issue #99, COR-1602

---

## What

Create five new PKG-layer documents in `src/fx_alfred/rules/` per approved PRP FXA-2124:
- COR-1705-REF: Code Review Classification System
- COR-1706-SOP: Code Review — Structural Checks
- COR-1707-SOP: Code Review — Cross-Cutting Concerns
- COR-1708-SOP: Code Review — Domain-Specific Checks
- COR-1709-SOP: Code Review — AI-Assisted Code + Quick Reference

Add cross-reference to COR-1602 Steps section. Archive `code-review-checklist.md` to `docs/archive/`.

---

## Why

Converts the 1022-line Chinese `code-review-checklist.md` into discoverable, atomic, English PKG-layer Alfred documents. All design decisions resolved in FXA-2124 PRP (unanimous 10.0/10 approval).

---

## Impact Analysis

- **Systems affected:** `src/fx_alfred/rules/` (5 new files), COR-1602 (1 line added)
- **Rollback plan:** Revert the commit; all new files are additive

---

## Implementation Plan

1. Create COR-1705-REF in `src/fx_alfred/rules/`
2. Create COR-1706-SOP through COR-1709-SOP in `src/fx_alfred/rules/`
3. Add cross-reference line to COR-1602 §Steps
4. Archive `code-review-checklist.md` to `docs/archive/code-review-checklist-v1.0.md`
5. Run `af validate` and `af index`
6. Open PR

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-06 | Initial version | Frank Xu |
