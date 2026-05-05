# SOP-1801: Pattern Promotion

**Applies to:** All projects using the COR document system
**Last updated:** 2026-05-05
**Last reviewed:** 2026-05-05
**Status:** Active
**Related:** COR-1800, COR-1000, COR-1101, COR-1102, COR-1300, COR-1301, COR-1500, COR-1602, COR-1608, COR-1609, COR-1610, COR-1613
**Task tags:** [pattern-promotion, prj-to-pkg, promotion, evolution, governance]

---

## What Is It?

A workflow for evaluating a proven PRJ-layer trial pattern and promoting it into the PKG/COR layer when it is reusable across projects.

Pattern promotion converts local practice into shared package governance without losing the originating evidence trail.

---

## Why

Projects often discover useful operating patterns before the package does. Without a promotion workflow, those patterns either stay trapped in one project or get copied into PKG too early while still carrying project-specific assumptions.

This SOP creates a reviewed path for deciding when a PRJ pattern should become a COR document, when an existing COR document should be amended instead, and when the pattern should stay local.

---

## When to Use

- A PRJ SOP, REF, checklist, prompt, or review loop has worked repeatedly and may benefit other projects.
- A project maintainer asks whether a local pattern should be generalized into PKG.
- A GitHub issue or CHG proposes moving a project-specific practice into a COR document.
- A pattern overlaps existing COR governance and needs a decision: create a new COR document, amend an existing one, defer, revise, or reject.
- A promoted PKG document may need reversal because later evidence shows it should not remain active.

---

## When NOT to Use

- The pattern is still an untested idea. Use a PRJ trial document first.
- The pattern only applies to one repository, host, account, vendor setup, or local environment.
- The request is just a normal edit to an existing COR document with no PRJ-to-PKG promotion question; use COR-1300.
- The request creates a new product capability, schema, CLI behavior, or architecture before the governance question is clear; use COR-1102 first.
- The promoted document is already active and only needs retirement; use COR-1301 directly unless a promotion-specific reversal decision is needed.

---

## Prerequisites

- An originating PRJ artifact exists or is summarized well enough to audit.
- The candidate pattern has trial evidence, not only author preference.
- The operator can identify the pattern rule, its scope, and at least one case where it should not be used.
- The promotion work has a GitHub issue or CHG so the decision is reviewable.
- If the promotion changes code, schema, CLI behavior, or tests, COR-1500 applies as an overlay.

---

## Candidate Pattern Contract

A candidate is ready for promotion review only when it defines these fields:

| Field | Required content |
|-------|------------------|
| Origin | PRJ document ID, issue, PR, CHG, discussion note, or summarized source |
| Trial status | Active trial, completed trial, superseded local pattern, or failed trial |
| Pattern rule | The reusable decision rule or operating loop in one paragraph |
| Scope | Who should use it and which artifact or workflow it governs |
| When to use | Concrete triggers that start the pattern |
| When not to use | Cases where the pattern would be noise, unsafe, or too local |
| Evidence | Linked or summarized uses, failures, reviews, and maintainer endorsements |
| Promotion criteria | Explicit threshold for promote, defer, revise, or reject |
| Retention plan | How the originating PRJ artifact will remain traceable after promotion |

If any field is missing, choose `revise` unless the pattern is clearly unsuitable.

---

## Promotion Criteria

Use these templates as the default evidence bar. A CHG may raise the bar, but it should not lower it without recording maintainer approval.

| Criterion | Normal pattern baseline | High-risk pattern baseline |
|-----------|-------------------------|----------------------------|
| Use count | At least 3 successful uses, or 2 substantial uses plus explicit maintainer endorsement | At least 5 successful uses across 2 projects, or explicit maintainer endorsement with risk rationale |
| Cross-project evidence | At least 1 independent project adoption, or maintainer endorsement that the pattern is intentionally PKG-level | At least 2 independent project adoptions, or council/maintainer endorsement recorded in the CHG |
| Failure-mode demo | At least 1 known failure mode, "when not to use" case, or defer/reject example | Failure modes plus mitigations for the most likely misuse cases |
| Time in trial | At least 14 days or 1 complete review/release/change cycle | At least 30 days or 2 complete review/release/change cycles |
| Counter-evidence review | Search issues, PR reviews, retrospectives, or discussion notes for objections and failures | Same as normal, plus explicit residual-risk notes in the CHG |

