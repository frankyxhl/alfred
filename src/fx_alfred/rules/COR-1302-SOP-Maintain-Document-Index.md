# SOP-1302: Maintain Document Index

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-14
**Last reviewed:** 2026-03-14
**Status:** Active

---

## What Is It?

A standard process for keeping document index files (COR-0000, ALF-0000, BLA-0000, etc.) in sync with the actual documents in the system.

---

## When to Update

- After creating a new document
- After renaming or renumbering a document
- After deprecating a document

---

## Steps

1. **Determine which index** — `COR-0000` for meta-layer documents, `<PREFIX>-0000` for business-layer documents
2. **Add, modify, or remove the row** — update the table in the correct category section
3. **Keep rows sorted by ACID number** — ascending within each category
4. **Update the Last updated date** on the index file

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-14 | Initial version | Claude Code |
