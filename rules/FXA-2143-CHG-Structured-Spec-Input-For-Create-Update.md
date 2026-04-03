# CHG-2143: Structured Spec Input For Create Update

**Applies to:** FXA project
**Last updated:** 2026-03-22
**Last reviewed:** 2026-03-22
**Status:** Completed
**Date:** 2026-03-22
**Requested by:** Frank
**Priority:** High
**Change Type:** Normal
**Related:** FXA-2140, FXA-2141

---

## What

Add a `--spec FILE` option to `af create` and `af update`. When provided, the command reads a YAML (or JSON) spec file, validates all fields against `core/schema.py`, and generates or patches the document from the validated spec. The existing CLI flags (`--prefix`, `--title`, etc.) continue to work unchanged.

---

## Why

Today, agents and scripts create documents by passing individual CLI flags or by writing Markdown directly. Both approaches are fragile:

- CLI flags (`af create sop --prefix FXA --area 21 --title "..."`) cannot pass section content, metadata values, or body text
- Direct Markdown writes bypass all validation and can produce documents that fail `af validate`

A structured spec file gives agents a typed, validated contract for document creation and updates. The flow becomes: **spec (YAML) → schema.py validation → normalize → render → write** — rather than "agent writes raw Markdown and hopes it's correct."

This change depends on FXA-2140 (core/schema.py) for field validation rules.

---

## Impact Analysis

- **Systems affected:** `create_cmd.py`, `update_cmd.py`, `core/schema.py` (FXA-2140)
- **Channels affected:** none (CLI only)
- **Downtime required:** No
- **Rollback plan:** Remove `--spec` option from both commands. No data migration needed; spec input is additive.
- **Breaking changes:** None — existing flags are unchanged. `--spec` is a new optional flag.
- **Dependency:** Requires FXA-2140 (schema.py) to be implemented first.

---

## Implementation Plan

### 1. Spec format (YAML)

**Create spec (`af create --spec`):**
```yaml
type: SOP
prefix: FXA
area: 21
title: "Release Build Workflow"
role: sop                        # optional, DocRole enum
metadata:
  Applies to: fx-alfred project
  Status: Draft
  Last reviewed: "2026-03-22"
sections:
  What Is It?: "This SOP covers the release build process..."
  Why: "Ensures consistent release quality."
  Steps:
    - Prepare release branch
    - Run af validate --all
    - Run tests
    - Publish to PyPI
```

**Patch spec (`af update --spec`):**
```yaml
# Only fields to change; omitted fields are preserved
metadata:
  Status: Active
  Last reviewed: "2026-03-22"
sections:
  Steps:
    - Prepare release branch
    - Run af validate --all
    - Run tests and af fmt --check
    - Publish to PyPI
```

### 2. Validation rules (via schema.py)

- `type` must be a valid `DocType`
- `role` (if present) must be a valid `DocRole`
- `metadata.Status` must be in `ALLOWED_STATUSES[doc_type]`
- Required metadata fields must be present (from `REQUIRED_METADATA[doc_type]`)
- Required sections must be present for the doc type (from `REQUIRED_SECTIONS[doc_type]`)
- Unknown metadata fields: warn but do not block
- `prefix` and `area` must be present for create; optional for update (read from existing doc)

### 3. `af create --spec FILE`

```bash
af create --spec specs/release_sop.yaml --root fx_alfred
```

- Load spec YAML
- Validate all fields against schema.py
- Resolve ACID (next available for prefix+area)
- Generate Markdown from spec
- Write to PRJ rules directory
- Update index

### 4. `af update DOC_ID --spec FILE`

```bash
af update FXA-2100 --spec specs/patch_status.yaml --root fx_alfred
```

- Load spec YAML (partial patch allowed)
- Validate changed fields against schema.py
- Apply patch via parser (preserve unchanged sections)
- Update `Last updated` date
- Write in-place

### 5. Dry-run support

Both commands accept `--dry-run`: validate and print what would be written without touching the filesystem.

### 6. Tests

- Valid spec creates document with correct content
- Invalid `Status` value is rejected with clear error
- Missing required section produces validation error
- Patch spec preserves unchanged sections
- `--dry-run` produces no file writes

---

## Testing / Verification

- `af create --spec valid_spec.yaml` creates a document that passes `af validate`
- `af create --spec invalid_status.yaml` exits non-zero with message: `Status 'InProgress' not allowed for SOP; allowed: Draft, Active, Deprecated`
- `af update FXA-2100 --spec patch.yaml` preserves all sections not in the patch
- `--dry-run` on both commands: no files written, output shows what would change
- Existing `af create sop --prefix FXA --area 21 --title "..."` still works (no regression)

---

## Approval

- [ ] Reviewed by: —
- [ ] Approved on: —

---

## Execution Log

| Date | Action | Result |
|------|--------|--------|

---

## Post-Change Review

_To be completed after implementation._

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-22 | Initial version | Frank + Claude Code |
