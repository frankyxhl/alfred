# SOP-1614: Multi Phase Execution Contract

**Applies to:** All projects using the COR document system
**Last updated:** 2026-05-06
**Last reviewed:** 2026-05-06
**Status:** Active
**Related:** COR-1103, COR-1202, COR-1500, COR-1602, COR-1612, COR-1615, COR-1801
**Task tags:** [multi-phase, execution-contract, phased-work, continuous-delivery, pr-slices, operator-defaults]
**Authored from:** BAB-2218-CHG-M3-Phase-7-12-Execution-Contract

---

## What Is It?

A workflow for creating a written execution contract before an agent continues
through multiple approved implementation phases or PR slices.

The contract records what is already authorized, what must remain true, how work
will be split, what validation and review gates apply, and when the executor
must stop instead of continuing automatically.

## Why

Approved multi-phase plans create a tension: stopping after every slice wastes
operator attention by re-asking settled questions, but pushing ahead without a
contract can turn a phased plan into an unsafe mega-change. A multi-phase
execution contract preserves both continuity and control.

The contract makes defaults explicit before implementation starts. It also gives
reviewers a stable artifact to check when deciding whether later slices stayed
inside the approved plan.

## When to Use

- An approved PRP, PLN, ADR set, or roadmap spans more than one implementation
  slice.
- The operator wants the executor to continue across slices without re-asking
  already-decided defaults.
- The work needs multiple PRs, review rounds, merge/pull/continue steps, or
  long-running validation decisions.
- The plan includes runtime data, privacy-sensitive outputs, credentials,
  external accounts, generated artifacts, or public PR text that need explicit
  guard rails.
- The executor needs a clear stop list before beginning continuous delivery.

## When NOT to Use

- The task is a single small CHG or one obvious PR.
- Product direction, architecture, schema, or ownership is still unsettled; use
  COR-1102 or the project proposal route first.
- The operator is only asking for a session plan; use COR-1202.
- A production incident needs immediate containment; use the project incident
  route and any emergency CHG process.
- The contract would grant broad permission without concrete slices, validation
  gates, and stop conditions.

## Prerequisites

- A higher-authority plan exists, such as an approved PRP, PLN, ADR, or
  reviewed roadmap.
- The operator has resolved the decisions that the contract will treat as
  defaults.
- The executor can name at least two slices and the exit condition for each.
- Review and validation expectations are known enough to write down.
- Privacy, runtime-data, credentials, and public-write constraints are known.

## Contract Contents

Every multi-phase execution contract should include these sections:

1. **Authority documents** - the approved PRP, PLN, ADRs, issue, or prior CHG
   that the contract is subordinate to.
2. **Operator defaults and permissions** - actions the executor may take without
   re-asking while the contract remains true.
3. **Non-negotiable behavior** - product, architecture, privacy, runtime-data,
   account, or review invariants that slices must not violate.
4. **Execution slices** - reviewable PR-sized slices with scope, out-of-scope
   boundaries, tests, validation, and exit conditions.
5. **Validation matrix** - commands, coverage or quality gates, long-run
   validations, and explicitly deferred checks.
6. **External review policy** - local review before PR, PR review bot workflow,
   round caps, and how actionable findings are handled.
7. **Branch, PR, and merge policy** - branch naming, draft/non-draft default,
   commit scope, merge/pull/continue sequence, and rollback expectations.
8. **Runtime-data and privacy rules** - what must not be committed, logged, or
   published in PR text or comments.
9. **Stop conditions** - conflicts, missing credentials, failing gates, review
   caps, destructive operations, or scope changes that require pausing.
10. **Retention and closeout** - where the contract, slice outcomes, review
    evidence, and deviations are recorded.

## Rules

- Continuous execution does not mean one large PR.
- The contract cannot override higher-authority ADRs, PRPs, PLNs, or project
  routing documents.
