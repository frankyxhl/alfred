# REF-1622: Multi-Agent Loop Project Configuration

**Applies to:** All projects adopting the COR-1617 Multi-Agent Workflow Loop
**Last updated:** 2026-05-17
**Last reviewed:** 2026-05-17
**Status:** Active
**Related:** COR-1617 (umbrella SOP), COR-1618 (consent auto-pick), COR-1619 (worker dispatch), COR-1620 (loop primitives), COR-1621 (triage)
**Disposition:** mandatory-bind

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
| `<repo-trusted-reactor-list>` | list[string] | yes | `[<repo-owner>]` | GitHub logins whose `<consent-signal>` reaction grants auto-pick eligibility. Multiple entries permitted; tested via jq array-membership (`<list> \| index(<login>)`) — see COR-1618 check 2 for the exact recipe. Note: jq's `IN(...)` is a stream-membership test, not array-membership, and cannot be passed a list parameter. |
| `<gh-write-identity>` | string | yes | — | The active `gh` account expected for all GitHub-visible writes (PRs, issue comments, review submissions). Verified by `gh auth status` per COR-1505. |
| `<pr-push-remote>` | string | yes | `fork` | The git remote that PR head branches push to; never `origin/main` directly. Single-remote projects (no fork) set this to `origin`; fork-PR projects set it to the fork remote (commonly `fork`). The invariant is "PR push goes here, not to `origin/main`" — the topology underneath is project-specific. (Renamed from `<fork-remote>` per FXA-2277 — original name presupposed a forked workflow that not all adopters use.) |

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
| `<weights-doc>` | string \| map<<spec-format>, string> | yes | — | The review-weights pointer the panel-review prompt cites verbatim. Two valid forms: (1) **Scalar**: a single ACID covering all artifact types (e.g. trinity's `TRN-1800`). (2) **Map**: keyed by `<spec-format>` enum values (`CHG`, `ADR`, `RFC`, `inline-PR-body` — see next row), each entry is the ACID whose rubric is loaded when an artifact of that form is reviewed (e.g. alfred's `{CHG: COR-1609, ADR: COR-1609, RFC: COR-1608, inline-PR-body: COR-1609}`). Adopters with one rubric across all artifact types use the scalar form; adopters keying off `<spec-format>` use the map form. **Code-review (phase 8) uses COR-1610 implicitly per COR-1617 §Phase 4 — selected by review-phase, not by `<spec-format>` — so `code` is NOT a valid map key.** Substituting weights from a different project is a guard-rail violation regardless of form. |
| `<spec-format>` | enum | yes | `CHG` | The artifact form plan-review scores: `CHG`, `ADR`, `RFC`, or `inline-PR-body`. Determines which review-scoring rubric (COR-1608/1609/1610) applies. |
| `<panel-pass-threshold>` | number | yes | `9.0` | All-individual score threshold; PASS requires every viable reviewer at or above this AND `blocking == []`. |

### Worker dispatch (COR-1619)

| Key | Type | Required | Default | Description |
|-----|------|----------|---------|-------------|
| `<worker-agent>` | string | yes | — | The coding worker identifier the orchestrator delegates substantial implementation to (e.g. `trinity-glm via droid exec`). |
| `<worker-min-loc>` | integer | yes | `30` | Lines-of-change threshold for the single-function trivial-fix branch. **At or below** this count: orchestrator edits directly. **Above**: dispatch to `<worker-agent>`. (Boundary alignment with COR-1619 §Decision Tree node C — both docs treat the threshold value itself as the orchestrator-direct ceiling.) |
| `<test-writer-worker-agent>` | string | no | same value as `<worker-agent>` | Distinct agent instance for the RED-phase test-writer per COR-1500 §Phase 1 Worker assignment. When unset (or equal to `<worker-agent>`), the two-worker split is OFF for this adopter and COR-1500 §AI-Assisted TDD Protocol Mandatory Rule #3 alone applies. Adopters opt in by setting this to a different model OR the same model with a different `:instance` suffix. **Adopters using the same model with different `:instance` suffix MUST verify with their dispatch backend that the suffix produces a fresh context (no shared KV cache / session state); if not verified, default to different-model differentiation.** |

