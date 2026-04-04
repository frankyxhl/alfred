# REF-0002: Document Format Contract

**Applies to:** All projects using the COR document system
**Last updated:** 2026-04-04
**Last reviewed:** 2026-03-20
**Status:** Active

---

## What Is It?

The single source of truth for Alfred document metadata format. All documents, templates, and validation rules must comply with this contract.

---

## H1 Format

```
# <TYP>-<ACID>: <Title>
```

- `TYP`: 3-letter uppercase type code (SOP, PRP, CHG, ADR, REF, PLN, INC)
- `ACID`: 4-digit number
- `Title`: human-readable title

**Exemption:** Documents with ACID=0000 (Index documents) are exempt from H1 format validation.

## Metadata Format Rules

1. **Format:** All fields use `**Key:** Value` (bold key, no list prefix `- `)
2. **No annotations in values:** `**Status:** Draft` not `**Status:** Draft (revised after review)`
3. **Field order:** Required fields first, then optional fields, then `---` separator
   - Applies to → Last updated → Last reviewed → Status → optional fields → `---`
4. **Dates:** ISO 8601 (YYYY-MM-DD)

## Required Fields

All document types require these fields:

| Field | SOP | PRP | CHG | ADR | REF | PLN | INC |
|-------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Applies to | Y | Y | Y | Y | Y | Y | Y |
| Last updated | Y | Y | Y | Y | Y | Y | Y |
| Last reviewed | Y | Y | Y | Y | Y | Y | Y |
| Status | Y | Y | Y | Y | Y | Y | Y |

## Allowed Status Values

| Type | Allowed Values |
|------|---------------|
| SOP | Active, Draft, Deprecated |
| PRP | Draft, Approved, Rejected, Implemented |
| CHG | Proposed, Approved, In Progress, Completed, Rolled Back |
| ADR | Proposed, Accepted, Superseded, Deprecated |
| PLN | Draft, Active, Completed, Cancelled |
| INC | Open, Resolved, Monitoring |
| REF | Active, Draft, Deprecated |

## Optional Fields

Optional fields are allowed but not required. Templates pre-populate type-default optional fields only.

| Field | Used by | Source |
|-------|---------|--------|
| Related | PRP, CHG, ADR | FXA-2116 PRP |
| Reviewed by | PRP, CHG | FXA-2116 PRP |
| Last executed | SOP | FXA-2116 PRP |
| Severity | INC | FXA-2116 PRP |
| Date | CHG, INC | COR-1602 review decision |
| Requested by | CHG | COR-1602 review decision |
| Priority | CHG | COR-1602 review decision |
| Change Type | CHG | COR-1602 review decision |
| Tags | All types | FXA-2200 PRP |

## Section Rules

1. Every document must have `## Change History` as the last section
2. Change History must have a table with columns: Date, Change, By
3. Body must be separated from metadata by `---`

## Language

All documents must be written in English. See COR-1401 (Documentation Language Policy).

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version, based on FXA-2116 PRP + FXA-2119 PLN confirmed decisions | Frank + Claude Code |
| 2026-03-22 | Added Language section referencing COR-1401 | GLM |
| 2026-04-04 | Added Tags optional field for all types per FXA-2200 | Claude Code |
