# SOP-1703: Fork Project

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-15
**Last reviewed:** 2026-03-15

---

## What Is It?

The process for creating a new project based on an existing project's document structure. Useful when the new project has similar workflows and document needs.

---

## Steps

1. **Initialize the new project** — follow COR-1700 (Initialize Project) first
2. **Review source project documents**
   ```bash
   af list   # in the source project — identify relevant documents
   ```
3. **Recreate relevant documents in the new project** — use `af create` with the new prefix:
   ```bash
   af create sop --prefix <NEWPREFIX> --area 20 --title "My SOP"
   ```
4. **Update content** — adapt titles, references, and sections to the new project context
5. **Review and remove** — skip documents that don't apply to the new project
6. **Rebuild the index**
   ```bash
   af index
   ```

---

## When to Use

- New project is structurally similar to an existing one
- You want a head start on project-layer documents

## When NOT to Use

- New project has very different needs — use COR-1700 (Initialize Project) alone
- Source project is archived — check if its documents are still relevant first

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-15 | Initial version | Claude Code |
| 2026-03-17 | Replace cp docs/*.md with af create workflow | Claude Code |
