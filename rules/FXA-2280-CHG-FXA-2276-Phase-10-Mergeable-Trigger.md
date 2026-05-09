# CHG-2280: FXA-2276 Phase 10 Mergeable Trigger

**Applies to:** FXA project
**Last updated:** 2026-05-10
**Last reviewed:** 2026-05-10
**Status:** Proposed
**Date:** 2026-05-10
**Requested by:** Frank (issue #128, session 2026-05-10)
**Priority:** Medium
**Change Type:** Normal
**Targets:** FXA-2276 (Phase 10 row, Phase 11 row, §Invocation `follow FXA-2276` row, new §Known Risk subsection)

---

## What

Amend alfred's instantiation of COR-1617 (FXA-2276) so that, in `follow FXA-2276` looping mode, the Phase 11 loop-restart wake is armed when the in-flight PR reaches **mergeable** state — not when the human merges it.

Concretely, **four** edits to `rules/FXA-2276-REF-Multi-Agent-Loop-Configuration.md`:

1. **§Adoption Status — Phase 10 row.** Current text:
   > `⚠ partial | "mergeable" declaration is manual operator-to-operator; merge-watch wakeup arming not yet automated.`

   Replacement:
   > `✓ adopted | merge-watch wake polls the mergeable conjunction (defined below). On detection, the orchestrator runs `git switch main` (no pull — origin/main has not yet advanced; see §Known Risk) and arms the Phase 11 wake (60 s cadence per COR-1620 §Cadence). Default sessions: behavior unchanged — sessions still end at handoff with no §11 wake; the polled-mergeable arming applies only under `follow FXA-2276` looping mode.`

2. **§Adoption Status — Phase 11 row.** Current text:
   > `⚠ conditional | Default sessions: not adopted; sessions end at PR-merged; no automatic next-pick wake. Looping mode (under `follow FXA-2276` queue-drain — see §Invocation): adopted; post-merge §11 wake (60 s) re-enters phase 1 to scan for the next eligible candidate. Available for adoption regardless of `/loop` cron.`

   Replacement:
   > `✓ adopted | Default sessions: behavior unchanged — sessions end at handoff; no §11 wake. Looping mode (under `follow FXA-2276` queue-drain — see §Invocation): the §11 wake fires on **mergeable detection** (not on merge event). The 60 s figure is the COR-1620 §Cadence loop-restart delay between arm and wake-fire; from the orchestrator's standpoint, the next phase 1 begins ~60 s after the in-flight PR becomes mergeable, regardless of whether the human has clicked merge.`

3. **§Invocation — `follow FXA-2276` row** (current line 84). Replace the phrase `On merge, re-enter phase 1 via §11 wake` with `On mergeable detection, re-enter phase 1 via §11 wake (see §Adoption Status Phase 10/11 for the polled conjunction)`. The rest of that row is unchanged.

4. **New §Known Risk subsection**, inserted between §Parametrization gaps and §Known limitation:

   > `## Known Risk — stale-base when next branch cuts pre-merge`
   >
   > `Under the Phase 10/11 mergeable trigger, the next phase 1 fires before the in-flight PR is merged. Phase 2 then cuts the next branch from origin/main per COR-1505 — but origin/main does not yet contain the in-flight PR's merge commit. The new branch's base lags by one PR.`
   >
   > `This is safe only when the next pick is independent of the in-flight PR (no shared file edits, no shared symbol renames, no schema dependency). The operator owns this independence: in looping mode, the next pick is selected per COR-1617 §1's scope-rank tree (RANK 1–4), and the operator pre-curates the queue so that adjacent picks don't overlap. If a session genuinely needs to chain dependent picks, the operator types `stop` / `pause` / `hold` to suppress the next §11 wake (COR-1620 §Primitive 2) and merges the in-flight PR before resuming.`
   >
   > `If a stale-based branch is already cut when the operator notices the dependency, recovery is the standard rebase: `git fetch origin main && git rebase origin/main` after the in-flight PR merges. No new tooling is added.`

The "mergeable conjunction" used by Phase 10's poll is:

- `mergeStateStatus == "CLEAN"` (CI green, branch-protection rules satisfied — implies no conflicts)
- `reviewDecision == "APPROVED"` *or* `reviewDecision == null` (the latter when branch protection does not require reviews)

The query is `gh pr view <N> --json mergeStateStatus,reviewDecision`. `mergeable` (the bare-conflict field) is omitted — it is weaker than `mergeStateStatus == "CLEAN"` and known to lag (gh CLI #9583). `statusCheckRollup` is also omitted — `CLEAN` already implies CI green.

If both conditions are not yet met, the merge-watch wake re-arms per the existing COR-1620 cadence (1800 s, capped at `<merge-watch-cap>` = 24).

This CHG is **PRJ-scoped**: it changes only alfred's instantiation. COR-1617, COR-1620, and COR-1622 are untouched. Other adopters of the cluster (e.g. trinity) keep the merged-trigger semantics unless they file their own equivalent.

## Why

Today, in looping mode, after the orchestrator hands off a PR (Phase 10), the loop sits idle until the operator clicks merge. The operator becomes a synchronous blocker — every loop iteration includes their merge-click latency in the critical path. For a multi-issue queue this serialises the operator's attention to the slowest single artifact.

The Phase-10 hand-off already declares "the orchestrator's job is done" once mergeability is reached: the panel has passed, CI is green, the bot is satisfied, no blockers are open. The merge event itself adds no further information the orchestrator can act on — it is a manual confirmation gate the operator owns. Continuing to wait on `mergedAt` therefore couples loop progress to a signal the orchestrator does not need.

Switching the Phase 11 trigger to mergeability decouples the next-pick from the merge-click. Operator merges at their own pace; orchestrator picks the next eligible issue immediately. In the steady state where issues are independent (operator-curated), this is a net latency reduction with no correctness loss.

The cost is a non-zero risk that the next branch is cut from `origin/main` *before* the in-flight PR has merged — making the new branch's base lag by one PR. The §Known Risk subsection documents this explicitly. Mitigation is operator queue curation plus the standard rebase-on-merge recovery; no new automation is added.

## Impact Analysis

**Files changed**

- `rules/FXA-2276-REF-Multi-Agent-Loop-Configuration.md` — Phase 10 row + Phase 11 row of the §Adoption Status table; one phrase in the §Invocation `follow FXA-2276` row; one new §Known Risk subsection; one new row in §Change History.

**Behavioural impact**

- In `follow FXA-2276` looping mode, the orchestrator no longer waits on `mergedAt` to start the next iteration; it polls the mergeable conjunction and arms Phase 11 on first detection.
- The user remains the merger; only the *gate to next-pick* moves earlier. No automated `gh pr merge` is added — per FXA-2276 §Phase 10 the orchestrator already does not merge.
- **Branch-guard pre-arm switch.** COR-1620 §Primitive 3 says the loop-restart wake's expected branch is `main`. Under this CHG, the wake is armed while HEAD is still on the in-flight feature branch. The orchestrator therefore runs `git switch main` (no `git pull --ff-only` — the in-flight PR isn't merged yet, so origin/main hasn't advanced) immediately before arming the Phase 11 wake. The wake's branch guard then passes; phase 1 re-enters as expected. Documented here as an alfred-local extension to COR-1620 §Primitive 3, not a change to the SOP.
- **Cleanup ownership.** The eventual fast-forward of local main to the merged in-flight PR is *not* automated by this CHG. It happens at session-start per CLAUDE.md §Workflow (`git status` / `git pull` smoke), or implicitly when the next phase 2 runs `git fetch origin main` per COR-1505 (the new branch is created from `origin/main`, so local main staleness does not affect correctness of subsequent picks). Default sessions are unaffected — the cleanup question only arises in looping mode.

**Out of scope** (explicitly deferred)

- Promoting the mergeable trigger to PKG (would require evidence from at least one other adopter; trinity's own posture is unchanged).
- A general parameter `<phase-11-trigger>: merged | mergeable` on COR-1622. If a second adopter wants this, file a follow-up against COR-1622; today it lives PRJ-only.
- Backstop for the mergeable→unmergeable race (e.g., the operator force-pushes after the loop has cut the next branch). The §Known Risk subsection covers it; no automation added.
- Automated dependency analysis between adjacent picks (would replace the "operator-curated independence" mitigation with a tool). Out of scope.

**Rollback**

The doc-level rollback is to revert the FXA-2276 edits on this CHG's PR; alfred's behaviour returns to the merged-trigger variant. The CHG document itself stays as a historical record.

For an in-flight orchestrator session caught mid-rollback:

- If the session has already armed Phase 11 on mergeable but not yet woken: operator types `stop` (touches the COR-1620 stop-marker), the wake fires as a no-op, in-flight PR proceeds to manual merge as normal.
- If a stale-based next branch is already cut and the operator notices a real dependency on the in-flight PR before merging: rebase the new branch onto `origin/main` after the in-flight PR merges (`git fetch origin main && git rebase origin/main`).

## Implementation Plan

1. Edit `rules/FXA-2276-REF-Multi-Agent-Loop-Configuration.md`:
   - Replace Phase 10 row with new wording (mergeable polling + pre-arm `git switch main` + immediate Phase 11 arming; default-vs-looping scope preserved).
   - Replace Phase 11 row with new wording (fires on mergeable detection; default-vs-looping scope preserved).
   - Replace the phrase `On merge, re-enter phase 1 via §11 wake` in the §Invocation `follow FXA-2276` row with `On mergeable detection, re-enter phase 1 via §11 wake`.
   - Insert §Known Risk subsection between §Parametrization gaps and §Known limitation: stale-base hazard, operator-curated independence, manual operator override (`stop` per COR-1620 §Primitive 2), rebase recovery.
   - Append change-history row dated 2026-05-10 referencing this CHG.
2. Run `af validate --root /Users/frank/Projects/alfred` to confirm structural correctness.
3. Open PR via Phase 7. Run trinity panel review (Phase 4) on this CHG before implementing per the SOP-prescribed order; landing the FXA-2276 edits is gated on panel pass.

## Testing / Verification

- `af validate` passes after FXA-2276 edits.
- Trinity panel quartet (`<panel-providers>` per FXA-2276) scores ≥ 9.0 against COR-1609 weights; all blocking empty.
- A reading of the Phase 10/11 rows + §Invocation row + §Known Risk produces an unambiguous procedure when read alone (no need to cross-check this CHG to interpret).
- The amended FXA-2276 has no internal contradiction: §Invocation row, Phase 10 row, and Phase 11 row all describe the same trigger (mergeable, not merged).

## Approval

- [ ] Approved by: <reviewer> on <date>

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-10 | Initial version — drafted from issue #128 to remove the operator merge-click as a synchronous blocker in `follow FXA-2276` looping mode. | Claude Opus 4.7 |
| 2026-05-10 | R2 (panel R1 fixes — codex 7.5 / gemini 8.4 / glm 8.9 / deepseek 9.2): (a) Phase 10 + Phase 11 target status raised from `⚠ partial`/`⚠ conditional` to `✓ adopted` per issue #128 acceptance criteria (4/4 convergent). (b) Added 4th edit covering the §Invocation `follow FXA-2276` row's "On merge" → "On mergeable detection" phrase update — without it the doc is internally contradictory (glm B1). (c) Default-vs-looping scope preserved in both row replacements (codex B4). (d) Branch-guard pre-arm step made explicit: `git switch main` (no pull) before arming Phase 11, with explicit COR-1620 §Primitive 3 alfred-local-extension note (deepseek A1). (e) "60 s" disambiguated as COR-1620 §Cadence loop-restart delay (codex B3). (f) Mergeable conjunction tightened to `mergeStateStatus == "CLEAN"` + `reviewDecision in ("APPROVED", null)`; `mergeable` field dropped (glm A2 — stale per gh CLI #9583); `statusCheckRollup` dropped (codex A2 + glm B2 — redundant with CLEAN). (g) COR-1501 mis-citation removed; replaced with "operator-curated independence" framing (gemini B2 + deepseek A4 convergent). (h) Rollback section extended with in-flight-session recovery (stop-marker for armed-but-not-woken; rebase-after-merge for stale-base) (gemini B3 + deepseek A3). (i) Cleanup ownership defined: session-start CLAUDE.md §Workflow + implicit COR-1505 fetch (codex B2 + deepseek A3). (j) Phase 10 row "current text" quote corrected to match actual line (glm A3). | Claude Opus 4.7 |
| 2026-05-10 | R3 (R2 convergent advisory): Phase 10 replacement text referenced "§Behavioural impact" which exists in this CHG but not in the target FXA-2276 — would have left a dangling cross-reference after the edit lands (glm A1 + deepseek A1 convergent). Repointed to `§Known Risk` (which IS added to FXA-2276 by edit #4). | Claude Opus 4.7 |
