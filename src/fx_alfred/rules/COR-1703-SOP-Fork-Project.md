# SOP-1703: Fork Project

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-15
**Last reviewed:** 2026-03-15

---

## What Is It?

The process for creating a new project based on an existing project's business-layer structure. Useful when the new project has similar workflows and document needs.

---

## Steps

1. **Initialize the new project** — follow COR-1700 (Initialize Project) first
2. **Copy business-layer documents from the source project**
   ```bash
   cp /path/to/source/docs/*.md /path/to/new-project/docs/
   ```
3. **Replace the prefix** — rename all files from source prefix to new prefix (e.g., BLA → TCY)
4. **Update headers** — change "Applies to", title numbers, and internal references in each file
5. **Review and remove** — delete any documents that don't apply to the new project
6. **Rebuild the index** — update the new project's `*-0000-REF-Document-Index.md`

---

## When to Use

- New project is structurally similar to an existing one
- You want a head start on business-layer documents

## When NOT to Use

- New project has very different needs — use COR-1700 (Initialize Project) alone
- Source project is archived — check if its documents are still relevant first

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-15 | Initial version | Claude Code |
