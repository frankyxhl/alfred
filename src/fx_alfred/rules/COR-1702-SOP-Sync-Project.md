# SOP-1702: Sync Project

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-15
**Last reviewed:** 2026-03-15
**Status:** Active

---

## What Is It?

The process for updating a project with the latest COR documents from the fx-alfred package.

---

## Why

COR documents evolve as processes improve. If a project stays on an older fx-alfred version, its bundled SOPs, PRPs, and guides become stale. Syncing ensures every project operates from the same current baseline.

---

## When to Use

- When a new version of fx-alfred is released with updated COR documents
- When onboarding a project that was initialized with an older version

## When NOT to Use

- When the project intentionally pins a specific fx-alfred version for stability
- When only USR/PRJ layer documents changed -- those are not affected by package sync

---

## Steps

1. **Upgrade fx-alfred to get latest COR documents**
   ```bash
   pip install --upgrade fx-alfred
   ```
2. **Verify** — check that COR documents are current:
   ```bash
   af list
   af read COR-0000
   ```

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-15 | Initial version | Claude Code |
| 2026-03-17 | Replace cp-based sync with pip install --upgrade fx-alfred | Claude Code |
| 2026-03-20 | Migrate to standard 5W1H section structure (FXA-2133) | Claude Code |
