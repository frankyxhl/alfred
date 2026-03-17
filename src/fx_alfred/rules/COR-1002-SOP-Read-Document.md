# SOP-1002: Read Document

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-14
**Last reviewed:** 2026-03-14

---

## What Is It?

A standard process for finding and reading existing documents in the system. Ensures team members can quickly locate the right document by number, type, or topic.

---

## Steps

1. **By number** — if you know the ACID number, list files matching the prefix:
   ```bash
   ls docs/COR-11*    # all "Do" phase docs
   ls docs/ALF-21*    # all "Development" category docs
   ```

2. **By type** — filter by the 3-letter type code:
   ```bash
   ls docs/*-SOP-*    # all SOPs
   ls docs/*-PLN-*    # all plans
   ls docs/*-ADR-*    # all decision records
   ```

3. **By keyword** — search document contents:
   ```bash
   grep -rl "keyword" docs/
   ```

4. **By prefix** — distinguish meta vs business layer:
   ```bash
   ls docs/COR-*      # universal/meta documents
   ls docs/ALF-*      # project-specific documents
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
