# CHG-2311: Strengthen L2 PR Readiness Loop Gates

**Applies to:** FXA project
**Last updated:** 2026-06-26
**Last reviewed:** 2026-06-26
**Status:** Proposed
**Related:** COR-1612, COR-1615, COR-1617, COR-1622, FXA-2276
**Date:** 2026-06-26
**Requested by:** Frank Xu
**Priority:** High
**Change Type:** Normal

---

## What

Strengthen Alfred's assisted PR delivery loop so an agent cannot treat "PR opened",
"branch pushed", or "local checks passed" as completion. The loop must carry a
current-head state packet and stop only when PR readiness is clean or the remaining
blocker is an explicit human approval or merge gate.


## Why

Recent L2 runs showed the useful boundary: the agent should keep driving CI,
review comments, GitHub App review, and mergeability checks until the PR is ready
for a human-only decision. A one-line personal preference is too easy to bypass;
the contract belongs in Alfred's SOP layer so every project adopting the loop can
inherit the same gate.


## Impact Analysis

- **Systems affected:** COR-1617 loop phase contract, COR-1615 GitHub App review
  loop completion criteria, COR-1622 project configuration schema, and Alfred's
  FXA-2276 instantiation.
- **Behavioral impact:** Phase 8 must maintain a state packet with head SHA,
  checks, review surfaces, blockers, and next action. Phase 10 handoff requires
  current-head readiness evidence, not local validation alone.
- **Compatibility:** Existing COR-1612 review-comment handling and COR-1615
  pre-merge sweep remain the mechanisms; this change tightens when they are
  considered complete.
- **Rollback plan:** Revert this CHG and the associated COR/FXA document edits,
  then rerun `af validate --root /Users/frank/Projects/alfred`.


## Acceptance Criteria

- A1: COR-1617 Phase 8 requires a current-head PR state packet after every push
  and before every handoff.
- A2: COR-1617 Phase 10 defines readiness as current-head review, checks,
  non-bookkeeping review-thread sweep, mergeability, and human-gate state.
- A3: COR-1615 completion criteria require recording checks, merge state, and
  the remaining human gate, not just bot-review cleanliness.
- A4: COR-1622 exposes project parameters for PR readiness checks and human
  approval/merge gates.
- A5: FXA-2276 instantiates those parameters for `frankyxhl/alfred`.
- A6: `af validate --root /Users/frank/Projects/alfred` passes, allowing the
  known FXA-2271 CTX warning if it still exists.


## Implementation Plan

1. Add PR readiness parameter rows to COR-1622.
2. Update COR-1617 Phase 8 and Phase 10 with the state packet and readiness gate.
3. Update COR-1615 completion criteria with the same readiness evidence.
4. Update FXA-2276 with Alfred-specific parameter values and Phase 10 wording.
5. Update FXA-0000 and run validation.


## Verification

Record before merge:

```bash
af validate --root /Users/frank/Projects/alfred
git diff --stat
```


## Change History

| Date | Change | By |
|------|--------|----|
| 2026-06-26 | Initial CHG for strengthening the L2 PR readiness loop gate | Codex |
