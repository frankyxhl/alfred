# REF-0002: Document Format Contract

**Applies to:** All projects using the COR document system
**Last updated:** 2026-06-14
**Last reviewed:** 2026-03-20
**Status:** Active
**Disposition:** inherit-only

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
| `mandatory-bind` | COR specification that cannot run standalone because adopting projects must fill project-specific placeholders. A PRJ/USR localization uses `**Instantiates:** COR-NNNN` to bind to the original. | The document contains unbound `<placeholder>` tokens, required project-specific values, or an explicit mandate that adopting projects MUST create a localized SOP before use. |
| `optional-overlay` | COR specification that runs standalone, but projects MAY localize it with a PRJ/USR overlay using `**Overlays:** COR-NNNN`. Overlay is permitted only when it adds substantive project-specific content. | A valid overlay must add operational details that cannot be correctly specified in COR, such as local roles, tool commands, environment paths, repository names, thresholds, escalation channels, or project-specific handoff steps. Cosmetic rewrites, restating COR text, or renaming examples are not sufficient. |
| `inherit-only` | Authoritative COR specification used as-is. PRJ/USR localized instances are forbidden; downstream docs may reference it via `**Related:**` only. | The document defines invariant rules or workflow steps that require no project-specific substitution and would become less governable if duplicated locally. |

### PRJ/USR-Side: Instantiates and Overlays

The `**Instantiates:**` and `**Overlays:**` fields appear on PRJ-layer or USR-layer documents to declare the binding to a COR (PKG-layer) original.

| Field | Meaning | Format |
|-------|---------|--------|
| `**Instantiates:** COR-NNNN` | Required localization of the referenced COR doc. Used when the COR doc has `**Disposition:** mandatory-bind`. | `COR-NNNN` |
| `**Overlays:** COR-NNNN` | Optional customization of the referenced COR doc. Used when the COR doc has `**Disposition:** optional-overlay`. | `COR-NNNN` |

### Layer Applicability

The `**Disposition:**` field applies to COR (PKG-layer) documents only. The `**Instantiates:**` and `**Overlays:**` fields apply to PRJ-layer AND USR-layer documents. USR-layer documents MAY use these fields to localize COR docs at the personal configuration layer.

### Backward Compatibility

All three fields are **optional** for documents created before the adoption of this specification. Documents created after this specification is adopted MUST include the relevant field when the document participates in the localization governance model — i.e., COR docs declare `**Disposition:**`, and PRJ/USR docs that localize a COR doc declare `**Instantiates:**` or `**Overlays:**`. Existing documents are never required to add these fields retroactively.

Section-level disposition is out of scope for v1; `**Disposition:**` applies to the whole COR document.


---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version, based on FXA-2116 PRP + FXA-2119 PLN confirmed decisions | Frank + Claude Code |
| 2026-03-22 | Added Language section referencing COR-1401 | GLM |
| 2026-04-04 | Added Tags optional field for all types per FXA-2200 | Claude Code |
| 2026-04-05 | Added Workflow input/output/requires/provides optional fields (SOP only) per FXA-2204 | GLM |
| 2026-04-26 | Added Section Rule 4 clarifying author-project ID attribution in Change History per FXA-2219 | Claude Code |
| 2026-06-14 | Added Localization Governance Fields section with Disposition (mandatory-bind/optional-overlay/inherit-only), Instantiates/Overlays, USR-layer applicability, backward-compat rules, and v1 section-level out-of-scope note per COR-204 | Claude Code |
