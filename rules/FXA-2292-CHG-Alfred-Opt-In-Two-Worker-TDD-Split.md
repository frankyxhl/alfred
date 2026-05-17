# CHG-2292: Alfred Opt-In Two Worker TDD Split

**Applies to:** FXA project
**Last updated:** 2026-05-17
**Last reviewed:** 2026-05-17
**Status:** Approved
**Related:** PRP-1507 (Two-Worker TDD Dispatch — design source); CHG-2287, CHG-2288, CHG-2289, CHG-2290, CHG-2291 (the bundled PKG-layer CHGs landed in PR #177 that introduce the `<test-writer-worker-agent>` schema row this CHG sets); GitHub issue #176; GitHub issue #166 (reconciliation CHG — soft merge-conflict risk noted below)
**Date:** 2026-05-17
**Requested by:** @frankyxhl
**Priority:** Medium
**Change Type:** Normal
**Targets:** rules/FXA-2276-REF-Multi-Agent-Loop-Configuration.md §Worker dispatch (COR-1619) table

---

## What

Append a new `<test-writer-worker-agent>` row to the §Worker dispatch (COR-1619) table in `rules/FXA-2276-REF-Multi-Agent-Loop-Configuration.md` with Alfred value `trinity-deepseek via droid exec`. This opts alfred into PRP-1507's two-worker TDD split: substantive code-bearing dispatches under FXA-2276 will be split between a test-writer worker (deepseek) and an implementer worker (glm), per COR-1500 §Phase 1 "Worker assignment" + COR-1619 §Two-Worker TDD Dispatch (both landed in PR #177).

This is CHG-E of PRP-1507 §Implementation Plan, the final CHG in the PRP-1507 implementation sequence after PKG-layer CHG-A/B/C1/C2/D shipped in PR #177.

## Why

Without this row alfred ships with `<test-writer-worker-agent>` unset, meaning COR-1500 §Phase 1's OFF-state branch applies and Mandatory Rule #3 alone governs (single agent, two sequential turns — same as pre-PRP-1507 behavior). Setting the parameter distinct from `<worker-agent>` (trinity-glm) turns the split ON for alfred, starting the §Validation log that PRP-1507 §Decisions items 1/2/4 re-evaluate against.

Deepseek-as-test-writer rationale (per PRP-1507 §Decisions item 1):
- Prior PR reviews on alfred PRs #117 / #154 / #173 / #177 demonstrate strong edge-case probing. PR #117 deepseek catches included consent-recipe failure modes the panel missed; PR #154 deepseek catches included GraphQL pagination edges; PR #177 deepseek scored 10.0 on the plan-review panel — strong static-correctness instinct.
- Not the implementer (glm) — cross-validation holds because the implementer cannot have authored the test, satisfying the "distinct instance" requirement of CHG-A's Worker assignment rule.

## Out of Scope

- Editing PRP-1507 itself — its §Decisions item 1 already names trinity-deepseek as the chosen test-writer; this CHG only codifies the choice in the PRJ REF.
- Adding `<test-writer-worker-agent>` rows to other adopters' PRJ REFs (trinity's TRN-1209, etc.). Each adopter decides independently; this CHG is alfred-only.
- Tracking the actual first-three two-worker dispatches in this CHG. Those land in PRP-1507 §Validation as separate sessions accumulate data.
- Changing FXA-2276's `<panel-providers>` (separate, already done in PR #174).
- The R14 residual sequencing fix from PR #177 — separate follow-up CHG (also queued from PR #177 retrospective). Tracking issue to be filed after this CHG merges.
- PRP-1507 cleanup CHG syncing PRP source to PR #177 R2-R13 refinements — separate follow-up. Tracking issue to be filed after this CHG merges.

## Impact Analysis

- **Systems affected:** `rules/FXA-2276-REF-Multi-Agent-Loop-Configuration.md` only (one new row appended to one table; no other content modified).
- **Behavioural impact:**
  - Default sessions (no `follow FXA-2276` invocation): unchanged — only orchestrator-direct work or single-worker dispatch is affected by the split, and default sessions don't use the loop.
  - Looping mode under `follow FXA-2276`: the next CHG whose implementation routes through a COR-1619 §Decision Tree WORKER leaf (W1/W2/W3/W4) AND does not match any COR-1500 §Phase 1 opt-out class will be the first two-worker dispatch. Doc-only CHGs that hit an O-leaf (orchestrator-direct) or match an opt-out class (config-only, characterization tests, vendored code, etc.) bypass the split entirely — the trigger is W-leaf routing, not just "code-bearing". The PRP-1507 §Validation log will record per-dispatch metrics (test-writer commit SHA, implementer commit SHA, RED test count, GREEN pass count, refactor status, retrospective notes including any implement-to-fit divergence).
  - Doc-only CHGs (e.g. the next routine PR): unchanged — opt-out class "Config / metadata-only change" + "Refactor with pre-existing coverage" + "Vendored code update" all match common doc PRs.
