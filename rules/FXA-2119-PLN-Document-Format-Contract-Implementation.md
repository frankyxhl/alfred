# PLN-2119: Document Format Contract Implementation

**Applies to:** FXA project
**Last updated:** 2026-03-20
**Last reviewed:** 2026-03-20
**Status:** Completed
**Related:** FXA-2116 (PRP), FXA-2117 (depends on this PLN)

---

## What Is It?

Implementation plan for FXA-2116 (Document Format Contract). Standardizes metadata format across all document types, enforces via validation, migrates existing documents, and updates templates.

---

## Decisions

| # | Question | Decision |
|---|----------|----------|
| 1 | REF documents get Status? | Yes — same as SOP: Active / Draft / Deprecated |
| 2 | Contract location? | COR-0002 in PKG layer |
| 3 | Index documents (ACID=0000) H1 format? | Exempt — treated as IDX type, skip H1 validation |
| 4 | Status values per type? | See table below |

### Status Values Per Type

| Type | Allowed Values | Template Default |
|------|---------------|-----------------|
| SOP | Active, Draft, Deprecated | Active |
| PRP | Draft, Approved, Rejected, Implemented | Draft |
| CHG | Proposed, Approved, In Progress, Completed, Rolled Back | Proposed |
| ADR | Proposed, Accepted, Superseded, Deprecated | Proposed |
| PLN | Draft, Active, Completed, Cancelled | Draft |
| INC | Open, Resolved, Monitoring | Open |
| REF | Active, Draft, Deprecated | Active |

### Required Fields Per Type

| Field | SOP | PRP | CHG | ADR | REF | PLN | INC |
|-------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Applies to | Y | Y | Y | Y | Y | Y | Y |
| Last updated | Y | Y | Y | Y | Y | Y | Y |
| Last reviewed | Y | Y | Y | Y | Y | Y | Y |
| Status | Y | Y | Y | Y | Y | Y | Y |

### Metadata Format Rules

1. All fields: `**Key:** Value` (bold, no list prefix `- `)
2. No annotations in values: `**Status:** Draft` not `**Status:** Draft (revised...)`
3. Order: Applies to → Last updated → Last reviewed → Status → optional fields → `---`
4. Dates: ISO 8601 (YYYY-MM-DD)

---

## Tasks

### Task 1: Create COR-0002-REF Contract Document

**Files:**
- Create: `fx_alfred/src/fx_alfred/rules/COR-0002-REF-Document-Format-Contract.md`

**Steps:**
1. Write the contract document in PKG rules directory (manual, `af create` rejects COR prefix)
2. Content: metadata format rules, required fields table, status values table, section rules
3. Run existing tests to verify no regression
4. Commit

### Task 2: Update `af create` Templates

**Files:**
- Modify: `fx_alfred/src/fx_alfred/templates/chg.md`
- Modify: `fx_alfred/src/fx_alfred/templates/inc.md`
- Modify: `fx_alfred/src/fx_alfred/templates/pln.md`
- Modify: `fx_alfred/src/fx_alfred/templates/prp.md`
- Modify: `fx_alfred/src/fx_alfred/templates/sop.md`
- Modify: `fx_alfred/src/fx_alfred/templates/adr.md`
- Modify: `fx_alfred/src/fx_alfred/templates/ref.md`
- Test: `fx_alfred/tests/test_create_cmd.py`

**Steps:**
1. Write failing tests: each template must have Applies to, Last updated, Last reviewed, Status; fields use `**Key:** Value` format; correct field order
2. Run tests — expect FAIL
3. Update all 7 templates to match contract (add missing fields, correct format, set default Status)
4. CHG: keep Requested by / Priority / Change Type as optional fields after Status
5. INC: keep Severity as optional field after Status
6. Run tests — expect PASS
7. Commit

### Task 3: Enhance `af validate` — Per-Type Required Fields + Status Values

**Files:**
- Modify: `fx_alfred/src/fx_alfred/commands/validate_cmd.py`
- Test: `fx_alfred/tests/test_validate_cmd.py`

**Steps:**
1. Write failing tests: valid status passes, invalid status fails, annotation in status fails, per-type required fields enforced, ACID=0000 exempt from H1 check
2. Run tests — expect FAIL
3. Add `ALLOWED_STATUS` dict and `REQUIRED_FIELDS_BY_TYPE` dict to validate_cmd.py
4. Replace fixed `REQUIRED_METADATA_FIELDS` with per-type lookup
5. Add status value validation (check against allowed set, reject annotations)
6. Add ACID=0000 exemption for H1 format check
7. Run tests — expect PASS
8. Run full test suite — expect all pass
9. Commit

### Task 4: Migrate Existing Documents

**Files:**
- Modify: all non-compliant documents in `alfred_ops/rules/` and `~/.alfred/`

**Steps:**
1. Run `af validate` to get full issue list
2. CHG-A: Convert `- **Key:** Value` → `**Key:** Value` (FXA-2101, FXA-2103, others)
3. CHG-B: Clean status annotations (FXA-2104: `Draft (revised...)` → `Draft`)
4. CHG-C: Add missing Status fields to SOPs (default Active), PLNs, REFs
5. CHG-D: Add missing Applies to / Last updated / Last reviewed to CHG documents
6. Run `af validate` — expect 0 issues (except Index H1, now exempt)
7. Commit

### Task 5: Close PRP

**Steps:**
1. `af update FXA-2116 --status Implemented`
2. `af update FXA-2119 --status Completed`
3. Commit

## Execution Order

```
Task 1 (Contract) → Task 2 (Templates) → Task 3 (Validate) → Task 4 (Migration) → Task 5 (Close)
```

Tasks 2 and 3 have no code overlap and could run in parallel.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version | Claude Code |
