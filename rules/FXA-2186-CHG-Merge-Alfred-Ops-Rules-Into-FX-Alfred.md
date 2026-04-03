# CHG-2186: Merge-Alfred-Ops-Rules-Into-FX-Alfred

**Applies to:** FXA project
**Last updated:** 2026-04-03
**Last reviewed:** 2026-04-03
**Status:** Proposed
**Date:** 2026-04-03
**Requested by:** —
**Priority:** Medium
**Change Type:** Normal

---

## What

Merge `alfred_ops/rules/` into `fx_alfred/rules/` (PRJ layer), archive the `alfred_ops` git history, then remove the `alfred_ops` directory. All 94+ FXA-*/ALF-* project documents move into the fx_alfred project root as the PRJ layer.

## Why

- `alfred_ops` exists solely to hold `rules/` — the `.claude/trinity.json` and `--project-dir/` inside are minimal/temporary
- Consolidating into `fx_alfred/rules/` simplifies the repo structure and eliminates the separate `alfred_ops` directory
- The PRJ layer (`fx_alfred/rules/`) is already the correct location per the three-layer document model
- pip packaging is unaffected: `pyproject.toml` only packages `src/fx_alfred/`, so `rules/` at project root is excluded

## Impact Analysis

- **Systems affected:**
  - Repository directory structure
  - `af` commands that use `--root alfred_ops` (3 external files + CLAUDE.md references)
  - FXA-2127 SOP (Commit Alfred Ops) — becomes obsolete
  - FXA-2100 and FXA-2125 reference FXA-2127 — dangling references after deprecation
  - 23 documents within `alfred_ops/rules/` that reference `alfred_ops` paths (79 occurrences)
  - `.claude/commands/evolve-sop.md` and `.claude/commands/evolve-cli.md`
  - `fx_alfred/CLAUDE.md` (5 lines reference `alfred_ops`)
  - Claude memory files (`~/.claude/projects/-Users-frank-Projects-alfred/memory/`): `project_af_command_usage.md`, `feedback_read_routing_sop.md`, `feedback_trinity_af_instructions.md`, and `MEMORY.md`
  - Top-level `rules/FXA-0000-REF-Document-Index.md` (duplicate, to be removed)
- **Git history:** `alfred_ops` is a standalone git repo with 36 commits. History will be archived via `git bundle` then discarded. Document provenance is acceptable to lose per stakeholder decision.
- **Rollback plan:** Restore from the archived bundle (`git clone fx_alfred/alfred_ops-archive.bundle alfred_ops`)

## Implementation Plan

1. Archive `alfred_ops` git history: `cd alfred_ops && git bundle create ../fx_alfred/alfred_ops-archive.bundle --all`
2. Copy all files from `alfred_ops/rules/` to `fx_alfred/rules/`
3. Remove top-level `rules/FXA-0000-REF-Document-Index.md` (duplicate of the one in alfred_ops)
4. Remove the `alfred_ops/` directory
5. Verify `af list --root fx_alfred` picks up the merged documents
6. Run `af validate --root fx_alfred` to check document integrity
7. Update references in external files (`--root alfred_ops` → `--root fx_alfred`):
   - `fx_alfred/CLAUDE.md`
   - `.claude/commands/evolve-sop.md`
   - `.claude/commands/evolve-cli.md`
8. Update `alfred_ops` references within merged `fx_alfred/rules/` documents (23 files, 79 occurrences)
9. Deprecate FXA-2127 (Commit Alfred Ops SOP) — no longer applicable
10. Update FXA-2100 and FXA-2125 to remove/replace references to FXA-2127
11. Update Claude memory files (`~/.claude/projects/-Users-frank-Projects-alfred/memory/`) that reference `alfred_ops`

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-03 | Initial version | — |
| 2026-04-03 | R2: fix rollback path, correct doc count 13→23, add memory files, add FXA-2100/2125 update step | — |
