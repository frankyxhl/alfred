# PRP-2116: Document Format Contract

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-20
**Last reviewed:** 2026-03-20
**Status:** Implemented
**Related:** FXA-2117 (af filter, depends on this PRP)
**Reviewed by:** —

---

## What Is It?

A formal specification for Alfred document structure, standardizing metadata format across all document types (SOP, PRP, CHG, ADR, REF, PLN, INC). Includes migration of existing documents and updated validation rules.

---

## Problem

1. Metadata format is inconsistent: some use `**Key:** Value`, others use `- **Key:** Value` (list prefix)
2. Status field has free-text annotations: `Draft (revised after COR-1602 review)` breaks machine parsing
3. Not all document types have a Status field — SOPs, REFs mostly lack it
4. Some documents miss required fields (Last reviewed)
5. `af filter` (FXA-2117) cannot work reliably without a guaranteed format contract
6. `af validate` checks structure but the rules aren't codified as a standalone spec document

---

## Scope

**In scope:**
- Define the Document Format Contract as a COR-level reference (target: COR-0002-REF or similar)
- Standardize metadata block format (all documents, all types)
- Define required vs optional fields per document type
- Define allowed Status values per document type
- Migrate all existing documents (PKG + PRJ) to comply
- Update `af validate` to enforce the contract
- Update `af create` templates to match the contract

**Out of scope:**
- YAML frontmatter migration (keep `**Key:** Value` format for now)
- Body content structure rules (section ordering, etc.) — future PRP
- markdown-it-py integration — not needed for this scope

---

## Proposed Solution

### Document Format Contract

```markdown
# <TYP>-<ACID>: <Title>

**Applies to:** <scope>
**Last updated:** YYYY-MM-DD
**Last reviewed:** YYYY-MM-DD
**Status:** <value>

---

## <Body sections>
...

---

## Change History

| Date | Change | By |
|------|--------|----|
```

### Metadata Rules

1. **Format:** All fields use `**Key:** Value` (bold, no list prefix)
2. **No annotations in values:** `**Status:** Draft` not `**Status:** Draft (revised...)`
3. **Order:** Applies to → Last updated → Last reviewed → Status → (optional fields) → separator
4. **Dates:** ISO 8601 (YYYY-MM-DD)

### Required Fields Per Type

| Field | SOP | PRP | CHG | ADR | REF | PLN | INC |
|-------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Applies to | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Last updated | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Last reviewed | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Status | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |

REF documents don't have Status (they're reference material, not lifecycle documents).

### Status Values Per Type

| Type | Allowed Values |
|------|---------------|
| SOP | Active, Draft, Deprecated |
| PRP | Draft, Approved, Rejected, Implemented |
| CHG | Proposed, Approved, In Progress, Completed, Rolled Back |
| ADR | Proposed, Accepted, Superseded, Deprecated |
| PLN | Draft, Active, Completed, Cancelled |
| INC | Open, Resolved, Monitoring |

### Optional Fields (per type)

| Field | Used by |
|-------|---------|
| Related | PRP, CHG, ADR |
| Reviewed by | PRP, CHG |
| Last executed | SOP |
| Severity | INC |

### Migration Plan

1. **CHG-A: Normalize metadata prefix** — Convert all `- **Key:** Value` to `**Key:** Value`
2. **CHG-B: Clean Status values** — Remove parenthetical annotations, map to allowed values
3. **CHG-C: Add missing Status fields** — Add Status to SOPs (default: Active), PLNs, etc.
4. **CHG-D: Add missing Last reviewed** — Backfill where absent
5. **CHG-E: Update af validate** — Enforce required fields per type + allowed Status values
6. **CHG-F: Update af create templates** — Ensure all templates include required fields with correct format

### Section Rules (minimal for v1)

1. Every document must have `## Change History` as the last section
2. Change History must have a table with columns: Date, Change, By
3. Body must be separated from metadata by `---`

---

## Open Questions

1. Should REF documents also get Status? (e.g., Current/Archived)
2. Should SOPs distinguish between Active (in use) and Draft (not yet reviewed)?
3. Should the contract be a COR document (bundled in PKG) or an ALF document (project-specific)?
4. How to handle the COR-1102 template which uses `**Status:** Draft` as an example — is this the contract itself or just a template?

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version from D19/D23 discussion | Claude Code |
