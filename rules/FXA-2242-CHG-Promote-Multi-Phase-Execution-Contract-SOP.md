# CHG-2242: Promote Multi Phase Execution Contract SOP

**Applies to:** FXA project
**Last updated:** 2026-05-06
**Last reviewed:** 2026-05-06
**Status:** In Progress
**Date:** 2026-05-06
**Requested by:** Frank
**Priority:** Medium
**Change Type:** Normal
**Related:** BAB-2218, BAB-2219, BAB-2220, COR-1300, COR-1613, COR-1801, COR-1000, COR-1101, COR-1302, COR-1602, COR-1609, COR-1612, COR-1615
**Tags:** promotion, multi-phase, execution-contract, pkg-governance

---

## What

Promote the reusable parts of `BAB-2218: M3 Phase 7-12 Execution
Contract` into a PKG-layer COR SOP:

`COR-1614-SOP-Multi-Phase-Execution-Contract.md`

The new SOP standardizes how an operator and agent turn an approved
multi-phase plan into a bounded execution contract: authority references,
operator defaults, reviewable slices, validation gates, review-loop caps,
privacy/runtime-data rules, stop conditions, and after-merge continuation.

## Why

`BAB-2218` solved a repeatable governance problem: when a plan is already
approved across several phases, the agent needs enough authorization to continue
without repeatedly interrupting the operator, while still preserving small PRs,
review gates, validation, and rollback boundaries.

Without a COR-level SOP, other projects will either copy the Babs contract
verbatim or improvise weaker variants. A promoted SOP gives them a reusable
pattern while removing Babs-specific details such as M3, Ticket/Billboard,
Citizen names, local paths, accounts, and phase numbers.

## Impact Analysis

- **Systems affected:**
  - `src/fx_alfred/rules/COR-1614-SOP-Multi-Phase-Execution-Contract.md` -
    new PKG SOP.
  - `src/fx_alfred/rules/COR-0000-REF-Document-Index.md` - add COR-1614.
  - `src/fx_alfred/rules/COR-1103-SOP-Workflow-Routing.md` - add routing
    discoverability for multi-phase execution contracts.
  - `src/fx_alfred/rules/COR-1613-SOP-Council-Review.md` - release the
    deferred `COR-1614-REF-Decision-Mechanism-Library` fallback ACID by changing
    that future split plan to use the next open ACID at the time of the split.
  - `rules/FXA-0000-REF-Document-Index.md` - add this CHG entry.
  - `rules/FXA-2242-CHG-Promote-Multi-Phase-Execution-Contract-SOP.md` - this
    promotion record.
- **Not affected:** CLI behavior, package schema, templates, runtime code,
  dependencies, and release version.
- **Origin retention:** `BAB-2218` remains the evidence artifact. It should be
  updated in the Babs repository with a pointer to COR-1614 when the Babs
  worktree is ready for that project-level doc update.
- **Rollback plan:** Revert the document-only implementation commit, including
  COR-1614, COR-0000, COR-1103, COR-1613, FXA-0000, and this CHG closeout. If
  implementation is split across multiple commits, revert all related commits
  in reverse order. Then rerun `PYTHONPATH=src .venv/bin/af validate --root .`
  and verify `af read COR-1614` no longer resolves.

## Candidate Pattern Contract

| Field | Value |
|-------|-------|
| Origin | `BAB-2218-CHG-M3-Phase-7-12-Execution-Contract.md` |
| Trial status | Active trial with one completed slice and one active follow-on slice |
| Pattern rule | For approved multi-phase work, create a contract that records the authority documents, operator defaults, non-negotiables, reviewable execution slices, validation matrix, external review policy, privacy/runtime-data rules, and hard stop conditions before continuous execution begins. |
| Scope | Agents and operators executing already-approved multi-phase plans through multiple reviewable PRs. |
| When to use | A plan spans multiple phases or PRs, directional decisions are already known, and the operator wants continuous delivery without repeated prompts for already-decided defaults. |
| When not to use | Single-slice work, unresolved product design, emergency fixes, vague permission requests, or work where runtime/privacy boundaries are not yet understood. |
| Evidence | `BAB-2218` approved after Trinity fast-review R2; PR #15 merged the PRP and contract; `BAB-2219` consumed PR A and PR #16 merged; `BAB-2220` is consuming PR B. |
| Promotion criteria | Promote if the abstracted COR SOP preserves the BAB-2218 safety properties, removes project-specific assumptions, defines clear when-not-to-use and stop-condition rules, and local Trinity review finds no blockers. |
| Retention plan | Keep `BAB-2218` as historical evidence. Add a pointer to COR-1614 later in Babs; do not delete or rewrite the originating CHG. |

