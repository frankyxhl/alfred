# CHG-2208: Add Pyright To FXA 2102 Release Prerequisites

**Applies to:** FXA project
**Last updated:** 2026-04-18
**Last reviewed:** 2026-04-18
**Status:** Approved
**Related:** FXA-2102 (Release to PyPI SOP — the target of this change), v1.6.0 publish incident (GitHub Actions run [24603123925](https://github.com/frankyxhl/alfred/actions/runs/24603123925) — failed `pyright src/` step, required v1.6.1 patch)
**Date:** 2026-04-18
**Requested by:** Frank
**Priority:** High
**Change Type:** Standard
**Scheduled:** ASAP

---

## What

Add `.venv/bin/pyright src/` to the FXA-2102 "Release to PyPI" SOP in two places:

1. **§Prerequisites** — add a new bullet: `Pyright clean (.venv/bin/pyright src/)`.
2. **§Steps / Step 1 "Verify readiness"** — add `.venv/bin/pyright src/` to the verification command block, alongside the existing `pytest`, `ruff check`, and `ruff format --check` lines.

Tiny, one-SOP-file edit. No code changes, no tool changes.


## Why

The v1.6.0 release on 2026-04-18 reached GitHub (tag + release v1.6.0 created) but **failed to publish to PyPI** because the `.github/workflows/publish.yml` workflow runs `pyright src/` and the commit had 16 type errors. FXA-2102's Prerequisites listed `pytest`, `ruff check`, and `ruff format --check` but **not** `pyright`, so the Leader-led pre-release gate passed locally and the publish step blew up in CI (see [failed run #24603123925](https://github.com/frankyxhl/alfred/actions/runs/24603123925)). We had to cut a same-day patch release v1.6.1 to get the v1.6 feature set onto PyPI.

Root cause: FXA-2102's Prerequisites diverged from `.github/workflows/publish.yml`'s actual CI gates. Fixing FXA-2102 to match prevents recurrence. Alfred's "SOP as system of record" principle demands the release SOP faithfully reflect what CI enforces.

Secondary benefit: every future Leader / agent following FXA-2102 catches type errors before cutting a GitHub release, avoiding the tag-exists-but-PyPI-missing split state.


## Impact Analysis

- **Systems affected:**
  - `rules/FXA-2102-SOP-Release-To-PyPI.md` — PRJ-layer SOP (verified via `af where FXA-2102`). Both "Prerequisites" bullet list and "Steps" Step 1 code block updated.

- **NOT affected:**
  - No code files changed.
  - No test files changed.
  - `pyproject.toml` already includes `pyright` in `dev` optional dependencies (verified).
  - `.github/workflows/publish.yml` — not changed; the CI gate stays; we're aligning the SOP to CI, not the other way around.
  - `FXA-2136` (README check SOP) — not touched.
  - Any other SOP.

- **Channels affected:** none.

- **Downtime required:** No.

- **Backward compatibility:** Fully additive — adds one Prerequisite + one command line. Future releases simply have one more checkbox. Zero impact on already-published versions.

- **Rollback plan:**
  - Revert the FXA-2102 edit commit.
  - `af validate --root .` clean (no schema change); `af fmt --check` clean.
  - No data migration, no PyPI impact.
  - Rollback verification: `af read FXA-2102 --root . | grep -i pyright` returns empty after rollback.


## Implementation Plan

### Phase 1 — CHG review

1. Leader dispatches Codex + Gemini (real CLI) to score this CHG against COR-1609 rubric. Both must score ≥ 9.0.
2. If either returns FIX, revise and re-dispatch per COR-1602 round rules (max 3 rounds).
3. On double PASS, status → `In Progress`.

### Phase 2 — Edit FXA-2102

4. Locate the SOP via `af where FXA-2102 --root .` (PRJ layer expected).

5. **Edit 1 — §Prerequisites bullet list.** Add a new bullet between the existing `Ruff format clean` line and `Dual code review passed`:

   ```
   - Pyright clean (`.venv/bin/pyright src/`) — catches type errors that the publish CI also runs
   ```

6. **Edit 2 — §Steps / Step 1 "Verify readiness".** Add one line to the existing code block, right after the `ruff format --check .` line:

   ```bash
   .venv/bin/pyright src/   # must be equivalent to the CI gate (`pyright src/` in .github/workflows/publish.yml)
   ```

7. **Edit 3 — §Change History**. Add one row:

   ```
   | 2026-04-18 | Add pyright to Prerequisites + Step 1 per CHG-FXA-2208 (post v1.6.0 incident). | Frank + Claude Code |
   ```

8. Run `af fmt FXA-2102 --write --root .` to canonicalise.

9. `af validate --root .` must pass clean.

### Phase 3 — Content review (COR-1610)

10. Leader dispatches Codex + Gemini (real CLI) against COR-1610 rubric for the SOP edit. Both must score ≥ 9.0.
11. Fix-or-defer per COR-1602 round rules.

### Phase 4 — PR + NRV-2506

12. Push branch `feat/fxa-2208-release-pyright-check`, open PR titled `fix(FXA-2208): add pyright to FXA-2102 release prerequisites`.
13. Triage any `chatgpt-codex-connector[bot]` comments per NRV-2506.
14. On all-green + double PASS, notify Leader for merge.

---

## Testing / Verification

- [ ] **SOP edit present:** `af read FXA-2102 --root . | grep -i pyright` returns both the Prerequisites bullet and the Steps code-block line.
- [ ] **Format compliance:** `af fmt FXA-2102 --check --root .` clean.
- [ ] **Structural validation:** `af validate --root .` clean.
- [ ] **Command accuracy:** run `.venv/bin/pyright src/` on the current tree — expect 0 errors (just verified for v1.6.1).
- [x] **CI alignment check:** `.github/workflows/publish.yml:18` runs `pyright src/`. The SOP uses `.venv/bin/pyright src/` (explicit venv path for reproducibility outside CI). Semantically identical (both use the same `src/` root); ACID-of-invocation is `pyright src/`.
- [ ] **Rollback verification:** `git revert` the edit; re-run `af validate`; re-run `af read FXA-2102 | grep pyright` → empty.

---

## Open Questions

All resolved:

1. **RESOLVED — Why not add ruff + validate also to the Steps code block?** They are already there. Only pyright is missing. This CHG is surgical: add exactly the one missing command to match CI. Expanding scope would require re-reviewing all four gates.

2. **RESOLVED — Why Prerequisites AND Steps, not just one?** Prerequisites is the human-readable checklist operators run through before starting; Steps Step 1 is the copy-paste command block the operator actually executes. Both need the command for the SOP to be self-consistent.

3. **RESOLVED — Priority: High or Medium?** Marked `High`. This gap just caused a same-day patch release (v1.6.0 → v1.6.1). Any future release is at the same risk until FXA-2102 is fixed.

4. **RESOLVED — Should this also update the CI workflow itself?** No. The workflow is correct and matches the declared release gate; it's the SOP that drifted. One-way fix.

---

## Alternatives Considered

- **Skip the SOP edit; rely on Leader discipline to remember pyright.** Rejected: contradicts Alfred's "SOP as system of record" principle; the whole point of the SOP is to codify the procedure so memory isn't the gate.
- **Remove pyright from the publish workflow instead.** Rejected: pyright caught a real class of bugs (TypedDict `total=False` access); removing the gate would regress code quality. The SOP is the one that's wrong, not CI.
- **Add a Makefile target (`make release-check`) that runs all four gates.** Rejected as scope creep. A Makefile is a separate artifact; this CHG is about SOP accuracy. A `make release-check` target could be a follow-up CHG if it proves useful.
- **Bundle with a broader FXA-2102 refresh (e.g., version bump helper, CHANGELOG auto-date).** Rejected: scope creep. Ship the minimum-viable SOP fix now.

---

## Approval

- [ ] Reviewed by: Codex + Gemini (COR-1602 parallel, COR-1609 CHG rubric ≥ 9.0)
- [ ] Approved on: <YYYY-MM-DD>

---

## Execution Log

| Date       | Action                                            | Result  |
|------------|---------------------------------------------------|---------|
| 2026-04-18 | CHG-2208 Proposed (post v1.6.0 incident)          | Draft   |
| YYYY-MM-DD | Phase 1 review (Codex + Gemini)                   | —       |
| YYYY-MM-DD | Phase 2 SOP edit                                  | —       |
| YYYY-MM-DD | Phase 3 content review                            | —       |
| YYYY-MM-DD | Phase 4 PR opened                                 | —       |
| YYYY-MM-DD | Merged                                            | —       |

---

## Post-Change Review

_To be filled in after merge:_

- Did the next release (v1.6.2 or v1.7.0) successfully run the pyright prerequisite?
- Did any other CI step surface a gap that should also be in FXA-2102?
- Any proposal for a `make release-check` Makefile target to chain all four gates?

---

## Change History

| Date       | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | By                |
|------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------|
| 2026-04-18 | Initial version | Claude (Opus 4.6) |
| 2026-04-18 | R1 review fixes (Codex 9.6 + Gemini 9.9, both real CLI): Change Type Normal → Standard per FXA-2137 precedent (Gemini adv); concrete GH Actions URL added to Related + Why for traceability (Gemini adv); fixed factual overstatement in §Why — old Prerequisites listed `pytest`/`ruff check`/`ruff format --check`, NOT `af validate` (Codex adv); softened "must match CI publish workflow" to "must be equivalent to the CI gate" to acknowledge the `.venv/bin/pyright` vs bare `pyright` path difference (Codex adv). | Claude (Opus 4.6) |
| 2026-04-18 | R1 double PASS (Gemini 9.9 + Codex 9.6, both real CLI). All 4 advisories addressed inline: Change Type Normal → Standard (FXA-2137 precedent); added GH Actions run URL 24603123925 to Related + Why for traceability; fixed factual overstatement (old Prereqs did not include af validate); softened CI-match wording. Standard change type permits approval after R1 double PASS. | Frank (Leader) |
