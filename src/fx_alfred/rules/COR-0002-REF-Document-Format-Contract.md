# REF-0002: Document Format Contract

**Applies to:** All projects using the COR document system
**Last updated:** 2026-06-14
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
| Workflow input | SOP only | FXA-2204 CHG |
| Workflow output | SOP only | FXA-2204 CHG |
| Workflow requires | SOP only | FXA-2204 CHG |
| Workflow provides | SOP only | FXA-2204 CHG |
| Tags | All types | FXA-2200 PRP |
| Disposition | COR docs only | COR-204 |
| Instantiates | PRJ/USR docs | COR-204 |
| Overlays | PRJ/USR docs | COR-204 |

## Section Rules

1. Every document must have `## Change History` as the last section
2. Change History must have a table with columns: Date, Change, By
3. Body must be separated from metadata by `---`
4. Change History entries may attribute changes to author-project IDs (e.g. `per FXA-2223`). These are PRJ-layer provenance from the document's authoring project and are not bundled in the package; downstream users will not find them via `af read`. This is informational, not a broken reference.

## Language

All documents must be written in English. See COR-1401 (Documentation Language Policy).

## Localization Governance Fields

These fields close the loop between COR (PKG) documents and their PRJ/USR localizations. They make the localization relationship machine-readable and auditable.

### COR-Side: Disposition

The `**Disposition:**` field appears on COR (PKG-layer) documents to declare what kind of localization the document permits or requires.

Allowed values:

| Value | Meaning | Criteria |
|-------|---------|----------|
| `core` | Authoritative COR specification. This document is the system of record. Projects MUST NOT create PRJ-localized overlay SOPs that contradict or duplicate its guidance; PRJ docs MAY reference it via `**Related:**` only. | SOP sections define invariant rules; no project-specific tailoring is needed or permitted. |
| `optional-overlay` | COR specification that projects MAY localize with a PRJ-overlay SOP. The overlay uses `**Overlays:** COR-NNNN` to bind to the original. Overlay is not required; the COR doc is usable as-is. | SOP is authoritative but explicitly acknowledges that some projects may need to customize sections. The bar for marking a field `optional-overlay` (rather than `core`) is the existence of any section where multiple reasonable project-specific interpretations could each be valid, AND no one interpretation can be designated the single correct one within the COR document. |
| `localization-required` | COR specification that REQUIRES each implementing project to produce a PRJ-layer overlay SOP using `**Instantiates:** COR-NNNN`. The overlay is mandatory for projects that fall within the document's "Applies to" scope. | SOP explicitly states "Projects MUST create a PRJ-localized SOP" or equivalent mandate. |

### PRJ/USR-Side: Instantiates and Overlays

The `**Instantiates:**` and `**Overlays:**` fields appear on PRJ-layer or USR-layer documents to declare the binding to a COR (PKG-layer) original.

| Field | Meaning | Format |
|-------|---------|--------|
| `**Instantiates:** COR-NNNN` | Required localization of the referenced COR doc. Used when the COR doc has `**Disposition:** localization-required`. | `COR-NNNN` |
| `**Overlays:** COR-NNNN` | Optional customization of the referenced COR doc. Used when the COR doc has `**Disposition:** optional-overlay`. | `COR-NNNN` |

### Layer Applicability

The `**Disposition:**` field applies to COR (PKG-layer) documents only. The `**Instantiates:**` and `**Overlays:**` fields apply to PRJ-layer AND USR-layer documents. USR-layer documents MAY use these fields to localize COR docs at the personal configuration layer.

### Backward Compatibility

All three fields are **optional** for documents created before the adoption of this specification. Documents created after this specification is adopted SHOULD include the relevant fields when the document participates in the localization governance model — i.e., COR docs SHOULD declare `**Disposition:**`, and PRJ/USR docs that localize a COR doc SHOULD declare `**Instantiates:**` or `**Overlays:**`. Existing documents are never required to add these fields retroactively.


---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version, based on FXA-2116 PRP + FXA-2119 PLN confirmed decisions | Frank + Claude Code |
| 2026-03-22 | Added Language section referencing COR-1401 | GLM |
| 2026-04-04 | Added Tags optional field for all types per FXA-2200 | Claude Code |
| 2026-04-05 | Added Workflow input/output/requires/provides optional fields (SOP only) per FXA-2204 | GLM |
| 2026-04-26 | Added Section Rule 4 clarifying author-project ID attribution in Change History per FXA-2219 | Claude Code |
| 2026-06-14 | Added Localization Governance Fields section with Disposition (core/optional-overlay/localization-required), Instantiates/Overlays, USR-layer applicability, and backward-compat rules per COR-204 | Claude Code |
