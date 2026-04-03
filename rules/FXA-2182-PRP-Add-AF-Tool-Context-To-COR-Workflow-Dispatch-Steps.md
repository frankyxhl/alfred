# PRP-2182: Add-AF-Tool-Context-To-COR-Workflow-Dispatch-Steps

**Applies to:** FXA project
**Last updated:** 2026-04-01
**Last reviewed:** 2026-04-01
**Status:** Approved

---

## What Is It?

Add `af read` / `af list` usage guidance to the dispatch steps of COR-1601 and COR-1602 so that dispatched reviewers know how to access project documents.

---

## Problem

COR workflow SOPs (COR-1601, COR-1602) define dispatch steps where the Leader forwards artifacts to Reviewers, but provide no guidance on how reviewers should access project documents. Since COR documents ARE part of the `af` package, every project using these workflows has `af` installed — yet reviewers dispatched via `/trinity` don't know to use `af read` to access referenced documents.

During the 2026-04-01 evolve-sop run (FXA-2175), Gemini's agent couldn't find FXA-2165 because it searched the filesystem directly instead of using `af read`. This caused a false -4 score deduction.

The project-level SOP (FXA-2100) was patched via CHG FXA-2181, but this only helps projects that customize their dispatch template. The COR layer is the canonical source that ALL projects inherit from — adding guidance here ensures every project benefits without requiring per-project patches. FXA-2181 becomes redundant once COR carries the guidance, but both can coexist harmlessly.

## Scope

**In scope:**
- COR-1601 Step 4 (Leader forwards to Reviewers)
- COR-1602 Step 2 (Leader dispatches Reviewers)
- Markdown content changes only

**Out of scope:**
- COR-1600, COR-1603, COR-1604, COR-1605 (no reviewer dispatch steps)
- Python code changes
- FXA-2148/FXA-2149 (prohibited mutation surface)

## Proposed Solution

Add a "Dispatch context" note to the dispatch steps of COR-1601 and COR-1602.

### COR-1601 (Leader Mediated Review Loop)

After Step 4 ("Worker sends to Leader — Leader forwards to Reviewer(s)"), insert:

```markdown
   **Dispatch context:** When forwarding to Reviewers, include instructions
   for accessing project artifacts. Since all projects using this workflow
   have `af` installed, include:
   - `af read <ACID>` — read a document by ID
   - `af list` — list all documents
```

### COR-1602 (Multi Model Parallel Review)

After Step 2 ("Leader dispatches Reviewers — all Reviewers receive the same artifact in parallel"), insert:

```markdown
   **Dispatch context:** When dispatching Reviewers, include instructions
   for accessing project artifacts. Since all projects using this workflow
   have `af` installed, include:
   - `af read <ACID>` — read a document by ID
   - `af list` — list all documents
```

**Files changed** (in the fx_alfred source repo at `/Users/frank/Projects/alfred/fx_alfred/`):
1. `fx_alfred/src/fx_alfred/rules/COR-1601-SOP-Workflow-Leader-Mediated-Review-Loop.md` — insert after Step 4
2. `fx_alfred/src/fx_alfred/rules/COR-1602-SOP-Workflow-Multi-Model-Parallel-Review.md` — insert after Step 2

**No Python code changes.** Markdown-only.

**SOPs affected:** COR-1601, COR-1602.

## Risk

- **Over-specificity.** `af` is named directly in a COR document. Mitigation: COR IS part of `af` — every project using COR has `af` installed by definition. This is not a third-party tool reference.
- **Stale examples.** If `af read`/`af list` syntax changes, the note becomes outdated. Mitigation: these are core stable commands unlikely to change.
- **Test impact.** Existing tests in `fx_alfred/tests/` may validate COR document structure. Mitigation: run `cd /Users/frank/Projects/alfred/fx_alfred && .venv/bin/pytest -v --tb=short` to verify no breakage.
- **Rollback.** `cd /Users/frank/Projects/alfred/fx_alfred && git checkout HEAD -- src/fx_alfred/rules/COR-1601-*.md src/fx_alfred/rules/COR-1602-*.md`

## Open Questions

None.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-01 | Initial version | — |
| 2026-04-01 | R1: Add Scope section, fix file paths, remove `af validate` from dispatch context, restate exact COR-1602 text, strengthen necessity argument (Codex feedback) | Claude Code |