## Promotion Evaluation

Per `COR-1801`, this is treated as a high-risk governance pattern because it
creates a multi-project workflow contract. The high-risk bar is met by explicit
maintainer endorsement plus risk rationale, rather than cross-project adoption:

- **Use count:** two substantial uses in one project. `BAB-2218` governed
  Phase 7 through `BAB-2219` and is governing Phase 8 through `BAB-2220`.
- **Cross-project evidence:** not yet independent, but the operator/maintainer
  explicitly asked to promote the pattern into COR. This satisfies the high-risk
  maintainer-endorsement substitute in COR-1801 because waiting for a second
  project would keep a known useful governance pattern local while active
  multi-phase delivery work is already reusing it.
- **Failure-mode demo:** known misuse cases are one unsafe mega-PR, contract
  text that silently overrides higher-authority ADR/PRP documents, public PR
  leakage of local paths/secrets, and agents continuing after a stop condition.
- **Time in trial:** less than 14 days, but one complete PR slice/review/merge
  cycle has completed. Maintainer explicitly accepts the lowered time-in-trial
  bar because the pattern is actively governing live multi-phase delivery and
  deferring promotion would leave the next similar contract without COR
  governance.
- **Counter-evidence:** no blocking review findings remain on `BAB-2218`.
  `BAB-2219` review found implementation issues that the contract's review-loop
  cap and external-review rules handled instead of bypassing.

Failure-mode mitigations:

- **Unsafe mega-PR:** COR-1614 must require reviewable slices and per-slice exit
  conditions.
- **Authority override:** COR-1614 must require subordinate authority references
  and stop-on-conflict behavior.
- **Public leakage:** COR-1614 must require privacy/runtime-data rules and
  changed-file scans before PR text or comments.
- **Continuation past blockers:** COR-1614 must define stop conditions and
  review-loop caps before execution begins.

Residual risk: early promotion means COR-1614 may need revision after the next
one or two multi-phase projects use it. This is acceptable because the pattern is
document-only, rollback is a document revert, and COR-1801 de-promotion or
amendment remains available if evidence turns negative.

Decision state requested: `promote`.

PKG relationship classification: create a new COR SOP rather than amend an
existing one. COR-1500 owns TDD for one implementation flow, COR-1602 owns
multi-reviewer parallel review, COR-1202 owns session-plan composition, and
COR-1103 owns routing. None of those documents owns the higher-level contract
that authorizes continuous delivery across multiple reviewed PR slices.

## Implementation Plan

1. Review this CHG locally with Trinity fast-review using `~/.codex/trinity.json`
   and the `fast-review` preset (`glm` + `deepseek`).
2. Revise until both reviewers pass or only explicitly accepted non-blocking
   advisories remain.
3. Create `COR-1614` in the PKG rules directory with:
   - COR-1000 conventions for new SOP metadata, ACID assignment, structure,
     and index maintenance;
   - standard SOP metadata and `Task tags`;
   - `Authored from: BAB-2218-CHG-M3-Phase-7-12-Execution-Contract`;
   - What/Why/When/When NOT sections;
   - prerequisites and contract contents;
   - positive rules, stop conditions, PR/merge policy, validation guidance,
     privacy/runtime-data guidance, retention guidance, examples, and steps.
4. Update `COR-0000` with the `1614 | SOP | Multi Phase Execution Contract`
   row.
