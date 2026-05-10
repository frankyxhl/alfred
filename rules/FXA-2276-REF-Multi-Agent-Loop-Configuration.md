# REF-2276: Multi-Agent Loop Configuration

**Applies to:** FXA project (alfred — `frankyxhl/alfred`)
**Last updated:** 2026-05-10
**Last reviewed:** 2026-05-10
**Status:** Active
**Related:** COR-1617 (umbrella SOP being instantiated), COR-1622 (parameter schema), FXA-2277 (CHG that landed alongside this doc)

---

## What Is It?

Alfred's instantiation of the COR-1622 parameter schema. Every key required by COR-1622 has a value (or an explicit `unset` for optional keys). Phases of COR-1617 are listed with adoption status — alfred today adopts a subset of the 12-phase loop, with the remainder filled in aspirationally for when the project moves toward fuller automation.

Read this document alongside COR-1617 (the SOP), COR-1622 (the schema), and the project CLAUDE.md (which describes alfred's actual day-to-day workflow).

---

## Why

PR #117 promoted trinity's TRN-1008 into the COR-1617 PKG cluster. Alfred is the second project to adopt the cluster; instantiating exposes any latent assumptions in the schema that fit trinity but not other adopters (FXA-2277 captures the two surfaced — `<weights-doc>` plurality and `<fork-remote>` rename). Beyond surfacing schema gaps, an explicit instantiation makes alfred's actual workflow inspectable and tunable: future drift between the doc and the project's behavior can be diff'd against this REF rather than re-derived.

---

## Parameter Values

### Identity & repository

| Key | Alfred value | Notes |
|-----|--------------|-------|
| `<repo>` | `frankyxhl/alfred` | derived from `gh repo view --json nameWithOwner` |
| `<repo-owner>` | `frankyxhl` | owner segment of `<repo>` |
| `<repo-trusted-reactor-list>` | `[frankyxhl]` | single trustee (matches trinity's posture) |
| `<gh-write-identity>` | `ryosaeba1985` | per global CLAUDE.md GitHub identity rule; verified via `gh auth status` per COR-1505 |
| `<pr-push-remote>` | `origin` | alfred has no fork remote; feature branches push directly to `origin/<branch>` (never to `origin/main`). The COR-1617 invariant holds; the topology underneath is single-remote. |

### Consent gate (COR-1618)

| Key | Alfred value | Notes |
|-----|--------------|-------|
| `<consent-signal>` | `rocket` | issue-body 🚀 reaction |
| `<intake-quality-mode>` | `2FA` | alfred has the `iterwheel-blueprint[bot]` intake check installed (issue #115 was rejected then re-accepted via the blueprint label flow) |
| `<intake-quality-label>` | `blueprint-ready` | applied by `iterwheel-blueprint[bot]` after intake template is satisfied |
| `<intake-quality-applier-set>` | `[iterwheel-blueprint[bot], frankyxhl]` | bot-applied (normal path) or owner-applied (manual override) |

### Review panel (COR-1602 binding)

| Key | Alfred value | Notes |
|-----|--------------|-------|
| `<panel-providers>` | `[glm, deepseek, codex, gemini]` | full quartet via `Skill(trinity)` dispatch; minimum 3 viable per COR-1602 viability rule |
| `<weights-doc>` | `{CHG: COR-1609, ADR: COR-1609, RFC: COR-1608, inline-PR-body: COR-1609}` | **map form** (per FXA-2277), keyed only by valid `<spec-format>` enum values per COR-1622. CHGs and ADRs both use COR-1609 (CHG/decision rubric, same scoring surface per COR-1617 §Phase 4). RFC uses COR-1608 (proposal/PRP-shaped). inline-PR-body defaults to COR-1609 since alfred's inline specs are CHG-shaped. **Code-review (phase 8) uses COR-1610 implicitly** per COR-1617 §Phase 4 — selected by review-phase, not by `<spec-format>`, so it does NOT appear as a map key. See "Known limitation" below for the deeper artifact-type vs spec-format gap. |
| `<spec-format>` | `CHG` | alfred's primary spec form; PRP used for larger proposals; ADR / RFC / inline-PR-body all valid per COR-1622 enum |
| `<panel-pass-threshold>` | `9.0` | per COR-1602 default |

### Worker dispatch (COR-1619)

| Key | Alfred value | Notes |
|-----|--------------|-------|
| `<worker-agent>` | `trinity-glm via droid exec` | per project CLAUDE.md "GLM = Worker, Codex/Gemini = Reviewer" |
| `<worker-min-loc>` | `30` | default; orchestrator edits direct ≤30 lines in single function, dispatches above |

### Bot polling (COR-1615 binding)

| Key | Alfred value | Notes |
|-----|--------------|-------|
| `<bot-actors>` | `[chatgpt-codex-connector[bot]]` | the only PR-review bot installed on the repo today; codex bot's review of PR #117 surfaced 18 real defects |

### Loop primitives (COR-1620)

| Key | Alfred value | Notes |
|-----|--------------|-------|
| `<wakeup-tool>` | `ScheduleWakeup` | Claude Code runtime primitive (alfred sessions run under Claude Code) |
| `<idle-cap>` | `12` | default — 6 h @ 1800 s |
| `<merge-watch-cap>` | `24` | default — 12 h @ 1800 s |

### R-count cap (COR-1617 §Phase 8)

| Key | Alfred value | Notes |
|-----|--------------|-------|
| `<max-r-count>` | `10` | default |
| `<max-r-count-extension>` | `3` | default — hard stop at R13 |
| `<convergence-severity>` | `advisory` | default — advisory-only findings → converge (Case A); P0/P1/P2 open → self-authorized extension (Case B) until hard stop at R13 |

---

## Invocation

Alfred-specific shorthand the operator types in chat to start the COR-1617 loop with this REF's parameters. The **initial** chat phrase is User-driven trigger #1 per COR-1617 §1 — gate-bypassed per COR-1618 §Normative Bypass Clause (live chat input subsumes consent + intake-quality signals for that one pick). **Subsequent picks** under looping mode (`follow FXA-2276` queue-drain) are Continuation or Loop-driven triggers per COR-1617 §1 — they re-apply COR-1618 `verify_consent_eligibility` in full.

| Phrase the operator types | Behavior |
|---|---|
| `follow FXA-2276` | Start COR-1617 in **looping mode**: the initial pick (live-chat-bypass) is the lowest-numbered RANK matching the COR-1617 §1 scope-rank tree (RANK 1 deferred tech-debt → RANK 2 unblocked → RANK 3 single-file CHG → RANK 4 multi-surface CHG); on a tie within the same rank, pick the smaller LoC estimate per COR-1617 §1. Run phases 2–10 on that pick. On mergeable detection (see §Adoption Status Phase 10/11 for the polled conjunction), execute Phase 11 (Retrospective) synchronously, then re-enter phase 1 via §12 wake and pick the next candidate **gated by full COR-1618 verify_consent_eligibility** (no bypass beyond the first pick). Idle-with-retry per §1 when the queue is empty. |
| `follow FXA-2276 once` | Same initial-pick rule (live-chat-bypass; lowest-numbered RANK + LoC tie-break) but **stop after phase 11** of that one pick — no §12 wake, no autonomous continuation. |
| `follow FXA-2276 for #N` | **User-directed pick of issue #N** — gate-bypassed per COR-1618 §Normative Bypass Clause (live chat input is consent), runs COR-1617 phases 2–11 on the named issue regardless of its rocket-gate state. Stops after Phase 11 (Retrospective) — no §12 wake, no autonomous continuation. The named issue overrides the scope-rank tree. |

**Composition rule**: the three variants are **mutually exclusive** — `follow FXA-2276 once for #N` and other combinations are not defined. Operator must pick exactly one variant per invocation. If a combined phrase appears, the orchestrator surfaces the ambiguity to the operator and does not pick.

The phrases extend COR-1617 §1's User-driven trigger row's phrase list (`"pick next issue" / "do <PREFIX>-<NNNN>" / "auto-pick"`) with alfred's own shorthand. They do not change the SOP's semantics — only add project-specific synonyms with clearer parameter-set binding.

When `follow FXA-2276` is in looping mode and the queue is empty, the orchestrator arms idle-with-retry per COR-1620 (1800 s cadence, capped at `<idle-cap>` = 12 wakes ≈ 6 hours). The operator can stop early by typing `stop` / `pause` / `hold` per COR-1620 §Primitive 2; that primitive places a **durable filesystem signal** at `$(git rev-parse --git-path trinity-loop-stopped)` which suppresses every subsequent wake until removed (the marker survives session restarts; resumption requires explicit operator removal or a fresh `follow FXA-2276` invocation).

---

## Adoption Status by Phase

Alfred today adopts a subset of COR-1617's 12 phases. The values above are filled aspirationally for the full cluster; the table below shows which phases run automatically vs which are user-initiated or manual today.

| Phase | Today | Notes |
|---|---|---|
| 1 — Auto-pick | ⚠ conditional | **Default sessions** (no `follow FXA-2276` invocation): user-initiated; the initial pick is bypassed per COR-1618 §Normative Bypass Clause. **Looping mode** (under `follow FXA-2276` queue-drain — see §Invocation): Phase 1 runs automatically post-§12 wake with full COR-1618 verify_consent_eligibility on every continuation candidate; the initial chat phrase remains user-driven and gate-bypassed for the *first* pick only. |
| 2 — Branch & identity | ✓ adopted | COR-1505 followed for every PR (PR #117 R1: branch base + `gh auth status`). |
| 3 — Plan | ✓ adopted | COR-1104 sizing applied; CHGs drafted for substantive changes (FXA-2275, FXA-2277). |
| 4 — Plan-review | ✓ adopted | trinity panel via `Skill(trinity)`; PR #117 R1 panel scored glm 9.40 / deepseek 9.00 against doc-only weights. |
| 5 — Dispatch | ⚠ partial | manual `/trinity` dispatch when the worker lane fits; COR-1619 decision tree applied informally rather than via automated routing. |
| 6 — Verify implementation | ✓ adopted | `af validate`, `pytest`, `ruff` per CLAUDE.md "Essential Commands". |
| 7 — PR open | ✓ adopted | `git push origin <branch>` (NOT to fork — per `<pr-push-remote>: origin`); `gh pr create` as `<gh-write-identity>`. |
| 8 — Iterate (CI + bot + code-review) | ✓ adopted | Codex bot reviews every push; PR #117 ran 12 R-rounds. CI checks via GitHub Actions. |
| 9 — Triage | ✓ adopted | COR-1621 severity vocab (P0–P3) applied; convergence rule + hallucinated-finding rejection used in PR #117. |
| 10 — Handoff + merge-watch | ✓ adopted | merge-watch wake polls the mergeable conjunction `mergeStateStatus == "CLEAN"` AND `reviewDecision in ("APPROVED", null)` (via `gh pr view <N> --json mergeStateStatus,reviewDecision`). On detection, the orchestrator runs `git switch main` (no pull — origin/main has not yet advanced; see §Known Risk), executes Phase 11 (Retrospective) synchronously (evidence re-fetched from GitHub PR review comments per COR-1617 §Phase 11 Step 1), then arms the Phase 12 wake (60 s cadence per COR-1620 §Cadence). The bare `mergeable` field is omitted (lags per gh CLI #9583, weaker than `CLEAN`); `statusCheckRollup` is omitted (`CLEAN` already implies CI green). **Default sessions**: behavior unchanged — sessions still end at handoff with no §12 wake; the polled-mergeable arming applies only under `follow FXA-2276` looping mode. |
| 11 — Retrospective | ✓ adopted | Synchronous; runs in the Phase 10 merge-watch wake turn (before human merge). Steps 2–3 (pattern check + CHG nomination) require user confirmation before writing. Evidence re-fetched from GitHub PR review comments using COR-1615 §Commands fetch endpoints (session state from Phase 8 rounds is unavailable across wakeup turns). **Alfred deviation from COR-1617 PKG precondition**: COR-1617 §Phase 11 states it runs after `git switch main && git pull --ff-only origin main`; under FXA-2280's mergeable trigger, Phase 11 fires before the PR is merged so origin/main has not advanced — the pull is a no-op. Functionally equivalent. **Alfred deviation — Trinity-miss/codex-catch**: alfred dispatches the panel via `Skill(trinity)` in-session; findings appear in chat, not as GitHub PR review comments. At merge-watch wake, panel findings are not GitHub-re-fetchable. Output `n/a — panel findings not GitHub-accessible` for this field. **Default sessions**: retrospective may be run manually at session end; no automated trigger. |
| 12 — Loop restart | ✓ adopted | **Default sessions**: behavior unchanged — sessions end at handoff; no §12 wake. **Looping mode** (under `follow FXA-2276` queue-drain — see §Invocation): the §12 wake fires on **mergeable detection** (not on merge event). The 60 s figure is the COR-1620 §Cadence loop-restart delay between arm and wake-fire; from the orchestrator's standpoint, the next phase 1 begins ~60 s after the in-flight PR becomes mergeable, regardless of whether the human has clicked merge. Branch-guard pre-arm (`git switch main` without `git pull --ff-only`, since the in-flight PR isn't merged yet so origin/main hasn't advanced) makes the COR-1620 §Primitive 3 check pass on wake; this is an alfred-local extension to §Primitive 3, not a change to the SOP. |

Legend: ✓ = automated/SOP-followed today; ⚠ = adopted with manual elements OR conditional on a specific invocation mode (e.g. `follow FXA-2276` looping); ❌ = aspirational, parameters filled but not run.

---

## Parametrization gaps (closed by FXA-2277)

Two gaps surfaced when this REF was first drafted; both are addressed by FXA-2277 in the same PR:

1. **`<weights-doc>` was scalar-only.** Alfred uses three different rubrics keyed by artifact type (COR-1608/1609/1610). A single-string `<weights-doc>` could not express that. FXA-2277 widens the type to `string | map<<spec-format>, string>`.
2. **`<fork-remote>` presupposed a forked workflow.** Alfred pushes feature branches to `origin` directly; the original key name implied a `fork` remote that doesn't exist. FXA-2277 renames the key to `<pr-push-remote>` while preserving the "never push to `origin/main`" invariant.

## Known Risk — stale-base when next branch cuts pre-merge

Under the Phase 10/11 mergeable trigger (FXA-2280), the next phase 1 fires before the in-flight PR is merged. Phase 2 then cuts the next branch from `origin/main` per COR-1505 — but `origin/main` does not yet contain the in-flight PR's merge commit. The new branch's base lags by one PR.

This is safe only when the next pick is independent of the in-flight PR (no shared file edits, no shared symbol renames, no schema dependency). The operator owns this independence: in looping mode, the next pick is selected per COR-1617 §1's scope-rank tree (RANK 1–4), and the operator pre-curates the queue so that adjacent picks don't overlap. If a session genuinely needs to chain dependent picks, the operator types `stop` / `pause` / `hold` to suppress the next §12 wake (COR-1620 §Primitive 2) and merges the in-flight PR before resuming.

If a stale-based branch is already cut when the operator notices the dependency, recovery is the standard rebase: `git fetch origin main && git rebase origin/main` after the in-flight PR merges. No new tooling is added.

The eventual fast-forward of local main to the merged in-flight PR happens at session-start per CLAUDE.md §Workflow (`git status` / `git pull` smoke), or implicitly when the next phase 2 runs `git fetch origin main` per COR-1505 (the new branch is created from `origin/main`, so local main staleness does not affect correctness of subsequent picks).

---

## Known limitation — artifact-type vs `<spec-format>` conflation

The COR-1622 schema (and TRN-1008 before it) uses `<spec-format>` as both:
- the *form* the project's primary specs take (one value: e.g. `CHG`)
- the *map key* for `<weights-doc>` routing (an enum: `CHG | ADR | RFC | inline-PR-body`)

Alfred's actual rubric routing is by **artifact type** under review (CHG, code, PRP, ADR), which doesn't cleanly fit the `<spec-format>` enum:
- `code` — not in the enum; per COR-1617 §Phase 4, code review uses COR-1610 by *phase* (phase 8), not by spec form. Adopters wanting a code-review rubric pick it up implicitly via phase selection, not via `<weights-doc>`.
- `PRP` — not in the enum; COR-1617 maps PRP-shaped specs to the `RFC` enum value, which then routes to COR-1608. Functionally equivalent but the naming is indirect.

The map above uses only valid `<spec-format>` enum keys per the contract. A future evolution could split `<spec-format>` (project's spec form) from `<artifact-rubric-map>` (review-time routing) for cleaner semantics; deferred to evidence-driven follow-up if the conflation produces real adopter confusion.

---

## When alfred deviates from COR-1617

These project-specific deviations are intentional and not gaps in the SOP:

- **Plan-review timing**: PR #117 ran panel-review *after* the initial push (R1 was the implemented draft, then panel scored it). COR-1617 §3-§4 prescribes plan-review *before* implementation. For small doc PRs the post-push variant is more efficient; for substantive code or contract changes alfred should follow the SOP-prescribed order. Treat the post-push variant as a documented shortcut, not a replacement.
- **Multi-bot iteration without re-running the panel**: alfred ran 12 codex-bot rounds on PR #117 without re-dispatching the trinity panel between rounds (panel passed at R2; subsequent fixes were bot-driven). Per COR-1621 "Re-dispatch the panel only when blockers (or convergent advisories) were addressed", this is correct — pure bot-found defects don't require panel re-scoring unless they uncover a blocker the panel missed.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-09 | Initial version — alfred's first instantiation of COR-1622, filed alongside FXA-2277 (which closes the schema gaps surfaced during this draft) | Claude Opus 4.7 |
| 2026-05-09 | R2: codex bot R1 P2 — `<weights-doc>` map keys (`code`, `PRP`) were not in the `<spec-format>` enum (`CHG | ADR | RFC | inline-PR-body`). Replaced with valid enum keys per COR-1617 §Phase 4 mapping. Added "Known limitation" section documenting the underlying artifact-type vs `<spec-format>` conflation as a deferred follow-up. | Claude Opus 4.7 |
| 2026-05-09 | Added §Invocation section documenting alfred-specific shorthand phrases (`follow FXA-2276`, `follow FXA-2276 once`, `follow FXA-2276 for #N`) that extend COR-1617 §1 User-driven trigger phrase list. Per-project synonym; no PKG SOP change. | Claude Opus 4.7 |
| 2026-05-09 | R3 (PR #120): trinity panel + codex bot R1 findings folded. (a) `lowest-rank-ID` (deepseek B1 + glm advisory convergent) → rewrote to match COR-1617 §1 actual rule (lowest-numbered RANK + LoC tie-break). (b) composition undefined (deepseek B2) → declared three variants mutually exclusive; combined phrases surface ambiguity to operator. (c) bypass scoping (bot R1#1) → bypass clause now scoped to the *initial* live-chat trigger only; subsequent looping-mode picks re-apply COR-1618 in full. (d) §Adoption Status (bot R1#2) → Phase 1 + Phase 11 moved from ❌ to ⚠ conditional, gated to looping mode. (e) `continuation mode` → `looping mode` (glm advisory; avoids overload with COR-1617 §1 "Continuation" trigger pattern name). (f) `§Bypass` → `§Normative Bypass Clause` (deepseek A1 typo ×3). (g) stop-marker durability noted explicitly per COR-1620 §Primitive 2 (deepseek A2). | Claude Opus 4.7 |
| 2026-05-10 | FXA-2280: Phase 10/11 trigger changed from PR-merged to PR-mergeable for `follow FXA-2276` looping mode. Phase 10 + Phase 11 raised to ✓ adopted; §Invocation `follow FXA-2276` row updated ("On merge" → "On mergeable detection"); new §Known Risk subsection documents the stale-base hazard (next branch cuts from origin/main before in-flight PR merges) with operator-curated independence + rebase recovery. Removes the operator merge-click as a synchronous blocker per issue #128. | Claude Opus 4.7 |
| 2026-05-10 | FXA-2283 R2: renumber 11-phase → 12-phase; Phase 11 = Retrospective (new synchronous phase); Phase 12 = Loop restart (formerly Phase 11); update all §11 references to §12; add Phase 11 Retrospective row to §Adoption Status; update §Invocation `follow FXA-2276 once` to stop after phase 11; update Known Risk §11 → §12. | Claude Code |
| 2026-05-10 | FXA-2283 R3: Phase 11 row — add alfred deviation note (git-pull no-op pre-merge under FXA-2280 mergeable trigger; update COR-1615 endpoint reference to §Commands); `follow FXA-2276 for #N` — fix phases 2–10 → 2–11, add "no §12 wake" clause. | Claude Code |
| 2026-05-10 | FXA-2283 R6: Phase 11 row — add Alfred deviation note for Trinity-miss/codex-catch: alfred dispatches the panel via Skill(trinity) in-session; findings not GitHub-re-fetchable; output `n/a — panel findings not GitHub-accessible`. | Claude Code |
| 2026-05-10 | Issue #144: add §R-count cap section instantiating `<max-r-count>` = 10, `<max-r-count-extension>` = 3, `<convergence-severity>` = advisory (all defaults). | Claude Sonnet 4.6 |
