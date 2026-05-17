# CHG-2289: COR-1619 Two-Worker TDD Dispatch Sub-Section

**Applies to:** FXA project
**Last updated:** 2026-05-17
**Last reviewed:** 2026-05-17
**Status:** Approved
**Related:** PRP-1507 (Two-Worker TDD Dispatch — design source), GitHub issue #175, CHG-2287 (CHG-A — COR-1500 §Phase 1 Worker assignment rule that this contract operationalises), CHG-2288 (CHG-B — Phase 2 implementer reading constraint that step 4 of this contract enforces), CHG-2290 (CHG-C2 — §Decision Tree branch that routes into this contract), CHG-2291 (CHG-D — `<test-writer-worker-agent>` parameter the contract gates on)
**Date:** 2026-05-17
**Requested by:** @frankyxhl
**Priority:** Medium
**Change Type:** Normal
**Targets:** src/fx_alfred/rules/COR-1619-SOP-Orchestrator-vs-Worker-Dispatch.md (new sub-section between §Worker Dispatch Contract and §Verification)

---

## What

Insert a new `## Two-Worker TDD Dispatch` sub-section in `src/fx_alfred/rules/COR-1619-SOP-Orchestrator-vs-Worker-Dispatch.md` between the existing `## Worker Dispatch Contract` section (ending at "see §Verification") and the existing `## Verification (post-dispatch and post-direct-edit)` section. The new sub-section contains the 8-step handoff contract specified in PRP-1507 §Proposed Solution lines 95–138, plus the symmetric worker-unavailability fallback paragraph (test-writer outage / implementer outage / refactor-phase outage) and the cost note. Content is verbatim from PRP-1507 §Proposed Solution **with one R2 refinement** at step 1's enforcement note (the `git restore` recovery scope was broadened from "off-list paths" to "every modified path outside the approved test paths" per codex bot P2 finding on PR #177; see Change History R2 row for details). The PRP-1507 source text retains the original wording and will be amended by a separate cleanup CHG.

The sub-section is CHG-C1 of PRP-1507 §Implementation Plan; the paired CHG-C2 (FXA-2290) edits the §Decision Tree mermaid block to route into this sub-section.

## Why

PRP-1507 declares the test-writer/implementer split as the rule at RED via CHG-A in COR-1500, but the rule has no operative effect without a concrete orchestrator-side handoff contract. CHG-C1 supplies that contract: 8 numbered steps covering dispatch of the test-writer, RED verification, test-writer commit (`test:` prefix), dispatch of the implementer with the test-writer's commit SHA as input, the implementer's test-file edit constraint with `git diff` enforcement scoped to `<test-writer-paths>`, full-suite verification with COR-1621 triage routing, implementer-as-refactorer default with two-tier enforcement (Tier 1 automated test-name-set + pass-count check; Tier 2 human review of the per-file test diff), and Phase 8 iteration routing across four mutually-exclusive cases (a/b/c/d) with the local-run gate added in R5.5 to prevent state-machine deadlock on additive-coverage requests.

The contract was the largest single surface in the PRP review (most R-round iterations concentrated here): Codex P1s closed in R3.5 (column-shape mismatch, mermaid chain preservation, violation remediation, test-file edit constraint); Gemini P0s closed in R3.5 (Open Questions → Decisions, Phase 8 routing, symmetric fallback); Codex P1s in R5.5 (step 8 commit prefix routing, refactor Tier 1/2 enforcement). The R6 PASS confirms the contract text is implementation-ready.

## Out of Scope

- Editing §Decision Tree — separate surface (a distinct heading region from §Worker Dispatch Contract per CLD-1802 §2 multi-section doc rule); lands as CHG-C2 / FXA-2290.
- Editing COR-1500 §Phase 1 or §Phase 2 — separate surfaces (different file); land as CHG-A / FXA-2287 and CHG-B / FXA-2288.
- Editing COR-1622 schema — separate surface (different file); lands as CHG-D / FXA-2291.
- Setting alfred's `<test-writer-worker-agent>` value — alfred opt-in lands as CHG-E (issue #176).
- Tooling-side detection of in-place assertion weakening — explicitly out of scope per PRP-1507 §C step 7 Tier 2 acknowledgement; deferred to human review.
- Generalising the contract beyond TDD-shaped dispatches (the contract assumes `<test-runner>`, `<linter>`, `<formatter>` exist; non-TDD dispatches continue under the existing single-worker contract).
- Renaming step prefixes (`test:` / `feat:` / `fix:`) — PRP-1507 §C steps 3 + 6 reference COR-1500 §Commit Strategy Option A verbatim.

## Impact Analysis

