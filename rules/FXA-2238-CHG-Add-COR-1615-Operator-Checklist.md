# CHG-2238: Add COR 1615 Operator Checklist

**Applies to:** FXA project
**Last updated:** 2026-05-05
**Last reviewed:** 2026-05-05
**Status:** Completed
**Date:** 2026-05-05
**Requested by:** Frank
**Priority:** Medium
**Change Type:** Normal
**Related:** COR-1615, COR-1612, COR-1615 review-loop checklist notes

---

## What

Add a compact operator checklist and portable prompt to `COR-1615: GitHub App PR Review Bot Loop`.

The checklist makes the existing non-negotiables easier for agents to follow:

- match every review result to the current `headRefOid`;
- treat acknowledgement reactions as in-progress, not approval;
- avoid duplicate review triggers while a request is pending;
- verify visible-write identity before public GitHub writes;
- avoid leaking local/private environment details;
- hand off actionable findings to COR-1612, then restart COR-1615 after fix pushes.

## Why

The current SOP already contains these rules, but they are spread across Prerequisites, Status Vocabulary, Steps, Completion Criteria, Pitfalls, and Examples. A short checklist improves operator recall during active PR review loops without duplicating the COR-1612 fix workflow.

## Impact Analysis

- **Systems affected:**
  - `src/fx_alfred/rules/COR-1615-SOP-GitHub-App-PR-Review-Bot-Loop.md` - add checklist and portable prompt.
  - `rules/FXA-0000-REF-Document-Index.md` - add this CHG entry.
- **Not affected:**
  - CLI behavior, package version, tests, and schema contracts.
  - COR-1612 fix-loop details; COR-1615 references COR-1612 instead of duplicating it.
- **Rollback plan:** Revert the document-only commit and rerun `PYTHONPATH=src .venv/bin/af validate --root .`.

## Implementation Plan

1. Create FXA-2238 CHG.
2. Add `## Operator Checklist` after COR-1615 Prerequisites.
3. Add `## Portable Operator Prompt` before COR-1615 References.
4. Update COR-1615 Change History.
5. Verify document validation and representative `af read` / `af plan` behavior.

## Testing / Verification

- [x] `PYTHONPATH=src .venv/bin/af validate --root .`
- [x] `PYTHONPATH=src .venv/bin/af read --root . COR-1615`
- [x] `PYTHONPATH=src .venv/bin/af plan --root . COR-1615 COR-1612 --todo --graph-format=ascii --graph`

## Execution Log

| Date | Action | Result |
|------|--------|--------|
| 2026-05-05 | Created CHG and updated COR-1615 with checklist/prompt. | Validation and representative read/plan checks passed. |

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-05 | Added CHG for COR-1615 operator checklist. | Codex |
