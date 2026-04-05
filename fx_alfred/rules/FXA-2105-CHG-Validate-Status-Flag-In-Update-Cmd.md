# CHG-2105: Validate-Status-Flag-In-Update-Cmd

**Applies to:** FXA project
**Last updated:** 2026-04-05
**Last reviewed:** 2026-04-05
**Status:** Proposed
**Date:** 2026-04-05
**Requested by:** —
**Priority:** Medium
**Change Type:** Normal

---

## What

Remove `has_spec` guard from status validation in `update_cmd.py` line 252 so that `--status` CLI flag is validated against `ALLOWED_STATUSES` regardless of whether `--spec` is provided.

## Why

`af update DOC --status InvalidValue` silently writes invalid statuses. Only `--spec`-sourced updates are validated. Per PRP FXA-2104.

## Impact Analysis

- **Systems affected:** `src/fx_alfred/commands/update_cmd.py` (one condition change)
- **Rollback plan:** Revert the single condition change (re-add `has_spec and` to line 252)

## Implementation Plan

1. TDD Red: Add test `test_update_cli_status_invalid_rejected` — `--status InvalidValue` must fail
2. TDD Red: Add test `test_update_cli_status_valid_succeeds` — `--status Active` must pass (regression guard)
3. TDD Green: Change line 252 from `if has_spec and "Status" in field_updates and doc_type_enum:` to `if "Status" in field_updates and doc_type_enum:`
4. TDD Refactor: Update comment on line 252-253 to reflect new behavior
5. Hard gate: pytest + ruff check

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-05 | Initial version | — |