5. Update `COR-1103` with routing and golden-rule pointers:
   - route approved multi-phase continuous-execution work to COR-1614 before
     implementation continues, either as a Route 4 execution-coordination
     sub-branch or as an overlay when an approved plan already exists;
   - add a golden rule that continuous multi-phase delivery requires an
     explicit contract with reviewable slices, validation gates, and stop
     conditions.
6. Amend `COR-1613` Open Questions to release the hard-coded
   `COR-1614-REF-Decision-Mechanism-Library` fallback. Future decision
   mechanism library extraction must use the next open ACID at the time of that
   future CHG, not the now-assigned COR-1614.
7. Run local verification:
   - `PYTHONPATH=src .venv/bin/af validate --root .`
   - `PYTHONPATH=src .venv/bin/af read --root . COR-1614`
   - `PYTHONPATH=src .venv/bin/af plan --root . COR-1614 --todo --graph-format=ascii --graph`
   - `PYTHONPATH=src .venv/bin/af plan --root . --task "multi phase execution contract" --todo --graph-format=ascii --graph`
   - `git diff --check`
   - privacy/local-detail scan over changed files.
8. Run Trinity fast-review on the implementation diff using
   `~/.codex/trinity.json`.
9. Iterate locally until GLM and DeepSeek approve.
10. Mark this CHG completed, commit, push a branch, and open a PR.
11. After PR creation, use COR-1615 to trigger/poll GitHub App review bot
    results and COR-1612 to fetch, classify, fix, validate, and reply to
    actionable findings until final review is clean.

## Contract Preview

The promoted SOP should abstract the BAB-2218 pattern into a reusable contract
shape like this:

```markdown
## Contract Contents

1. Authority documents: the approved PRP/ADR/PLN this contract is subordinate to.
2. Operator defaults: what the executor may do without re-asking.
3. Non-negotiables: product, privacy, runtime-data, and review-loop invariants.
4. Execution slices: each PR-sized slice with scope, tests, validation, and exit condition.
5. Review policy: local review before PR, GitHub review bot loop after PR, and cap rules.
6. Stop conditions: when the executor must pause instead of continuing.
7. Retention: how the originating plan and contract remain auditable.
```

The SOP body must make the core rule explicit: continuous execution authorizes
continuity of already-decided defaults, not larger blast radius.

## Acceptance Criteria

- [x] `COR-1614-SOP-Multi-Phase-Execution-Contract.md` exists in the PKG
  layer.
- [x] COR-1614 defines when to use and when not to use a multi-phase execution
  contract.
- [x] COR-1614 defines required contract sections: authority, operator
  defaults, execution slices, validation matrix, external review policy,
  branch/PR/merge policy, runtime/privacy rules, stop conditions, and retention
  guidance.
- [x] COR-1614 makes clear that continuous execution does not authorize one
  unsafe mega-PR or override higher-authority ADR/PRP documents.
- [x] COR-0000 and COR-1103 are updated for discovery.
- [x] COR-1613 Open Question 1 no longer hard-codes
  `COR-1614-REF-Decision-Mechanism-Library.md` as a future ACID.
- [x] Local validation and Trinity implementation fast-review pass before the PR
  is opened.
- [ ] PR feedback is completed through COR-1615 and COR-1612.

## Open Questions / Defaults

- **New SOP or amend existing SOP?** Default: new SOP. No existing COR SOP owns
  the multi-phase execution-contract responsibility.
- **ACID?** Default: COR-1614. It is absent from COR-0000 and sits between
  Council Review (`COR-1613`) and GitHub App PR review bot loop (`COR-1615`).
  COR-1613 currently mentions a deferred future `COR-1614-REF` extraction; this
  CHG explicitly releases that hard-coded fallback and changes the future split
  plan to use the next open ACID when that future CHG happens.
- **Need PRP first?** Default: no. This promotion creates a document-only
  governance SOP and does not change CLI behavior, schema, review thresholds, or
  multiple COR workflows. If Trinity finds unresolved design trade-offs, route
  to PRP before implementation.
