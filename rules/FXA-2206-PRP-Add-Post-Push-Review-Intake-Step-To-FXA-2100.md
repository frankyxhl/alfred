# PRP-2206: Add Post-Push Review Intake Step To FXA-2100

**Applies to:** FXA project
**Last updated:** 2026-04-06
**Last reviewed:** 2026-04-06
**Status:** Approved

---

## What Is It?

A proposal to evolve FXA-2100 by adding an explicit post-push review-intake step so that PR comments and CI findings are processed in a defined loop instead of ad-hoc.

---

## Problem

FXA-2100 currently defines the pre-merge dual-review loop and round limit, but it does not explicitly describe how to process newly arriving review comments or CI failures after the initial merge-ready decision. This leaves a governance gap: the team has no standardized closure behavior for post-push feedback.

## Scope

**In scope:**

1. Add one explicit step in FXA-2100 requiring post-push review-intake handling.
2. Define required actions for actionable/advisory/false-positive comments.
3. Add loop cap language aligned with existing bounded-loop principles.
4. Update pass criteria so closure includes post-push intake completion.
5. Record change history entry in FXA-2100.

**Out of scope:**

- Any CLI feature or command implementation.
- Changes to FXA-2148 / FXA-2149 / FXA-2146.
- Rewriting unrelated SOPs.

## Proposed Solution

Update FXA-2100 with a new post-push intake sub-loop that:

1. Checks PR comments and CI after push.
2. Categorizes findings as actionable / advisory / false positive.
3. Applies only mechanical fixes directly in-loop.
4. Sends substantive changes back through the existing dual-review gate.
5. Exits when CI is green and no unresolved actionable items remain, with a maximum of 3 iterations.

## Open Questions

None.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-06 | Initial version | Codex |
| 2026-04-06 | Review pass (simulated local run): candidate approved for CHG implementation | Codex |
