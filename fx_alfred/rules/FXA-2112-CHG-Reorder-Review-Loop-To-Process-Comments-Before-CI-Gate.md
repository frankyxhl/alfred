# CHG-2112: Reorder Review Loop To Process Comments Before CI Gate

**Applies to:** FXA project
**Last updated:** 2026-04-06
**Last reviewed:** 2026-04-06
**Status:** Proposed
**Date:** 2026-04-06
**Requested by:** Codex reviewer (PR #38 comment #3037676271)
**Priority:** Medium
**Change Type:** Normal

---

## What

Restructure the Post-Push Review Loop (Phase 7) in both FXA-2148 and FXA-2149 so that actionable review comments are **fixed before** the CI-green exit check, rather than after it.

Currently both SOPs categorize comments (Step 25/28) but then check CI (Step 26/29) and loop back to the wait step if CI is red — skipping the actionable-comment fix step entirely. This means reviewer feedback that could resolve the CI failure is never acted on, wasting loop iterations.

## Why

When CI is failing due to issues already identified by reviewers, the current ordering blocks the fix path: the loop burns iterations re-checking CI without ever acting on the comments that explain the fix. With a max-3 iteration budget, this can exhaust the loop before any actionable comment is addressed.

Origin: Codex P1 review comment on PR #38 (commit b4b1c79), categorized as substantive per SOP Step 30a — deferred from the review loop to a standalone CHG.

## Impact Analysis

- **Systems affected:** FXA-2148-SOP-Evolve-SOP.md (Phase 7, Steps 24–28), FXA-2149-SOP-Evolve-CLI.md (Phase 7, Steps 27–31)
- **Rollback plan:** Revert to current ordering (CI check before comment processing)
- **Risk: stale comments** — comments fetched may refer to a previous push. Mitigated by the existing "mechanical only" constraint; substantive issues already exit the loop.

## Implementation Plan

Merge the separate CI-gate and actionable-fix branches into a unified iteration body. Both SOPs get the same structural change; only the hard-gate command differs.

### FXA-2148 (Evolve-SOP) — Steps 24–28 become:

```
24. **Wait for CI + automated reviews** — sleep 3 minutes after PR is opened (or after each fix-push), then:
    gh pr checks <PR-number>
    gh api --paginate repos/{owner}/{repo}/pulls/<PR-number>/comments
25. **Categorize each review comment:**
    - Actionable / Advisory / False positive (unchanged)
26. **If actionable items exist:**
    a. Fix — mechanical only; substantive → exit loop, re-run Phase 5 Step 20
    b. Re-run hard gate (af --root ... validate)
    c. Commit + push
27. **Check CI** — if CI is not green and no fixes were pushed in Step 26, go to Step 24 (counts as one iteration). If fixes were pushed in Step 26, go to Step 24 (CI will re-run on the new push).
28. **Exit loop** — when: CI passes AND 0 unresolved actionable comments, OR max iterations reached.
```

### FXA-2149 (Evolve-CLI) — Steps 27–31 become:

```
27. **Wait for CI + automated reviews** — sleep 3 minutes after PR is opened (or after each fix-push), then:
    gh pr checks <PR-number>
    gh api --paginate repos/{owner}/{repo}/pulls/<PR-number>/comments
28. **Categorize each review comment:**
    - Actionable / Advisory / False positive (unchanged)
29. **If actionable items exist:**
    a. Fix — mechanical only; substantive → exit loop, re-run Phase 5 from Step 22
    b. Re-run hard gate (pytest + ruff)
    c. Commit + push
30. **Check CI** — if CI is not green and no fixes were pushed in Step 29, go to Step 27 (counts as one iteration). If fixes were pushed in Step 29, go to Step 27 (CI will re-run on the new push).
31. **Exit loop** — when: CI passes AND 0 unresolved actionable comments, OR max iterations reached.
```

### Edge case: CI red + 0 actionable comments

Step 27/30 handles this explicitly: "if CI is not green and no fixes were pushed" → loop back to wait step, counting as one iteration. The max-3 iteration budget prevents infinite polling.

### Steps

1. Replace Phase 7 steps in FXA-2148 with the text above
2. Replace Phase 7 steps in FXA-2149 with the text above
3. Update loop-limit header step ranges if needed
4. Run `af validate` to confirm document health

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-06 | Initial version — from PR #38 substantive review comment | Claude Code |
| 2026-04-06 | R1 fix: add concrete step rewrites, CI-red+0-comments edge case, precision wording | Claude Code |
