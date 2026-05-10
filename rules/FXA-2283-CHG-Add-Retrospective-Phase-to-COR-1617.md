# CHG-2283: Add Retrospective Phase to COR-1617

**Applies to:** FXA project
**Last updated:** 2026-05-10
**Last reviewed:** 2026-05-10
**Status:** Proposed
**Date:** 2026-05-10
**Requested by:** Frank Xu (session 2026-05-10)
**Priority:** Medium
**Change Type:** Normal
**Targets:** `src/fx_alfred/rules/COR-1617-SOP-Multi-Agent-Workflow-Loop.md`, `src/fx_alfred/rules/COR-1620-SOP-Self-Pacing-Loop-Primitives.md`, `rules/FXA-2276-REF-Multi-Agent-Loop-Configuration.md`
**Closes:** #133
**Depends on:** #134 (shipped PR #138 — COR-1200 §Scoring now active; Step 3 note updated accordingly)

---

## What

Insert a new **§Phase 11 (Retrospective)** into COR-1617 in the reserved slot between §Phase 10 (Handoff + merge-watch) and §Phase 11 (Loop restart, renumbered to §Phase 12). Update COR-1620 §When to Use and §Primitives counter table to reflect the new phase numbers.

Phase 11 is **synchronous** — it runs in the same session turn, no wakeup armed. Four steps:
1. Emit a metrics block (R-count, finding counts, detection gap)
2. Pattern check against project memory (user-confirmed write)
3. CHG nomination if pattern recurred ≥2 rounds within this PR (user-confirmed issue creation)
4. Hand off to Phase 12

## Why

COR-1617 §Phase 11 contained an explicit forward pointer: *"If a future retrospective phase is added (e.g., per-PR retro), it inserts BEFORE this §11 step; renumber accordingly."* Every loop iteration discards per-PR learnings — finding patterns, detection gaps, slow convergence — without a structured checkpoint. MEMORY writes happen ad-hoc (or not at all); CHG nominations emerge only when the user manually notices a pattern.

