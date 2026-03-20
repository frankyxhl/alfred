# SOP-1002: Read Document

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-14
**Last reviewed:** 2026-03-14
**Status:** Active

---

## What Is It?

A standard process for finding and reading existing documents in the system. Ensures team members can quickly locate the right document by number, type, or topic.

---

## Why

Without a standard lookup process, team members waste time guessing file paths or searching manually. This SOP provides consistent methods for finding any document by number, type, keyword, or prefix.

---

## When to Use

- Looking up a specific document by its ACID number
- Browsing available documents by type or prefix
- Finding a document when you only know the topic or keyword
- Orienting yourself in the document system for the first time

---

## When NOT to Use

- Creating a new document (use COR-1001 instead)
- Updating or modifying an existing document (use `af update`)
- Searching for content across multiple documents (use `af search`)

---

## Steps

1. **By number** — if you know the ACID number, read it directly:
   ```bash
   af read COR-1001    # read a specific document by PREFIX-ACID
   af read ALF-2100
   ```

2. **By type** — list all documents and filter visually or by type:
   ```bash
   af list             # shows all documents across all layers with type codes
   ```

3. **By keyword** — list and scan titles, or read relevant documents:
   ```bash
   af list             # scan titles for relevant documents
   ```

4. **By prefix** — list shows prefix and layer for each document:
   ```bash
   af list             # PKG layer shows COR docs; PRJ/USR show project-specific docs
   ```

---

## Document Structure

Every document starts with a header block:

```
# SOP-ACID: Title
Applies to: ...
Last updated: YYYY-MM-DD
```

Read the **What Is It?** section first for a quick summary, then drill into specific sections as needed.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-14 | Initial version | Claude Code |
| 2026-03-20 | Added Why/When to Use/When NOT to Use sections per ALF-2210 | Claude Code |
