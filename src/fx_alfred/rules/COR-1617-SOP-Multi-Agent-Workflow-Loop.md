# SOP-1617: Multi-Agent Workflow Loop

**Applies to:** All projects with a multi-provider review setup and an autonomous-orchestrator capability
**Last updated:** 2026-05-17
**Last reviewed:** 2026-05-17
**Status:** Active
**Related:** COR-1602 (Multi Model Parallel Review — composes for plan-review and code-review panels), COR-1615 (GitHub App PR Review Bot Loop — composes for §8 bot polling), COR-1618 (consent auto-pick), COR-1619 (worker dispatch), COR-1620 (loop primitives), COR-1621 (triage), COR-1505 (branch + identity hygiene), COR-1104 (CHG sizing), COR-1622 (parameter schema), COR-1506 (issue quality gate — Phase 1 autonomous picks)

---

## What Is It?

The end-to-end loop a multi-agent orchestrator runs to ship a PR through a multi-provider review panel: pick the next issue, plan, panel-review the plan, dispatch implementation, verify, panel-review the code, iterate on bot/CI findings, hand off to the user for merge, then auto-pick the next issue.

This SOP is the **umbrella**: it sequences the twelve phases and routes each phase to its atomic SOP. It does not own consent-gate semantics (COR-1618), worker-dispatch decisions (COR-1619), wakeup mechanics (COR-1620), or triage logic (COR-1621); each is a single-surface SOP composed here.

It also does not own the panel-review pattern itself (delegated to COR-1602) or the bot-poll pattern (delegated to COR-1615) — those are the prior-art PKG SOPs this loop is built on top of.

---

## Why

Multi-provider review (a panel of N≥3 reviewers per major change) catches classes of bugs single-reviewer flows miss — convergence across heterogeneous models is high-signal. But running it cleanly takes discipline: parallel dispatch, correct weights, honest gate enforcement. The loop also has a worker layer (orchestrator delegates implementation to a coding worker) and an auto-pick layer (orchestrator picks the next issue without user input). Each is a non-trivial decision; documented together as one umbrella they form a coherent operating model.

Three failure modes recur when the loop is re-derived ad-hoc per session:

1. **Stale-branch base** — branching off a local `main` that lags `origin/main`, producing phantom-reference bugs. Closed by COR-1505.
2. **Wrong dispatch lane** — orchestrator hand-edits 200-line refactors that should go to a worker, or dispatches a 2-line typo fix that round-trips for no reason. Closed by COR-1619.
3. **Wrong gate semantics** — accepting a 3-of-N PASS panel as "good enough" instead of holding the all-individual line, then later discovering the dissenter caught a real bug. Closed by COR-1621.

---

## When to Use

- Substantive PRs that touch behaviour, schemas, or public surfaces.
- Any PR where a single-reviewer judgment call could be wrong (architecture, contract changes, security-adjacent code).
- Cross-cutting refactors (multi-file rename, API rename, lifting an abstraction).
- New CHGs / SOPs / PRPs.
- The first PR of a session (also re-pins branch base + identity even if the panel is skipped).

## When NOT to Use

- One-line bug fixes with an obvious cause (typo, missing import, wrong constant). Direct edit, single-reviewer or self-review, ship.
- Pure documentation changes that don't touch CHGs / SOPs (README polish, CHANGELOG re-flow). Self-review is fine.
- Generated-file regeneration (`make build`, `af index`). The generator is the reviewer.
- Reverts of an already-reviewed change (the original PR carried the panel; a clean revert inherits the gate).

---

## Project Configuration

Every project that adopts this SOP MUST instantiate COR-1622's parameter schema as a PRJ-layer REF doc. Missing required keys is a hard error — orchestrator aborts.

The phases below reference parameters by `<key>`. See COR-1622 for the full key list.

---

## Phases

The loop has **12 phases**:

