# CHG-2323: Declare Review Loop Back-Edges

**Applies to:** FXA project
**Last updated:** 2026-08-12
**Last reviewed:** 2026-08-12
**Status:** Completed
**Date:** 2026-08-12
**Requested by:** Frank Xu (session request: retrofit tier-1 candidates from the COR-1005 corpus audit)
**Priority:** Medium
**Change Type:** Normal
**Targets:** src/fx_alfred/rules/COR-1600-SOP-Workflow-Direct-Review-Loop.md, src/fx_alfred/rules/COR-1601-SOP-Workflow-Leader-Mediated-Review-Loop.md

---

## What

Symmetric-class retrofit of the two prose-loop review SOPs, applying COR-1005
(Engineer Workflow Loops) to its tier-1 audit candidates:

- **COR-1600**: declare `{id: revise-resend, from: 6, to: 5, max_iterations: 5,
  condition: "iteration is on and not all reviewers approve"}`; step 6 body now
  carries the exhaustion path (escalate unresolved findings to the Leader).
- **COR-1601**: declare `{id: revise-cycle, from: 7, to: 4, max_iterations: 5,
  condition: "iteration is on and Leader requests revision or redirects the approach"}`; step 7 body now
  carries the final call (Leader stops the loop and Arbitrates or Accepts with
  justification).

Shared before/after invariant (symmetric class): each member's prose loop
("repeat step N") becomes a declared `Workflow loops:` back-edge with
`max_iterations: 5` matching each SOP's own §Iteration Mode default, plus the
§Termination Criteria exhaustion behavior restated in the loop's `from` step
body per COR-1005 step 3. No other steps change.

## Why

The COR-1005 audit (2026-08-11, post-#320) found only COR-1602 and COR-1005
declare machine-readable loops; every other iterative SOP is a prose loop —
COR-1005 failure mode ① (invisible to `af plan`, `--graph`, `af validate`) and
③ in the step bodies: the 5-round budget and exhaustion behavior existed only
in §Iteration Mode / §Termination Criteria, invisible to the planner and absent
from the step an executing agent actually follows (COR-1005 step 3 requires the
exhaustion behavior in the `from` step body, not only elsewhere).

## Impact Analysis

- **Systems affected:** two PKG rules docs (COR-1600, COR-1601); this CHG
  document itself plus its PRJ index row (`rules/FXA-0000`, via `af index`);
  one CHANGELOG Unreleased entry. COR-0000 is untouched (no new PKG documents).
  No code paths change.
- **Consumers:** `af plan --graph COR-1600/1601` now renders the review
  back-edge; checklists gain the exhaustion instruction. Behavior of the SOPs
  as read by humans is unchanged except the previously-undefined exhaustion
  case is now defined.
- **No cascade:** COR-1602/1005 referenced, not edited.
- **Rollback plan:** revert the two doc edits, set this CHG to Rolled Back,
  re-run `af index` so the FXA-0000 row reflects the Rolled Back status, and
  remove (or amend to "rolled back") the CHANGELOG Unreleased entry.

## Implementation Plan

1. Capture before graphs (`af plan --graph` both docs).
2. Add `Workflow loops:` metadata + exhaustion prose per member; Change History
   rows; Last updated bumps.
3. Validate: `af validate` both docs, `af plan --graph` renders both back-edges,
   docs drift test, CHANGELOG Unreleased entry.
4. Before/after graph comparison attached to PR; COR-1615 bot loop to merge-ready.

---

## Change History

| Date       | Change          | By          |
|------------|-----------------|-------------|
| 2026-08-12 | Initial version | Claude Code |
| 2026-08-12 | Implemented: back-edges declared, exhaustion paths added, graphs verified | Claude Code |
| 2026-08-12 | Codex R1: max_iterations 3→5 to match each SOP's documented §Iteration Mode default; corrected Why claim (budget existed outside step bodies) | Claude Code |
| 2026-08-12 | Codex R2: Impact Analysis now lists every touched file (CHG itself, FXA-0000 index row, CHANGELOG) | Claude Code |
| 2026-08-12 | Codex R3: rollback plan covers index re-run and CHANGELOG entry removal | Claude Code |
| 2026-08-12 | Codex R4/R5: exhaustion final call limited to step 6's enumerated Arbitrate/Accept; stale abandon wording purged from CHG and CHANGELOG | Claude Code |
| 2026-08-12 | Codex R6/R7: loop condition covers Redirect re-entry; CHG quotation synced to the SOP's condition string | Claude Code |
