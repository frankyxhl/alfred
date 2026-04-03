# CHG-2122: Enhance Validate Per Type Fields And Status

**Applies to:** FXA project
**Last updated:** 2026-03-20
**Last reviewed:** 2026-03-20
**Status:** Completed
**Date:** 2026-03-20
**Requested by:** Frank
**Priority:** High
**Change Type:** Normal
**Related:** FXA-2116, FXA-2119, FXA-2120

---

## What

Enhance `af validate` (`fx_alfred/src/fx_alfred/commands/validate_cmd.py`) with three changes:

1. **Per-type required fields** — Replace the fixed `REQUIRED_METADATA_FIELDS` set with a `REQUIRED_FIELDS_BY_TYPE` dict. All types require Applies to, Last updated, Last reviewed, Status.

2. **Status value validation** — Add `ALLOWED_STATUS` dict. If a document has a Status field and its type has an allowed set, validate the value is in that set. Reject annotations (any value containing parentheses) on the Status field.

3. **Index document exemption** — Documents with ACID=0000 are Index documents; skip H1 format check for them.

**Note:** FXA-2119 PLN Decision #1 overrides FXA-2116 PRP regarding REF Status. REF documents get Status with allowed values: Active / Draft / Deprecated (same as SOP).

### Allowed Status Values

| Type | Allowed Values |
|------|---------------|
| SOP | Active, Draft, Deprecated |
| PRP | Draft, Approved, Rejected, Implemented |
| CHG | Proposed, Approved, In Progress, Completed, Rolled Back |
| ADR | Proposed, Accepted, Superseded, Deprecated |
| PLN | Draft, Active, Completed, Cancelled |
| INC | Open, Resolved, Monitoring |
| REF | Active, Draft, Deprecated |

### Out of scope (v1)

- Field order validation (Applies to → Last updated → ... ) — defer to future CHG
- List prefix format validation (`- **Key:**` vs `**Key:**`) — defer to future CHG
- Annotation check on non-Status fields — defer to future CHG

## Why

Current `af validate` only checks 3 fixed metadata fields and doesn't validate Status values at all. The Document Format Contract (COR-0002) defines per-type rules that need enforcement. Without this, `af validate` can't catch non-compliant documents.

## Impact Analysis

- **Systems affected:** `fx_alfred/src/fx_alfred/commands/validate_cmd.py`, `fx_alfred/tests/test_validate_cmd.py`
- **Rollback plan:** `git revert` the commit

## Implementation Plan (TDD per COR-1500)

1. Write failing tests (minimum test cases):
   - SOP with `Status: Active` → no issue
   - SOP with `Status: InvalidValue` → reports issue
   - PRP with `Status: Draft` → no issue
   - CHG with `Status: In Progress` → no issue (space in value)
   - CHG with `Status: Draft (revised after review)` → reports issue (annotation)
   - REF with `Status: Active` → no issue (PLN override)
   - CHG missing `Applies to` → reports issue (per-type required field)
   - SOP missing `Status` → reports issue
   - ACID=0000 document with non-standard H1 → H1 check skipped, no issue
   - ACID=0000 document → metadata still validated (only H1 exempt)
2. Run tests — confirm RED
3. Implement: add `ALLOWED_STATUS`, `REQUIRED_FIELDS_BY_TYPE`, ACID=0000 exemption
4. Run tests — confirm GREEN
5. Refactor if needed
6. Run full test suite — confirm no regression
7. Commit

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version | Claude Code |
| 2026-03-20 | Round 1 revision: added compliant metadata, REF Status override note, explicit out-of-scope, expanded test cases | Claude Code |