### R-count cap (COR-1617 §Phase 8)

| Key | Type | Required | Default | Description |
|-----|------|----------|---------|-------------|
| `<max-r-count>` | integer | yes | `10` | Soft cap — round at which the cap check first fires. On this round and every round thereafter, the orchestrator evaluates Case C / A / B before continuing. |
| `<max-r-count-extension>` | integer | yes | `3` | Additional rounds auto-authorized when P0/P1/P2 findings remain open. Hard stop (Case C) triggers at `<max-r-count>` + `<max-r-count-extension>`. |
| `<convergence-severity>` | enum | yes | `advisory` | Finding severity at or below which the PR is considered converged (Case A). Enum values in ascending severity order: `advisory` (no P0/P1/P2 open) < `p2` (no P0/P1 open) < `p1` (no P0 open). Note: `advisory` here is a threshold label, not COR-1621's "advisory" finding class. |

### Resilience (CLI retry / failure escalation)

| Key | Type | Required | Default | Description |
|-----|------|----------|---------|-------------|
| `<cli-retry-attempts>` | integer | yes | `3` | Maximum retry attempts per provider per round when a panel-provider CLI fails (timeout, non-zero exit, or missing binary). `0` = fail-fast: surface the failure immediately without retrying. This value governs retry count in place of COR-1617 §Failure Modes' hardcoded "retry once" rule — adopters that set this key get `<cli-retry-attempts>` retries, not 1. |
| `<cli-retry-backoff-seconds>` | integer | yes | `600` | Seconds to wait between retry attempts. |
| `<cli-retry-on-failure>` | enum | yes | `pause-and-ask` | Action when all retry attempts are exhausted. One of: `pause-and-ask` — surface the failure to the operator and wait for instruction; `mark-non-viable` — treat the provider as non-viable for this run and continue if the panel retains ≥3 viable verdicts (see §Review panel `<panel-providers>`); `abort-loop` — stop the run entirely. |

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
| `<pr-push-remote>` | `fork` |
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
| `<max-r-count>` | `10` (default) |
| `<max-r-count-extension>` | `3` (default) |
| `<convergence-severity>` | `advisory` (default) |
| `<cli-retry-attempts>` | `3` (default) |
| `<cli-retry-backoff-seconds>` | `600` (default) |
| `<cli-retry-on-failure>` | `pause-and-ask` (default) |
| `<bot-actors>` | `[chatgpt-codex-connector[bot]]` |
| `<wakeup-tool>` | `ScheduleWakeup` |
| `<idle-cap>` | `12` |
| `<merge-watch-cap>` | `24` |

---

## Guard Rails

