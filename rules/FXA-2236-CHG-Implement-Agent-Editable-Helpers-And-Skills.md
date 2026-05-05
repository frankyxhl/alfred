# CHG-2236: Implement Agent Editable Helpers And Skills

**Applies to:** FXA project
**Last updated:** 2026-05-05
**Last reviewed:** 2026-05-05
**Status:** Completed
**Date:** 2026-05-05
**Requested by:** Frank
**Priority:** Medium
**Change Type:** Normal
**Related:** FXA-2235, GitHub issue #94
**Reviewed by:** Pre-approved by FXA-2235 PRP strict review

---

## What

Implement the approved P0 surface from `FXA-2235: Agent Editable Helpers And Skills`:

- `af agent call` and `af agent run` for explicitly gated local helper/script execution.
- `af skill list` and `af skill read` for read-only skill-document discovery.
- `af plan --with-skills` for task-scoped skill recommendations.
- A PRJ REF usage document for Agent Helpers and Skills.

---

## Why

FXA-2235 established that Alfred needs a controlled learn-by-doing surface for reusable local helper functions and skill documents while preserving deterministic, safe-by-default behavior for existing commands. The implementation makes that approved design available behind explicit command surfaces and tests the safety boundary.

---

## Impact Analysis

- **Systems affected:**
  - `src/fx_alfred/cli.py` — register lazy `agent` and `skill` command groups.
  - `src/fx_alfred/commands/agent_cmd.py` — implement `af agent call/run`.
  - `src/fx_alfred/commands/skill_cmd.py` — implement `af skill list/read`.
  - `src/fx_alfred/core/agent_helpers.py` — helper discovery, gated import, execution envelopes.
  - `src/fx_alfred/core/skills.py` — skill classification, matching, JSON result shapes, resolution.
  - `src/fx_alfred/commands/plan_cmd.py` — add `--with-skills` and JSON schema version `3` when `recommended_skills` is present.
  - `tests/test_agent_cmd.py`, `tests/test_skill_cmd.py`, `tests/test_plan_cmd.py`, `tests/test_lazy.py` — TDD coverage.
  - `rules/FXA-2237-REF-Agent-Helpers-And-Skills-Usage.md` — usage guidance, created via `af create ref --prefix FXA --area 22`.
  - `rules/FXA-0000-REF-Document-Index.md` — index updates for CHG/REF.
- **Not affected:**
  - Existing command behavior for `af guide`, `af validate`, and normal `af plan` without `--with-skills`.
  - Schema metadata fields; P0 does not add `SKL`, `Skill status`, or `Helper functions`.
  - PKG helper registry; P0 supports only PRJ and USR helper files.
- **Rollback plan:** Revert the implementation commit. Verify `af agent` / `af skill` no longer appear in `af --help`, `af plan --with-skills` is rejected as an unknown option, and `PYTHONPATH=src .venv/bin/af validate --root .` remains clean.

---

## Implementation Plan

1. Add RED tests for lazy nested groups and helper gate behavior.
2. Implement `core/agent_helpers.py`:
   - exact `ALFRED_AGENT_TOOLS=1` gate,
   - PRJ/USR helper path resolution,
   - PRJ import-failure no-fallback rule,
   - public function registration,
   - duplicate arg rejection,
   - async execution,
   - JSON envelopes.
3. Implement `commands/agent_cmd.py`.
4. Add RED tests for skill classification, matching, resolution, and JSON output.
5. Implement `core/skills.py` and `commands/skill_cmd.py`.
6. Add RED tests for `af plan --with-skills`, including JSON schema `3`, empty matches, text placement, and no helper imports.
7. Extend `commands/plan_cmd.py`.
8. Create the PRJ usage REF with `af create ref --prefix FXA --area 22 --title "Agent Helpers And Skills Usage"`.
9. Run full verification and address review findings before opening a normal PR.

---

## Testing / Verification

- [x] `PYTHONPATH=src .venv/bin/pytest tests/test_agent_cmd.py tests/test_skill_cmd.py tests/test_plan_cmd.py tests/test_lazy.py -q`
- [x] `PYTHONPATH=src .venv/bin/pytest -q`
- [x] `PYTHONPATH=src .venv/bin/ruff check .`
- [x] `PYTHONPATH=src .venv/bin/ruff format --check .`
- [x] `PYTHONPATH=src .venv/bin/pyright src/`
- [x] `PYTHONPATH=src .venv/bin/af validate --root .`

---

## Approval

- [x] Reviewed by: FXA-2235 PRP strict review (GLM 9.1/10, DeepSeek 9.0/10)
- [x] Approved on: 2026-05-05

---

## Execution Log

| Date       | Action | Result |
|------------|--------|--------|
| 2026-05-05 | Created CHG from approved FXA-2235 PRP. | Ready for TDD implementation. |
| 2026-05-05 | Added RED tests for agent helpers, skill docs, plan recommendations, and lazy command help. | Failed for missing command surface as expected. |
| 2026-05-05 | Implemented `af agent`, `af skill`, `af plan --with-skills`, README/changelog/version updates, and FXA-2237 usage REF. | Targeted and full verification passed. |
| 2026-05-05 | Ran Trinity fast-review. | PASS from GLM and DeepSeek; addressed low-risk clarity/test-coverage advisories before final verification. |

---

## Post-Change Review

Implemented per FXA-2235 P0. The only intentional contract tightening versus
the original issue text is skill classification: P0 requires explicit
`Tags: skill` on REF/SOP documents and does not classify by title alone. This
keeps `Skill:` headings descriptive rather than executable/discoverable
metadata.

Trinity fast-review passed with no blocking findings. Follow-up edits removed
redundant control-flow/readability code and added tests for skill layer
filtering, full-ID skill reads, not-found skill reads, and text-mode agent
errors. Deferred advisories: script-run timeout and skill scoring stop-word
tuning are P1 design choices, not P0 blockers.

---

## Change History

| Date       | Change                                                | By    |
|------------|-------------------------------------------------------|-------|
| 2026-05-05 | Initial implementation CHG from approved FXA-2235 PRP. | Codex |
