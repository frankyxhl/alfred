# SOP-2125: Workflow Routing PRJ

**Applies to:** FXA project
**Last updated:** 2026-04-04
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

9. Create a task ticket / GitHub issue?
   └── COR-1501 (Create GitHub Issue)
       Determine type → write with blueprint template → gh issue create --repo <repo> → gh issue view <number>

10. Pick next open issue / start autonomous loop?
    └── FXA-2276 (Multi-Agent Loop Configuration)
        Invocations (rocket-gate semantics per COR-1618 §Normative Bypass — bypass applies only when the operator names a specific ACID):
        - `follow FXA-2276`        → looping mode: full COR-1618 verify_consent_eligibility on every pick (no bypass); pick lowest-rank rocket-eligible issue, run COR-1617 phases 2–10, on mergeable detection run Phase 11 (Retrospective) synchronously, then re-enter phase 1 via §12 wake; idle-retry 1800 s × 12 ≈ 6 h when queue empty
        - `follow FXA-2276 once`   → same gate as `follow FXA-2276` (full COR-1618 on every pick) but single pick, run phases 2–11, stop after phase 11 (no §12 wake, no autonomous continuation)
        - `follow FXA-2276 for #N` → user-directed pick of issue #N — gate-bypassed per COR-1618 §Normative Bypass Clause, run phases 2–11 regardless of rocket-gate state, stop after phase 11 (no §12 wake)
        Underlying chain (for drop-down debugging): COR-1617 §1 (Auto-pick) → COR-1618 (consent) → COR-1506 (quality) → scope-rank tree
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
fx_alfred: Documents live in rules/ (PRJ layer), document changes committed with code
COR-1501: GitHub issue = blueprint template + stack-type-* / stack-area-* label pair
FXA-2276: "follow FXA-2276" is the alfred entry-point for picking the next open issue (User-driven trigger per COR-1617 §1, gate-bypassed per COR-1618 §Normative Bypass)
```

## Steps

This is a routing SOP — no procedural steps. The Project Decision Tree above is the primary content. Follow it to determine which SOP applies to your current task.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version per FXA-2220 | Frank + Claude Code |
| 2026-03-20 | Rewritten: added project decision tree, project context, expanded golden rules | Frank + Claude Code |
| 2026-03-20 | FXA-2133: Add Why, When to Use, When NOT to Use sections (5W1H migration) | Claude Code |
| 2026-03-21 | Added Steps section (routing SOP, no procedural steps) | Claude Code |
| 2026-03-30 | CHG FXA-2153: Translated decision tree from Chinese to English (COR-0002/COR-1401 compliance) | Claude Code |
| 2026-04-04 | CHG FXA-2190: Remove deprecated FXA-2127 ref from decision tree, fix stale "no remote" golden rule | Claude Code |
| 2026-05-10 | issue #126: add branch 9 (Create GitHub issue → COR-1501) to decision tree; add COR-1501 traceability line to Golden Rules | Claude Opus 4.7 |
| 2026-05-16 | issue #162: add branch 10 (Pick next open issue / autonomous loop → FXA-2276) to decision tree; add FXA-2276 line to Golden Rules | Claude Opus 4.7 |
| 2026-05-16 | issue #163 (bundled with #162 in PR #164): tighten branch 10 header — clarify that only `follow FXA-2276 for #N` is gate-bypassed; `follow FXA-2276` and `follow FXA-2276 once` apply full COR-1618 verify_consent_eligibility on every pick (aligns with the FXA-2276 §Invocation tightening in the same PR) | Claude Opus 4.7 |
