# CHG-2277: COR-1622 Schema Refinements For Heterogeneous Adopters

**Applies to:** FXA project
**Last updated:** 2026-05-09
**Last reviewed:** 2026-05-09
**Status:** Proposed
**Date:** 2026-05-09
**Requested by:** Frank (via session 2026-05-09)
**Priority:** Medium
**Change Type:** Normal
**Targets:** COR-1622, COR-1617, COR-1505

---

## What

Two refinements to the COR-1622 parameter schema, surfaced when alfred itself attempted to instantiate it (the FXA-2276 REF companion in this PR):

1. **`<weights-doc>` becomes plural-or-scalar.** Type changes from `string` to `string | map<<spec-format>, string>`. Adopters can either point at a single project-wide weights document (trinity's pattern with `TRN-1800`) OR a map keyed by `<spec-format>` (alfred's pattern: `{CHG → COR-1609, code → COR-1610, PRP → COR-1608}`).

2. **`<fork-remote>` renamed to `<pr-push-remote>`.** The original name presupposed a forked-fork PR workflow; alfred pushes feature branches to `origin` directly (no fork remote). The rename keeps the *semantic* invariant ("the remote PRs are pushed to, never `origin/main` directly") while removing the misleading "fork" framing. Updates the references in COR-1617 §Phase 7 and COR-1505 §Examples.

## Why

PR #117's COR-1617 cluster shipped with a TRN-1008-shaped schema — fitted to trinity's actual workflow but baking in two assumptions other adopters don't share:

- **Single weights doc.** Trinity uses `TRN-1800` for everything; alfred per its own CLAUDE.md uses `COR-1608/1609/1610` keyed by artifact type. Forcing alfred to pick one is a contract-vs-reality mismatch — the weights actually used at panel-review time depend on whether the artifact is a CHG, code, or PRP.
- **Fork remote naming.** Trinity uses a `fork` remote for the `ryosaeba1985`-side push; alfred has no fork remote. Both projects honor the "never push to `origin/main`" invariant, but the schema's *name* implies a topology alfred doesn't use.

Both surface honestly only when a non-trinity project tries to instantiate. Alfred itself is the first such project (FXA-2276 in this PR). Fixing both before the schema accumulates more dependents.

## Impact Analysis

**Files changed**

- `src/fx_alfred/rules/COR-1622-REF-Multi-Agent-Loop-Project-Configuration.md` — three rows in the schema table (`<weights-doc>` description + type, `<fork-remote>` rename); worked-example rename; change-history row.
- `src/fx_alfred/rules/COR-1617-SOP-Multi-Agent-Workflow-Loop.md` — §Phase 7 reference; §Guard Rails reference; §Failure Modes references if any; change-history row.
- `src/fx_alfred/rules/COR-1505-SOP-Branch-and-Identity-Hygiene.md` — §Steps + §Examples references; change-history row.

**Behavioural impact**

- Trinity's existing instantiation continues working unchanged: `<weights-doc>: TRN-1800` is still a valid scalar value; `<pr-push-remote>: fork` is the renamed equivalent of `<fork-remote>: fork`.
- Alfred can now express its actual rubric routing: `<weights-doc>: {CHG → COR-1609, code → COR-1610, PRP → COR-1608}`.
- No code change anywhere — pure SOP doc edits.

**Out of scope** (explicitly deferred)

- Adding a `<panel-rubric-fallback>` key for `<spec-format>` values not in the map. Defer to an evidence-driven follow-up if alfred's panel needs it.
- Documenting the GitHub-Actions PR-push-without-fork-remote pattern as a standalone alternative-runtime SOP. Defer.
- Any change to COR-1602/1615 (the panel/bot-loop SOPs the cluster composes). Out of scope for this CHG.

## Implementation Plan

1. Edit COR-1622 §Identity & repository row for `<fork-remote>` → rename to `<pr-push-remote>` with updated description ("the git remote that PR head branches push to; never `origin/main` directly. Single-remote projects use `origin`; fork-PR projects use `fork`.").
2. Edit COR-1622 §Review panel row for `<weights-doc>` → change type to `string | map<<spec-format>, string>` and update description.
3. Edit COR-1622 §Worked Example rows: rename `<fork-remote>` → `<pr-push-remote>` (value stays `fork` for trinity).
4. Edit COR-1617 §Phase 7 PR-open shell snippet — `<fork-remote>` → `<pr-push-remote>`.
5. Edit COR-1617 §Guard Rails — `<fork-remote>` → `<pr-push-remote>`.
6. Edit COR-1505 §Steps + §Examples + §Guard Rails — every `<fork-remote>` → `<pr-push-remote>`.
7. Add change-history rows on all three files.
8. Run `af validate --root .` to confirm no structural issues.
9. (Companion in same PR) Create FXA-2276-REF using the new schema.
10. Commit + push + PR; trinity panel-review (glm + deepseek) + codex bot iteration.

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-09 | Initial version — proposed during alfred FXA-2276 instantiation when schema gaps surfaced | Claude Opus 4.7 |
