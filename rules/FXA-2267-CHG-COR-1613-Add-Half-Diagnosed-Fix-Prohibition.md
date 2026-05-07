# CHG-2267: COR-1613-Add-Half-Diagnosed-Fix-Prohibition

**Applies to:** FXA project
**Last updated:** 2026-05-03
**Last reviewed:** 2026-05-03
**Status:** Approved
**Date:** 2026-05-03
**Requested by:** Frank Xu (companion CHG to FXA-2265 / COR-1503)
**Priority:** Medium
**Change Type:** Normal
**Targets:** COR-1613 (PKG)

---

## What

Add one line to COR-1613 §When NOT to Use:

```
- A fix PR whose diagnosis was incomplete — the Council Review Unit cannot record a falsified hypothesis it never saw. The fix must first complete COR-1503 (Diagnose Feedback Loop) Phase 1–5 before entering Council Review.
```


## Why

COR-1503 §Relationship to COR-1613 states that a Council Review of a half-diagnosed fix is **forbidden**. Currently this prohibition lives only in COR-1503 and is unenforceable when a fix PR enters Council Review without any COR-1503 declaration. Adding it to COR-1613 §When NOT to Use makes the prohibition enforceable by giving the dispatcher a concrete rule to check during COR-1613 §Step 1 (Declare the Review Unit). This was identified as a gap in FXA-2265 round-2 review (DeepSeek) and resolved in round 3 via commitment to this parallel CHG.


## Impact Analysis

- **Systems affected:** `src/fx_alfred/rules/COR-1613-SOP-Council-Review.md` only (one line in §When NOT to Use).
- **Backward compatibility:** Additive only. No existing Council reviews are retroactively invalidated.
- **Rollback plan:** Revert this CHG's commit. The prohibition in COR-1503 remains but is discoverable only by reading COR-1503, not from COR-1613.


## Implementation Plan

1. Read current `src/fx_alfred/rules/COR-1613-SOP-Council-Review.md`.
2. Insert the new bullet in §When NOT to Use, after the existing "Mid-task micro-choices" line.
3. Update COR-1613 metadata: `Last updated: 2026-05-03`, append Change History row.
4. Run `af fmt` and `af validate`.
5. Commit with message: `chg(FXA-2267): add half-diagnosed fix prohibition to COR-1613`.

---

## Change History

| Date       | Change                                                                   | By       |
|------------|--------------------------------------------------------------------------|----------|
| 2026-05-03 | Initial version — companion CHG to FXA-2265 PRP for COR-1613 prohibition | Frank Xu |
| 2026-05-03 | Implemented in same PR: COR-1613 §When NOT to Use now includes half-diagnosed-fix prohibition. | Frank Xu |
