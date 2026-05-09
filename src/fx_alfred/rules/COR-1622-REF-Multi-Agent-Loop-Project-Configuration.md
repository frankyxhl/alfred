# REF-1622: Multi-Agent Loop Project Configuration

**Applies to:** All projects adopting the COR-1617 Multi-Agent Workflow Loop
**Last updated:** 2026-05-09
**Last reviewed:** 2026-05-09
**Status:** Active
**Related:** COR-1617 (umbrella SOP), COR-1618 (consent auto-pick), COR-1619 (worker dispatch), COR-1620 (loop primitives), COR-1621 (triage)

---

## What Is It?

The parameter schema for the COR-1617 Multi-Agent Workflow Loop. Every project that adopts the loop drops a small PRJ-layer instantiation document (e.g. `<PRJ>-<ACID>-REF-Multi-Agent-Loop-Config.md`) that fills in concrete values for the keys defined here.

The schema separates the *shape* of the loop (specified once in the COR cluster) from the *values* a given repo plugs in (identities, providers, weight pointers, label names). Without this separation, every adopting project would either fork the SOPs or accumulate hard-coded references to the originating project.

---

## Why

The trinity-project predecessor (TRN-1008) embedded `frankyxhl`, `ryosaeba1985`, `iterwheel-blueprint[bot]`, four named providers, `trinity-glm`, `TRN-1800`, and `chatgpt-codex-connector[bot]` directly in the SOP body. Promoting that text to PKG would force every consumer either to use those exact identities or to mentally substitute on every read. A parameter schema makes substitution explicit and once.

---

## How to Use

1. Read this REF to understand the keys.
2. Create a PRJ-layer REF document at your project root (e.g. `rules/<PREFIX>-<ACID>-REF-Multi-Agent-Loop-Config.md`).
3. Fill in every required key. Mark optional keys as `unset` if you do not use the corresponding feature.
4. Reference the PRJ doc by ACID from any SOP that adopts COR-1617.

---

## Placeholder Convention

The cluster uses `<angle-bracket>` syntax for **two distinct namespaces** that must not be conflated:

| Namespace | Examples | Resolved by |
|-----------|----------|-------------|
| **Project-config keys** (defined in this REF) | `<repo>`, `<gh-write-identity>`, `<consent-signal>`, `<panel-providers>`, `<wakeup-tool>` | Per-project COR-1622 instantiation document; values are stable across a session |
| **Runtime variables** (NOT defined here) | `<branch>`, `<sha>`, `<issue>`, `<slug>`, `<changed-files>`, `<test-runner>`, `<linter>`, `<formatter>` | Resolved at command-execution time from git state, the project's tooling config, or the orchestrator's working memory |

When a doc uses `<X>`, look it up here first. If absent, treat as a runtime variable and resolve from context. Project-config keys never appear unquoted in shell commands without prior substitution; runtime variables are inline shorthand for "fill this in at exec time."

---

## Parameter Schema

### Identity & repository

| Key | Type | Required | Default | Description |
|-----|------|----------|---------|-------------|
| `<repo>` | string | yes | derived from `gh repo view --json nameWithOwner` | The `owner/name` repo path. Used in every `gh api repos/<repo>/...` call. |
| `<repo-owner>` | string | yes | the owner segment of `<repo>` | The GitHub login that owns `<repo>`. Convenience derivation; stated explicitly so other keys can default to it. |
| `<repo-trusted-reactor-list>` | list[string] | yes | `[<repo-owner>]` | GitHub logins whose `<consent-signal>` reaction grants auto-pick eligibility. Multiple entries permitted; matched via `IN([...])`. |
| `<gh-write-identity>` | string | yes | — | The active `gh` account expected for all GitHub-visible writes (PRs, issue comments, review submissions). Verified by `gh auth status` per COR-1505. |
| `<fork-remote>` | string | yes | `fork` | Remote name for the forked workflow. PRs are pushed here, never to `origin/main`. |

### Consent gate (COR-1618)

