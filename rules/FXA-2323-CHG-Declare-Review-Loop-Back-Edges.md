# CHG-2323: Declare Review Loop Back-Edges

**Applies to:** FXA project
**Last updated:** 2026-08-12
**Last reviewed:** 2026-08-12
**Status:** Proposed
**Date:** 2026-08-12
**Requested by:** Frank Xu (session request: retrofit tier-1 candidates from the COR-1005 corpus audit)
**Priority:** Medium
**Change Type:** Normal
**Targets:** src/fx_alfred/rules/COR-1600-SOP-Workflow-Direct-Review-Loop.md, src/fx_alfred/rules/COR-1601-SOP-Workflow-Leader-Mediated-Review-Loop.md

---

## What

Symmetric-class retrofit of the two prose-loop review SOPs, applying COR-1005
(Engineer Workflow Loops) to its tier-1 audit candidates:

- **COR-1600**: declare `{id: revise-resend, from: 6, to: 5, max_iterations: 3,
  condition: "iteration is on and not all reviewers approve"}`; step 6 gains the
  missing exhaustion path (escalate unresolved findings to the Leader).
- **COR-1601**: declare `{id: revise-cycle, from: 7, to: 4, max_iterations: 3,
  condition: "iteration is on and Leader requests revision"}`; step 7 gains the
  missing exhaustion path (Leader stops the loop and Arbitrates / Accepts with
  justification / abandons).

Shared before/after invariant (symmetric class): each member's prose loop
("repeat step N") becomes a declared `Workflow loops:` back-edge with
`max_iterations: 3` matching family precedent COR-1602, plus an explicit
exhaustion path in the loop's `from` step body. No other steps change.

## Why

The COR-1005 audit (2026-08-11, post-#320) found only COR-1602 and COR-1005
declare machine-readable loops; every other iterative SOP is a prose loop —
COR-1005 failure mode ① (invisible to `af plan`, `--graph`, `af validate`) and
③ (success-only exits: neither SOP defines what happens when rounds are
exhausted; "or max rounds reached" names no number and no behavior).

## Impact Analysis

- **Systems affected:** two PKG rules docs + COR-0000/PRJ index untouched (no
  new documents). No code paths change.
- **Consumers:** `af plan --graph COR-1600/1601` now renders the review
  back-edge; checklists gain the exhaustion instruction. Behavior of the SOPs
  as read by humans is unchanged except the previously-undefined exhaustion
  case is now defined.
- **No cascade:** COR-1602/1005 referenced, not edited.
- **Rollback plan:** revert the two doc edits, set this CHG to Rolled Back.

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
