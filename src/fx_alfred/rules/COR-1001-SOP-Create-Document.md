# SOP-1001: Create Document

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-14
**Last reviewed:** 2026-03-14
**Status:** Active

---

## What Is It?

The generic process for creating any new document in the system. This SOP covers naming, numbering, and placement. For type-specific templates, see the relevant SOP (COR-1000 for SOP, COR-1100 for ADR, COR-1101 for CHG, etc.).

---

## Why

A consistent naming and numbering system is essential for documents to be findable, sortable, and unambiguous. This SOP is the single source of truth for how any document gets created in the system.

---

## When to Use

- Creating any new document in the COR or project-specific document system
- Determining the correct ACID number, prefix, or type code for a new document
- Setting up a new document with proper naming convention and placement

---

## When NOT to Use

- Reading or searching for existing documents (use COR-1002 instead)
- Updating an existing document's metadata or content (use `af update`)
- Creating documents outside the COR document system

---

## Steps

1. **Determine the prefix** — `COR` for universal meta-layer docs, or project code (`ALF`, `BLA`, `CLR`) for business-layer docs
2. **Determine the ACID number** — run `af list` to find the next available ACID in the correct category, or use `af create --area` to auto-assign
3. **Determine the type code** — SOP, PLN, INC, CHG, ADR, or REF
4. **Create the file** — use the naming convention below
5. **Use the correct template** — refer to the type-specific SOP for the template
6. **Update the index** — follow COR-1302 (Maintain Document Index)

---

## Naming Convention

```
<PREFIX>-<ACID>-<TYP>-<Title-In-Kebab-Case>.md
```

- **PREFIX** — `COR` (universal) or project code (`ALF`, `BLA`, `CLR`)
- **ACID** — 4-digit Johnny Decimal number: Area(1) + Category(1) + Item(2)
- **TYP** — 3-letter document type
- **Title** — kebab-case, verb+object for actions

Examples:
- `COR-1000-SOP-Create-SOP.md`
- `COR-1100-SOP-Create-Decision-Record.md`
- `ALF-2100-SOP-TDD-Development-Workflow.md`
- `ALF-2200-PLN-Automation-Roadmap.md`

---

## Numbering System (PDCA + Johnny Decimal)

### Meta Layer — `COR-` (universal, applies to all projects)

| ACID | Phase | Category |
|------|-------|----------|
| 10xx | Do | Document creation and reading |
| 11xx | Plan | Decision and change planning |
| 12xx | Check | Review and retrospective |
| 13xx | Act | Update, deprecation, and index maintenance |
| 14xx | Constraint | Universal rules and principles |

### Business Layer — project prefix (varies per project)

| ACID | Category |
|------|----------|
| 20xx | Infrastructure |
| 21xx | Development |
| 22xx | Planning |
| 23xx | Incident |
| 24xx | Constraint |

Business layer categories can be extended per project as needed.

---

## Type Codes

| Code | Type |
|------|------|
| ADR | Architecture / Any Decision Record |
| CHG | Change request |
| INC | Incident record |
| PLN | Plan or roadmap |
| PRP | Proposal |
| REF | Reference document |
| SOP | Standard Operating Procedure |

Type codes are always three letters.

**Note:** Area selection is user-chosen and is not bound to any specific type. COR-1001 is the sole authority for numbering rules.

---

## Language Policy

All documents must be written in English. Discussions may happen in any language, but the recorded document is always in English.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-08 | Initial version, converted from TEMPLATE-SOP.md | Claude Code |
| 2026-03-14 | PDCA + Johnny Decimal migration: renamed from ALF-1000 to COR-1001, removed template (moved to COR-1000), updated numbering system | Claude Code |
| 2026-03-20 | Added Why/When to Use/When NOT to Use sections per ALF-2210 | Claude Code |