- A project that adopts COR-1617 MUST instantiate this schema before any orchestrator session runs the loop. Missing or `unset` required keys is a hard error — orchestrator aborts and surfaces.
- Substituting `<weights-doc>` with a foreign project's weights doc is a guard-rail violation. Each project's panel-review uses the project's own weights table.
- `<intake-quality-mode>` may not silently change between sessions. If a project moves from `1FA` to `2FA` mid-flight, every previously-rocket-eligible issue must be re-checked against the new mode.
- `<cli-retry-on-failure>` = `mark-non-viable` interacts with the `<panel-providers>` 3-viable-minimum rule: after marking a provider non-viable, verify the remaining panel still meets the 3-viable gate before continuing, AND that the failed provider was not the prior round's sole dissenter (per COR-1617 §Failure Modes). If either condition fails, escalate to the operator regardless of this setting.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-09 | Initial version — extracted parameter schema from TRN-1008 R1–R26 to support COR-1617 cluster promotion (alfred#115) | Claude Opus 4.7 |
| 2026-05-09 | R2: added §Placeholder Convention distinguishing project-config keys from runtime variables (convergent advisory from glm+deepseek R1 panel); added `<repo-owner>` row (deepseek R1 advisory) | Claude Opus 4.7 |
| 2026-05-09 | R6: `<repo-trusted-reactor-list>` description updated — was "matched via `IN([...])`"; now correctly documents jq's `index` array-membership and notes that `IN(...)` is a stream-membership test that cannot take a list parameter. Aligns with COR-1618 R5 recipe. Codex bot R5 P2 cross-doc-drift finding. | Claude Opus 4.7 |
| 2026-05-09 | R9: `<worker-min-loc>` boundary semantics aligned with COR-1619 §Decision Tree — was "at or above → worker" (so the value 30 went to worker); now "at or below → orchestrator, above → worker" (so 30 stays with orchestrator). COR-1619 was the operative dispatch SOP and already used "at or below"; this fixes the contract divergence. Codex bot R8 P2 boundary finding. | Claude Opus 4.7 |
| 2026-05-09 | FXA-2277: two schema refinements surfaced when alfred attempted to instantiate. (1) `<fork-remote>` renamed to `<pr-push-remote>` — original name presupposed a forked-fork workflow that not all adopters use; alfred pushes feature branches to `origin` directly. The invariant ("never push to `origin/main`") is preserved; only the name changed. (2) `<weights-doc>` type widened from `string` to `string \| map<<spec-format>, string>` — adopters with one rubric across artifact types use the scalar form (trinity's `TRN-1800`); adopters keying off `<spec-format>` use the map form. Trinity's existing instantiation continues working unchanged. | Claude Opus 4.7 |
| 2026-05-09 | R3 (PR #119): codex bot R2 P2 — `<weights-doc>` schema-row description showed an example with invalid map keys (`code`, `PRP` — not in the `<spec-format>` enum). Same class of bug fixed in FXA-2276 R2 but not propagated to COR-1622 itself. Replaced with valid enum keys (alfred's actual map: `{CHG: COR-1609, ADR: COR-1609, RFC: COR-1608, inline-PR-body: COR-1609}`); added explicit note that `code` is not a valid key (code review uses COR-1610 by phase per COR-1617 §Phase 4). Adopters copying the schema row now get a valid instantiation. | Claude Opus 4.7 |
| 2026-05-10 | FXA-146: add §Resilience parameter group (`<cli-retry-attempts>`, `<cli-retry-backoff-seconds>`, `<cli-retry-on-failure>`) covering CLI/provider-failure retry behavior. Defaults (3 attempts / 600 s / pause-and-ask) match Babs operator policy. Guard rail added for `mark-non-viable` interaction with 3-viable-minimum. Worked Example updated with trinity's effective defaults (all three keys inherit schema defaults; no behavior change). | Claude Sonnet 4.6 |
| 2026-05-10 | DeepSeek R1 advisory fixes: `<cli-retry-attempts>` — added per-provider-per-round scope and explicit COR-1617 §Failure Modes override note; guard rail — added dissenter exception condition; Worked Example — moved three resilience rows to match schema section order (after §Worker dispatch, before §Bot polling). | Claude Sonnet 4.6 |
| 2026-05-10 | Issue #144: add §R-count cap parameter group (`<max-r-count>`, `<max-r-count-extension>`, `<convergence-severity>`) for COR-1617 §Phase 8 round-count guard. Defaults (10 / 3 / advisory) define soft cap R10, hard stop R13. Worked Example updated with trinity's effective defaults (all three inherit schema defaults). | Claude Sonnet 4.6 |
| 2026-05-10 | Issue #144 R2: `<convergence-severity>` — add enum ordering note (advisory < p2 < p1) and clarify that `advisory` is a threshold label, not COR-1621's "advisory" finding class (GLM P1 / DeepSeek P3). | Claude Sonnet 4.6 |
| 2026-05-17 | FXA-2291 (CHG-D of PRP-1507): added optional `<test-writer-worker-agent>` row under §Worker dispatch (COR-1619). Default = same value as `<worker-agent>` (split OFF for non-adopters; backwards-compatible). MUST-level `:instance` suffix verification note. Bundled with CHG-A/B/C1/C2 in PR closing issue #175. | Claude Opus 4.7 |
