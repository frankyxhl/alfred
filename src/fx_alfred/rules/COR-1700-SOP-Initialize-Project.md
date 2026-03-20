# SOP-1700: Initialize Project

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-15
**Last reviewed:** 2026-03-15
**Status:** Active

---

## What Is It?

The process for onboarding a new project into the Alfred document system. After initialization, the project's LLM can run `af list` and `af read` to operate autonomously within the system.

---

## Steps

1. **Choose a 3-letter prefix** — must be unique across all projects (e.g., TCY for tracy)
2. **Install fx-alfred into the project**
   ```bash
   pip install fx-alfred
   ```
3. **Read the quick start guide**
   ```bash
   af guide
   ```
4. **Create your first document and generate the index**
   ```bash
   af create sop --prefix <PREFIX> --area 20 --title "My First SOP"
   af index
   ```
   The `af index` command generates the `<PREFIX>-0000-REF-Document-Index.md` automatically.
5. **Add INIT reference to project config** — in `CLAUDE.md` or equivalent:
   ```markdown
   Run `af list` and `af read COR-0001` before starting any task.
   ```
6. **Verify** — ask the LLM to run `af list` and confirm it understands the system

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-15 | Initial version | Claude Code |
| 2026-03-17 | Replace cp-based setup with pip install fx-alfred + af create workflow | Claude Code |
