# CHG-2183: Add-AF-Tool-Context-To-COR-Workflow-Dispatch-Steps

**Applies to:** FXA project
**Last updated:** 2026-04-01
**Last reviewed:** 2026-04-01
**Status:** Completed
**Date:** 2026-04-01
**Requested by:** User request + Evolve-SOP FXA-2175
**Priority:** Medium
**Change Type:** Normal

---

## What

Add "Dispatch context" note with `af read`/`af list` usage to COR-1601 Step 4 and COR-1602 Step 2 in the fx_alfred source.

## Why

Dispatched reviewers don't know to use `af` commands to access project documents. COR is the canonical source all projects inherit from.

## Impact Analysis

- **Systems affected:** COR-1601, COR-1602 (bundled PKG-layer documents in fx_alfred)
- **Rollback plan:** `cd fx_alfred && git checkout HEAD -- src/fx_alfred/rules/COR-1601-*.md src/fx_alfred/rules/COR-1602-*.md`

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-01 | Initial version | — |
