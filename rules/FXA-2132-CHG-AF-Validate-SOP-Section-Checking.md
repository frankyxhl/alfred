# CHG-2132: AF Validate SOP Section Checking

**Applies to:** FXA project
**Last updated:** 2026-03-20
**Last reviewed:** 2026-03-20
**Status:** Completed
**Date:** 2026-03-20
**Requested by:** Frank
**Priority:** High
**Change Type:** Normal
**Related:** ALF-2210, FXA-2131, FXA-2133

---

## What

Add SOP section checking to `af validate`. For SOP documents, validate presence of required sections: What Is It?, Why, When to Use, When NOT to Use, Steps. Conditionally require Examples if document has Prerequisites or > 5 top-level Steps. Section ordering is advisory, not validated.

## Why

Without machine validation, migrated SOPs can lose required sections over time. `af validate` is the enforcement mechanism.

## Impact Analysis

- **Systems affected:** `validate_cmd.py`, `tests/test_validate_cmd.py`
- **Rollback plan:** `git revert`

## Implementation Plan (TDD per COR-1500)

1. Write failing tests:
   - SOP with all required sections → no issue
   - SOP missing "Why" → reports issue
   - SOP missing "When to Use" → reports issue
   - SOP missing "When NOT to Use" → reports issue
   - SOP with Prerequisites but no Examples → reports issue
   - SOP with > 5 Steps but no Examples → reports issue
   - SOP with 3 Steps and no Examples → no issue (not required)
   - Non-SOP document (PRP, CHG) → section check skipped
2. Run tests — RED
3. Implement in validate_cmd.py
4. Run tests — GREEN
5. Full suite — no regression
6. Commit

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version | Claude Code |
