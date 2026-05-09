# REF-2276: Multi-Agent Loop Configuration

**Applies to:** FXA project (alfred — `frankyxhl/alfred`)
**Last updated:** 2026-05-09
**Last reviewed:** 2026-05-09
**Status:** Active
**Related:** COR-1617 (umbrella SOP being instantiated), COR-1622 (parameter schema), FXA-2277 (CHG that landed alongside this doc)

---

## What Is It?

Alfred's instantiation of the COR-1622 parameter schema. Every key required by COR-1622 has a value (or an explicit `unset` for optional keys). Phases of COR-1617 are listed with adoption status — alfred today adopts a subset of the 11-phase loop, with the remainder filled in aspirationally for when the project moves toward fuller automation.

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

---

## Invocation

Alfred-specific shorthand the operator can type in chat to start the COR-1617 loop with this REF's parameters. All variants are User-driven trigger #1 per COR-1617 §1 (gate-bypass per COR-1618 §Bypass — live chat input subsumes consent + intake-quality signals).

| Phrase the operator types | Behavior |
|---|---|
| `follow FXA-2276` | Start COR-1617 in **continuation mode** with these parameters: pick the lowest-rank-ID rocket-eligible open issue per COR-1618 + the COR-1617 §1 scope-rank tree, run phases 2–10 on it, on merge re-enter phase 1 (per §11 wake) and pick the next eligible issue. Idle-with-retry per §1 when the queue is empty. |
| `follow FXA-2276 once` | Same as above but **stop after phase 10** of the first pick — no §11 wake, no autonomous continuation. Useful when the operator wants one PR shipped, not a queue drain. |
| `follow FXA-2276 for #N` | **User-directed pick of issue #N** — gate-bypass per COR-1618 §Bypass clause (live chat input is consent), runs COR-1617 phases 2–10 on the named issue regardless of its rocket-gate state. Single-issue, no autonomous continuation. |

The phrases extend COR-1617 §1's User-driven trigger row's phrase list (`"pick next issue" / "do <PREFIX>-<NNNN>" / "auto-pick"`) with alfred's own shorthand. They do not change the SOP's semantics — only add a project-specific synonym.

When `follow FXA-2276` is in continuation mode and the queue is empty, the orchestrator arms idle-with-retry per COR-1620 (1800 s cadence, capped at `<idle-cap>` = 12 wakes ≈ 6 hours). Operator can stop early by typing `stop` / `pause` / `hold` per COR-1620 §Primitive 2 (stop-marker).

---

## Adoption Status by Phase

Alfred today adopts a subset of COR-1617's 11 phases. The values above are filled aspirationally for the full cluster; the table below shows which phases run automatically vs which are user-initiated or manual today.

| Phase | Today | Notes |
|---|---|---|
| 1 — Auto-pick | ❌ user-initiated | alfred sessions are user-driven; the rocket-gate parameters are filled in for the day alfred runs autonomous picks (e.g. via `/loop` cron). Until then, all picks bypass per COR-1618 §Normative Bypass Clause. |
| 2 — Branch & identity | ✓ adopted | COR-1505 followed for every PR (PR #117 R1: branch base + `gh auth status`). |
| 3 — Plan | ✓ adopted | COR-1104 sizing applied; CHGs drafted for substantive changes (FXA-2275, FXA-2277). |
| 4 — Plan-review | ✓ adopted | trinity panel via `Skill(trinity)`; PR #117 R1 panel scored glm 9.40 / deepseek 9.00 against doc-only weights. |
| 5 — Dispatch | ⚠ partial | manual `/trinity` dispatch when the worker lane fits; COR-1619 decision tree applied informally rather than via automated routing. |
| 6 — Verify implementation | ✓ adopted | `af validate`, `pytest`, `ruff` per CLAUDE.md "Essential Commands". |
| 7 — PR open | ✓ adopted | `git push origin <branch>` (NOT to fork — per `<pr-push-remote>: origin`); `gh pr create` as `<gh-write-identity>`. |
| 8 — Iterate (CI + bot + code-review) | ✓ adopted | Codex bot reviews every push; PR #117 ran 12 R-rounds. CI checks via GitHub Actions. |
| 9 — Triage | ✓ adopted | COR-1621 severity vocab (P0–P3) applied; convergence rule + hallucinated-finding rejection used in PR #117. |
| 10 — Handoff + merge-watch | ⚠ partial | "mergeable" declaration is manual operator-to-operator; merge-watch wakeup arming not yet automated. |
| 11 — Loop restart | ❌ not adopted | sessions end at PR-merged; no automatic next-pick wake. Available for adoption when alfred runs `/loop` mode. |

Legend: ✓ = automated/SOP-followed today; ⚠ = adopted with manual elements; ❌ = aspirational, parameters filled but not run.

---

## Parametrization gaps (closed by FXA-2277)

Two gaps surfaced when this REF was first drafted; both are addressed by FXA-2277 in the same PR:

1. **`<weights-doc>` was scalar-only.** Alfred uses three different rubrics keyed by artifact type (COR-1608/1609/1610). A single-string `<weights-doc>` could not express that. FXA-2277 widens the type to `string | map<<spec-format>, string>`.
2. **`<fork-remote>` presupposed a forked workflow.** Alfred pushes feature branches to `origin` directly; the original key name implied a `fork` remote that doesn't exist. FXA-2277 renames the key to `<pr-push-remote>` while preserving the "never push to `origin/main`" invariant.

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
