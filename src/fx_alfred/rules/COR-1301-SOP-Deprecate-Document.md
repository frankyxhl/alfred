# SOP-1301: Deprecate Document

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-20
**Last reviewed:** 2026-03-14
**Status:** Active

---

## What Is It?

A standard process for retiring a document that is no longer needed. Documents are never deleted — they are marked as deprecated so the history remains traceable.

---

## Why

Deleting documents destroys audit trails; deprecation preserves history while clearly signalling a document is no longer active.

---

## When to Use

- A document is obsolete and has been replaced by a newer version
- A document covers a process that no longer exists
- A document was created in error and should not be referenced

---

## When NOT to Use

- The document still has active consumers or references that depend on it
- The content needs updating rather than retiring — use the update process instead
- You want to temporarily hide a document — deprecation is permanent intent

---

## Steps

1. **Confirm the document is no longer needed** — check if any other documents reference it
2. **Add a deprecation notice** — insert at the top of the document, below the title:
   ```markdown
   > **DEPRECATED** — This document is no longer active as of YYYY-MM-DD.
   > Superseded by: <COR-NNNN / ALF-NNNN> (if applicable)
   ```
3. **Update the Change History** — add an entry noting the deprecation and reason
4. **Update referencing documents** — any document that links to this one should be updated to point to the replacement (if any)
5. **Do not delete the file** — deprecated documents stay in their layer for historical reference

---

## Rules

- Never delete a document — deprecate it instead
- If a document is being replaced, always link to the replacement in the deprecation notice
- If a deprecated document is later needed again, remove the deprecation notice and add a Change History entry noting the reactivation

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-14 | Initial version | Claude Code |
| 2026-03-20 | Added Why/When to Use/When NOT to Use sections per FXA-2223 | Claude Code |
