# SOP-1701: Archive Project

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-15
**Last reviewed:** 2026-03-15
**Status:** Active

---

## What Is It?

The process for retiring a project that is no longer active. The project is preserved for historical reference but marked as archived.

---

## Steps

1. **Confirm the project is no longer active** — check with stakeholders or project lead
2. **Add an archive notice** — create or update the project's README:
   ```markdown
   > **ARCHIVED** — This project is no longer active as of YYYY-MM-DD.
   > Reason: <why it was archived>
   ```
3. **Deprecate all active business-layer documents** — follow COR-1301 for each
4. **Final commit** — commit the archive notice and deprecation changes
5. **Do not delete the project** — archived projects stay for historical reference
6. **Update any cross-references** — other projects that link to this one should note the archive

---

## When NOT to Archive

- The project is paused but expected to resume — leave it as-is
- Only some documents are outdated — deprecate those individually (COR-1301), don't archive the whole project

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-15 | Initial version | Claude Code |
