# CHG-2118: COR-1103-Add-Diagnose-Routing

**Applies to:** FXA project
**Last updated:** 2026-05-03
**Last reviewed:** 2026-05-03
**Status:** Proposed
**Date:** 2026-05-03
**Requested by:** Frank Xu (companion CHG to FXA-2116 / COR-1503)
**Priority:** Medium
**Change Type:** Normal
**Targets:** COR-1103 (PKG)

---

## What

Add COR-1503 (Diagnose Feedback Loop) entry to COR-1103 in two places:

1. **OVERLAYS section** — add one line:
   ```
   • Diagnose a bug or perf regression → COR-1503 (Diagnose Feedback Loop: build feedback loop → reproduce → hypothesise → instrument → fix → regression-test)
   ```

2. **PRIMARY ROUTE branch 2** — add a sub-branch under "Something broken/failing/unexpected?":
   ```
   2. Something broken/failing/unexpected?
      ├── Cause is unknown → COR-1503 (Diagnose Feedback Loop)
      ├── Bug/incident (cause known) → INC (project-level SOP)
      └── Fix requires system change → INC + CHG (COR-1101)
   ```


## Why

COR-1503 was approved via FXA-2116 PRP. Without router insertion, COR-1103 §PRIMARY ROUTE branch 2 ("Something broken/failing/unexpected?") would route directly to INC + CHG with no diagnosis SOP in between — the exact gap COR-1503 fills.


## Impact Analysis

- **Systems affected:** `src/fx_alfred/rules/COR-1103-SOP-Workflow-Routing.md` only (2 small additions, no removals).
- **Backward compatibility:** Additive only. Existing INC + CHG route preserved; COR-1503 is inserted as the first sub-branch when the cause is unknown.
- **Rollback plan:** Revert this CHG's commit. COR-1503 remains discoverable by direct `af read COR-1503`.


## Implementation Plan

1. Read current `src/fx_alfred/rules/COR-1103-SOP-Workflow-Routing.md`.
2. Insert the OVERLAYS line after the existing "Multi-reviewer decision" line.
3. Insert the COR-1503 sub-branch under PRIMARY ROUTE branch 2.
4. Update COR-1103 metadata + Change History.
5. Run `af fmt` and `af validate`.
6. Commit with message: `chg(FXA-2118): add COR-1503 diagnose routing to COR-1103`.

---

## Change History

| Date       | Change                                                               | By       |
|------------|----------------------------------------------------------------------|----------|
| 2026-05-03 | Initial version — companion CHG to FXA-2116 PRP for COR-1503 routing | Frank Xu |
