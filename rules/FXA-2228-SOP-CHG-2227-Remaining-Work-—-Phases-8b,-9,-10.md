# SOP-2228: CHG-2227 Remaining Work — Phases 8b, 9, 10

**Applies to:** FXA project
**Last updated:** 2026-04-29
**Last reviewed:** 2026-04-29
**Status:** Active
**Depends on:** FXA-2227 (CHG; presentation-layer implementation, partially shipped)
**Related:** FXA-2102 (release SOP), FXA-2136 (README check), CHG-2226 (data layer, complete)

---

## What Is It?

A pause-resume tracker for the three remaining phases of CHG-2227 (Branching ASCII Presentation Layer). Phases 1+2+3+4+5+7+8a are merged in `main`; this SOP captures the work still owed to ship v1.8.0 to PyPI: documentation + version bump (8b), final multi-model code review across all six merged PRs (9), and the release itself (10).

## Why

CHG-2227 was paused after Phase 8a (PR #73, `_BRANCHES_RENDERER_READY` flip + plan-path branches propagation) without writing the trailing context anywhere durable. Without this SOP, resuming requires reconstructing state from `git log`, the CHG document, and conversation memory — none of which is reliable for cross-session work. This SOP makes the remaining steps executable cold by anyone (or any future Claude session) walking up to the project.

---

## When to Use

- Resuming CHG-2227 from a paused state — read this top-to-bottom before any commits
- Auditing what's left before tagging v1.8.0
- Onboarding a reviewer who needs the full picture without re-reading 6 PRs

## When NOT to Use

- For NEW CHG-2227 phases (1–8a) — they are merged; consult `git log` and CHG-2227 history instead
- For the next release after v1.8.0 — write a fresh tracker scoped to that version's work

---

## Current State (as of 2026-04-29)

**Merged in `main`:**

| PR | Phase | Title |
|----|-------|-------|
| #66 | (CHG doc) | CHG-2226 Data Layer document |
| #67 | (CHG doc) | CHG-2227 Presentation Layer document |
| #68 | 1+2+3 (CHG-2226) | Data layer (sub-step parser, `Workflow branches:` schema, validator) |
| #69 | 3 | `branch_geometry` primitive (~210 LOC, 11 invariants + 6 goldens) |
| #70 | 4 | `dag_graph.py` nested integration + extracted `core/branch_layout.py` |
| #71 | 5 | `ascii_graph.py` flat integration |
| #72 | 7 | `mermaid.py` sub-step IDs |
| #73 | 8a | `_BRANCHES_RENDERER_READY = True` + `plan_cmd` branches propagation + ClickException wrap |

**Test/lint state on `main`:** 835/835 pass · pyright 0 errors · ruff clean.

**Branch already exists:** `feat/fxa-2227-phase-8b-docs-version-bump` does NOT yet exist — Phase 8b has not been started.

**Outstanding validator follow-ups (deferred during reviews, NOT blocking 8b/9/10):**
The renderer-side guards in `branch_layout.py` gracefully skip these malformed inputs; the validator should also reject them at parse time. Tracked separately under CHG-2226 follow-up scope:

1. Reject `Workflow branches[].to` with length not in [2, 4]
2. Reject duplicate IDs in `Workflow branches[].to`
3. Reject duplicate `from` values across multiple `Workflow branches` entries
4. Reject duplicate sub-step rows under same `from_step` (e.g., `3a, 3a`)
5. Reject same integer N appearing as both plain step AND sub-stepped siblings

Do NOT bundle these into Phase 8b/9/10. They belong in a separate FXA-2229 (or similar) follow-up that touches `core/workflow.py:validate_branches`.

---

## Steps

### Phase 8b — Docs + version bump + dependency

**Branch:** `docs/fxa-2227-phase-8b-docs-version`
**Files modified:**

| File | Change |
|------|--------|
| `pyproject.toml` | `version = "1.7.1" → "1.8.0"`; ADD `"wcwidth"` to `dependencies` (was a transitive of `branch_geometry` in #69 but not declared) |
| `src/fx_alfred/CHANGELOG.md` | Add v1.8.0 entry; **MUST include `⚠ Breaking — todo[].index format`** entry per CHG-2226 §Risks (strict-numeric-regex consumers like `^\d+\.\d+$` need to update to `^\d+\.\d+[a-z]?$`) |
| `CLAUDE.md` | One-paragraph note about `Workflow branches:` authoring |
| `rules/COR-1202-*` (PKG, read-only) | Cannot edit directly. Either skip or propose a PRP to upstream the one-line mention |

**Steps:**

1. `git checkout main && git pull origin main`
2. `git checkout -b docs/fxa-2227-phase-8b-docs-version`
3. Bump `pyproject.toml` version: `version = "1.8.0"`. Add `"wcwidth>=0.2.13"` to `dependencies`.
4. Update `src/fx_alfred/CHANGELOG.md` with a v1.8.0 entry. Required content:
   - `### Added` — branching ASCII rendering in `af plan --graph` for both nested + flat layouts; Mermaid sub-step IDs; `wcwidth` dependency.
   - `### Changed` — `_BRANCHES_RENDERER_READY` defaults to `True`; `af validate` accepts `Workflow branches:` SOPs.
   - `### Breaking` — `todo[].index` format extends from `^\d+\.\d+$` to `^\d+\.\d+[a-z]?$`. Consumers parsing this with strict numeric regex must update.
5. Update `CLAUDE.md` with a one-paragraph user-facing note. Suggested location: under "Architecture" or "Workflow" section. Keep it short — this is consumer-facing, not internal-CHG documentation.
6. Run: `.venv/bin/pytest -q && .venv/bin/pyright src/ && .venv/bin/ruff check . && .venv/bin/ruff format --check .` — expect clean.
7. Commit: `chore(FXA-2227): docs + version bump v1.7.1 → v1.8.0 (Phase 8b)`. Push, open PR, await trinity + bot review per the same iteration loop used for 4/5/7/8a.

**Exit:** PR merged. `pyproject.toml` version is `1.8.0` on `main`. CHANGELOG documents the breaking change. CLAUDE.md mentions `Workflow branches:` authoring.

---

### Phase 9 — Multi-model code review of the COMBINED CHG-2227 surface

**Why a separate phase, given each PR was already reviewed:** PR-by-PR review focuses on local correctness; a combined review checks cumulative architecture, doc/code consistency, and end-to-end behavior. Per CHG-2227 §Phase 9.

**Inputs to reviewers:**

- Diff: `git diff $(git merge-base origin/main <CHG-2226-merge-base>)..main -- src/fx_alfred/core/branch_geometry.py src/fx_alfred/core/branch_layout.py src/fx_alfred/core/dag_graph.py src/fx_alfred/core/ascii_graph.py src/fx_alfred/core/mermaid.py src/fx_alfred/commands/plan_cmd.py src/fx_alfred/core/workflow.py src/fx_alfred/core/phases.py`
- Test diff: `tests/test_branch_geometry.py`, `tests/test_branch_layout.py`, `tests/test_dag_graph_branches.py`, `tests/test_ascii_graph_branches.py`, `tests/test_mermaid.py` (Phase 7 additions only), `tests/test_plan_cmd.py` (Phase 8a additions), `tests/test_workflow_branches_validate.py`, `tests/test_plan_cmd_substeps.py`
- CHG-2227 document
- CHANGELOG v1.8.0 entry (from Phase 8b)

**Reviewers:** Codex + Gemini in parallel via trinity-codex / trinity-gemini agents per COR-1602. Both must score ≥ 9.0 per COR-1610 to PASS.

**Up to 3 rounds.** Findings → coder subagent (sonnet) per saved memory rule.

**Exit:** Both reviewers PASS. No FIX outstanding.

---

### Phase 10 — Release v1.8.0

**Per FXA-2102 (release SOP) — DO NOT skip the manual smoke test.**

**Pre-release checklist:**

1. `main` is green: tests + pyright + ruff all clean
2. `pyproject.toml` version is `1.8.0` (from Phase 8b)
3. CHANGELOG v1.8.0 entry committed
4. Phase 9 review passed (both reviewers ≥ 9.0)

**Manual smoke test (REQUIRED — Gemini Round 1 advisory; the goldens prove geometry but not real-terminal rendering):**

1. `pip install -e .` from a clean venv to install the local pre-release wheel
2. Build a 3-way branchy fixture SOP and run:
   ```
   af plan --task "..." COR-1500 COR-1602 --todo --graph --root .
   ```
   in a real interactive terminal (iTerm2 / macOS Terminal / Linux gnome-terminal — NOT a pipe-to-file, NOT pytest's captured stdout). Visually eyeball:
   - 3-way Audit Ledger fixture output matches the goldens at `tests/test_branch_geometry.py`
   - CJK terminal handles label truncation visibly without breaking width
   - Flat layout produces the same branch shape as nested but without the inner phase-box borders
3. Run `af plan --graph-format=mermaid` against the same fixture; paste the output into the Mermaid Live Editor (https://mermaid.live) and confirm sub-step nodes (`S1_3a`, `S1_3b`, `S1_3c`) render with edges connecting parent → siblings → convergence

**If smoke test fails:** STOP. Do not tag. File a bug, fix, re-do Phase 9 if scope-significant.

**If smoke test passes:**

1. `gh release create v1.8.0 --title "v1.8.0" --notes "<copy-paste CHANGELOG v1.8.0 entry>"` from `main` (NOT a feature branch)
2. GitHub Actions auto-publishes to PyPI (per FXA-2102's release pipeline)
3. Wait ~3-5 min for PyPI to update
4. Verify: `pipx upgrade fx-alfred` (or `pip install --upgrade fx-alfred` in a sandbox), then `af --version` shows `1.8.0`
5. Run `af plan ...` against the smoke-test fixture from the upgraded install — confirm the output matches Step 2 above (proves the wheel built + uploaded correctly)

**Exit:** v1.8.0 live on PyPI. `pipx upgrade fx-alfred` works. Branchy SOP renders correctly from the published wheel.

---

## Examples

**Example 1 — Resuming Phase 8b cold:**

```bash
git checkout main && git pull origin main
git log --oneline | head -5
# Expect last commit: PR #73 merge (Phase 8a)
git checkout -b docs/fxa-2227-phase-8b-docs-version
# Edit pyproject.toml, CHANGELOG.md, CLAUDE.md per §Phase 8b Steps
.venv/bin/pytest -q && .venv/bin/pyright src/ && .venv/bin/ruff check .
git commit -m "chore(FXA-2227): docs + version bump v1.7.1 → v1.8.0 (Phase 8b)"
```

**Example 2 — Phase 10 smoke-test failure:**

If `af plan --graph` against a real terminal renders garbled CJK truncation: STOP. Do not tag. File a bug citing the specific terminal + fixture + visible defect, then add a regression test that captures the failing geometry against `wcwidth.wcswidth` invariants. Re-run Phase 9 review on the fix.

---

## Resume Protocol

If you arrive at this SOP cold (new session, no context):

1. Read this entire SOP top-to-bottom
2. Read CHG-2227 document at `rules/FXA-2227-CHG-*.md` for the full design context
3. Run `.venv/bin/pytest -q` to confirm the baseline is still green
4. Identify which Phase (8b / 9 / 10) is next via `git log --oneline main | head -10` — match against the "Merged in main" table above
5. Check if any branches are already in flight: `git branch -a | grep fxa-2227`
6. Proceed with the matching Phase's Steps section

---

## Guard Rails

- Do NOT add validator-side rejection logic (the 5 deferred items in §Current State) to ANY of these phases — they belong in a separate FXA-2229 follow-up
- Do NOT bundle Phase 8b doc work into a Phase 9 review-fix commit — keep the commits atomic per the per-phase pattern that worked for #69–#73
- Do NOT skip Phase 9 even though every PR was already individually reviewed — the combined surface check is non-negotiable per CHG-2227 §Phase 9
- Do NOT skip the Phase 10 manual smoke test — automated tests prove geometry, not real-terminal rendering
- All implementation work goes through the `coder` subagent (sonnet) per the saved memory rule (`feedback_always_use_coder_subagent.md`); do NOT edit code directly from the orchestrator

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-29 | Initial version — captures pause-resume state after PR #73 merge | Frank + Claude Code |
