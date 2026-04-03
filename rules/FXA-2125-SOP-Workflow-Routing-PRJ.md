# SOP-2125: Workflow Routing PRJ

**Applies to:** FXA project
**Last updated:** 2026-03-30
**Last reviewed:** 2026-03-20
**Status:** Active

---

## What Is It?

Project-level workflow routing for the FXA (fx-alfred) project. Supplements COR-1103 (PKG) with project-specific decision tree, SOP mappings, and golden rules.

---

## Why

Without project-level routing, contributors must memorize which SOP applies to each situation. This document provides a single lookup point that maps common tasks to the correct FXA procedure, reducing wrong-workflow errors.

---

## When to Use

- Starting any task in the FXA project and unsure which SOP to follow
- Onboarding a new contributor who needs to understand FXA workflows
- Verifying that the correct procedure is being followed for a given task

---

## When NOT to Use

- Working in a different project (ALF, COR) -- use that project's routing document
- The task and its SOP are already known -- go directly to that SOP

---

## Project Decision Tree

```
What do you need to do in the FXA project?

1. Release a new version?
   └── FXA-2102 (Release To PyPI)
       Prerequisites: tests pass + ruff clean + version bump + pushed to main + README up to date (FXA-2136)
       Steps: gh release create → CI auto-publish → verify on PyPI

2. Develop a new feature / modify code?
   └── FXA-2100 (Leader Mediated Development)
       New feature: PRP (COR-1102) → Review (COR-1602 strict) → CHG → TDD
       Modify existing: CHG (COR-1101) → Review → TDD (COR-1500)
       Implementation: /trinity glm "task" (GLM writes code)
       Review: /trinity codex "review" gemini "review" (Codex+Gemini review code)

3. Bug / incident occurred?
   └── ALF-2300 (Record Incident)
       Record: what happened, impact, resolution, follow-up
       If code changes needed: INC + CHG (COR-1101) → TDD

4. Review PRP/CHG/Code?
   └── COR-1602 (Parallel Review) + scoring rubric:
       PRP → COR-1608 (6 dimensions + OQ hard gate)
       CHG → COR-1609 (5 dimensions, PLN/ADR fallback)
       Code → COR-1610 (5 dimensions)
       All reviewers read COR-1611 (Calibration Guide)

5. View/manage Draft PRPs?
   └── af list --type PRP --root fx_alfred
       Approval: COR-1602 strict (both >= 9)
       Implementation: CHG → TDD

6. Create/modify project documents?
   └── af create --prefix FXA --area 21 --root fx_alfred
       Document type selection: COR-1102 decision table
       Update: af update IDENTIFIER --root fx_alfred

7. Discuss/track a topic?
   └── COR-1201 (Discussion Tracking)
       D new <topic> / D list / D show N / D start N / D done N / D defer N

8. Run validation?
   └── .venv/bin/pytest tests/ -v --tb=short      (tests)
       .venv/bin/ruff check .                       (lint)
       af validate --root fx_alfred                (document validation)

9. End of session?
   └── FXA-2127 (Commit Alfred Ops)
       Steps: git status → delete ALF-0000 → git add rules/ → git commit → af validate
       If code changes exist: follow FXA-2102 release process
```

## Project Context

```
Package:     fx-alfred
Source:      fx_alfred/src/fx_alfred/
Tests:       fx_alfred/tests/ (pytest)
Docs:        fx_alfred/rules/ (af CLI)
Prefix:      FXA
Area:        21 (2100-2199)
Root:        --root /Users/frank/Projects/alfred/fx_alfred
Dev install: cd fx_alfred && pip install -e .
```

## Project Golden Rules

```
FXA-2102: Release = version bump → push → gh release create → CI publishes to PyPI
FXA-2100: Leader dispatches GLM (Worker), reviews with Codex+Gemini (Reviewer)
ALF-2300: Incident = record what happened, impact, resolution, follow-up
COR-1500: Any code change → TDD: failing test first, then green, then refactor
af create: Never manually create .md files, always af create --prefix FXA --area 21
af validate: Run after document migrations to confirm 0 issues
fx_alfred: Documents live in rules/ (PRJ layer), document changes, no remote (local git only)
```

## Steps

This is a routing SOP — no procedural steps. The Project Decision Tree above is the primary content. Follow it to determine which SOP applies to your current task.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version per ALF-2206 | Frank + Claude Code |
| 2026-03-20 | Rewritten: added project decision tree, project context, expanded golden rules | Frank + Claude Code |
| 2026-03-20 | FXA-2133: Add Why, When to Use, When NOT to Use sections (5W1H migration) | Claude Code |
| 2026-03-21 | Added Steps section (routing SOP, no procedural steps) | Claude Code |
| 2026-03-30 | CHG FXA-2153: Translated decision tree from Chinese to English (COR-0002/COR-1401 compliance) | Claude Code |
