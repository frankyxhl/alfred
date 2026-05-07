# CHG-2272: Merge fx_alfred/rules Into Top-Level rules

**Applies to:** FXA project
**Last updated:** 2026-05-07
**Last reviewed:** 2026-05-07
**Status:** Proposed
**Date:** 2026-05-07
**Requested by:** —
**Priority:** Medium
**Change Type:** Normal

---

## What

Merge the orphan `fx_alfred/rules/` PRJ-style tree into the canonical top-level `rules/` tree by renumbering the 23 colliding FXA ACIDs and moving the non-colliding FXA-2248 directly. Delete `fx_alfred/rules/` after the move. Update repo-level references (CLAUDE.md, the COR-1204 CTX-Format pilot pointer, and one test-file comment).


## Why

The repository accumulated two PRJ-like trees that reuse the FXA-21xx ACID space for **different content**:

- `rules/` (top-level, 149 files): the alfred project's main workstream — `FXA-2102-SOP-Release-To-PyPI`, `FXA-2148-SOP-Evolve-SOP`, `FXA-2247-CHG-Pytest-Governance`, etc.
- `fx_alfred/rules/` (25 files): an evolve-audit + COR-promotion + glossary-pilot tree that started using `FXA-2100`, `FXA-2102`, `FXA-2123`, etc. independently.

`af` only scans one PRJ root per `--root` flag, so the divergence is invisible until two docs claim the same ACID. Reusing the same ACID for different content also breaks the COR-0002 contract that an ACID is a stable identifier.

The two trees are **not mirrors** — only `FXA-0000-REF-Document-Index.md` shares a filename, with different content. Going forward only `rules/` (top-level) will exist.


## Impact Analysis

**Files renumbered (24 docs)**

| Old (in `fx_alfred/rules/`) | New (in top-level `rules/`) |
|---|---|
| FXA-2100 REF Evolve CLI Run | FXA-2249 |
| FXA-2101 PRP Extract H1 Regex | FXA-2250 |
| FXA-2102 CHG Consolidate H1 Regex | FXA-2251 |
| FXA-2103 REF Evolve Run | FXA-2252 |
| FXA-2104 PRP Validate Status Flag | FXA-2253 |
| FXA-2105 CHG Validate Status Flag | FXA-2254 |
| FXA-2106 REF Evolve Run | FXA-2255 |
| FXA-2107 CHG Add Completion Checklist (CLI SOP) | FXA-2256 |
| FXA-2108 PRP Deduplicate Total Issues | FXA-2257 |
| FXA-2109 CHG Deduplicate Total Issues | FXA-2258 |
| FXA-2110 CHG Add Completion Checklist (Evolve SOP) | FXA-2259 |
| FXA-2111 CHG Add Post-Push Review Loop | FXA-2260 |
| FXA-2112 CHG Reorder Review Loop | FXA-2261 |
| FXA-2113 PRP COR-1613 Council Review | FXA-2262 |
| FXA-2114 CHG COR-1103 Add Council Routing | FXA-2263 |
| FXA-2115 CHG COR-1602 Add Council Cross-Reference | FXA-2264 |
| FXA-2116 PRP COR-1503 Diagnose Feedback Loop | FXA-2265 |
| FXA-2118 CHG COR-1103 Add Diagnose Routing | FXA-2266 |
| FXA-2119 CHG COR-1613 Add Half-Diagnosed Fix Prohibition | FXA-2267 |
| FXA-2120 CHG COR-1504-REF Diagnose Phase Gates | FXA-2268 |
| FXA-2121 PRP COR-1203 Pre-Task Alignment | FXA-2269 |
| FXA-2122 CHG COR-1103 Add Pre-Task Alignment Routing | FXA-2270 |
| FXA-2123 CTX Alfred Glossary | FXA-2271 |
| FXA-2248 REF SOP Outcome Notebook | FXA-2248 (no change) |

**Internal cross-refs to update**: 23 inside the renumbered docs. Cross-tree refs to top-level (FXA-2148 / 2149 / 2150 / 2230) stay untouched.

**Repo-level references to update**:

- `CLAUDE.md` lines 92 and 141 — change `fx_alfred/rules/` to `rules/` (project root PRJ).
- `src/fx_alfred/rules/COR-1204-REF-CTX-Format.md` line 62 — update `FXA-2123-CTX-Alfred-Glossary.md` reference to `FXA-2271-CTX-Alfred-Glossary.md`.
- `tests/test_workflow_loops.py` line 898 — fix incorrect comment (`PKG layer is bundled in fx_alfred/rules/` → `PKG layer is bundled in src/fx_alfred/rules/`). PKG bundle has always been at `src/fx_alfred/rules/`; the comment was wrong before this CHG.

**Out of scope**:

- `src/fx_alfred/rules/` (PKG layer, the bundled COR docs that ship in the wheel) — untouched.
- `~/.alfred/` (USR layer) — untouched.
- `src/fx_alfred/CHANGELOG.md:204` historical reference (PR #63) — left as-is, describes past state.
- Any structural change to `af` scanner or schema — none required.


## Implementation Plan

1. Apply renumber mapping script to all 23 renumbered files: rewrite H1 ACID and any internal FXA-21xx refs that map within the renumber set.
2. Move FXA-2248 directly (no body change — its only refs are top-level 2150 / 2230).
3. Delete the `fx_alfred/rules/` directory entirely.
4. Apply repo-level reference updates (CLAUDE.md, COR-1204, tests/test_workflow_loops.py).
5. Run `af index --root /Users/frank/Projects/alfred` to regenerate the top-level FXA-0000 index.
6. Run `af validate --root /Users/frank/Projects/alfred` — must report 0 structural issues.
7. Run `pytest -q`, `ruff check`, `ruff format --check`, `pyright src/` — must all pass.


---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-07 | Initial version | — |
