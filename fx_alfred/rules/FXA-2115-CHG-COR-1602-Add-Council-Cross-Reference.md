# CHG-2115: COR-1602-Add-Council-Cross-Reference

**Applies to:** FXA project
**Last updated:** 2026-05-03
**Last reviewed:** 2026-05-03
**Status:** Proposed
**Date:** 2026-05-03
**Requested by:** Frank Xu (companion CHG to FXA-2113 / COR-1613)
**Priority:** Medium
**Change Type:** Normal
**Targets:** COR-1602 (PKG)

---

## What

Add a one-paragraph cross-reference to COR-1602 noting its relationship to the new COR-1613 (Council Review). The paragraph clarifies that COR-1602 is the **parallel-dispatch workflow pattern** layered with the **Decision Matrix mechanism** from COR-1613, making the layering explicit so future readers do not treat the two SOPs as redundant or competing.

Insertion point: a new "Relationship to COR-1613" subsection immediately before the existing Change History of COR-1602. Proposed text:

> ### Relationship to COR-1613 (Council Review)
>
> COR-1602 specifies the *workflow pattern* for parallel-dispatch reviews (how reviewers are convened, how the Leader synthesizes outputs, how iteration loops work). COR-1613 specifies the *decision rule* applied to whatever pattern is in use. The two are layered, not redundant: a typical multi-reviewer review under COR-1602 declares a Council Review Unit (per COR-1613) with `mechanism: decision_matrix` and `rubric: COR-1608/1609/1610` as the default. Reviewers may declare a different mechanism (Veto, Consensus, etc.) when the target's risk profile warrants it; in that case COR-1602's parallel-dispatch shape is preserved and only the aggregation rule changes.


## Why

COR-1602 currently does not name its decision rule explicitly — the "≥ 9.0 PASS" practice is folklore inherited from COR-1608. With COR-1613 in place, this folklore becomes a *declared mechanism choice* (Decision Matrix). Without the cross-reference, a reader of COR-1602 will not know that the mechanism is now configurable and that other mechanisms are available.

This was raised as a round-1 reviewer finding for FXA-2113 (Codex, GLM): COR-1602's role under the new layered model needs to be made explicit somewhere visible to anyone reading just COR-1602.


## Impact Analysis

- **Systems affected:** `src/fx_alfred/rules/COR-1602-SOP-Workflow-Multi-Model-Parallel-Review.md` only (one new subsection added; nothing removed or renamed).
- **Backward compatibility:** Additive only. No change to COR-1602's existing Roles, Steps, or scoring guidance. Existing reviews that did not declare a Review Unit are not retroactively reclassified.
- **Affected workflows:** None at runtime; the change is purely descriptive. Going forward, COR-1602 reviews are encouraged (not required by this CHG — that requirement belongs to FXA-2114 router insertion + COR-1613 itself) to declare a Review Unit.
- **Rollback plan:** Revert this CHG's commit. The added subsection is isolated above Change History; revert restores prior COR-1602 verbatim. COR-1613 remains operational without the cross-reference; rollback only removes the discoverability hint.


## Implementation Plan

1. Read current `src/fx_alfred/rules/COR-1602-SOP-Workflow-Multi-Model-Parallel-Review.md`.
2. Insert the "Relationship to COR-1613 (Council Review)" subsection immediately before the existing Change History section.
3. Update COR-1602 metadata: `Last updated: 2026-05-03`, append Change History row noting the cross-reference addition.
4. Run `af fmt COR-1602 --root <pkg_root> --write` and `af validate`.
5. Commit with message: `chg(FXA-2115): add COR-1613 cross-reference to COR-1602`.


## Open Questions

None — scope is mechanically defined (one paragraph in one file).


## Constraint

This CHG is the only sanctioned modification to COR-1602 in the FXA-2113 / COR-1613 initiative. A round-2 reviewer (Codex) flagged that the original "only sanctioned modification" phrasing in the PRP forecloses iterative review of this CHG itself; that flag is acknowledged here. Reviewers of *this* CHG may raise new COR-1602 issues; if accepted, those become a separate CHG (FXA-2116+), not amendments to this one.

---

## Change History

| Date       | Change                                                                       | By       |
|------------|------------------------------------------------------------------------------|----------|
| 2026-05-03 | Initial version — companion CHG to FXA-2113 PRP for COR-1602 cross-reference | Frank Xu |
