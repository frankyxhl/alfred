# CHG-2219: Migrate ALF Prefix To FXA In PRJ Rules

**Applies to:** FXA project (`fx_alfred/rules/` PRJ layer)
**Last updated:** 2026-04-26
**Last reviewed:** 2026-04-26
**Status:** Approved
**Date:** 2026-04-26
**Requested by:** Frank Xu
**Priority:** High (blocks `af` CLI — duplicate ACID error)
**Change Type:** Normal
**Targets:** `rules/ALF-*.md` (6 documents)

---

## What

Rename all ALF-prefixed PRJ documents in `fx_alfred/rules/` to the FXA prefix, and update every reference across the repo.

| Old | New | Type | Title |
|-----|-----|------|-------|
| ALF-2206 | FXA-2220 | PRP | Layered Workflow Routing USR And PRJ |
| ALF-2208 | FXA-2221 | PRP | Standardized Review Scoring Framework |
| ALF-2209 | FXA-2222 | PRP | Team Skill Session Resume |
| ALF-2210 | FXA-2223 | PRP | Standardized SOP Section Structure |
| ALF-2211 | FXA-2224 | PRP | Workflow Enforcement From Advisory To Mandatory |
| ALF-0000 | (delete) | REF | Auto-regenerated — content folds into FXA-0000 by `af index` |

## Why

Duplicate ACID `ALF-2206` between USR (`~/.alfred/ALF-2206-SOP-Multi-Model-Feasibility-Study.md`, 2026-04-25) and PRJ (`fx_alfred/rules/ALF-2206-PRP-Layered-Workflow-Routing-USR-And-PRJ.md`, 2026-03-20) blocks `af guide` / `af plan` / `af read` with `Error: Duplicate ALF-2206 found`.

Root cause: USR and PRJ both issue into the shared `ALF-NNNN` pool with no coordination. The PRJ `fx_alfred` documents predate the FXA prefix convention; later FXA-prefixed PRJ docs (FXA-21xx series) were added but the original 6 ALF-prefixed docs were never migrated. ALF-2208/9/10/11 are time bombs — USR can collide with any of them next.

Renaming only ALF-2206 unblocks `af` today but leaves 4 future collisions. Migrating all 6 eliminates the structural problem: PRJ `fx_alfred/rules/` uses FXA exclusively; USR `~/.alfred/` retains the ALF namespace.

## Impact

- **Renamed files** (6): `rules/ALF-{0000,2206,2208,2209,2210,2211}-*.md` → `rules/FXA-{0000-merged,2220,2221,2222,2223,2224}-*.md` (ALF-0000 deleted; FXA-0000 absorbs entries via `af index`).
- **In-content header updates**: Each renamed doc's `# PRP-NNNN: …` line and any internal cross-references.
- **Cross-references to update** (~25 occurrences across):
  - `CLAUDE.md`, `README.md` (project root)
  - `rules/FXA-21*.md` (CHGs and PRPs that cite the ALF docs)
  - `src/fx_alfred/CHANGELOG.md`
  - `src/fx_alfred/rules/COR-100*.md` (PKG docs that mention ALF as an example prefix — verify each)
- **`af index`** regenerates `FXA-0000-REF-Document-Index.md`; `ALF-0000` is removed from the working tree.
- **Historical references** (commit messages, PR bodies, closed issues): not rewritten — they remain pointing to ALF-NNNN, which is acceptable because the CHG record below maps old→new for forensic lookup.
- **Rollback:** revert this PR; `git mv` is reversible.

## Approval

- [x] Approved by: Frank Xu on 2026-04-26 (via session decision)

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-26 | Initial proposal — full migration of 6 ALF docs to FXA prefix in PRJ layer | Claude Code |