- **Systems affected:** `src/fx_alfred/rules/COR-1619-SOP-Orchestrator-vs-Worker-Dispatch.md` only (one new sub-section inserted between two existing sections; no existing text modified by this CHG).
- **Behavioural impact:** Adopters who leave `<test-writer-worker-agent>` unset see no behaviour change — the existing single-worker §Worker Dispatch Contract continues to apply; the new §Two-Worker TDD Dispatch sub-section's intro paragraph gates entry on "COR-1500 §Phase 1's 'Worker assignment' rule applies", which requires the parameter to be set distinct. Adopters who set the parameter gain a concrete 8-step contract with explicit retry caps, enforcement diff scopes, fallback semantics, and Phase 8 routing.
- **Compatibility:** Backwards-compatible. The §Worker Dispatch Contract and §Verification sections immediately above and below the new sub-section are untouched; the existing §Decision Tree and §Guard Rails and §Examples sections later in the file are also untouched (Decision Tree is patched by CHG-C2 in the same PR but as a separately-atomic surface).
- **Risk surface:** Low-to-moderate. The new sub-section is large (~50 lines of normative text) and prescriptive; misreading the step-4 test-file edit constraint or the step-7 refactor carve-out could surface as confusion at first adoption. The R6 panel pass mitigates this — every reviewer scored this surface at PASS after the R5.5 step 8 + refactor enforcement fixes — but adopters should expect to consult the contract by-step on their first two-worker dispatch.
- **Rollback plan:** Revert this commit. The sub-section is additive; no other section depends on its existence textually. CHG-C2's mermaid block has a "TW -- Yes --> TW1[TWO-WORKER TDD<br/>see §Two-Worker TDD Dispatch]" edge that becomes a dangling reference if CHG-C1 is reverted without also reverting CHG-C2 — bundle PR revert covers both.

## Acceptance Criteria

- A1: `src/fx_alfred/rules/COR-1619-SOP-Orchestrator-vs-Worker-Dispatch.md` contains a new `## Two-Worker TDD Dispatch` sub-section inserted between the existing `## Worker Dispatch Contract` section (ending at "see §Verification.") and the existing `## Verification (post-dispatch and post-direct-edit)` section.
- A2: The sub-section's body (intro paragraph + 8 numbered steps + Worker unavailability fallback paragraph with three branches + Cost note paragraph) matches PRP-1507 §Proposed Solution lines 95–138 verbatim. The 8 steps are: (1) dispatch test-writer with output constraint + verification + push/commit constraint + enforcement note; (2) orchestrator RED verification with 2-retry cap; (3) orchestrator commits with `test:` prefix; (4) dispatch implementer with reading constraint + test-file edit constraint + verification + enforcement diff scoped to `<test-writer-paths>`; (5) orchestrator GREEN verification with COR-1621 triage routing; (6) orchestrator commits with `feat:`/`fix:` prefix; (7) refactor pass with implementer-as-refactorer default + Tier 1/Tier 2 enforcement + edit-constraint persistence with carve-out; (8) Phase 8 iteration routing across four cases (a/b/c/d) with local-run gate in cases (a) and (c).
- A3: The Worker unavailability fallback paragraph contains all three symmetric branches (test-writer outage, implementer outage, refactor-phase outage) and references `<cli-retry-on-failure>` = `mark-non-viable` per COR-1622 §Resilience.
- A4: The Cost note paragraph references the §Validation plan and the first-three-dispatches re-evaluation trigger.
- A5: No existing text in §Worker Dispatch Contract or §Verification or §Decision Tree or §Guard Rails or §Examples is modified by this CHG. (CHG-C2 patches §Decision Tree in the same PR but as a separately-atomic edit.)
- A6: `Last updated` and `Last reviewed` in COR-1619 frontmatter are updated to 2026-05-17 (one update per file covers both CHG-C1 and CHG-C2).
- A7: A Change History row dated 2026-05-17 referencing CHG-C1 (FXA-2289) and PRP-1507 is appended to COR-1619.
- A8: `af validate --root /Users/frank/Projects/alfred` reports 0 issues after the edit.
- A9: This CHG document (`rules/FXA-2289-CHG-COR-1619-Two-Worker-TDD-Dispatch-Sub-Section.md`) exists, has `Status: Proposed` on creation and is moved to `Status: Completed` in the merge commit.

## Implementation Plan

