# PRP-2104: Validate-Status-Flag-In-Update-Cmd

**Applies to:** FXA project
**Last updated:** 2026-04-05
**Last reviewed:** 2026-04-05
**Status:** Draft

---

## What Is It?

Proposal to fix a validation gap in `af update` where `--status` flag bypasses status validation when `--spec` is not provided.

---

## Problem

In `src/fx_alfred/commands/update_cmd.py` line 252-254, the status validation guard is:

```python
if has_spec and "Status" in field_updates and doc_type_enum:
    validate_spec_status(doc_type_enum, field_updates["Status"])
```

The `has_spec` condition means `af update DOC --status InvalidValue` silently writes an invalid status. Only `af update DOC --spec patch.yaml` (with Status in the spec) triggers validation. This allows documents to enter invalid states that `af validate` would later flag.

## Proposed Solution

1. Remove the `has_spec` guard so that status validation runs whenever `"Status"` is in `field_updates` and `doc_type_enum` is available.
2. Change line 252 from `if has_spec and "Status" in field_updates and doc_type_enum:` to `if "Status" in field_updates and doc_type_enum:`.
3. Add tests: (a) `--status InvalidValue` without `--spec` must fail, (b) `--status Active` without `--spec` must still succeed.

## Risks / Trade-offs

- **Backward compatibility:** Any existing script or workflow using `af update DOC --status <invalid>` will now fail with a clear error. This is the intended behavior — silent acceptance of invalid statuses was the bug.
- **Unknown doc types:** When `doc_type_enum` is None (unrecognized type code), validation is skipped. This preserves current behavior — no regression.
- **`--field Status X` path:** Both `--status` and `--field Status X` flow through `cli_field_updates`, so the fix covers both paths.

## Out of Scope

- Retroactive cleanup of documents already containing invalid statuses
- Changes to `af validate` behavior
- Changes to `af create` status validation (already validates correctly)

## Open Questions

None — the fix is a single condition removal with clear test coverage.

## SOP References

- COR-0002: Document Format Contract (defines valid status values per type)

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-05 | Initial version | — |
