# CHG-2297: CLAUDE Md Refresh And Drift Guard

**Applies to:** FXA project
**Last updated:** 2026-06-12
**Last reviewed:** 2026-06-11
**Status:** Completed
**Date:** 2026-06-11
**Requested by:** Frank Xu (session review finding 2026-06-10; follow-up batch 2026-06-11)
**Priority:** Medium
**Change Type:** Normal
**Targets:** CLAUDE.md; tests/test_docs_drift.py

---

## What

Refresh the project CLAUDE.md (the agent runbook) to current reality, and add a drift-guard test so the documented surface can no longer silently diverge from the code:

1. **Broken paths fixed:** §Workflow's smoke commands point at `/Users/frank/Projects/alfred/fx_alfred` — a directory that does not exist (both `af guide --root` and `af validate --root` as written fail). Corrected to the repo root.
2. **Commands section completed:** 6 of 20 CLI commands are undocumented (`agent`, `issue`, `skill`, `star`, `starred`, `unstar`).
3. **Architecture tree completed:** 13 of 19 `core/` modules and 6 of 22 `commands/` modules are missing (the whole graph-rendering cluster, compose, steps, workflow, preferences, skills, agent helpers, plus agent/issue/skill/star commands and the Phase 0 log scaffolding — annotated as not wired).
4. **Drift classes removed instead of guarded where cheaper:** the hardcoded package version (`v1.17.1` vs actual `1.18.0`) is replaced by a pointer (`af --version` / pyproject.toml); the "Active PRPs (Draft)" table (one row stale-Draft, one row referencing the no-longer-existing ALF-2203) is replaced by a live-command pointer (`af list --type PRP`).
5. **New `tests/test_docs_drift.py`:** asserts every CLI command registered in `cli.py` appears as `af <name>` in CLAUDE.md; every `commands/*.py` and `core/*.py` module name appears in CLAUDE.md; the dead `alfred/fx_alfred` path string does not reappear; no hardcoded `fx-alfred vX.Y.Z` version pattern returns.


## Why

CLAUDE.md is the per-session instruction surface for every agent working in this repo — drift here propagates into every future session. Found 🔴-adjacent in the 2026-06-10 project review: version two release cycles stale, a third of the documented architecture missing, and — worst — the session-start smoke commands are broken as written (an agent following the runbook literally gets `No such file or directory`). The same review's meta-lesson (the `af plan` truncation bug surviving multiple reviews) argues for mechanical guards over manual upkeep: the new test makes command/module coverage a CI property, and the version/PRP-table removals delete two drift classes outright rather than guarding them.


## Out of Scope

- README.md (verified current in the 2026-06-10 review).
- The user-level `~/.claude/CLAUDE.md` (different repo).
- Restructuring CLAUDE.md sections or changing workflow policy content (routing rules, review gates, release SOP references stay as written, minus factual corrections).
- Guarding free-text accuracy (e.g. SOP table descriptions) — only mechanically checkable surfaces are tested.


## Acceptance Criteria

- A1: `tests/test_docs_drift.py` fails on pre-change CLAUDE.md (RED) and passes post-change (GREEN), covering: all `cli.py` lazy subcommand names present as `af <name>`; all `commands/*.py` + `core/*.py` module filenames present; `Projects/alfred/fx_alfred` absent; regex `fx-alfred v\d` absent.
- A2: §Workflow smoke commands execute successfully as written (paths exist).
- A3: No stale Active-PRPs table; the replacement pointer command works.
- A4: Full gates: pytest, ruff check, ruff format --check, pyright, `af validate`.


## Implementation Plan

1. **RED:** add `tests/test_docs_drift.py`; confirm 4 failure classes fire on current CLAUDE.md.
2. **GREEN:** rewrite the drifted CLAUDE.md sections (Project header, Commands, Architecture tree, Essential Commands paths, Workflow paths, Active PRPs → pointer); annotate log_* Phase 0 scaffolding as not wired.
3. Verify A1–A4.
4. Trinity triad review (glm, deepseek, minimax), COR-1610, all ≥ 9.0; fix convergent findings.
5. PR per COR-1505.

---

## Change History

| Date       | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | By               |
|------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------|
| 2026-06-11 | Initial version — refresh agent runbook + add docs drift guard (2026-06-10 review finding) | Claude (Fable 5) |
| 2026-06-11 | RED (5 drift guards firing on old runbook) + GREEN (full refresh; 2 drift classes deleted; smoke paths fixed and executed exit-0). 981 tests. | Claude (Fable 5) |
| 2026-06-11 | R1 code-review panel [glm, deepseek, minimax] per COR-1602/COR-1610: glm 9.3 PASS, deepseek 10.0 PASS, minimax 9.7 PASS — gate met, blocking empty. Convergent advisory (glm+minimax, self-verified against module docstring): branch_layout.py description was wrong ("lane layout" → actual "branch-group discovery") — fixed with phrasing covering function + purpose. Notable panel-redundancy sample: deepseek's per-module fact-check passed the same entry glm caught. MiniMax style advisory: redundant framework-agnostic paragraph after the tree (duplicated Key Design Patterns) — deleted. MiniMax theoretical advisory (substring false-PASS for future generic module names) recorded, not changed. Status → Approved | Claude (Fable 5) |
| 2026-06-12 | Released in v1.19.0 (PyPI, 2026-06-12) — status Approved → Completed per FXA-2102 Step 7 | Claude (Fable 5) |
