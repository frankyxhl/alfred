# PRP-2188: Fix-FXA-2125-Stale-Alfred-Ops-Refs

**Applies to:** FXA project
**Last updated:** 2026-04-04
**Last reviewed:** 2026-04-04
**Status:** Approved

---

## What Is It?

Remove stale references in FXA-2125 (Workflow Routing PRJ) left over from the alfred_ops merge (FXA-2186).

---

## Problem

FXA-2125 has two stale references from the alfred_ops merge:

1. **Decision tree item 9** routes "End of session?" to FXA-2127 (Commit Alfred Ops), which is now Deprecated. FXA-2186 step 10 explicitly called for this cleanup but it was not completed for FXA-2125.

2. **Golden rule** states "fx_alfred: Documents live in rules/ (PRJ layer), document changes, no remote (local git only)" — but fx_alfred has a GitHub remote (git@github.com:frankyxhl/alfred.git). The "no remote" clause was inherited from the old alfred_ops repo.

## Proposed Solution

1. **Remove decision tree item 9** (section "End of session? → FXA-2127") entirely from the `## Project Decision Tree` section of FXA-2125. After the alfred_ops merge, there is no separate "commit alfred_ops" step. Document commits follow the normal git workflow.

2. **Update the golden rule** in the `## Project Golden Rules` code block. Replace:
   ```
   fx_alfred: Documents live in rules/ (PRJ layer), document changes, no remote (local git only)
   ```
   With:
   ```
   fx_alfred: Documents live in rules/ (PRJ layer), document changes committed with code
   ```

## Out of Scope

- **FXA-2100** (Leader Mediated Development): FXA-2186 step 10 called for updating both FXA-2100 and FXA-2125. FXA-2100 was already cleaned up — `grep FXA-2127 FXA-2100` returns no matches. No action needed.
- **FXA-2127** itself: already marked Deprecated. No further changes needed.
- **Other documents**: references to FXA-2127 in REF/run-log documents (FXA-2155, FXA-2158, FXA-2172, FXA-2175) are historical records, not actionable routing.

## Risks

- **Low**: merge conflict if FXA-2125 is modified concurrently. Mitigated by single-branch evolve workflow.
- **Low**: removing item 9 leaves no explicit "end of session" guidance. Acceptable because document commits are now part of the normal git workflow, not a separate SOP.

## Open Questions

None. Both changes are straightforward corrections of factual inaccuracies.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-04 | Initial version | Claude Code |
| 2026-04-04 | R1 revision: add exact replacement text, Out of Scope, Risks per Gemini review (7.8) | Claude Code |