- **Babs origin update in this PR?** Default: no. Babs lives in a separate
  repository with active unrelated work. Preserve the retention requirement in
  this CHG and update `BAB-2218` separately when the Babs worktree is ready.

## Testing / Verification

Pre-implementation:

- [x] CHG review R1: `trinity review --config ~/.codex/trinity.json --root . --preset fast-review --scope rules/FXA-2242-CHG-Promote-Multi-Phase-Execution-Contract-SOP.md`
- [x] CHG review R2: same command after R1 advisories
- [x] CHG review R3: same command after COR-1613 ACID-reservation blocker resolution

Implementation:

- [x] `PYTHONPATH=src .venv/bin/af validate --root .`
- [x] `PYTHONPATH=src .venv/bin/af read --root . COR-1614`
- [x] `PYTHONPATH=src .venv/bin/af plan --root . COR-1614 --todo --graph-format=ascii --graph`
- [x] `PYTHONPATH=src .venv/bin/af plan --root . --task "multi phase execution contract" --todo --graph-format=ascii --graph`
- [x] `git diff --check`
- [x] Privacy/local-detail scan over changed files
- [x] Implementation review, PKG docs: `trinity review --config ~/.codex/trinity.json --root . --preset fast-review --scope src/fx_alfred/rules`
- [x] Implementation review, FXA docs: `trinity review --config ~/.codex/trinity.json --root . --preset fast-review --scope rules`

## Approval

- [x] CHG reviewed by Trinity fast-review
- [x] Approved for COR-1614 implementation
- [x] Implementation reviewed by Trinity fast-review before PR

## Execution Log

| Date | Action | Result |
|------|--------|--------|
| 2026-05-06 | Created promotion CHG. | Ready for Trinity fast-review before implementation. |
| 2026-05-06 | Trinity fast-review R1. | GLM PASS and DeepSeek PASS 9.1/10 with advisories. Folded in acceptance criteria, open defaults, COR-1000 invocation, new-SOP rationale, concrete COR-1103 routing target, and root-relative commands. |
| 2026-05-06 | Trinity fast-review R2. | DeepSeek PASS 9.0/10; GLM found a blocker that COR-1614 was hard-coded in COR-1613 as a possible future decision-mechanism-library REF. Expanded this CHG to release that deferred fallback by amending COR-1613 during implementation. |
| 2026-05-06 | Trinity fast-review R3. | GLM PASS and DeepSeek PASS 9.1/10. Folded in advisories for explicit time-in-trial waiver, failure-mode mitigations, residual risk, COR-1613 acceptance criterion, and COR-1103 placement guidance. CHG approved for implementation. |
| 2026-05-06 | Implemented COR-1614 and references. | Added COR-1614, COR-0000 row, COR-1103 routing and golden rule, and COR-1613 fallback release. Local validation, read/plan smoke checks, diff whitespace check, and privacy scan passed. |
| 2026-05-06 | Trinity implementation review, PKG docs. | Scope `src/fx_alfred/rules`: GLM PASS and DeepSeek PASS. Folded in advisory fixes for COR-0000 Last updated date and COR-1801 body reference in COR-1614. |
| 2026-05-06 | Trinity implementation review, FXA docs. | Scope `rules`: GLM PASS and DeepSeek PASS with non-blocking advisories only. Ready for PR creation. |

## Post-Change Review

- Pending until COR-1614 is implemented, locally reviewed, and PR feedback is
  resolved.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-06 | Initial CHG for promoting the BAB-2218 execution contract pattern to COR-1614. | Codex |
| 2026-05-06 | Fold in Trinity R1 advisories before implementation. | Codex |
| 2026-05-06 | Address Trinity R2 ACID-reservation blocker by adding COR-1613 fallback-release scope. | Codex |
| 2026-05-06 | Mark CHG approved after Trinity R3 PASS and advisory fold-in. | Codex |
| 2026-05-06 | Record implementation verification and Trinity implementation review results. | Codex |
