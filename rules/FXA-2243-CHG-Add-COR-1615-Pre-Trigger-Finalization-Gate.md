# CHG-2243: Add COR 1615 Pre Trigger Finalization Gate

**Applies to:** FXA project
**Last updated:** 2026-05-06
**Last reviewed:** 2026-05-06
**Status:** Completed
**Date:** 2026-05-06
**Requested by:** Frank
**Priority:** Medium
**Change Type:** Normal
**Related:** COR-1615, COR-1612, PR #101
**Tags:** github-review, bot-review, workflow-efficiency, pr-readiness

---

## What

Add a pre-trigger finalization gate and decision tree to `COR-1615: GitHub App
PR Review Bot Loop`.

Before manually posting `@codex review` or requesting a GitHub App reviewer, the
operator must finish all known local closeout commits, status flips, index
updates, PR-body-driven doc edits, generated-doc refreshes, validation fixups,
and whitespace fixups. The manual review trigger should happen only after the
current head is the head the operator actually intends to have reviewed.

## Why

PR #101 exposed a sequencing inefficiency: the bot review passed on one head,
then a known CHG closeout commit was pushed afterward. COR-1615 correctly
requires a fresh review after every push, but it did not explicitly prevent
operators from triggering review before known local follow-up commits were done.

The improved SOP preserves the current-head correctness rule while reducing
wasted review bot passes. The decision tree makes the loop easier for agents to
follow because the key branches are visible before the detailed step text.

## Impact Analysis

- **Systems affected:**
  - `src/fx_alfred/rules/COR-1615-SOP-GitHub-App-PR-Review-Bot-Loop.md` - add
    the finalization gate, decision tree, checklist item, completion criterion,
    pitfall, and example.
  - `rules/FXA-0000-REF-Document-Index.md` - add this CHG entry.
  - `rules/FXA-2243-CHG-Add-COR-1615-Pre-Trigger-Finalization-Gate.md` - this
    change record.
- **Not affected:** CLI behavior, package schema, CI configuration, review bot
  integration, and COR-1612 review-response rules.
- **Rollback plan:** Revert this document-only change and rerun
  `PYTHONPATH=src .venv/bin/af validate --root .`.

## Implementation Plan

1. Update COR-1615 metadata dates.
2. Add a prerequisite and operator-checklist item requiring known local
   closeout/fixup commits to be completed before a manual review trigger.
3. Insert a `Run the pre-trigger finalization gate` step before trigger
   decision/trigger steps.
4. Add a Mermaid decision tree before the detailed steps.
5. Add a completion criterion, pitfall, example, portable-prompt bullet, and
   change-history entry.
6. Add this CHG to the FXA index.
7. Run local validation and representative `af read` / `af plan` checks.

## Acceptance Criteria

- [x] COR-1615 explicitly tells operators to finish known local closeout,
  status, index, generated-doc, PR-body, validation, and whitespace commits
  before posting a manual review trigger.
- [x] COR-1615 keeps the existing rule that any push after review creates a new
  `headRefOid` that must be reviewed again.
- [x] COR-1615 includes a decision tree covering pre-trigger finalization,
  pending requests, stale-head handling, COR-1612 fix loops, and checks.
- [x] COR-1615 explains the PR #101-style failure mode as a pitfall or example.
- [x] The portable operator prompt includes the pre-trigger finalization check.
- [x] FXA index includes this CHG.
- [x] Local validation and representative read/plan checks pass.

## Testing / Verification

- [x] `PYTHONPATH=src .venv/bin/af validate --root .`
- [x] `PYTHONPATH=src .venv/bin/af read --root . COR-1615`
- [x] `PYTHONPATH=src .venv/bin/af read --root . FXA-2243`
- [x] `PYTHONPATH=src .venv/bin/af plan --root . COR-1615 COR-1612 --todo --graph-format=ascii --graph`
- [x] `git diff --check`

## Execution Log

| Date | Action | Result |
|------|--------|--------|
| 2026-05-06 | Added COR-1615 pre-trigger finalization gate, decision tree, and FXA-2243 CHG. | Validation and representative read/plan checks passed. |

## Post-Change Review

- The SOP now distinguishes two cases:
  - known local follow-up commits before review: finish them first, then trigger
    one review for the intended head;
  - review/CI-response commits after review: push them, then restart COR-1615
    for the new head.
- The decision tree gives operators and agents a compact view of the loop before
  they read the detailed steps.
- This reduces wasted manual bot triggers without weakening current-head review
  correctness.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-06 | Added CHG for COR-1615 pre-trigger finalization gate. | Codex |
