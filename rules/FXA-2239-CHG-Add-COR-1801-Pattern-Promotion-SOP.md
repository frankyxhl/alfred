# CHG-2239: Add COR-1801 Pattern Promotion SOP

**Applies to:** FXA project
**Last updated:** 2026-05-05
**Last reviewed:** 2026-05-05
**Status:** Completed
**Date:** 2026-05-05
**Requested by:** Frank
**Priority:** Medium
**Change Type:** Normal
**Related:** GitHub issue #62, COR-1800, COR-1000, COR-1102, COR-1101, COR-1300, COR-1301, COR-1500, COR-1602, COR-1613

---

## What

Add a new PKG-level SOP, `COR-1801: Pattern Promotion`, that formalizes how a proven PRJ-layer trial pattern is evaluated and promoted into the PKG/COR layer.

The proposed SOP will cover:

- candidate pattern definition;
- evidence and promotion criteria templates;
- promotion issue workflow;
- reviewer decision states;
- PKG authoring conventions;
- PRJ historical-retention rules after promotion;
- de-promotion / reversal workflow;
- a worked example based on KIW-0710 as illustrative source material only.

## Why

GitHub issue #62 identifies a current gap: Alfred supports PKG / USR / PRJ layers, but it does not document a reusable workflow for lifting a pattern from PRJ trial status into a universal PKG/COR SOP after the pattern proves itself.

Without a promotion SOP:

- useful PRJ patterns can remain local and rediscovered by each project;
- immature or project-specific patterns can be promoted too early;
- reviewers lack a shared rubric for deciding `promote`, `defer`, `reject`, or `revise`;
- PRJ source documents may be deleted or overwritten, losing the evidence trail.

This CHG creates the missing governance path without changing CLI behavior.

## Impact Analysis

- **Systems affected:**
  - `src/fx_alfred/rules/COR-1801-SOP-Pattern-Promotion.md` — new PKG SOP.
  - `src/fx_alfred/rules/COR-0000-REF-Document-Index.md` — add COR-1801.
  - `src/fx_alfred/rules/COR-1800-REF-Evolution-Philosophy.md` — add relationship pointer to COR-1801.
  - `src/fx_alfred/rules/COR-1103-SOP-Workflow-Routing.md` — add routing hint for PRJ-to-PKG pattern promotion.
  - `rules/FXA-0000-REF-Document-Index.md` — add this CHG entry.
- **Not affected:**
  - CLI commands, package version, schema fields, and templates.
  - Any local Kiwari files; KIW-0710 is not a runtime or validation dependency.
  - Automatic promotion tooling. Promotion remains a reviewed document workflow.
- **Rollback plan:** Commit the implementation atomically; rollback is reverting that document-only commit and rerunning `PYTHONPATH=src .venv/bin/af validate --root .`. If implementation is split across multiple commits, revert all related commits together.

## Implementation Plan

1. **Review this CHG first** — completed via `trinity review --preset fast-review --scope rules/FXA-2239-CHG-Add-COR-1801-Pattern-Promotion-SOP.md`; implementation may start only after the CHG status is `Approved`.
2. **Create COR-1801** in PKG:
   - filename: `src/fx_alfred/rules/COR-1801-SOP-Pattern-Promotion.md`;
   - title: `Pattern Promotion`;
   - type: SOP;
   - status: Active.
3. **Author COR-1801 core sections:**
   - What Is It?
   - Why
   - When to Use
   - When NOT to Use
   - Candidate Pattern Contract
   - Promotion Criteria
   - Promotion Workflow
   - PKG Authoring Conventions
   - PRJ Retention After Promotion
   - De-promotion / Reversal
   - Worked Example
   - Steps
   - Completion Criteria
   The `Steps` section must include this decision workflow:
   1. Nominate candidate pattern from PRJ evidence.
   2. Validate candidate contract completeness.
   3. Gather evidence against explicit criteria.
   4. Classify relationship to existing PKG documents: amend existing SOP/REF, create new COR document, defer, or reject.
   5. Run promotion review and choose exactly one first-time promotion state: `promote`, `defer`, `reject`, or `revise`.
   6. If promoting, author the PKG change through the normal CHG/PRP lifecycle and assign a new COR ACID.
   7. Retain and update the originating PRJ document as historical evidence.
   8. Verify PKG references, indexes, validation, and review evidence.
4. **Define interaction with existing governance SOPs:**
   - Use GitHub issue + CHG as the default promotion vehicle.
   - Use COR-1000 when promotion creates a new PKG SOP; use COR-1300 when promotion amends an existing PKG document instead.
   - Require PRP first when the promotion creates a new governance family, changes schema/CLI behavior, has unresolved design trade-offs, or would substantially alter multiple COR workflows.
   - Use COR-1101 for the implementation CHG and COR-1500 for code-bearing promotions.
   - Use COR-1602 / COR-1608 / COR-1609 / COR-1610 / COR-1613 review gates according to artifact type.
   - Assign a new COR ACID to promoted PKG documents; never reuse the originating PRJ ACID.
   - If the candidate overlaps an existing PKG SOP, prefer amending the existing SOP unless the pattern is atomic and independently reusable.
5. **Resolve issue #62 placement decision:**
   - Use `COR-1801`, adjacent to `COR-1800 Evolution Philosophy`.
   - Rationale: pattern promotion is part of COR evolution governance, so the 18xx family is the closest existing namespace.
6. **Use KIW-0710 only as a summarized example:**
   - Mention it as an originating PRJ trial SOP from the Kiwari project.
   - Do not require `/Users/frank/Projects/martin/kiwari` or any local path in COR-1801.
   - Define the example inline. The R3-outcome triple-fork pattern is: after a multi-reviewer round, classify the outcome as exactly one of `unanimous pass`, `leader accept with logged residual`, or `escalate`, instead of treating review completion as binary pass/fail.
   - Use outcome `defer unless maintainer endorsement or cross-project evidence is supplied`, because the summarized tracker evidence alone does not meet the pattern's own threshold.