A high-risk pattern changes governance families, review thresholds, release gates, schema, CLI behavior, security-sensitive operations, or multi-project workflow contracts.

Maintainer endorsement can substitute for cross-project adoption when the pattern is foundational package governance and the CHG explains why waiting for another project would block useful standardization.

---

## Promotion Decisions

Choose exactly one first-time promotion state:

| State | Meaning | Required next action |
|-------|---------|----------------------|
| `promote` | The pattern is reusable, evidence meets the bar, and PKG is the right layer | Implement the PKG change through CHG/PR and assign a new COR ACID |
| `defer` | The pattern may be useful, but evidence is not strong enough yet | Keep the PRJ trial; record the re-nomination trigger |
| `reject` | The pattern is too local, unsafe, obsolete, or conflicts with COR principles | Record the reason; do not promote unless new evidence changes the decision |
| `revise` | The idea is promising but the candidate is incomplete or too project-specific | Revise the candidate contract or PRJ source, then rerun promotion review |

Use `defer` when the main gap is evidence. Use `revise` when the main gap is document quality, abstraction, or missing contract fields.

---

## Governance Interactions

- Use a GitHub issue plus CHG as the default promotion vehicle.
- Use COR-1102 first when the promotion creates a new governance family, changes schema or CLI behavior, has unresolved design trade-offs, or substantially changes multiple COR workflows.
- Use COR-1101 for the implementation CHG.
- Use COR-1000 when promotion creates a new PKG SOP.
- Use COR-1300 when promotion amends an existing PKG document instead of creating a new one.
- Use COR-1301 when a promoted document must be deprecated or superseded.
- Use COR-1500 when the promotion includes code, tests, CLI behavior, or package assets beyond documents.
- Use COR-1608 for PRP scoring, COR-1609 for CHG scoring, COR-1610 for code review scoring, and COR-1613 for the multi-reviewer decision rule.
- Use COR-1602 or another COR-1600 through COR-1605 workflow according to the review or implementation shape.

---

## PKG Authoring Conventions

- Assign a new COR ACID. Never reuse the originating PRJ ACID in the PKG layer.
- Prefer amending an existing COR document when the pattern is an extension of that document's current responsibility.
- Create a new COR document only when the pattern is atomic, reusable, and not already owned by an existing SOP or REF.
- Remove project names, local paths, local accounts, private hostnames, and repository-specific commands from normative steps.
- Keep project-specific facts only in examples or an origin-evidence section.
- Preserve origin traceability with `Related` metadata, an `Authored from` field when appropriate, or a short example that names the originating PRJ artifact.
- Turn local commands into variables or generic command templates.
- Define both positive triggers and "when not to use" cases.
- Keep the originating PRJ document after promotion. Do not delete the evidence trail.

---

## PRJ Retention After Promotion

After a PRJ pattern is promoted:

1. Leave the originating PRJ artifact in place unless there is a separate deprecation CHG.
2. Add a note to the PRJ artifact pointing to the promoted COR document.
3. If the PRJ document should no longer be executed locally, deprecate it per the PRJ equivalent of COR-1301.
4. Preserve links to trial evidence, review notes, and failures.
5. Do not rewrite the PRJ history to make the promotion appear inevitable.

The PRJ artifact remains historical evidence. The COR document becomes the reusable source of truth.

---

## De-promotion / Reversal

Use this path only after a pattern has already been promoted.

1. Open or reuse a GitHub issue describing why the PKG document may no longer be valid.
2. File a CHG that cites the promoted COR document, the originating PRJ evidence, and the new counter-evidence.
3. Decide whether to amend, supersede, deprecate, or keep the COR document.
4. If the document should retire, deprecate it per COR-1301 instead of deleting it.
5. Update indexes and references so users are routed to the replacement or warned that no replacement exists.
6. Keep both the original promotion record and reversal record auditable.

---

## Guard Rails