1. Open `src/fx_alfred/rules/COR-1619-SOP-Orchestrator-vs-Worker-Dispatch.md`.
2. Locate the end of the `## Worker Dispatch Contract` section (the line "The worker's report is a *claim*, not proof. The orchestrator MUST re-run the verification commands locally before staging — see §Verification.").
3. Insert a blank line, then the new `## Two-Worker TDD Dispatch` sub-section verbatim from PRP-1507 §Proposed Solution lines 95–138, then a blank line before the existing `## Verification (post-dispatch and post-direct-edit)` heading.
4. Update `Last updated` and `Last reviewed` to 2026-05-17.
5. Append a Change History row dated 2026-05-17 referencing CHG-C1 (FXA-2289) and PRP-1507.
6. Run `af validate --root /Users/frank/Projects/alfred`; expect 0 issues.
7. CHG-C2 (FXA-2290) edits the same file at §Decision Tree mermaid block. Coordinate the two edits in one editing pass per Implementation Plan of the bundle PR, but document them as separate CHGs per CLD-1802 atomicity.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-17 | Initial version — drafted as CHG-C1 of PRP-1507 §Implementation Plan, bundled with CHG-A/B/C2/D in PR closing issue #175 | Claude Opus 4.7 |
| 2026-05-17 | R1 plan-review panel (alfred triad, gemini substituted for minimax which hit usage limit): glm 9.91, deepseek 10.0, gemini 10.0 — PASS, blocking == []. P3 advisory: TW1 leaf label uses all-caps `TWO-WORKER TDD` while prose heading uses title case — matches PRP-1507 verbatim and existing leaf-label convention (W1-W4, O1-O4 all use all-caps); not folded. P3 advisory: soft revert coupling with CHG-C2 — both rollback plans acknowledge this and recommend bundle-PR revert. Status moved Proposed → Approved. | Claude Opus 4.7 |
| 2026-05-17 | R2 (codex bot static-diff review on PR #177): P2 finding — step 1 enforcement note's `git restore` recovery only covered off-list paths, but a worker that *reports* a production-source edit (in-list but outside test paths) would have its stub/implementation remain in the worktree and could be committed with the RED test in step 3, defeating the no-production-output constraint. Fix: broadened the violation handler to restore *every* modified path outside the approved test paths, whether or not in the reported list. This is a **refinement of PRP-1507 §Proposed Solution line 104** — the verbatim PRP text had the same gap; the SOP text now closes it. Follow-up: PRP-1507 itself should be amended to match (deferred to a separate cleanup CHG; the operative text is here in COR-1619, not in the PRP). | Claude Opus 4.7 |
| 2026-05-17 | R3 (PR #177 codex bot P2 follow-on): R2 fix used `git restore` only, which is a no-op on UNTRACKED files (`??` entries in `git status --porcelain`) — a test-writer that creates a NEW production stub would leave it on disk after recovery, still committable with the RED test in step 3. Fix: split cleanup into `git restore -- <path>` for tracked modifications AND `git clean -f -- <path>` for untracked additions. Both branches cover the same off-test-path scope (whether-or-not in reported list) as in R2. Same PRP-1507 deviation note as R2 — PRP source still needs the matching cleanup CHG. | Claude Opus 4.7 |
| 2026-05-17 | R4 (PR #177 codex bot P2 follow-on, step 4 enforcement note): bare `git restore <test-writer-paths>` only restores the worktree from the already-staged index, so a worker that *staged* a test weakening before returning would leave the weakened test in the index for the next commit. Fix: command updated to `git restore --source=<test-writer-commit> --staged --worktree -- <test-writer-paths>` — restores BOTH index and worktree to the test-writer-commit state. Same PRP-1507 deviation note as R2/R3 — PRP source still needs the matching cleanup CHG. | Claude Opus 4.7 |
| 2026-05-17 | R5 (PR #177 codex bot P2 follow-on, step 1 enforcement note): same class of bug as R4 but on the RED-phase cleanup. R3 wording used bare `git restore -- <path>` which only resets worktree from the already-staged index, so a worker-staged production-source edit would survive and ship with the `test:` commit. Fix: command now uses `git restore --staged --worktree -- <path>` to reset BOTH from HEAD for tracked entries; `git clean -f -- <path>` added for both untracked (`??`) entries AND for the residual after un-staging an `A  path` entry. Same PRP-1507 deviation note as R2/R3/R4. | Claude Opus 4.7 |
| 2026-05-17 | R6 (PR #177 codex bot P2 follow-on, step 4 detection gap): R4 fixed the recovery side; this round addresses the detection side. Bare `git diff <test-writer-commit> -- <test-writer-paths>` compares worktree-vs-commit only — a worker that stages a weakening then restores the worktree before returning leaves no worktree diff (the staged weakening survives in the index). Fix: detection now runs BOTH `git diff <test-writer-commit> -- <test-writer-paths>` (worktree) AND `git diff --cached <test-writer-commit> -- <test-writer-paths>` (index); either non-empty fires the violation handler. Recovery unchanged from R4. Same PRP-1507 deviation note as R2-R5. | Claude Opus 4.7 |
| 2026-05-17 | R7 (PR #177 codex bot P2 follow-on, rename handling + comprehensive rewrite): the recipe-style approach (R2-R5 incremental fixes to step 1) was missing the rename case (`R  oldpath -> newpath` in porcelain — a single `git restore --staged --worktree -- <path>` can't handle this because the porcelain text is "old -> new" not a single pathspec). Rather than incrementally adding another case, the step 1 enforcement note has been rewritten as **contract + implementation guidance**: (a) a normative "Cleanup contract" declares the intent (every off-test entry reset to HEAD, untracked deleted, renames decomposed) independent of specific commands; (b) non-exhaustive guidance covers tracked (M/A/D), untracked (`??`), renames, and a catch-all (`git reset` + `git checkout` + `git clean`). This preempts future codex findings on other git-edge-cases. Same PRP-1507 deviation note as R2-R6. | Claude Opus 4.7 |