7. **Update PKG references:**
   - Add COR-1801 to `src/fx_alfred/rules/COR-0000-REF-Document-Index.md`.
   - Add a relationship pointer from `src/fx_alfred/rules/COR-1800-REF-Evolution-Philosophy.md` to COR-1801 as a peer 18xx governance SOP, not as a PRJ derivative under the existing project-SOP relationship diagram.
   - Add a routing hint in `src/fx_alfred/rules/COR-1103-SOP-Workflow-Routing.md` for "promote PRJ pattern to PKG".
8. **Verify:**
   - `PYTHONPATH=src .venv/bin/af validate --root .`
   - `PYTHONPATH=src .venv/bin/af read --root . COR-1801`
   - `PYTHONPATH=src .venv/bin/af plan --root . COR-1801 --todo --graph-format=ascii --graph`
   - `PYTHONPATH=src .venv/bin/af list --root . --source pkg --type SOP`
9. **Implementation review:** run Trinity fast-review on the implementation diff and revise until pass.
10. **Open a normal PR** referencing issue #62. If COR-1801 satisfies the issue acceptance criteria, the PR body may use `Closes #62`; otherwise it must leave follow-up promotion exercise explicit.

## Acceptance Criteria

- [x] `COR-1801-SOP-Pattern-Promotion.md` exists in the PKG layer.
- [x] COR-1801 defines candidate pattern requirements: PRJ source, trial status, origin, rule, when/when-not, and explicit promotion criteria.
- [x] COR-1801 includes promotion criteria templates: use-count, cross-project evidence, failure-mode demo, time-in-trial, and counter-evidence review.
- [x] COR-1801 defines promotion states: promote, defer, reject, and revise, plus a separate de-promotion / reversal path for already-promoted PKG documents.
- [x] COR-1801 defines how promotion reuses GitHub issues, CHGs, PRPs, COR ACID assignment, and existing SOP amendments.
- [x] COR-1801 defines PKG authoring conventions that abstract away project-specific details while retaining origin traceability.
- [x] COR-1801 requires retaining the originating PRJ SOP as historical evidence after promotion.
- [x] COR-1801 includes a worked example based on KIW-0710 without depending on KIW files being available on another machine.
- [x] COR-0000 and relevant routing/evolution references are updated.

## Open Questions / Defaults

- **PKG or USR?** Default: PKG. The workflow standardizes a multi-project promotion mechanism, not Frank-only preference.
- **Cross-project threshold?** Default: at least one independent project adoption or explicit maintainer endorsement for initial promotion eligibility. COR-1801 should present stricter templates for high-risk patterns.
- **De-promotion weight?** Default: issue + CHG. No new CLI command; reversal should be auditable and reviewed. A de-promoted PKG document is deprecated per COR-1301, not deleted, unless the CHG proves that amendment is safer than deprecation.
- **Does implementing COR-1801 itself promote a KIW pattern?** Default: no. The worked example exercises the evaluation workflow and may produce `defer` when evidence is insufficient.

## Testing / Verification

- [x] CHG review: `trinity review --preset fast-review --scope rules/FXA-2239-CHG-Add-COR-1801-Pattern-Promotion-SOP.md`
- [x] Implementation review: `trinity review --preset fast-review --scope "FXA-2239 COR-1801 implementation"`
- [x] `PYTHONPATH=src .venv/bin/af validate --root .`
- [x] `PYTHONPATH=src .venv/bin/af read --root . COR-1801`
- [x] `PYTHONPATH=src .venv/bin/af plan --root . COR-1801 --todo --graph-format=ascii --graph`
- [x] `PYTHONPATH=src .venv/bin/af list --root . --source pkg --type SOP`

## Approval

- [x] CHG reviewed by Trinity fast-review
- [x] Approved for COR-1801 implementation

## Execution Log

| Date | Action | Result |
|------|--------|--------|
| 2026-05-05 | Created CHG from GitHub issue #62. | Ready for Trinity fast-review before implementation. |
| 2026-05-05 | Trinity fast-review R1. | GLM PASS; DeepSeek FIX. Revised for self-contained worked example, cross-SOP workflow interactions, COR-1301 de-promotion default, Approval section, and explicit PKG paths. |
| 2026-05-05 | Trinity fast-review R2. | GLM PASS; DeepSeek PASS. Addressed remaining advisory notes before implementation. |
| 2026-05-05 | Trinity fast-review R3. | GLM FIX; DeepSeek PASS. Fixed CHG lifecycle status, completed-review checkbox, and governance cross-references. |
| 2026-05-05 | Trinity fast-review R4. | GLM PASS; DeepSeek PASS. CHG approved for implementation. |
| 2026-05-05 | Implemented COR-1801 and PKG references. | Added COR-1801, COR-0000 index entry, COR-1800 relationship pointer, and COR-1103 routing hints. |
| 2026-05-05 | Ran validation and COR-1801 CLI checks. | `af validate`, `af read`, `af plan`, and `af list` passed. |
| 2026-05-05 | Trinity implementation review R1. | GLM PASS; DeepSeek content clean but flagged unrelated untracked `.claude/` and `tmp/` files. Those files remain excluded from the commit. |
| 2026-05-05 | Ran full local verification. | `ruff check`, `ruff format --check`, `pytest`, and `pyright` passed. |
| 2026-05-05 | Trinity implementation review R2. | GLM PASS; DeepSeek PASS on commit-scoped `main..HEAD` review. |

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-05 | Initial CHG for COR-1801 Pattern Promotion SOP. | Codex |