```
1. Auto-pick               ← consent gate per COR-1618
2. Branch & identity       ← COR-1505
3. Plan                    ← CHG sizing per COR-1104
4. Plan-review             ← N-provider panel per COR-1602
5. Dispatch                ← orchestrator-vs-worker per COR-1619
6. Verify implementation   ← read symbols, tests, lint, validate
7. PR open                 ← push to <pr-push-remote>; gh pr create
8. Iterate                 ← CI poll + bot poll per COR-1615 + code-review panel per COR-1602
9. Triage                  ← per COR-1621
10. Handoff + merge-watch  ← user merges; merge-watch wake per COR-1620
11. Retrospective          ← synchronous; no wakeup
12. Loop restart           ← post-handoff wake per COR-1620
```

### Phase-to-SOP routing

| # | Phase | Owns | Delegates to |
|---|-------|------|--------------|
| 1 | Auto-pick | trigger-pattern selection (user-driven / continuation / loop-driven); idle-with-retry arming | **COR-1618** (consent gate); **COR-1506** (issue quality gate — autonomous picks only); **COR-1620** (wake mechanics) |
| 2 | Branch & identity | — | **COR-1505** (branch base, create-only, identity gate) |
| 3 | Plan | issue → CHG decision | **COR-1104** (skip / inline / full) |
| 4 | Plan-review | parallel dispatch of `<panel-providers>`; gate enforcement (`all-individual ≥ <panel-pass-threshold>` AND `blocking == []`); `<weights-doc>` selection | **COR-1602** (Reviewer fan-in pattern) |
| 5 | Dispatch | direct-vs-worker decision | **COR-1619** (decision tree + worker contract) |
| 6 | Verify | run verification commands; spot-check invariants | — |
| 7 | PR open | push to `<pr-push-remote>`; `gh pr create --base main --head <head-spec>` (form depends on topology — see §Phase 7) | — |
| 8 | Iterate | per-R-push wake-arming (270 s active poll); 3-endpoint bot poll | **COR-1615** (bot-loop semantics); **COR-1602** (code-review panel); **COR-1620** (wake mechanics) |
| 9 | Triage | finding routing | **COR-1621** (triage tree + severity) |
| 10 | Handoff + merge-watch | "mergeable" declaration; arm merge-watch wake | **COR-1620** (wake mechanics, merge-watch counter, branch guard) |
| 11 | Retrospective | metrics block; pattern check; CHG nomination | — (synchronous; no delegation) |
| 12 | Loop restart | post-handoff 60 s wake to re-enter phase 1 | **COR-1620** (wake mechanics) |

### Phase 1 — Auto-pick

Three trigger patterns:

| Trigger | When | Mandate source |
|---------|------|----------------|
| **User-driven** | User explicitly names a target issue in chat (e.g. `do <PREFIX>-<NNNN>`, `follow FXA-2276 for #N`) | Mandate granted by the message itself; consent gate **BYPASSED** per COR-1618 §Normative Bypass Clause. Phrases that do NOT name a target issue (e.g. bare "pick next issue", "auto-pick", "follow FXA-2276") fall through to the Continuation or Loop-driven row — they direct the loop to START but do not consent to a specific issue. |
| **Continuation** | Just-merged a PR while a prior auto-pick mandate is still in force | Mandate carried forward; consent gate applies |
| **Loop-driven** | A periodic re-fire scheduled by a wakeup primitive (per COR-1620) | Mandate is the loop invocation itself; consent gate applies on every tick |

For autonomous picks (continuation, loop-driven), apply COR-1618 `verify_consent_eligibility(<issue_num>)`. Pass → apply COR-1506 quality check. If COR-1506 score ≥ 8.0 → continue to scope-rank tree. If COR-1506 score < 8.0 → apply label / skip per COR-1506 §Integration with COR-1617; advance to next consent-eligible candidate. Consent fail → arm idle-with-retry per COR-1620 (cadence 1800 s; counter `idle wake N of <idle-cap>`).

#### Scope-rank tree (after consent gate passes)

| Rank | Type | Action |
|------|------|--------|
| 1 | Deferred internal tech-debt with consent-eligible tracking issue | Take if no Rank 1 dependency |
| 2 | Issue unblocked by just-shipped PR | Take if user mandate present |
| 3 | Single-file CHG | Take |
| 4 | Multi-surface CHG with clear scope | Take |
| — | Broad audit / large design | Defer; ask user even with consent signal |

