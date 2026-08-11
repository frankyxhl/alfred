# CHG-2322: Add COR-1005 Engineer Workflow Loops

**Applies to:** FXA project
**Last updated:** 2026-08-11
**Last reviewed:** 2026-08-11
**Status:** Completed
**Date:** 2026-08-11
**Requested by:** Frank Xu (session request: loop-engineering SOP for non-sequential SOP execution)
**Priority:** Medium
**Change Type:** Normal
**Targets:** src/fx_alfred/rules/COR-1005-SOP-Engineer-Workflow-Loops.md (new), src/fx_alfred/rules/COR-1000-SOP-Create-SOP.md, src/fx_alfred/rules/COR-1103-SOP-Workflow-Routing.md, src/fx_alfred/rules/COR-0000-REF-Document-Index.md

---

## What

One new PKG-layer SOP promoting loop engineering — the design discipline for
non-sequential SOPs — plus pointer rows in the two authoring/routing documents:

- **COR-1005 SOP — Engineer Workflow Loops**: when to use sequential steps vs
  `Workflow branches:` vs `Workflow loops:` vs a cross-SOP back-edge; dual-exit
  design (observable success condition + defined exhaustion path);
  `max_iterations` budgeting; observable `condition` predicates; exact metadata
  syntax; verification via `af plan --graph` and `af validate`; runtime-governance
  pointers to COR-1620/1624/1625/1626.
- **COR-1000**: one Prerequisites pointer line to COR-1005.
- **COR-1103**: one intent-router row for loop/branch SOP design.
- **COR-0000**: index row for 1005.

## Why

The engine already parses, validates, and renders `Workflow loops:` /
`Workflow branches:` metadata, and the corpus has seven-plus SOPs that *run*
specific loops (COR-1617 cluster, COR-1624–1627, COR-1503, COR-1600/1601) — but
no document teaches authors *how to design* a loop. Result: only COR-1602
declares a machine-readable loop; every other iterative process is authored as
prose ("repeat as needed"), invisible to `af plan`, `--graph`, and `af validate`.
External grounding: LangChain "The Art of Loop Engineering" (exit criteria via
rubrics, verification loops) and cobusgreyling/loop-engineering (phased autonomy
— already covered by COR-1624–1626; the authoring-discipline gap is what remains).

## Impact Analysis

- **Systems affected:** PKG rules corpus only (one new doc + three one-line/one-row
  edits). No code paths change; `af` behavior identical.
- **Consumers:** COR-1005 is `inherit-only`; all projects see it via `af guide`
  routing. Non-authors see one extra `af list` row.
- **No cascade:** COR-1617/1620/1624–1627 are referenced, not edited.
- **Rollback plan:** delete COR-1005, revert the three pointer/index edits,
  set this CHG to Rolled Back, `af index` to refresh the PRJ index.

## Implementation Plan

1. Author COR-1005 following COR-1602/COR-1628 section conventions; syntax
   examples verified against `src/fx_alfred/core/workflow.py` schema.
2. Add COR-1000 Prerequisites pointer + COR-1103 router row + COR-0000 index row.
3. CHANGELOG Unreleased entry; regenerate `docs/` via `scripts/build_docs.py`.
4. Validate: full pytest (docs drift/format tests), `af validate`, `af fmt --check`
   on the new doc, `af plan --graph COR-1005` visual check.
5. Review per COR-1600 (Direct Review) minimum, then PR.

---

## Change History

| Date       | Change          | By          |
|------------|-----------------|-------------|
| 2026-08-11 | Initial version | Claude Code |
| 2026-08-11 | Implemented: COR-1005 authored, pointers + index + CHANGELOG updated | Claude Code |