Evidence from this session (alfred PRs #126–#132): codex bot caught `--repo` propagation gap that trinity scored advisory-only (PR #131 R1); same "Applies-to scope" finding recurred R1→R2 before R3 fix; `feedback_pr_body_closing_keyword.md` MEMORY entry was written ad-hoc rather than surfaced automatically.

## Surfaces

| File | Change |
|------|--------|
| `src/fx_alfred/rules/COR-1617-SOP-Multi-Agent-Workflow-Loop.md` | Phase count 11→12; ASCII phase block: add "11. Retrospective", renumber Loop restart to 12; routing table: add Phase 11 row, renumber Phase 11→12; §Phase 10: "arm phase 11" → "execute Phase 11 (Retrospective), then arm Phase 12"; insert new §Phase 11 (Retrospective) with 4 steps; §Phase 12 (renumbered): remove forward-pointer note; Change History rows |
| `src/fx_alfred/rules/COR-1620-SOP-Self-Pacing-Loop-Primitives.md` | Related metadata: add §11 retrospective; §When to Use: §11 loop restart → §12 loop restart; §Primitives table: add synchronous note for Retrospective; Change History row |
| `rules/FXA-2276-REF-Multi-Agent-Loop-Configuration.md` | 11-phase → 12-phase; §Invocation: §11 wake → §12 wake; §Adoption Status: Phase 10 row updated (Retrospective synchronous before Phase 12 arm), new Phase 11 Retrospective row, Phase 12 Loop restart row; Known Risk §11 → §12; Change History row |

**Out of scope:** New COR-1622 parameters, automated MEMORY writes or issue creation, changes to COR-1618/COR-1619/COR-1621.

## Impact Analysis

- **Adopters affected:** All projects adopting COR-1617; alfred project (FXA-2276 instantiation) immediately.
- **Mandatory vs. opt-in:** Phase 11 (Retrospective) is mandatory in the pipeline ordering, but Steps 2–3 within it are opt-in (user-confirmed). An adopter that wants zero friction can confirm "no" to both optional steps and Phase 11 completes in ~2 seconds.
- **Phase renumber impact:** Existing phases 1–10 are semantically unchanged. COR-1620's Loop restart primitive is re-labeled §12 but its behavior is identical. Project-layer documents that hardcode "§11 loop restart" must update to "§12 loop restart" (COR-1620 §When to Use and FXA-2276 §Invocation/§Adoption Status are updated in this CHG; no other known references).
- **Rollback:** `git revert` on both COR-1617 and COR-1620 commits restores the 11-phase structure and forward-pointer note.

## Implementation Plan

1. Grep all Phase 11 references (pre-flight): COR-1617 lines 60, 73, 90, 232, 236–242; COR-1620 lines 7, 39, 116
2. Edit COR-1617: update phase count, ASCII block, routing table, §Phase 10 cleanup line, insert §Phase 11 (Retrospective), rename §Phase 12 (Loop restart) + remove forward-pointer note, add Change History row
3. Edit COR-1620: update Related metadata, §When to Use, §Primitives table, add Change History row
4. `af validate --root /Users/frank/Projects/alfred` — must pass
5. Push branch, open PR with `Closes #133`; verify `closingIssuesReferences`
6. Trinity fast-review (glm + deepseek); iterate until both ≥ 9.0 and codex bot clean

## §Phase 11 Draft Content

> Inserted in COR-1617 as `### Phase 11 — Retrospective` between §Phase 10 and the current §Phase 11 (renumbered §Phase 12).

### Phase 11 — Retrospective

Synchronous — runs immediately after Phase 10 cleanup (`git switch main && git pull --ff-only origin main`). No wakeup armed; no panel review. Optional steps (Steps 2–3) require user confirmation before writing.

**Step 1 — Metrics block.** Emit (use COR-1621 severity classifications P0–P3):
```
Retro PR #<N> (closes #<issue>): R<count> rounds
Findings: P0=<n> P1=<n> P2=<n> P3=<n> | Codex: <k> findings
Late-catch (R3+): <finding class or "none">
Trinity-miss/codex-catch: <finding class or "none">
```

**Step 2 — Pattern check.** For each finding class surfaced in Step 1:
- Search project memory for an existing entry covering it.
- If found: note "matches memory entry — known pattern, no write needed."
- If not found AND (class recurred ≥2 rounds in this PR OR was a codex-only catch): present memory candidate to user; write only on confirmation.

**Step 3 — CHG nomination.** Using only in-PR evidence (GitHub PR evidence re-fetched in Step 1 — bot review comments and R-count from PR #<N>), nominate a CHG if any of these holds:
- Same finding class recurred across ≥2 rounds within this PR
- Same codex-vs-trinity detection gap repeated across ≥2 rounds
- R-count ≥ 4 on the same class

Output a 3-line nomination (target SOP, evidence — round numbers and finding class, one-sentence proposed amendment). Present to user; on confirmation, create a GitHub issue per COR-1501.

*Note: once COR-1200 §Scoring ships (issue #134), score findings per COR-1200 §Scoring; use the composite threshold (≥7.5 = create issue) instead of the count rule above.*

**Step 4 — Hand off.** Print "Retro complete." and proceed to Phase 12 (Loop restart).

## Acceptance Criteria

- [ ] COR-1617 ASCII phase block shows 12 phases: "11. Retrospective" + "12. Loop restart"
- [ ] COR-1617 routing table has Phase 11 (Retrospective) row and Phase 12 (Loop restart) row
- [ ] COR-1617 §Phase 10 cleanup reads "execute Phase 11 (Retrospective), then arm Phase 12" — not "arm phase 11"
- [ ] COR-1617 §Phase 11 (new) has 4 steps: Metrics block / Pattern check / CHG nomination / Hand off
- [ ] COR-1617 §Phase 11 (new) states synchronous — no wakeup armed; optional Steps 2–3 require user confirmation
- [ ] COR-1617 §Phase 12 (renumbered) forward-pointer note removed
- [ ] COR-1620 Related metadata includes "§11 retrospective, §12 loop restart"
- [ ] COR-1620 §When to Use updated from §11 → §12 for loop restart
- [ ] COR-1620 §Primitives counter table includes a Retrospective row (synchronous — no counter)
- [ ] `grep -n "§11\|phase 11\|Phase 11" src/fx_alfred/rules/COR-161*.md` returns no stray old-Phase-11-as-loop-restart references
- [ ] `af validate --root /Users/frank/Projects/alfred` passes
- [ ] Trinity fast-review (glm + deepseek) both ≥ 9.0

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-10 | Initial version per issue #133 | Claude Code |
| 2026-05-10 | R1 fixes: added Impact Analysis (B1/GLM); added COR-1620 §Primitives AC (A1/GLM); scoped Step 3 to in-PR evidence only to resolve statefulness gap (B2/DeepSeek); added COR-1621 ref to Step 1; abstracted MEMORY path (A2/GLM) | Claude Code |
| 2026-05-10 | R2 fixes (bot P2s): Step 1 — add GitHub re-fetch instruction (session state unavailable in merge-watch wake turn); Step 3 — replace "session state" with "GitHub PR evidence re-fetched in Step 1"; update COR-1200 §Scoring note (PR #138 shipped); add FXA-2276 to Targets + Surfaces + Impact Analysis (stale 11→12 references fixed). | Claude Code |
| 2026-05-10 | R3 fixes (GLM B1/A, DeepSeek B1/A1/A2/A3 convergent): Step 1 — explicit jq R-count command + assumption note; COR-1615 §Commands three endpoints named; COR-1621 re-apply instruction; Late-catch and Trinity-miss derivation rules added. Step 3 note: "interim" → "remains the default". FXA-2276: Phase 11 deviation note (git-pull no-op pre-merge); `for #N` phases 2–10 → 2–11. | Claude Code |
| 2026-05-10 | R4 (bot P2): §Phase 11 Draft Content Step 3 — replace stale "session state from this Phase 11 turn" with "GitHub PR evidence re-fetched in Step 1" to match COR-1617 R2/R3 fix. | Claude Code |