Branches are NOT mutually exclusive. Rule: take the **lowest-numbered RANK** that matches; on a tie, pick the smaller LoC estimate.

**Re-verify** the consent gate before each git operation that publishes work (branch create, push, PR open). Mid-loop revocation aborts in-flight work and surfaces to user — do NOT retry, do NOT silently switch to another candidate. See COR-1618 §Steps for the re-verification semantics.

### Phase 2 — Branch & identity

Run COR-1505 in full. Two gates: branch base (`git fetch origin main` + `--porcelain` + `git switch -c`) and identity (`gh auth status` matches `<gh-write-identity>`).

### Phase 3 — Plan

Apply COR-1104 to decide skip / inline / full CHG. For full CHGs, draft under `rules/<PREFIX>-<ACID>-CHG-*.md` with `Status: Proposed`.

### Phase 4 — Plan-review

Dispatch `<panel-providers>` in parallel via the project's review-dispatch mechanism. Compose COR-1602 with these specifics:

- **Weights table**: pass `<weights-doc>` verbatim in every prompt. Do NOT substitute another project's weights.
- **Spec format**: `<spec-format>` selects the review rubric. The four enum values map as follows: `CHG` → COR-1609; `ADR` → COR-1609 (decision-record-shaped, same scoring surface); `RFC` → COR-1608 (proposal-shaped); `inline-PR-body` → use the rubric matching the artifact the inline spec describes (CHG-shaped → COR-1609; PRP-shaped → COR-1608). Code-review (phase 8) uses COR-1610 regardless of `<spec-format>` — that rubric is selected by review-phase, not by spec form.
- **Gate**: `decision == PASS AND weighted_score ≥ <panel-pass-threshold> AND blocking == []` for **every viable reviewer**. Mean is informational only.
- **Viability**: at least 3 viable verdicts required. With < 3, abort and surface the outage. See §Failure Modes.

Common R1 universal-blocker classes (catalogue, derived from TRN-1008 lineage):

- Returncode precedence undefined.
- I/O contract widening.
- Static-template constraints incompatible with runtime gating.
- Stale-base reference / phantom file (closed by phase 2).
- Panel reviewing the wrong project's weights doc (use `<weights-doc>`).

A structured verdict with `decision: PASS` but `weighted_score < <panel-pass-threshold>` is **malformed**. Coerce to FIX (the schema rule says PASS requires score-and-blocking-empty); iterate.

| Panel result | Action |
|--------------|--------|
| All viable PASS, every score ≥ `<panel-pass-threshold>`, all blocking empty | Status: Approved → phase 5 |
| 3 PASS + 1 FIX | NOT passed — fix dissenter's blockers, re-dispatch |
| All PASS but one reviewer below threshold | NOT passed — coerce to FIX, iterate |
| All PASS, all blocking empty, advisories present | Passed — fix convergent advisories before code-review (phase 8); see COR-1621 |

### Phase 5 — Dispatch

Apply COR-1619 decision tree. For worker dispatch, honor the COR-1619 §Worker Dispatch Contract verbatim.

### Phase 6 — Verify implementation

Trust but verify. Whether the diff came from `<worker-agent>` or the orchestrator's own direct edits, the same checks apply:

```bash
grep -n "<each-helper-name>" <changed-files>     # symbols exist
<test-runner> <changed-paths>                    # all green
<linter> <changed-paths>                         # clean
<formatter> --check <changed-paths>              # clean
af validate --root .                             # repo-relative
```

Spot-check 1–2 key invariants from the CHG by reading code (regex flags, constants, error-handler exception lists).

### Phase 7 — PR open

