# SOP-1300: Update Document

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-14
**Last reviewed:** 2026-03-14
**Status:** Active

---

## What Is It?

A standard process for modifying an existing document. Ensures all changes are traceable through the Change History and that the document remains consistent with the rest of the system.

---

## Why

Consistent update procedures keep the document system auditable and prevent silent changes that break cross-references.

---

## When to Use

- When editing any existing document (SOP, PRP, CHG, ADR, REF, etc.)
- When updating metadata fields (status, dates, related documents)
- When adding or correcting content in an existing document

---

## When NOT to Use

- When creating a new document from scratch — use COR-1000 (SOP) or COR-1001 (other types)
- When deprecating a document — use COR-1301 instead
- When the document does not yet exist

---

## Steps

1. **Read the current version** — understand the existing content before making changes (see COR-1101)
2. **Make your edits** — update the relevant sections
3. **Update the Last updated date** — change to today's date
4. **Add a Change History entry** — append a row with date, description of change, and author
5. **Review cross-references** — check if other documents reference this one and need updating
6. **Sync if applicable** — if this is a COR document, ensure copies in other projects are also updated

---

## Rules

- Never delete Change History entries — they are the audit trail
- Keep the document structure consistent with the template defined in COR-1100
- If the change is significant enough to warrant discussion, create a Decision Record first (COR-1000)

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-14 | Initial version | Claude Code |
| 2026-03-20 | Added Why/When to Use/When NOT to Use sections per ALF-2210 | Claude Code |
