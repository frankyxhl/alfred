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
| `<weights-doc>` | `{CHG: COR-1609, code: COR-1610, PRP: COR-1608}` | **map form** (per FXA-2277) — alfred routes to the appropriate review-scoring rubric by artifact type rather than using a single project weights doc |
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