| Key | Type | Required | Default | Description |
|-----|------|----------|---------|-------------|
| `<consent-signal>` | string | yes | `rocket` | The reaction emoji name (per GitHub's reactions API: `rocket`, `+1`, `heart`, `hooray`, `eyes`) that signals consent. Reactions are matched on the issue body, not on comments. |
| `<intake-quality-mode>` | enum | yes | `1FA` | `1FA` (consent only) or `2FA` (consent plus intake-quality label applied by a trusted actor). |
| `<intake-quality-label>` | string | only if `2FA` | unset | Label name that signals intake quality has been verified (e.g. `blueprint-ready`). |
| `<intake-quality-applier-set>` | list[string] | only if `2FA` | unset | GitHub logins authorized to apply `<intake-quality-label>`. The most-recent `LABELED` event for the label must have `actor.login` in this set. |

### Review panel (COR-1602 binding)

| Key | Type | Required | Default | Description |
|-----|------|----------|---------|-------------|
| `<panel-providers>` | list[string] | yes | — | The provider identifiers dispatched in parallel for plan-review and code-review (e.g. `[gemini, codex, glm, deepseek]`). Minimum **3 viable** verdicts required to enforce the gate. |
| `<weights-doc>` | string | yes | — | ACID of the project's review-weights document (e.g. `TRN-1800`). Referenced verbatim in every panel-review prompt; substituting weights from a different project is a guard-rail violation. |
| `<spec-format>` | enum | yes | `CHG` | The artifact form plan-review scores: `CHG`, `ADR`, `RFC`, or `inline-PR-body`. Determines which review-scoring rubric (COR-1608/1609/1610) applies. |
| `<panel-pass-threshold>` | number | yes | `9.0` | All-individual score threshold; PASS requires every viable reviewer at or above this AND `blocking == []`. |

### Worker dispatch (COR-1619)

| Key | Type | Required | Default | Description |
|-----|------|----------|---------|-------------|
| `<worker-agent>` | string | yes | — | The coding worker identifier the orchestrator delegates substantial implementation to (e.g. `trinity-glm via droid exec`). |
| `<worker-min-loc>` | integer | yes | `30` | Lines-of-change threshold below which the orchestrator edits directly; at or above, dispatch to `<worker-agent>`. |

### Bot polling (COR-1615 binding)

| Key | Type | Required | Default | Description |
|-----|------|----------|---------|-------------|
| `<bot-actors>` | list[string] | yes | — | GitHub App logins whose review/comment activity counts as bot review (e.g. `[chatgpt-codex-connector[bot]]`). Polled per-HEAD across the three `gh api` review/comment endpoints documented in COR-1615. |

### Loop primitives (COR-1620)

| Key | Type | Required | Default | Description |
|-----|------|----------|---------|-------------|
| `<wakeup-tool>` | string | yes | `ScheduleWakeup` | The runtime primitive that arms a future re-entry. Default assumes Claude Code; alternative orchestrators substitute their own primitive and adapt COR-1620's stop-marker mechanics accordingly. |
| `<idle-cap>` | integer | yes | `12` | Maximum consecutive idle wakes before COR-1620 surfaces "loop has been idle" and pauses. |
| `<merge-watch-cap>` | integer | yes | `24` | Maximum consecutive merge-watch wakes before COR-1620 surfaces "merge-watch pending" and pauses. |

---

## Worked Example

Trinity instantiates this schema as `TRN-1209-REF-Multi-Agent-Loop-Config.md` (illustrative — actual ACID assigned by the trinity project):

| Key | Trinity value |
|-----|---------------|
| `<repo>` | `frankyxhl/trinity` |
| `<repo-owner>` | `frankyxhl` |
| `<repo-trusted-reactor-list>` | `[frankyxhl]` |
| `<gh-write-identity>` | `ryosaeba1985` |
| `<fork-remote>` | `fork` |
| `<consent-signal>` | `rocket` |
| `<intake-quality-mode>` | `2FA` |
| `<intake-quality-label>` | `blueprint-ready` |
| `<intake-quality-applier-set>` | `[iterwheel-blueprint[bot], frankyxhl]` |
| `<panel-providers>` | `[gemini, codex, glm, deepseek]` |
| `<weights-doc>` | `TRN-1800` |
| `<spec-format>` | `CHG` |
| `<panel-pass-threshold>` | `9.0` |
| `<worker-agent>` | `trinity-glm via droid exec` |
| `<worker-min-loc>` | `30` |
| `<bot-actors>` | `[chatgpt-codex-connector[bot]]` |
| `<wakeup-tool>` | `ScheduleWakeup` |
| `<idle-cap>` | `12` |
| `<merge-watch-cap>` | `24` |

---

## Guard Rails

- A project that adopts COR-1617 MUST instantiate this schema before any orchestrator session runs the loop. Missing or `unset` required keys is a hard error — orchestrator aborts and surfaces.
- Substituting `<weights-doc>` with a foreign project's weights doc is a guard-rail violation. Each project's panel-review uses the project's own weights table.
- `<intake-quality-mode>` may not silently change between sessions. If a project moves from `1FA` to `2FA` mid-flight, every previously-rocket-eligible issue must be re-checked against the new mode.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-09 | Initial version — extracted parameter schema from TRN-1008 R1–R26 to support COR-1617 cluster promotion (alfred#115) | Claude Opus 4.7 |
| 2026-05-09 | R2: added §Placeholder Convention distinguishing project-config keys from runtime variables (convergent advisory from glm+deepseek R1 panel); added `<repo-owner>` row (deepseek R1 advisory) | Claude Opus 4.7 |
