# CHG-2114: COR-1103-Add-Council-Review-Routing

**Applies to:** FXA project
**Last updated:** 2026-05-03
**Last reviewed:** 2026-05-03
**Status:** Proposed
**Date:** 2026-05-03
**Requested by:** Frank Xu (companion CHG to FXA-2113 / COR-1613)
**Priority:** Medium
**Change Type:** Normal
**Targets:** COR-1103 (PKG)

---

## What

Add COR-1613 (Council Review) to COR-1103 in three places, so the new SOP is discoverable from the session-start router rather than orphaned:

1. **OVERLAYS section** — add one line:
   ```
   • Multi-reviewer decision      → COR-1613 (declare Review Unit: mechanism, threshold, reviewers)
   ```

2. **Golden Rules section** — add one line:
   ```
   COR-1613: Multi-reviewer decision → declare Review Unit before reviewers begin (mechanism / rubric / threshold / reviewers); record per Step 6
   ```

3. **Workflow Selection — Parallel evaluation table** — add a footnote under the table:
   > Council Review (COR-1613) operates orthogonally: COR-1602 picks the *workflow pattern* (parallel dispatch + Leader synthesis); COR-1613 picks the *decision rule* (default = Decision Matrix). Declare both for any multi-reviewer review.


## Why

COR-1613 was approved via FXA-2113 PRP. Without router insertion, no agent or human reading COR-1103 at session start will know to invoke it; the SOP would be reachable only by direct reference, which defeats the routing layer. This is the explicit "orphaned-SOP" risk flagged in the FXA-2113 round-1 review (Gemini, 2026-05-03) and committed to as in-scope by FXA-2113 §1.0.


## Impact Analysis

- **Systems affected:** `src/fx_alfred/rules/COR-1103-SOP-Workflow-Routing.md` only (3 small additions, no removals).
- **Backward compatibility:** Additive only. No existing routes change. The intent router is unchanged at the primary-route level (1–8); COR-1613 is added to the OVERLAYS that apply *after* primary routing, matching the pattern used by COR-1500/1606/1608/1611.
- **Affected workflows:** Any multi-reviewer review that previously inherited the implicit Decision-Matrix mechanism without declaring it. Going forward, the router prompts the dispatcher to declare a Review Unit. No retroactive change to historical reviews.
- **Rollback plan:** Revert this CHG's commit. The 3 added lines are isolated; revert restores prior COR-1103 verbatim. COR-1613 itself remains discoverable by direct `af read COR-1613` even without the router entry, so reverting does not "break" anything — it just removes the discoverability shortcut.


## Implementation Plan

1. Read current `src/fx_alfred/rules/COR-1103-SOP-Workflow-Routing.md`.
2. Insert the OVERLAYS line after the existing `• Review scoring rubric → COR-1608/1609/1610 + COR-1611` line (preserves alphabetical-ish OVERLAY ordering).
3. Insert the Golden Rules line after the existing `COR-1611:` line (groups review-related rules together).
4. Append the Workflow-Selection footnote immediately after the `Parallel evaluation` table (before the `Implementation coordination` heading).
5. Update COR-1103 metadata: `Last updated: 2026-05-03`, append Change History row.
6. Run `af fmt COR-1103 --root <pkg_root> --write` and `af validate`.
7. Commit with message: `chg(FXA-2114): add COR-1613 routing entries to COR-1103`.


## Open Questions

None — scope is mechanically defined (3 specific insertions in one file).

---

## Change History

| Date       | Change                                                               | By       |
|------------|----------------------------------------------------------------------|----------|
| 2026-05-03 | Initial version — companion CHG to FXA-2113 PRP for COR-1613 routing | Frank Xu |
