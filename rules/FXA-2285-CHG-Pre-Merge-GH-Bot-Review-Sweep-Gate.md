# CHG-2285: Pre Merge GH Bot Review Sweep Gate

**Applies to:** FXA project
**Last updated:** 2026-05-15
**Last reviewed:** 2026-05-15
**Status:** Completed
**Related:** COR-1602, COR-1612, COR-1615, COR-1613, FXA-2276, GitHub issue #156
**Date:** 2026-05-15
**Requested by:** @ryosaeba1985
**Priority:** High
**Change Type:** Normal
**Targets:** src/fx_alfred/rules/COR-1602-SOP-Workflow-Multi-Model-Parallel-Review.md; src/fx_alfred/rules/COR-1612-SOP-Respond-To-PR-Review-Comments.md; src/fx_alfred/rules/COR-1615-SOP-GitHub-App-PR-Review-Bot-Loop.md
**Closes:** #156

---

## What

Add a hard pre-merge GitHub-side review sweep gate across COR-1602, COR-1612, and COR-1615. The gate requires an agent to reconcile asynchronous GitHub App review bot threads before declaring a PR merge-ready, even when the in-conversation multi-model panel has already passed.


## Why

Issue #156 records three real-session misses in the trinity review loop: voyager PR #13 and PR #14 were declared merge-ready after trinity PASS while Codex GitHub-bot P2 findings remained open, and voyager PR #15 caught six missed GitHub-bot findings only because the operator manually ran the sweep. COR-1602 currently treats reviewer approval as sufficient, COR-1612 is reactive once comments are already noticed, and COR-1615 lacks a required pre-merge trigger. The SOPs need a synchronized gate so "merge-ready" means every active review channel has been drained.


## Out of Scope

- New automation that resolves or replies to GitHub review threads without agent judgment.
- Changing the content rubric for GitHub App review bots.
- Replacing multi-model panel review, Council Review mechanisms, or CI gates.
- Editing unrelated SOPs outside COR-1602, COR-1612, and COR-1615.


## Impact Analysis

- **Systems affected:** COR review workflow docs bundled in `src/fx_alfred/rules/`; downstream agents that follow COR-1602, COR-1612, or COR-1615 before PR handoff.
- **Behavioral impact:** Agents must run a GitHub-side sweep before declaring merge-ready in PR-context work. Trinity/panel PASS remains necessary where configured, but it is no longer sufficient when GitHub-side review threads exist.
- **Compatibility:** Existing COR-1613 decision-mechanism rules stay intact; this CHG adds a PR-readiness precondition outside the Council vote itself.
- **Zero-thread / no-bot case:** If no GitHub App review bot is installed, or the sweep finds zero non-bookkeeping GitHub-side review threads, the gate is vacuously satisfied after the sweep is recorded.
- **Rollback plan:** Keep the three target SOP edits atomic in one implementation commit; rollback by reverting that commit plus this CHG/tracker/index commit if separated, then rerun `.venv/bin/af validate --root /Users/frank/Projects/alfred`.


## Acceptance Criteria

- A1: COR-1602 Termination Criteria says PR-context artifacts are not done until GitHub-side review threads are resolved or answered, and explicitly states in-conversation panel PASS is necessary but not sufficient.
- A2: COR-1615 When to Use and completion criteria include a pre-merge / merge-ready sweep trigger.
- A3: COR-1615 documents the additive pre-merge sweep filter on top of its existing inline-comment and review-summary commands, including a filter for bookkeeping bots such as `iterwheel-clearance[bot]`, plus thread-aware state for unresolved vs outdated/resolved status.
- A4: COR-1612 contains a Pre-Merge Sweep subsection that points back to COR-1615 and describes how fetched findings enter the existing response loop.
- A5: COR-1602 references COR-1612/COR-1615 in Related metadata or relationship text, and COR-1612/COR-1615 reference COR-1602 where the pre-merge gate depends on panel/Pull Request readiness.
- A6: COR-1615 Examples include a durable, anonymized real-session sweep example based on the voyager PR evidence summarized in issue #156, without depending on external PR links as the only evidence.
- A7: `.venv/bin/af validate --root /Users/frank/Projects/alfred`, `.venv/bin/pytest -v --tb=short`, `.venv/bin/ruff check .`, and `.venv/bin/ruff format --check .` pass.


## Implementation Plan

1. Update COR-1602 Related metadata and Termination Criteria with the GitHub-side review-thread gate. Keep the COR-1613 relationship unchanged: the sweep is a PR-readiness precondition, not a Council mechanism override.
2. Update COR-1615 Related metadata, When to Use, Operator Checklist, Commands, Steps, Completion Criteria, Examples, and Portable Operator Prompt so "run before merge-ready" is a first-class trigger.
3. Add a COR-1615 pre-merge sweep recipe that reuses the existing inline-comment and review-summary fetch surfaces, adds the non-bookkeeping filter, and points operators to GraphQL/thread-aware state for unresolved vs outdated/resolved status.
4. Update COR-1612 Related metadata and add a Pre-Merge Sweep subsection before the generic response steps, routing pre-merge sweep findings through the existing classification/fix/reply loop.
5. Run document formatting/validation and the project test/lint gates.
6. Open a PR with a body that includes Summary, Why, Surfaces, Test plan, and `Closes #156`.

---

## Change History

| Date       | Change                                                                                                                                                                                                   | By    |
|------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------|
| 2026-05-15 | Initial plan for issue #156 pre-merge GitHub-bot review sweep gate | Codex |
| 2026-05-15 | Plan-review PASS from Trinity panel (GLM 9.2, Gemini 9.3, DeepSeek 9.3); folded convergent advisories on metadata, zero-thread behavior, command reuse, rollback atomicity, and example provenance | Codex |
| 2026-05-15 | Implemented COR-1602/COR-1612/COR-1615 pre-merge GitHub-side review sweep gate; local verification passed: shell snippets under set -euo pipefail, af validate, pytest, ruff check, ruff format --check. | Codex |
| 2026-05-15 | R1 bot fix: added fail-closed nested review-thread comment pagination guard to COR-1615 GraphQL sweep example. | Codex |
