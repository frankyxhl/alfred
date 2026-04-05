# CHG-2109: Deduplicate-Total-Issues-In-Validate-Cmd

**Applies to:** FXA project
**Last updated:** 2026-04-06
**Last reviewed:** 2026-04-06
**Status:** Completed
**Date:** 2026-04-06
**Requested by:** —
**Priority:** Medium
**Change Type:** Normal

---

## What

Move the `total_issues = sum(len(i) for i in issues_by_doc.values())` calculation in `validate_cmd.py` to before the `if json_output:` block, eliminating the redundant second computation at line 312. Remove the duplicate assignment and reuse the variable for both the text-output summary and the exit-code check.

## Why

The same sum expression appears at lines 308 (text branch) and 312 (exit code). The dict `issues_by_doc` is not mutated between the two sites, making the second call redundant. Moving it earlier also ensures `total_issues` is defined in both the JSON and text branches, preventing a potential scope issue if future refactors remove the second assignment.

## Impact Analysis

- **Systems affected:** `src/fx_alfred/commands/validate_cmd.py` only
- **Rollback plan:** Revert the single commit

## Implementation Plan

1. Write a test that asserts `total_issues` is consistent between text and JSON output paths
2. Move `total_issues` calculation before `if json_output:` block
3. Remove duplicate assignment at line 312
4. Remove `total_issues` assignment inside `else` block (line 308)
5. Verify all tests pass + ruff clean

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-06 | Initial version | — |