- Every slice must stay independently reviewable, testable, and revertable.
- Operator defaults are valid only while the contract remains true.
- Open questions become explicit decisions before implementation proceeds.
- Runtime data, credentials, private host details, and local-only paths must not
  become public artifacts by accident.
- External review caps must be explicit before the first PR opens.
- After every merge, pull the updated base and verify the next slice still
  matches the contract.
- If a project-specific execution contract becomes a reusable cross-project
  pattern, evaluate that follow-on promotion through COR-1801.

## Stop Conditions

Stop and report instead of continuing when:

- a slice would violate an authority document or contract rule;
- implementation requires a new product, architecture, schema, or ownership
  decision;
- required credentials, accounts, tools, or binaries are unavailable and no
  deterministic fallback preserves the acceptance claim;
- a validation gate fails for reasons that cannot be isolated safely;
- a review-loop cap is reached while required findings remain;
- continuing would require committing runtime data, transcripts, secrets,
  private network details, local absolute paths, or host-specific state;
- a destructive git or production operation would be needed;
- the next slice is materially larger or riskier than the contract described.

## Review And PR Policy

- Run the selected local review workflow before opening each PR when the project
  requires it.
- After a PR opens, use COR-1615 for GitHub App review bot trigger/poll/current
  head matching when such a bot is part of the gate.
- Use COR-1612 for fetched PR review findings: classify, fix, validate, reply,
  and push.
- Do not treat acknowledgement reactions, queued states, or old-head reviews as
  approval.
- Record skipped long validations and the reason they were deferred.
- If the contract defines a review cap, stop at that cap and summarize instead
  of silently continuing.

## Steps

1. **Confirm authority** - name the higher-authority documents and verify the work is already approved for multi-phase execution.
2. **Capture operator defaults** - write the permissions, account constraints, review caps, long-validation decisions, and continuation expectations.
3. **List non-negotiables** - record product, architecture, runtime-data, privacy, and review invariants.
4. **Define slices** - split the work into reviewable slices with scope, out-of-scope boundaries, tests, validation, and exit conditions.
5. **Define validation** - list normal gates, slice-specific gates, coverage or quality expectations, long validations, and deferred checks.
6. **Define review and PR flow** - specify local review, branch naming, PR default, GitHub App review loop, review-response route, merge policy, and continuation after merge.
7. **Define stop conditions** - write the exact conflicts or failures that halt automatic continuation.
8. **Review the contract** - run the appropriate review workflow before using the contract as execution authority.
9. **Execute slice by slice** - follow the contract, validate each slice, open focused PRs, and resolve review findings.
10. **Re-check after each merge** - pull the base branch, verify the next slice still matches the contract, then continue or stop.
11. **Close out and retain evidence** - update the contract or tracker with review results, deviations, skipped checks, merge status, and follow-up work.

## Completion Criteria

- Authority documents are named and the contract is subordinate to them.
- Operator defaults and permissions are explicit.
- Every slice has scope, tests, validation, and exit conditions.
- Privacy, runtime-data, and public-write rules are explicit.
- Stop conditions are specific enough for an executor to halt without guessing.
- Local and PR review loops are named with caps or escalation rules.
- The contract and originating evidence remain traceable after the work
  completes.

## Examples

### Example 1 - Promote an approved roadmap into continuous execution

An approved roadmap has four remaining phases. The operator has already decided
the implementation order, validation gates, and review cap. Create a contract
that records those defaults, splits the work into four PR slices, and lets the
executor continue after each merge while all stop conditions remain false.

### Example 2 - Do not use for unresolved design

A proposal says "build a new sync system" but the storage model and conflict
rules are undecided. Do not write an execution contract yet. Route to PRP/design
review first, then write a contract only after the design is approved.

### Example 3 - Stop after review cap

A slice reaches the contract's review cap while a required PR finding remains.
The executor stops, reports the unresolved finding and validation state, and
does not continue to the next slice until the operator resolves the conflict.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-06 | Initial version promoted from BAB-2218 per FXA-2242. | Codex |
