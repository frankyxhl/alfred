# CHG-2124: Layered Workflow Routing AF Guide

**Applies to:** FXA project
**Last updated:** 2026-03-20
**Last reviewed:** 2026-03-20
**Status:** Completed
**Date:** 2026-03-20
**Requested by:** Frank
**Priority:** High
**Change Type:** Normal
**Related:** FXA-2220, COR-1103

---

## What

Implement FXA-2220 PRP: layered workflow routing with enhanced `af guide`. Four deliverables:

1. **Enhance `af guide`** — Change from static quick-start to dynamic routing output that scans PKG → USR → PRJ for `*-SOP-Workflow-Routing*.md` documents, filters by `Status: Active`, and outputs full content per layer
2. **Move quick-start to `af --help`** — Current `templates/guide.md` content becomes CLI epilog
3. **Create USR routing doc** — `ALF-2207-SOP-Workflow-Routing-USR.md` in `~/.alfred/` with cross-project user preferences
4. **Create PRJ routing doc** — `FXA-2125-SOP-Workflow-Routing-PRJ.md` in `alfred_ops/rules/` with project-specific SOP mappings (separate ACID from this CHG to avoid duplicate)

### `af guide` implementation detail

- Add `@root_option` and `@click.pass_context` decorators to `guide_cmd`
- Use `scan_or_fail(ctx)` from `_helpers.py` to find all documents (follows established helper pattern)
- Filter by filename containing `SOP-Workflow-Routing`
- Parse metadata, select only `Status: Active`
- If multiple Active in one layer, use lowest ACID
- Output full document text per layer with separator headers
- Missing layer → output note, continue

## Why

COR-1103 (PKG) can only reference generic SOP types, not project-specific SOPs. Without USR/PRJ routing docs, the agent must discover project workflows by reading all documents or being reminded. `af guide` as the delivery mechanism gives a single command for full routing context.

## Impact Analysis

- **Systems affected:** `guide_cmd.py`, `cli.py` (epilog), `templates/guide.md` (removed or repurposed), `tests/test_guide_cmd.py`
- **Rollback plan:** `git revert` the commit

## Implementation Plan (TDD per COR-1500)

1. Write failing tests for new `af guide` behavior:
   - Scans and outputs PKG routing doc
   - Scans and outputs USR routing doc if present
   - Scans and outputs PRJ routing doc if present
   - Skips Deprecated routing docs
   - Handles missing layers gracefully
   - Shows separator headers between layers
   - Handles MalformedDocumentError (show filename + error, continue to next valid candidate or next layer)
   - Warns when multiple Active routing docs found in same layer
   - Selects lowest-ACID doc when multiple Active exist (tie-break verification)
   - `af --help` epilog contains quick-start content (document naming, layer system, create examples)
2. Run tests — confirm RED
3. Implement `guide_cmd.py` changes
4. Run tests — confirm GREEN
5. Write failing test for `af --help` epilog content, then add epilog to `cli.py` — RED then GREEN
6. Run full test suite — confirm no regression
7. Create USR routing doc (`~/.alfred/ALF-2207-SOP-Workflow-Routing-USR.md`)
8. Create PRJ routing doc (`alfred_ops/rules/FXA-2125-SOP-Workflow-Routing-PRJ.md`)
9. Remove or repurpose `templates/guide.md` (cleanup after migration)
10. Update memory entry: `af guide --root <project-root>` instead of `af read COR-1103`
11. Commit

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version | Claude Code |
| 2026-03-20 | Round 1 revision: PRJ routing doc ACID changed to FXA-2125, added @click.pass_context, scan_or_fail(ctx) instead of scan_documents(root), added MalformedDocumentError + multi-match warning tests, added guide.md cleanup step | Claude Code |
| 2026-03-20 | Round 2 revision: memory entry includes --root, added lowest-ACID tie-break test, epilog migration now TDD-driven (RED first), malformed doc fallback clarified | Claude Code |
