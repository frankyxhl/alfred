# CHG-2122: COR-1103-Add-Pre-Task-Alignment-Routing

**Applies to:** FXA project
**Last updated:** 2026-05-03
**Last reviewed:** 2026-05-03
**Status:** Approved
**Date:** 2026-05-03
**Requested by:** Frank Xu (companion CHG to FXA-2121 / COR-1203)
**Priority:** Medium
**Change Type:** Normal
**Targets:** COR-1103 (PKG)

---

## What

Add COR-1203 (Pre-Task Alignment) to COR-1103 in two places:

1. **OVERLAYS section** — add one line after the existing COR-1503 entry:
   ```
   • Pre-task alignment → COR-1203 (Socratic interview: 7-step loop before PRP/non-trivial code changes; challenge against glossary, sharpen terms, stop when crisp or user-declined)
   ```

2. **Workflow Sequence** — insert COR-1203 after COR-1201 (load tracker) and before `af guide`:
   ```
   COR-1203 ──────────► Pre-task alignment (mandatory offer for PRPs, optional for CHGs)
   ```

## Why

COR-1203 was approved via FXA-2121 PRP. Without router insertion, operators would need to discover and remember to invoke COR-1203 manually. The placement in the session-start sequence ensures alignment is offered before task routing and execution.

## Impact Analysis

- **Systems affected:** `src/fx_alfred/rules/COR-1103-SOP-Workflow-Routing.md` only (2 small additions).
- **Backward compatibility:** Additive only. No existing routes change.
- **Rollback plan:** Revert this CHG's commit.

## Implementation Plan

1. Read current COR-1103.
2. Insert COR-1203 in Workflow Sequence diagram after COR-1201 and before `af guide`.
3. Insert OVERLAYS line after the COR-1503 entry.
4. Update COR-1103 metadata and Change History.
5. Run `af fmt` and `af validate`.
6. Commit.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-03 | Initial version — companion CHG to FXA-2121 PRP for COR-1203 routing | Frank Xu |
| 2026-05-03 | Implemented in same PR: COR-1103 Workflow Sequence + OVERLAYS + Golden Rule line for COR-1203. | Frank Xu |
