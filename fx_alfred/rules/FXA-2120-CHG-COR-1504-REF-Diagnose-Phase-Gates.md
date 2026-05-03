# CHG-2120: COR-1504-REF-Diagnose-Phase-Gates

**Applies to:** FXA project
**Last updated:** 2026-05-03
**Last reviewed:** 2026-05-03
**Status:** Proposed
**Date:** 2026-05-03
**Requested by:** Frank Xu (companion CHG to FXA-2116 / COR-1503)
**Priority:** Medium
**Change Type:** Normal
**Targets:** COR-1504 (PKG, new REF)

---

## What

Create the sibling PKG reference document `COR-1504-REF-Diagnose-Phase-Gates.md` at `src/fx_alfred/rules/`, linked from COR-1503 §Phase Enforcement Gates. The REF contains the detailed evidence-artefact specification table (6 rows, one per phase) with notes on what constitutes valid evidence per gate. The table was extracted from COR-1503 in FXA-2116 round-3 review to resolve atomicity stress flagged in round 2 (DeepSeek). COR-1503 keeps a one-line-per-phase summary table with a link to this REF.


## Why

The detailed gate table grew the SOP body by ~30% and was flagged as a COR-1400 atomicity concern. Extracting it to a sibling REF keeps COR-1503 atomic ("define the diagnosis loop") while preserving the gate enforcement that makes the SOP load-bearing against the "1 sentence + REF" minimal alternative discussed in the FXA-2116 §Problem steelman.


## Impact Analysis

- **Systems affected:** `src/fx_alfred/rules/COR-1504-REF-Diagnose-Phase-Gates.md` (new file) + `src/fx_alfred/rules/COR-1503-SOP-Diagnose-Feedback-Loop.md` (link to the REF already present in §Phase Enforcement Gates).
- **Backward compatibility:** Additive only. COR-1503's one-line summaries are independently usable; the REF adds precision for operators who need the full evidence spec.
- **Cross-document coupling:** If COR-1504 is updated, COR-1503's one-line summaries must be reviewed for consistency in the same PR. This coupling is manageable — both documents share a declared dependency and the review checklist catches drift.
- **Rollback plan:** Revert this CHG's commit and delete COR-1504. The detailed gate table was inlined in COR-1503 in PRP draft R2; if extraction proves unwieldy, revert to the inline version.


## Implementation Plan

1. File `src/fx_alfred/rules/COR-1504-REF-Diagnose-Phase-Gates.md` has been written alongside this CHG.
2. Run `af fmt` and `af validate`.
3. Commit with message: `ref(COR-1504): phase gates reference for COR-1503 diagnose loop`.

---

## Change History

| Date       | Change                                                                    | By       |
|------------|---------------------------------------------------------------------------|----------|
| 2026-05-03 | Initial version — companion CHG to FXA-2116 PRP for COR-1504 REF creation | Frank Xu |
