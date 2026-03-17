# SOP-1700: Initialize Project

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-15
**Last reviewed:** 2026-03-15

---

## What Is It?

The process for onboarding a new project into the Alfred document system. After initialization, the project's LLM can read `.alfred/INIT.md` and operate autonomously within the system.

---

## Steps

1. **Choose a 3-letter prefix** — must be unique across all projects (e.g., TCY for tracy)
2. **Copy `.alfred/` into the project** — this gives the project all COR meta-layer documents
   ```bash
   cp -r /path/to/alfred/.alfred/ /path/to/new-project/.alfred/
   ```
3. **Create `docs/` directory** — for business-layer documents
   ```bash
   mkdir -p docs
   ```
4. **Create the project index** — `<PREFIX>-0000-REF-Document-Index.md` in `docs/`
   ```markdown
   # REF-0000: Document Index (<PREFIX> Business Layer)

   **Applies to:** <project name>
   **Last updated:** YYYY-MM-DD

   ---

   ## Category Structure

   | Area | Category | Description |
   |------|----------|-------------|
   | 20xx | (define per project) | ... |

   ---

   ## Document List

   (empty — add documents as they are created)

   ---

   ## See Also

   - .alfred/COR-0000-REF-Document-Index.md — Meta layer documents

   ---

   ## Change History

   | Date | Change | By |
   |------|--------|----|
   | YYYY-MM-DD | Initial version | Author |
   ```
5. **Add INIT reference to project config** — in `CLAUDE.md` or equivalent:
   ```markdown
   Read .alfred/INIT.md before starting any task.
   ```
6. **Verify** — ask the LLM to read `.alfred/INIT.md` and confirm it understands the system

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-15 | Initial version | Claude Code |