- Do not promote a pattern only because it worked once.
- Do not promote host-specific, account-specific, or repository-specific details into normative PKG text.
- Do not let the promotion workflow modify its own evidence standards without a separate CHG or PRP.
- Do not treat a `defer` decision as rejection; it is a request for more evidence.
- Do not delete source PRJ artifacts during promotion.
- Do not use COR-1801 to bypass COR-1102 when the proposed change needs design approval first.

---

## Steps

### 1. Nominate the candidate pattern

Create or identify a GitHub issue and CHG that states the originating PRJ artifact, the pattern rule, why it may be PKG-level, and the requested outcome.

### 2. Validate the candidate contract

Check the Candidate Pattern Contract table. If origin, scope, when-to-use, when-not-to-use, evidence, or retention plan is missing, choose `revise` or update the CHG before implementation.

### 3. Gather evidence

Collect use count, cross-project evidence, failure modes, time-in-trial, and counter-evidence. Summaries are acceptable when the originating project is not available on the current machine, but the summary must be specific enough for reviewers to evaluate.

### 4. Classify the PKG relationship

Decide whether the pattern should amend an existing COR document, create a new COR document, remain PRJ-local, or be rejected. Prefer amendment when an existing SOP already owns the responsibility.

### 5. Run promotion review

Review the CHG using the selected COR-1600 through COR-1605 workflow and declare the COR-1613 decision rule if multiple reviewers are used. For CHGs, apply COR-1609 scoring. For PRPs, apply COR-1608 scoring.

### 6. Choose the decision state

Record exactly one of `promote`, `defer`, `reject`, or `revise` in the CHG or issue. For `defer`, include the re-nomination trigger. For `revise`, list the missing candidate-contract fields or abstraction fixes.

### 7. Implement the PKG change when promoting

If creating a new SOP, follow COR-1000 and assign a new COR ACID. If amending an existing document, follow COR-1300. If code is involved, follow COR-1500. Update package indexes, routing references, and related documents.

### 8. Retain the origin and verify

Update the originating PRJ artifact with a pointer to the promoted COR document or recorded decision. Run package validation and any relevant CLI read/plan/list checks. Record review artifacts and verification results in the CHG or PR.

---

## Completion Criteria

- Candidate contract is complete or the decision explicitly explains why it is not.
- Promotion criteria are evaluated against evidence, not preference.
- Decision state is recorded as `promote`, `defer`, `reject`, or `revise`.
- If promoted, the PKG document uses a new COR ACID and does not reuse the PRJ ACID.
- If promoted, project-specific details are abstracted out of normative text.
- Existing COR documents are amended instead of duplicated when they already own the behavior.
- Originating PRJ evidence is retained and linked or summarized.
- Related indexes, routing documents, and references are updated.
- Review and validation results are recorded.

---

## Examples

### Example 1: Promoting a PR review bot loop

An originating PRJ SOP, `BAB-1504-SOP-GitHub-Codex-PR-Review-Loop`, proved a repeatable loop for requesting and interpreting a Codex GitHub App review. Promotion review found the core pattern was not BAB-specific: request once, poll without spam, match the review to the current PR head, and hand actionable findings to the PR-comment response SOP.

The PKG version became COR-1615. It removed project-specific assumptions, generalized the wording to GitHub App PR review bots including Codex and Copilot, retained origin traceability, and added package-level guard rails for visible-write identity and current-head matching.

Decision: `promote`.

### Example 2: Deferring the KIW-0710 R3-outcome triple fork

An originating PRJ trial SOP from the Kiwari project, known as KIW-0710, describes an R3 review outcome pattern. The inline pattern is: after a multi-reviewer round, classify the outcome as exactly one of `unanimous pass`, `leader accept with logged residual`, or `escalate`, instead of treating review completion as binary pass/fail.

Summarized evidence cites use in Kiwari review tracking, including CHG-1300 Track A2 and CHG-1400. The rule is clear and potentially useful, but this summarized evidence alone does not show independent project adoption or explicit maintainer endorsement for PKG-level promotion.

Decision: `defer`.

Re-nomination trigger: provide at least one independent project adoption, or record maintainer endorsement that this is intentionally PKG-level despite limited cross-project evidence.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-05 | Initial SOP for PRJ-to-PKG pattern promotion per FXA-2239. | Codex |