- **Compatibility:** Backwards-compatible. The new row uses the optional `<test-writer-worker-agent>` parameter introduced by CHG-D (PR #177). Adopters who haven't merged PR #177 are unaffected (this CHG depends on it).
- **Cost:** ~2× per-dispatch worker latency and token cost when the split fires (one test-writer round-trip + one implementer round-trip in series). The PRP §Validation re-evaluation trigger after 3 dispatches will quantify the actual cost vs defect-density benefit. If no measurable benefit emerges, FXA-2276 can revert this CHG via a follow-up.
- **Risk surface:** Very low. The row is data-only; no logic changes. The Notes field references PRP-1507 §Validation log as the re-evaluation trigger, so the CHG is self-documenting.
- **Soft merge-conflict risk with #166**: issue #166's reconciliation CHG also edits `rules/FXA-2276-REF-Multi-Agent-Loop-Configuration.md` (removes the §Adoption Status Phase 1 deviation note). This CHG-E edits §Worker dispatch (different section). Per the issue #176 dep wording, the risk is git auto-merge resolving the two PRs landing in either order. In practice, edits to non-overlapping markdown sections auto-merge cleanly. If a conflict arises, the merge resolution is mechanical (preserve both edits). Not a hard blocker for this CHG.
- **Rollback plan:** Revert this commit. The row vanishes; alfred reverts to single-worker dispatch (CHG-A's OFF-state branch). The PKG SOPs (PR #177 CHGs) remain unchanged because they are framework-agnostic.

## Acceptance Criteria

- A1: `rules/FXA-2276-REF-Multi-Agent-Loop-Configuration.md` §Worker dispatch (COR-1619) table contains a new row keyed `<test-writer-worker-agent>` appended after the existing `<worker-min-loc>` row.
- A2: Alfred value = `trinity-deepseek via droid exec`. Notes column references PRP-1507 §Decisions item 1 + §Validation log re-evaluation trigger.
- A3: `Last updated` and `Last reviewed` fields in FXA-2276 frontmatter updated to 2026-05-17.
- A4: §Change History row dated 2026-05-17 referencing this CHG (FXA-2292) and PRP-1507.
- A5: `af validate --root /Users/frank/Projects/alfred` reports 0 issues.
- A6: This CHG document exists, Status moves Proposed → Approved after panel pass, → Completed at merge.
- A7: PR body uses bare `Closes #176` token. After merge, `gh issue view 176` shows CLOSED.
- A8: PR body explicitly calls out the soft merge-conflict risk with #166 (the reconciliation CHG that also edits FXA-2276 but at §Adoption Status Phase 1).

## Implementation Plan

1. `git fetch origin main && git status --porcelain && git switch -c docs/prp-1507-chg-e-alfred-opt-in origin/main` (COR-1505).
2. `gh auth status` → confirm `ryosaeba1985` active.
3. `af create chg --prefix FXA --acid 2292 --title "Alfred Opt-In Two Worker TDD Split"` (this is CHG-E).
4. Edit `rules/FXA-2276-REF-Multi-Agent-Loop-Configuration.md` §Worker dispatch (COR-1619) table to add the new row.
5. Update FXA-2276 `Last updated` / `Last reviewed` to 2026-05-17.
6. Add Change History row dated 2026-05-17 referencing FXA-2292 + PRP-1507.
7. `af validate --root /Users/frank/Projects/alfred`; expect 0 issues.
8. `af index --root /Users/frank/Projects/alfred` to refresh the document index.
9. Run `.venv/bin/pytest -v --tb=short`, `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`. All pass.
10. Dispatch alfred triad plan-review via `Skill(trinity)` with COR-1609 weights (TDD N/A → Completeness 35%, Consistency 25%).
11. Iterate on findings per COR-1621.
12. Commit + push + `gh pr create` with bare `Closes #176` token. PR body includes the soft-merge-conflict note about #166.
13. Phase 8 iterate; Phase 11 retro; Phase 12 wake.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-17 | Initial version — drafted as CHG-E of PRP-1507 §Implementation Plan, the final CHG after PR #177 merged CHG-A/B/C1/C2/D. Closes issue #176. | Claude Opus 4.7 |
| 2026-05-17 | R1 plan-review panel (alfred triad, gemini substituted for minimax which hit usage limit again this session): glm 9.8, deepseek 9.575, gemini 10.0 — PASS aggregate 9.79, blocking == []. Advisories folded pre-commit: (a) GLM P3 — dispatch trigger clarified as "W-leaf routing", not just "code-bearing CHG"; (b) GLM P3 — out-of-scope follow-ups note tracking issues to be filed after merge; (c) GLM P3 — range notation `CHG-2287..CHG-2291` replaced with explicit ACID list. DeepSeek P2 (PRP-ordering downgrade) is self-mitigated by AC A8 — no fix needed; the PR body will explicitly call out the deviation. Other P3 advisories (validation re-eval timeout; deepseek self-selection circularity; PRs #173/#177 evidence extension) are non-actionable in this PR. Status moved Proposed → Approved. | Claude Opus 4.7 |
