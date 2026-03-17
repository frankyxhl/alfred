# SOP-1702: Sync Project

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-15
**Last reviewed:** 2026-03-15

---

## What Is It?

The process for updating a project's `.alfred/` directory with the latest COR documents from the alfred source repository.

---

## Steps

1. **Pull latest from alfred repo**
   ```bash
   cd /path/to/alfred
   jj git fetch && jj rebase -d main
   ```
2. **Copy `.alfred/` to the target project**
   ```bash
   cp -r /path/to/alfred/.alfred/ /path/to/target-project/.alfred/
   ```
3. **Verify** — check that the target project's `.alfred/COR-0000-REF-Document-Index.md` matches the source

---

## When to Sync

- After COR documents are updated in the alfred repo
- When onboarding a project that was initialized with an older version

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-15 | Initial version | Claude Code |