```bash
git add <specific-paths>                              # never -A
git commit -m "..."                                   # HEREDOC for formatting
git push <pr-push-remote> <branch-name>               # never to origin/main

# gh pr create --head form depends on topology:
#   Fork-PR    (<pr-push-remote> = a fork remote owned by <gh-write-identity>):
#     --head <gh-write-identity>:<branch>
#   Single-remote (<pr-push-remote> = "origin", same repo as <repo>):
#     --head <branch>     OR     --head <repo-owner>:<branch>
# The `--head <user>:<branch>` form selects a head repo by owner; pointing at
# <gh-write-identity> when the branch actually lives on <repo-owner>'s repo
# would resolve to the wrong head repository or fail to create the PR.
gh pr create --repo "<repo>" --base main \
             --head <head-spec> ...
```

PR body includes: Summary / Why / Surfaces / Test plan / Files / `Closes #<issue>`. Plan-review gate scores belong in the body when applicable.

The closing token must be **bare** — `Closes #<N>` (or `Fixes #<N>` / `Resolves #<N>`) with nothing between the verb and the `#<N>` ref except whitespace, since GitHub's auto-linker matches `(close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved)\s+(?:[\w.-]+/[\w.-]+)?#\d+`. Phrasings like `Closes routing gap from issue #126` or `Closes issue #127` do not fire the parser, even though they read naturally — the issue stays open after merge and must be closed by hand. Place the token on its own line or as a leading clause of a sentence; the descriptive scope sentence ("…closes the routing gap surfaced in issue #126…") goes elsewhere.

Verify the auto-link before merge: `gh pr view <N> --repo <repo> --json closingIssuesReferences` must list every issue this PR is intended to close. An empty array means the parser didn't match — fix the body via `gh pr edit <N> --body-file <path>` and re-check, rather than relying on a manual close after merge.

### Phase 8 — Iterate

After every R-push, arm a poll wake per COR-1620 (cadence 270 s for active polling, 1200–1800 s for long-running CI/panel).

Three poll endpoints (per COR-1615; missing any one leaves inline blockers untriaged):

| Endpoint | Catches | HEAD anchor |
|----------|---------|-------------|
| `gh api repos/<repo>/pulls/<N>/reviews` | review summaries | `.commit_id == HEAD` |
| `gh api repos/<repo>/issues/<N>/comments` | PR-conversation comments | `.updated_at > <HEAD push timestamp>` (use `updated_at` to catch sticky-comment edits) |
| `gh api repos/<repo>/pulls/<N>/comments` | inline path/line review comments (where bot reviews land) | `.commit_id == HEAD` |

`gh api` returns REST snake_case (`submitted_at`/`created_at`). `gh pr view --json` returns gh-wrapper camelCase. Pick one form and stick with it; mixing produces null-timestamps and silent misses. **REST is recommended** because the inline-review-comments endpoint is only on `gh api`.

CI status splits four ways:

| CI status | Action |
|-----------|--------|
| Pending / queued | Wait another 270 s |
| Cancelled | Re-trigger workflow + wait |
| Timeout | Log + re-trigger ONCE; 3 timeouts on same PR → abort + surface "likely test or infra regression" |
| Failed | Read failing log; fix in code; push R<n+1> |

Code-review panel runs once per HEAD when CI is green AND bot has reviewed the current HEAD. Panel gate per phase 4. If gate met → phase 10. If gate not met → triage per phase 9 → push R<n+1> → loop back.

### Round-count cap

Cap check fires on every round where R-number ≥ `<max-r-count>` (default 10 per COR-1622 §R-count cap). Cases are evaluated in the order listed:

| Case | Condition | Action |
|------|-----------|--------|
| **C — Hard stop** | R-number ≥ `<max-r-count>` + `<max-r-count-extension>` | Halt. Surface to user: "PR #\<N\> reached R\<count\> (soft cap `<max-r-count>` + `<max-r-count-extension>` extension rounds). Remaining: P0=\<n\> P1=\<n\> P2=\<n\> advisory=\<n\>. Trend: \<converging / flat / diverging\>. Recommend: [merge as-is / address manually / close]. Awaiting decision." |
| **A — Converged** | All remaining findings are at or below `<convergence-severity>` (default `advisory` — no P0/P1/P2 open) | Declare convergence. Proceed to Phase 10. No user alert. |
| **B — Extension** | P0/P1/P2 still open AND R-number < `<max-r-count>` + `<max-r-count-extension>` | Log: "R\<N\>: unresolved P\<k\> findings; self-authorizing extension round \<ext#\>." Continue Phase 8. |

Case C is evaluated first: reaching the extended hard-stop round requires operator sign-off even when all findings have converged, to prevent silent auto-merge after an unusually long iteration cycle. If C fires, halt — do NOT proceed to Phase 10.

### Phase 9 — Triage

Apply COR-1621 to every finding. Plan-review architectural blockers go back to phase 4 (re-dispatch panel after CHG fix); code-review and bot findings flow through the severity tree. Re-dispatch the panel only when blockers (or convergent advisories) were addressed.

### Phase 10 — Handoff + merge-watch

When PR is mergeable (CI green, bot 👍, panel gate met, no open blockers):

- The orchestrator's job is done.
- The repo owner merges manually. `<gh-write-identity>` typically cannot merge under branch protection — that is intentional.
- Do NOT spam `gh pr merge --auto` retries; the GraphQL endpoint will reject.
- Arm a **merge-watch** wake per COR-1620: 1800 s cadence, counter `merge-watch wake N of <merge-watch-cap> for branch <BRANCH_NAME>`, polls `gh pr view <N> --json mergedAt -q .mergedAt` on wake.
- On merge detected: cleanup (`git switch main && git pull --ff-only origin main`), execute Phase 11 (Retrospective), then arm Phase 12.

The merge-watch wake's branch guard (per COR-1620 Primitive 3) ensures that if the user switches off the watched branch to do other work, the wake becomes a no-op without auto-switching.

### Phase 11 — Retrospective

Synchronous — runs immediately after Phase 10 cleanup (`git switch main && git pull --ff-only origin main`). No wakeup armed; no panel review. Optional steps (Steps 2–3) require user confirmation before writing.

**Step 1 — Metrics block.** Re-fetch evidence from GitHub before emitting (Phase 11 runs in the merge-watch wake turn; Phase 8 session state is not available):
- **R-count**: `gh pr view <N> --json commits --jq '.commits | length'` — accurate when the guard rail (one commit per round, never amend) is followed. If admin-only commits were added within a round before requesting the next review (e.g., COR-1615 CHG closeout/status/index updates), commit count overstates R-count; adjust manually by inspecting commit messages or timestamps and subtracting admin-only commits. Use the bare number (not `#<N>`) — in POSIX shell, `#` after whitespace starts a comment and drops the argument.
- **Findings (P0–P3)**: Fetch bot review comments via COR-1615 §Commands fetch endpoints (`gh api .../pulls/<N>/reviews`, `.../issues/<N>/comments`, `.../pulls/<N>/comments`); re-apply COR-1621 triage to each raw finding to produce P0–P3 classification. Codex finding count = comments from the codex bot identity across all three endpoints.
- **Late-catch (R3+)**: A finding whose first appearance (by review timestamp) is on round R3 or later.
- **Trinity-miss/codex-catch**: A finding that appears in codex bot comments but not in any panel (GLM/DeepSeek) comment on the same round. Requires panel findings to be posted as GitHub PR review comments or another durable GitHub-re-fetchable artifact. If the panel ran in-session (e.g., via `Skill(trinity)`) without posting findings to GitHub, output `n/a — panel findings not GitHub-accessible`.

Emit:
```
Retro PR #<N> (closes #<issue>): R<count> rounds
Findings: P0=<n> P1=<n> P2=<n> P3=<n> | Codex: <k> findings
Late-catch (R3+): <finding class or "none">
Trinity-miss/codex-catch: <finding class, "none", or "n/a — panel findings not GitHub-accessible">
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

*Note: COR-1200 §Scoring (shipped in PR #138) defines a 4-dimension rubric (Frequency/Actionability/Impact/Detection gap) with composite threshold ≥7.5 = create issue. Adopters MAY use that rubric instead of the count rule above; the count rule remains the default.*

**Step 4 — Hand off.** Print "Retro complete." and proceed to Phase 12 (Loop restart).

### Phase 12 — Loop restart

After phase 10 completes (PR merged + main checked out + main pulled) and phase 11 (Retrospective) finishes, arm a single 60 s wake (per COR-1620's hard floor) whose prompt re-runs phase 1. The 60 s captures the post-handoff burst window where the operator may signal a queued issue immediately after merge.

The wake's prompt MUST include the FIRST stop-marker guard and SECOND branch guard from COR-1620.

---

## Guard Rails

- For autonomous picks, never invent work when no candidate is consent-eligible. Idle is not exit — phase 1 arms idle-with-retry per COR-1620 until interrupted (live-chat user-directed pick) or stopped (per COR-1620 §Stop conditions).
- Never panel-review without `<weights-doc>` in the prompt.
- Never accept 3-of-N PASS as gate-met when the dissenter raises a blocker (per COR-1621).
- Never push to `origin/main`. Push to `<pr-push-remote>`.
- Never bypass the identity gate (per COR-1505).
- Never trust worker reports without spot-checking (per COR-1619 §Verification).
- Never sleep > 270 s when actively polling (per COR-1620 cadence rules).
- Never amend a published commit. Add a new commit; the CHG history table tracks iterations.
- Never skip the CHG for substantive changes (per COR-1104). Plan-review can't run without something to review.

---

## Failure Modes

### Reviewer / provider unavailability

A provider call that times out, exits non-zero, uses a missing binary, returns non-2xx, or emits malformed JSON does NOT count as a verdict. Retry per `<cli-retry-attempts>` (default 3 per COR-1622 §Resilience), waiting `<cli-retry-backoff-seconds>` between attempts (default 600 s); if all attempts fail, apply `<cli-retry-on-failure>` (default `pause-and-ask` per COR-1622 §Resilience). When `<cli-retry-on-failure>` = `mark-non-viable`: proceed with N-1 only if N-1 ≥ 3 AND the failed provider wasn't the prior round's dissenter; otherwise abort the panel and surface the outage. Always document the missing reviewer in the PR body.

Below 3 viable: convergence signal collapses; do NOT proceed with 2-of-2.

### User override mid-loop (covers consent revocation)

The auto-pick mandate is checked at phase 1, but the user can revoke or redirect at any point. User messages mid-loop take priority. Save loop state (current phase, R-number, panel verdicts so far, pending fixes, active CHG path), acknowledge, act on the message; on resume restart from saved state.

**Consent revocation special case**: if `<repo-trusted-reactor-list>` removes the consent reaction mid-loop, the COR-1618 re-verify before each git op fails-closed; treat as user override, abort, surface the issue number.

**Post-handoff rejection** (user rejects a panel-passed PR pre-merge or asks for revert post-merge): resume at phase 9 with the rejection treated as a new finding. If the rejection cites scope/architectural dimensions the panel missed, note the blind-spot in the rejection PR's commit message or body — the rejection itself is the artifact future plan-review prompts can grep for.

### CHG abandonment after R3+ reveals wrong approach

When 3+ rounds converge on "this approach is structurally wrong, not just buggy" (multiple reviewers flag the same architectural blocker in R3 that they raised in R1), do NOT loop indefinitely. Exit: draft a `## Lessons Learned` section in the CHG, set `Status: Rolled Back` (per COR-0002 allowed CHG status values), file a follow-up issue/CHG with the alternative approach, close the PR pointing at the follow-up. The rolled-back CHG stays as historical record.

### Wakeup tool unavailable / loop stop conditions

Per COR-1620 §Stop / failure conditions (cases a–f).

### Concurrent orchestrators

Two orchestrators racing for the same consent-eligible issue: best-effort claim-comment mechanism. Each orchestrator posts `🤖 Auto-pick claim: <id> at <ISO-8601>` on the tracking issue at branch-creation time, after re-polling for an existing claim within the last 10 minutes. If a recent foreign claim is found, abort and surface to user. Not transactional; 10-minute window is the tolerance for duplicate work safely undoable via `git branch -D`.

---

## Lineage

This SOP is the PKG-layer generalization of trinity's `TRN-1008-SOP-Multi-Agent-Review-Loop`. The original was iterated across PRs #66 → #73 (R1–R26) plus follow-up CHGs TRN-3029 (two-layer rocket-gate), TRN-3030 (SOP self-perpetuation via idle-with-retry + loop-restart), and TRN-3031 (merge-watch active-work cancellation). Full archaeology — *why each check is shaped the way it is* — lives in TRN-1008's change history in the trinity repo. Surfaced for promotion to PKG by the COR-1602 / COR-1615 prior-art alignment review on trinity PR #73 head a2589db (alfred#115).

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-09 | Initial version — umbrella SOP composing COR-1602 + COR-1615 + COR-1618/1619/1620/1621 + COR-1505 + COR-1104; generalized from trinity TRN-1008 (alfred#115) | Claude Opus 4.7 |
| 2026-05-09 | R4: §Phase 4 spec-format mapping rewritten — was `CHG/code/PRP` (different namespace from `<spec-format>` enum); now maps the four enum values (CHG, ADR, RFC, inline-PR-body) to COR-1608/1609 explicitly + clarifies that COR-1610 is selected by code-review-phase, not by spec form. Codex bot R3 P2 finding. | Claude Opus 4.7 |
| 2026-05-09 | R6: §Failure Modes "CHG abandonment" — `Status: Abandoned` is not in COR-0002's allowed CHG status enum (Proposed/Approved/In Progress/Completed/Rolled Back). Replaced with `Status: Rolled Back`. Codex bot R5 P2 finding (`af validate` would reject CHGs following the previous guidance). | Claude Opus 4.7 |
| 2026-05-09 | FXA-2277: `<fork-remote>` references renamed to `<pr-push-remote>` (4 sites — §Phases TOC, §Phase 7 routing row, §Phase 7 shell snippet, §Guard Rails). Semantic invariant preserved; only the name changed to accommodate single-remote adopters like alfred. | Claude Opus 4.7 |
| 2026-05-09 | R2 (PR #119): codex bot R1 P2 — §Phase 7 `gh pr create --head` form was hardcoded to `<gh-write-identity>:<branch>`, which works for fork-PR but breaks for single-remote topology where the branch lives on `<repo-owner>`'s repo. Snippet now documents both forms with topology-conditional comment; `--head <head-spec>` placeholder lets the adopter substitute. Routing-table row also updated. | Claude Opus 4.7 |
| 2026-05-10 | FXA-2283: Insert §Phase 11 (Retrospective) in reserved slot; renumber Loop restart §11→§12; update phase count (11→12), ASCII block, routing table, §Phase 10 cleanup line, §What Is It? description. Phase 11 is synchronous — 4 steps: metrics block (COR-1621 P0–P3), pattern check (project memory), CHG nomination (in-PR evidence, ≥2 rounds), hand off. | Claude Code |
| 2026-05-10 | FXA-2283 R2: Step 1 — add GitHub re-fetch instruction (Phase 8 session state unavailable in merge-watch wake turn); Step 3 — replace "session state" with "GitHub PR evidence re-fetched in Step 1"; update COR-1200 §Scoring note (PR #138 shipped). | Claude Code |
| 2026-05-10 | FXA-2283 R3: Step 1 — expand re-fetch instructions: explicit jq R-count command + single-commit-per-round assumption; COR-1615 §Commands three fetch endpoints named; COR-1621 triage re-apply instruction; Late-catch and Trinity-miss derivation rules. Step 3 note: "interim default" → "remains the default". | Claude Code |
| 2026-05-10 | §Phase 7: tighten `Closes #<issue>` prescription — the token must be a bare `verb + #N` match for GitHub's auto-linker regex; any intervening words ("Closes routing gap from issue #126", "Closes issue #127") silently disable auto-close on merge. Added the regex inline + a `gh pr view <N> --json closingIssuesReferences` verify step that fires before merge instead of after, so the post-merge "manually close" recovery path is no longer necessary. Evidence: alfred PR #130 (issue #126 stayed open after merge with the first phrasing) and PR #131 (issue #127 with the second phrasing). | Claude Opus 4.7 |
| 2026-05-10 | FXA-2283 R5: §Phase 11 Step 1 R-count command — `gh pr view #<N>` → `gh pr view <N>` with note that `#` after whitespace starts a POSIX comment and drops the argument. Codex bot R4 P2 finding. | Claude Code |
| 2026-05-10 | FXA-2283 R6: §Phase 11 Step 1 — R-count note updated: commit count is accurate only when one-commit-per-round guard rail holds; if admin-only commits precede a review request, adjust manually (codex bot R5 P2 / Thread 5). Trinity-miss/codex-catch definition updated: requires panel findings posted as GitHub review comments; if panel ran in-session via Skill(trinity), output `n/a — panel findings not GitHub-accessible` (Thread 6). Emit template updated to allow `n/a`. | Claude Code |
| 2026-05-10 | FXA-2283 R7: §Phase 11 Step 1 R-count — "adjust manually" expanded with method hint (inspect commit messages/timestamps, subtract admin-only commits). GLM advisory A4. | Claude Code |
| 2026-05-10 | FXA-148 R1: §Failure Modes — "Retry once" → "Retry per `<cli-retry-attempts>` (default 3 per COR-1622 §Resilience)"; "if it still fails" → "if all attempts fail". Parameterizes the hardcoded retry count to defer to COR-1622. GLM/DeepSeek advisory on PR #147 R1. | Claude Sonnet 4.6 |
| 2026-05-10 | FXA-148 R2: §Failure Modes — also parameterize exhaustion action: "mark the provider unavailable for this round" → "apply `<cli-retry-on-failure>` (default `pause-and-ask`)"; N-1/dissenter guard-rail conditionalized to `mark-non-viable` branch only. GLM P1-B1 on PR #149 R1. | Claude Sonnet 4.6 |
| 2026-05-10 | FXA-148 R3: §Failure Modes — add `<cli-retry-backoff-seconds>` (default 600 s) between retry attempts; codex bot P2 Thread 2 on PR #149 R2. | Claude Sonnet 4.6 |
| 2026-05-10 | FXA-148 R4: §Failure Modes — expand failure-condition list to include "exits non-zero" and "uses a missing binary" (matching COR-1622 §Resilience trigger list); previously only timeout/non-2xx/malformed-JSON were listed, leaving CLI-specific failure modes outside the retry path. | Claude Sonnet 4.6 |
| 2026-05-10 | Issue #144: §Phase 8 — add §Round-count cap: three-tier logic (Case A converged / Case B extension / Case C hard stop) with parameters `<max-r-count>` (default 10), `<max-r-count-extension>` (default 3), `<convergence-severity>` (default advisory) defined in COR-1622 §R-count cap. Prevents unbounded iteration loops. | Claude Sonnet 4.6 |
| 2026-05-10 | Issue #144 R2: §Round-count cap — (1) Case C condition `==` → `≥` (GLM P0/DeepSeek P2: equality left R>hard-stop with no case firing); (2) reorder table to C→A→B to match evaluation priority; (3) update trailing note to include rationale for C-first ordering. | Claude Sonnet 4.6 |
| 2026-05-11 | PR #154 codex-bot Thread 1: wire COR-1506 quality gate into Phase 1 — Related header, routing table row 1, and phase flow (consent pass → COR-1506 check → scope-rank tree). Autonomous picks now explicitly apply the quality gate before the scope-rank tree. | Claude Sonnet 4.6 |
| 2026-05-17 | issue #166: tighten §Phase 1 User-driven trigger row — only phrases that name a target issue (e.g. `do <PREFIX>-<NNNN>`) qualify for bypass; non-naming phrases (`pick next issue`, `auto-pick`) become autonomous triggers and apply full COR-1618 + COR-1506. Reconciles §Phase 1 with COR-1618 §Normative Bypass Clause's strict definition. | Claude Opus 4.7 |
