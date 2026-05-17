# PRP-1507: Two-Worker TDD Dispatch

**Applies to:** All projects adopting COR-1500 (TDD) and COR-1617 (Multi-Agent Loop) with a coding-worker layer
**Last updated:** 2026-05-17
**Last reviewed:** 2026-05-17
**Status:** Approved
**Related:** COR-1500 (TDD Development Workflow — amended by this proposal), COR-1619 (Orchestrator vs Worker Dispatch — amended), COR-1622 (parameter schema — amended), COR-1617 §Phase 5 (dispatch routing — consumes the split), FXA-2276 (alfred PRJ REF — opts in via parameter)
**Reviewed by:** glm-5.1 (R6: 9.9), deepseek-v4 (R6: 9.0), minimax-m2.7 (R6: 9.55), codex-gpt-5.5 (R6: 9.6), gemini-3 (R6: 9.9) — quintet panel under COR-1602 + COR-1608 (PRP scoring rubric)

---

## What Is It?

An opt-in configuration for substantive code-bearing dispatches under the multi-agent loop: when a project sets `<test-writer-worker-agent>` distinct from `<worker-agent>` (a new optional COR-1622 parameter), the worker that writes the failing test (RED) and the worker that writes the implementation (GREEN) MUST be distinct agent instances unless the change falls into one of the enumerated opt-out classes. The proposal amends COR-1500 (TDD), COR-1619 (Dispatch), and COR-1622 (Schema); each amendment lands as its own CHG after this PRP is approved. Projects that leave the new parameter unset see no behaviour change — COR-1500 §AI-Assisted TDD Protocol Mandatory Rule #3 alone applies as today.

---

## Problem

COR-1500 §AI-Assisted TDD Protocol Mandatory Rule #3 forbids one agent from writing tests and implementation **simultaneously**, but is satisfied as long as the same agent writes them in two sequential turns. The single agent still holds the implementation design in working memory throughout the RED phase. Three structural risks follow:

1. **Implement-to-fit bias.** The test author is incentivised to write tests they know their planned implementation will pass — a self-fulfilling spec rather than an independent contract. Symptom: changing the implementation in obvious ways still keeps the test green.
2. **Weakened RED probing.** An agent already holding the GREEN design cannot author RED tests that probe edge cases the implementation will miss. Off-by-one, boundary, and error-path coverage degrades to whatever the implementer happened to consider.
3. **No cross-validation.** Without an independent test-writer, the orchestrator's verification (`pytest`, `ruff`, `af validate`) confirms tests pass — not that they constrain the right behaviour.

COR-1619's worker contract assumes a single `<worker-agent>`; COR-1617 §Phase 5 routes through that single lane; COR-1622 declares only the singleton `<worker-agent>` parameter. No PKG-layer surface today distinguishes test-writing capacity from implementation capacity.

User flagged this on 2026-05-17 during plan-review for CHG-2286 (`rules/FXA-2286-CHG-Explicit-UTF-8-For-Alfred-Document-IO.md`):

> "For the implementation, will there at least 2 sub-agents? one for writing all the tests code, one for implementation? if not, we should also improve this SOP globally....maybe for all development related SOPs to standardize this process."

The two-agent pattern is established practice in pair-programming literature ("ping-pong programming") and in several commercial multi-agent dev tooling stacks, but it is not codified in COR-1500 or COR-1619. The single-worker pattern is the silent default in every alfred PR shipped to date; the implement-to-fit risk has accumulated invisibly because no retrospective tooling can distinguish spec-derived from impl-derived tests after the fact.

---

## Scope

**In scope (v1):**

- A new "Worker assignment" sub-section in COR-1500 §Phase 1 (RED) declaring `test-writer ≠ implementer` as the rule for substantive code dispatches when the two-worker split is active (gated by the new `<test-writer-worker-agent>` parameter; OFF by default for non-adopters), with an enumerated opt-out list.
- A new rule in COR-1500 §Phase 2 (GREEN) constraining what the implementer worker is allowed to read.
- A new §Two-Worker TDD Dispatch sub-section in COR-1619 containing the handoff contract (commits, verification gates, worker-prompt boilerplate).
- A new branch in the COR-1619 §Decision Tree that asks "Two-worker TDD applicable?" before falling through to the existing single-worker tree.
- A new optional `<test-writer-worker-agent>` key in COR-1622's parameter schema, defaulting to the same value as `<worker-agent>` so non-adopters see no behaviour change.
- A PRJ-REF update for alfred (FXA-2276) opting into the split by setting `<test-writer-worker-agent>` to a distinct agent identifier; trinity's TRN-1008 may follow if it adopts.

**Out of scope (v1):**

- Mandating the two-worker split for non-code SOPs (docs, governance, metadata — single worker is fine; the bias mode does not apply).
- Choosing the specific worker provider for tests vs implementation. PRJ REFs decide; the PKG SOP only mandates that the two slots be distinct.
- Multi-worker patterns beyond two (e.g. test-writer + implementer + independent code-reviewer trio). The current evidence supports the two-worker split; three-worker would be a separate proposal with its own evidence.
- Backfilling the split onto in-flight PRs. The amendment applies only to new picks after the SOP lands; rolled-up retrospective coverage is not feasible.
- Code-review-panel changes. The panel is post-implementation and orthogonal to who authored the tests vs implementation.
- Automated detection of "test-writer also implemented" violations. The proposed enforcement is procedural / orchestrator-side; tooling-side detection is deferred until evidence shows procedural enforcement is insufficient.

---

## Proposed Solution

### COR-1500 §Phase 1 (RED) — new "Worker assignment" sub-section

Inserted between the existing "Rules:" block and "Test structure convention (Arrange-Act-Assert):".

> #### Worker assignment
>
> When the RED phase is dispatched to `<worker-agent>` (per COR-1619) AND the project's `<test-writer-worker-agent>` parameter is set to a value distinct from `<worker-agent>` (per COR-1622), the **test-writer worker** and the **implementer worker** for the GREEN phase MUST be distinct agent instances. "Distinct" means different model identifiers OR the same model with different `:instance` suffixes (e.g. `glm:writer` vs `glm:impl`).
>
> Scope of the constraint: the same agent identity MUST NOT author both the failing tests and the GREEN-phase implementation for the **same task**, regardless of session boundaries (a fresh session by the same agent for the same task does not satisfy the rule). The rule applies until the CHG/PR is merged; subsequent CHGs are new tasks with their own assignment.
>
> This rule subsumes COR-1500 §AI-Assisted TDD Protocol Mandatory Rule #3 ("Agent must not write test and implementation simultaneously"): a distinct-instance requirement is strictly stronger than the simultaneity ban.
>
> When `<test-writer-worker-agent>` is unset (or equal to `<worker-agent>`), the two-worker split is OFF for this project; Rule #3 alone applies. The rest of this sub-section assumes the split is ON.
>
> Opt out (use a single worker even when the split is ON; document the reason in the CHG `## Implementation Order` section):
>
> | Opt-out class | Why single-worker is safe |
> |---------------|---------------------------|
> | Trivial single-function fix ≤ `<worker-min-loc>` (default 30) | COR-1619 routes this to the orchestrator already, so no worker is dispatched at all. |
> | Refactor with pre-existing test coverage covering the changed surface | The existing tests are the spec; no new test authorship is needed. CHG must name the specific tests covering the change so the reviewer can assert adequacy. |
> | Config / metadata-only change | No behaviour change to test; implement-to-fit bias has nothing to bias. |
> | Characterization tests on legacy code | Tests capture *actual* behaviour, not desired behaviour; the bias mode does not apply. Same agent characterizes + refactors per COR-1500 §Characterization Tests (Legacy Code). |
> | Generated test scaffolding | Deterministic codegen (e.g. pytest parametrize expansion, hypothesis strategies emitted from a schema); no human / agent judgment in the test body, so no bias to cross-validate. |
> | Vendored code update with no behaviour change | Bumping a dependency / re-importing upstream code; the upstream tests are authoritative. |
>
> Any other opt-out is a CHG-level argument and must be reviewed by the plan-review panel. In opt-out cases the two-worker split does not apply for this dispatch; COR-1500 §AI-Assisted TDD Protocol Mandatory Rule #3 (no simultaneous test+impl by one agent) alone governs.

### COR-1500 §Phase 2 (GREEN) — new rule appended to "Rules:"

> - When the two-worker split is in effect (i.e. RED was dispatched to a distinct test-writer worker per Phase 1's "Worker assignment" sub-section), the implementer worker MUST NOT read the test-writer's structured report, prose commentary, or session transcripts. The implementer reads (a) the failing test files committed by the test-writer, (b) the CHG/PRP body, and (c) the production source tree being modified — i.e., the existing codebase under change. The constraint forbids only the test-writer's *commentary channel*; the test is the spec, and the source is the substrate. Commentary may leak the test-writer's intended implementation, defeating the cross-validation the split exists to provide.

### COR-1619 — new §Two-Worker TDD Dispatch sub-section

Inserted between §Worker Dispatch Contract and §Verification.

> ### Two-Worker TDD Dispatch
>
> When COR-1500 §Phase 1's "Worker assignment" rule applies (substantive code change, `<test-writer-worker-agent>` set distinct from `<worker-agent>`, no opt-out class matching), the orchestrator runs the following handoff contract instead of a single worker dispatch:
>
> 1. **Dispatch test-writer worker** (`<test-writer-worker-agent>`) with the COR-1619 §Worker Dispatch Contract items, plus:
>    - Spec pointer: the CHG/PRP path.
>    - Output constraint: failing tests only — NO implementation, NO stubs in production source.
>    - Verification commands: `<test-runner> <test-paths>` MUST report failures (RED).
>    - Push/commit constraint: do NOT push or commit; report files modified.
>    - *Enforcement note:* the push/commit constraint is orchestrator-trust-based; the dispatch backend may not enforce read-only mounts or commit-blocking flags. Orchestrator detects violations post-dispatch by comparing the worker's reported file list against `git status --porcelain` after the dispatch returns (since both workers commit through the orchestrator's identity, `git log --author=` does not differentiate them). **On detection of a violation** (worker modified production source files outside the reported list, or wrote files outside the test paths): orchestrator runs `git restore` on the off-list paths, surfaces the violation in the dispatch log + CHG `## Implementation Order`, and re-dispatches the test-writer with the violation as explicit feedback. Repeated violations (≥2 from the same worker on the same task) escalate per step 2's retry cap.
> 2. **Orchestrator verifies** the tests fail on current HEAD by re-running `<test-runner>`. If any new test passes (i.e., the test does not actually fail on the un-implemented code), reject the test-writer's work and re-dispatch with the specific failing assertion as feedback. **Maximum 2 re-dispatches** of the test-writer per task; on the third failed attempt, escalate: the orchestrator either authors the test inline (only if the test fits the ≤ `<worker-min-loc>` single-function rule per COR-1619) or routes back to plan-review with a spec-ambiguity finding.
> 3. **Orchestrator commits** the test files with prefix `test:` per COR-1500 §Commit Strategy Option A.
> 4. **Dispatch implementer worker** (`<worker-agent>`) with the COR-1619 §Worker Dispatch Contract items, plus:
>    - Spec pointer: the CHG/PRP path PLUS the failing-test commit SHA (so the implementer can `git show` the tests).
>    - Reading constraint: do NOT read the test-writer's structured report or any worker-output channel; the failing tests, CHG/PRP body, and existing production source are the only inputs.
>    - **Test-file edit constraint**: the implementer MUST NOT modify, delete, weaken, or skip any test file the test-writer committed in step 3. The implementer MAY add NEW test files (different paths from the test-writer's commit) that exercise the implementation's internal scaffolding, but these new tests are advisory and do NOT replace the test-writer's tests as the cross-validation surface. If the implementer believes a test-writer test is incorrect, the implementer reports the issue in its structured output and the orchestrator routes to step 2's escalation (re-dispatch test-writer or plan-review spec-ambiguity) — the implementer does not unilaterally fix it.
>    - Verification commands: `<test-runner>` MUST report all green (including tests the test-writer added — verify they are present and passing, not removed or skipped).
>    - *Enforcement note:* orchestrator runs `git diff <test-writer-commit> -- <test-writer-paths>` (where `<test-writer-paths>` is the exact file list the test-writer committed in step 3, not a broader glob) after the implementer's dispatch returns; any non-empty diff on those specific paths fires the test-file edit constraint violation handling (`git restore <test-writer-paths>` to the test-writer commit, surface the violation, re-dispatch implementer with the violation as explicit feedback). Implementer-added test files at OTHER paths are NOT subject to the diff check — they are advisory and stay on the branch.
> 5. **Orchestrator verifies** all tests pass by re-running `<test-runner>` plus the standard verification gates (`<linter>`, `<formatter> --check`, `af validate --root .`). Triage of any failures:
>    - Test added by test-writer fails on implementer's commit → re-dispatch implementer with the specific failing test name. Same 2-retry cap as step 2; on third failure, escalate to plan-review for spec ambiguity.
>    - Test in an unrelated module fails (regression in pre-existing code) → orchestrator triages per COR-1621: if scope is single-function and within `<worker-min-loc>`, orchestrator fixes inline; otherwise re-dispatch implementer with the regressed test paths added to the spec pointer. Do NOT silently skip / xfail the regression.
> 6. **Orchestrator commits** the implementation with prefix `feat:` / `fix:` per COR-1500 §Commit Strategy Option A.
> 7. **Refactor pass** (Phase 3 of COR-1500): the **implementer worker** runs the refactor by default per §Decisions item 2; the orchestrator may substitute only when the post-refactor diff fits the ≤ `<worker-min-loc>` single-function rule per COR-1619. The test-writer does NOT run the refactor in v1 (this preserves test-writer independence for the next cycle: the test-writer never sees the GREEN implementation, keeping its edge-case-probing posture for future tasks on the same module). During refactor only, the **reading constraint** of step 4 is lifted — the refactorer MAY read any artifact produced in this dispatch (tests, implementation, commentary), since the cross-validation served its purpose at GREEN. The **test-file edit constraint** of step 4 persists with a narrow carve-out: the refactorer MAY reorganise test structure (rename helpers, extract fixtures, reorder imports) but MUST NOT (a) weaken, remove, or skip any assertion from the test-writer's tests, (b) move tests between files (file-path changes alter test node IDs, which break the test-name-set check below and hide weakening behind movement), or (c) rename test functions in ways that change tested semantics.
>
>    **Enforcement is two-tier, because semantic weakening cannot be reliably detected by automation:**
>    - *Tier 1 (automated, fast)*: orchestrator runs `<test-runner>` with `--collect-only` (or equivalent) before and after the refactor and compares the test-name-set (qualified `file::class::test_name` IDs). Any removed test name, any test-name-set difference at all (additions OR removals), and any reduction in pass-count fires the violation handler immediately: revert refactor, re-dispatch implementer with explicit feedback. This catches removed tests, moved tests (file-path changes), and renamed tests — but does NOT catch in-place assertion weakening (same test name, same pass count, weakened assertion still passes).
>    - *Tier 2 (human review, surfaced in PR body)*: orchestrator emits the per-file diff under `<test-writer-paths>` in the CHG `## Implementation Order` AND in the PR body under a `### Refactor test-file changes` heading. The plan-review panel and code-review bot are explicitly asked to scan this diff for assertion weakening. This is a documented enforcement gap: in-place assertion weakening is detectable only by reading the diff, not by running tests. The PR is gated on Tier 2 reviewer attention; CHGs SHOULD NOT merge with Tier 1 green if Tier 2 review was skipped.
>
>    Subsequent cycles re-apply the test-writer/implementer separation from step 1.
> 8. **Phase 8 (Iterate) re-dispatch routing.** When COR-1617 §Phase 8 surfaces a new finding requiring code (bot review comment, CI failure, panel finding), the orchestrator decides between four mutually exclusive cases:
>    - **(a) New test+implementation pair needed** (e.g., reviewer asks "add a test for the empty-input edge case and handle it") → re-enter this contract from step 1 with the new scope. Test-writer authors the new failing test; orchestrator commits it per step 3 with `test:` prefix. Orchestrator runs `<test-runner>` locally on the just-committed test; **if the test fails** (expected RED — the implementation does not yet cover the requested behaviour), continue to step 4 to dispatch implementer (which produces a `feat:`/`fix:` commit per step 6); **if the test unexpectedly passes** (the existing implementation already covers the requested behaviour, so the new test is additive coverage rather than a new behavioural constraint), skip implementer dispatch entirely — the test-writer's step-3 `test:` commit is the final commit for this iteration, no implementation commit is produced, and the iteration is done. This local-run gate exists because additive-coverage requests are common in PR review and forcing a redundant implementer round-trip burns latency and risks hallucinated changes.
>    - **(b) Implementation-only fix to satisfy existing tests** (e.g., CI failure on a test the test-writer already authored; reviewer asks to fix a regression flagged by an existing test) → if the fix scope is ≤ `<worker-min-loc>` lines in a single function per COR-1619's single-function rule, the orchestrator handles inline (no worker dispatch); otherwise dispatch implementer worker only, with the failing test name as feedback. No new test authorship, so no test-writer dispatch. This matches step 5's precedent (small-scope regression fix routes through the orchestrator; larger fixes route through the implementer).
>    - **(c) Test-only edit to existing tests** (e.g., reviewer asks to tighten an assertion) → dispatch `<test-writer-worker-agent>` to author the edit. Orchestrator commits the edit per step 3 with `test:` prefix. Orchestrator runs `<test-runner>` locally on the just-committed test; **if the test fails on the current implementation** (the tightening surfaces a real defect or imposes a new constraint), dispatch implementer per step 4 (which produces a `feat:`/`fix:` commit per step 6); **if the test still passes** (the edit is a clarification or additive assertion that current code already satisfies), skip implementer dispatch — the test-writer's step-3 `test:` commit is the final commit for this iteration, no implementation commit is produced, and the iteration is done.
>    - **(d) Documentation / comment / config-only fix** → orchestrator handles directly per COR-1619's existing tree (no worker dispatch needed).
>    Each iteration round is logged in the CHG `## Implementation Order` with the case (a/b/c/d) selected, the local-run gate outcome (for a/c), the orchestrator-inline-vs-worker decision (for b), and the rationale. Cases (a) and (c) re-apply the §Worker assignment rule for the test-writer; the implementer is dispatched only when the local-run gate confirms a real failure. Case (b) is a degenerate single-worker dispatch when above the inline threshold, or orchestrator-direct when below. Case (d) bypasses worker dispatch entirely.
>
> **Worker unavailability fallback.** Two symmetric branches per COR-1622 §Resilience retry policy when `<cli-retry-on-failure>` is `mark-non-viable`:
>
> - **Test-writer outage** (`<test-writer-worker-agent>` CLI fails before step 3 commits): orchestrator authors the tests inline (effectively `test-writer = orchestrator` for this dispatch) if the test surface fits the ≤ `<worker-min-loc>` single-function rule per COR-1619; otherwise the dispatch is paused, the orchestrator surfaces the outage in the CHG `## Implementation Order`, and the loop arms a 1800 s wake per COR-1620 to retry the worker.
> - **Implementer outage** (`<worker-agent>` CLI fails after step 3 commits the test-writer's tests but before step 6): the test-writer's failing-test commit stays on the branch (it is already pushed in the orchestrator-commits-after-step-3 path; or held locally if not yet pushed — orchestrator records which case applies). Orchestrator falls back to authoring the implementation inline only if the implementation surface fits the ≤ `<worker-min-loc>` single-function rule per COR-1619; otherwise the dispatch is paused, the test-writer's commit remains (do NOT revert it — it is already validated cross-spec by the test-writer), the orchestrator surfaces the outage, and the loop arms a 1800 s wake per COR-1620 to retry the worker. **Refactor-phase outage** (both workers fail at step 7): orchestrator runs the refactor inline if the diff fits the ≤ `<worker-min-loc>` rule; otherwise the refactor is deferred to a follow-up CHG (the GREEN implementation already shipped a passing test suite).
>
> All fallbacks MUST be recorded in the CHG `## Implementation Order` section and surfaced in the PR body. Falling back does NOT alter the §Worker assignment rule for future dispatches.
>
> **Cost note.** Two-worker dispatch roughly doubles per-task worker latency and token cost vs single-worker (one test-writer round-trip + one implementer round-trip in series, vs one combined round-trip). The PRP §Validation plan tracks defect-density and panel-review findings vs the single-worker baseline; if no measurable benefit appears after the first three two-worker dispatches, the default is revisited per a follow-up CHG.

### COR-1619 §Decision Tree — insertion patch

Replace the existing `A[Implementation task] --> B{Generated file regen only?}` head of the tree with two new gating nodes; the rest of the existing tree (`B`, `MIX`, `H0`, `H`, `C`, `D`, `E`, `F`, `G`, plus all leaf nodes) is unchanged.

> ```mermaid
> flowchart TD
>     A[Implementation task] --> P{"&lt;test-writer-worker-agent&gt;<br/>set distinct from<br/>&lt;worker-agent&gt;?"}
>     P -- No --> B{Generated file regen only?}
>     P -- Yes --> TW{Two-worker TDD applicable?<br/>(substantive code, no opt-out class matches)}
>     TW -- Yes --> TW1[TWO-WORKER TDD<br/>see §Two-Worker TDD Dispatch]
>     TW -- No --> B
>     B -- Yes --> O1[ORCHESTRATOR<br/>run the generator]
>     B -- No --> MIX{Mixed code+doc?}
>     %% existing tree continues unchanged from MIX onward
> ```

Node `P` is the parameter gate (skipped entirely when `<test-writer-worker-agent>` is unset / equal to `<worker-agent>`, leaving the original tree behaviour intact). Node `TW`'s "No" branch is taken when an opt-out class from COR-1500 §Phase 1 matches. The CHG-C2 implementation MUST preserve every existing node from `MIX` onward verbatim — the `%% existing tree continues` comment is illustrative; the actual amended mermaid block re-includes the full existing chain (`MIX → H0 → H → C → D → E → F → G` plus leaves `O1/O2/O3/O4/W1/W2/W3/W4`).

### COR-1622 — new optional `<test-writer-worker-agent>` key

Added under §Worker dispatch (COR-1619). Column shape matches the existing COR-1622 schema rows verbatim: `Key | Type | Required | Default | Description`.

> | Key | Type | Required | Default | Description |
> |-----|------|----------|---------|-------------|
> | `<test-writer-worker-agent>` | string | no | same value as `<worker-agent>` | Distinct agent instance for the RED-phase test-writer per COR-1500 §Phase 1 Worker assignment. When unset (or equal to `<worker-agent>`), the two-worker split is OFF for this adopter and COR-1500 §AI-Assisted TDD Protocol Mandatory Rule #3 alone applies. Adopters opt in by setting this to a different model OR the same model with a different `:instance` suffix. **Adopters using the same model with different `:instance` suffix MUST verify with their dispatch backend that the suffix produces a fresh context (no shared KV cache / session state); if not verified, default to different-model differentiation.** |

The default-to-`<worker-agent>` shape preserves backwards compatibility — every existing adopter sees identical behaviour until they explicitly set the key to a distinct value. Non-adopters continue under COR-1500 §AI-Assisted TDD Protocol Mandatory Rule #3 only.

**On naming.** Verbose `<test-writer-worker-agent>` chosen over shorter alternatives (`<test-worker-agent>`, `<red-worker-agent>`) for semantic precision: the slot is specifically a *writer* of tests (RED-phase author), not a generic test-related worker that might also include test runners or coverage tooling. The verbosity cost is paid once per PRJ REF; reader clarity is paid every time the schema is consulted.

### FXA-2276 (alfred PRJ REF) — new row under §Worker dispatch

| Key | Alfred value | Notes |
|-----|--------------|-------|
| `<test-writer-worker-agent>` | `trinity-deepseek via droid exec` (proposed) | Distinct from `<worker-agent>: trinity-glm`. Deepseek selected as test-writer because (a) its prior PR reviews show strong edge-case probing on alfred PRs #117 / #154, and (b) it is not the implementer, so cross-validation holds. Re-evaluate after first 3 dispatches per §Validation below. |

---

## Decisions

All design questions resolved in v1; deferred follow-on work is enumerated below each decision with a concrete trigger condition.

1. **Provider pairing for alfred — Decision: `<test-writer-worker-agent> = trinity-deepseek`, `<worker-agent> = trinity-glm`.** Deepseek selected as test-writer because (a) its prior PR reviews on alfred PRs #117 / #154 demonstrate strong edge-case probing, and (b) it is not the implementer, so cross-validation holds. *Re-evaluation trigger* (for a follow-up CHG, not an open question): any of the first 3 dispatches recorded in §Validation surfaces evidence of weak edge-case probing OR a panel-review finding attributable to test-writer bias.
2. **Refactor-phase assignment — Decision: implementer worker runs refactor by default; orchestrator override only when the post-refactor diff fits the ≤ `<worker-min-loc>` single-function rule.** Implementer-as-refactorer-default keeps the test-writer's independence for the next cycle (the test-writer never sees the GREEN implementation, preserving its edge-case-probing posture for future tasks on the same module). *Re-evaluation trigger*: a retrospective shows refactor-phase choices producing measurable test-writer bias on subsequent dispatches.
3. **Two-Worker default — Decision: v1 ships with opt-in (`<test-writer-worker-agent>` defaults to same value as `<worker-agent>`; split is OFF for non-adopters).** Flipping the default to "set distinct unless explicitly equated" is out of scope for v1. *Re-evaluation trigger*: a follow-up PRP after 6 months of alfred-and-trinity adoption telemetry shows the split's cost is offset by defect reduction across ≥ 80% of adopting dispatches.
4. **Parameter naming — Decision: `<test-writer-worker-agent>`.** Verbose name chosen over `<test-worker-agent>` / `<red-worker-agent>` for semantic precision (the slot is specifically a *writer* of tests, not a generic test-related worker). The verbosity cost is paid once per PRJ REF; reader clarity is paid every time the schema is consulted. *Re-evaluation trigger*: ≥3 adopters report the name as a usability barrier in their PRJ REFs.

§Validation logs the data that feeds the re-evaluation triggers.

---

## Open Questions

None — all design questions resolved in §Decisions above. The re-evaluation triggers under each decision identify future-CHG scope, not unresolved questions in this PRP. Per COR-1102's Hard Gate ("All Open Questions must be resolved before review begins"), this PRP enters review with an empty open-questions surface.

---

## Validation

After the SOP amendments land, the orchestrator under FXA-2276 SHALL accumulate the first **three** two-worker dispatches in this section. If a candidate CHG matches an opt-out class (per §Phase 1 opt-out table) or triggers a worker-unavailability fallback (per §Two-Worker TDD Dispatch fallback), record its CHG ID + opt-out class / fallback reason in the log below and continue picking until three two-worker dispatches accumulate.

Per-dispatch record:

```
Dispatch N:
- CHG: <FXA-NNNN-CHG-…>
- Mode: two-worker | opt-out (<class>) | fallback (<reason>)
- Test-writer commit SHA: <…>           [two-worker only]
- Test-writer worker: trinity-deepseek  [two-worker only]
- Implementer commit SHA: <…>
- Implementer worker: trinity-glm
- Test outcomes: <RED tests N; GREEN passed N; refactor pass green>
- Retrospective notes: <implement-to-fit detected? RED edge-case coverage vs single-worker baseline? hand-off friction? latency delta?>
```

The first three two-worker dispatches feed back into:
- Decision 1's re-evaluation trigger (provider pairing for alfred — does deepseek as test-writer actually probe edge cases better than alternatives?).
- Decision 2's re-evaluation trigger (refactor-phase assignment — does implementer-as-refactorer-default produce measurable test-writer bias on subsequent dispatches?).
- Decision 4's re-evaluation trigger (parameter naming — do operators stumble on `<test-writer-worker-agent>` in their PRJ REFs?).

Decision 3's long-term-default-flip trigger (6 months of cross-project adoption telemetry, ≥80% defect-reduction-offsets-cost evidence) is a SEPARATE re-evaluation track from the first-three-dispatches gate — Decision 3 governs the **PKG-layer global default** across all adopters, while this §Validation log governs **alfred's project-level opt-in**. If after three two-worker dispatches the split shows no measurable benefit at the alfred project scope (RED probing strength flat; same defects caught in code-review; no detected impl-to-fit divergence; latency cost not offset by defect reduction), revisit alfred's opt-in (FXA-2276 row removal) in a follow-up alfred CHG; the PKG default remains opt-in for other adopters per Decision 3.

---

## Implementation Plan

Each amendment lands as its own CHG (single-surface per atomicity discipline per CLD-1802 / COR-1400):

1. **CHG-A**: amend COR-1500 §Phase 1 (RED) — add "Worker assignment" sub-section + opt-out table.
2. **CHG-B**: amend COR-1500 §Phase 2 (GREEN) — append the "implementer reads tests + CHG + source only" rule.
3. **CHG-C1**: amend COR-1619 — add §Two-Worker TDD Dispatch sub-section (handoff contract + fallback + cost note).
4. **CHG-C2**: amend COR-1619 — insert the new top-level "Two-worker TDD applicable?" branch in §Decision Tree (separate CLD-1802 surface from C1: the decision-tree mermaid block is a distinct heading region from §Worker Dispatch Contract).
5. **CHG-D**: amend COR-1622 — add `<test-writer-worker-agent>` schema row.
6. **CHG-E**: amend FXA-2276 — opt alfred in by setting `<test-writer-worker-agent>` and document the deviation rationale.

Dependency order: A and B may land in parallel; C1 and C2 may land in parallel (independent surfaces); D depends on no other; E depends on D being merged first (E references the new schema row), AND should land after issue #166's reconciliation CHG (which removes the FXA-2276 §Adoption Status Phase 1 deviation note); otherwise CHG-E's new schema-row addition may conflict with #166's edit-set at merge time. Bundling CHGs A, B, C1, C2, D into one PR (five CHGs in one PR) is acceptable since each CHG is independently atomic, but the PR description must list each CHG separately and the reviewer should confirm per-CHG atomicity.

The first end-to-end two-worker dispatch (per §Validation) lands on the **next code-bearing CHG** picked under FXA-2276 after CHGs A–E merge; it is not a separate deliverable of this PRP.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-17 | Initial version — drafted under FXA-2276 looping mode in response to issue #171. PKG-layer PRP at COR-1507 chosen as first available slot in the COR-1500 (TDD) series. | Claude Opus 4.7 |
| 2026-05-17 | R2: plan-review panel (glm + deepseek + minimax) — all FIX. Address blockers: (a) DeepSeek P0 — COR-1500 "MUST" vs COR-1622 "OFF when unset" contradiction → §Phase 1 now gates on `<test-writer-worker-agent>` being set distinct, with explicit Rule #3-only fallback when off; (b) DeepSeek P0 — implementer reading constraint forbade production source → §Phase 2 + §C step 4 now explicitly allow source tree; (c) DeepSeek P1 — unbounded test-writer re-dispatch → §C step 2 caps at 2 re-dispatches with escalation; (d) DeepSeek P1 — unrelated test regressions unspecified → §C step 5 adds COR-1621 triage routing; (e) MiniMax P0 — CHG-C bundled two CLD-1802 surfaces → split into CHG-C1 (sub-section) + CHG-C2 (decision tree branch); (f) MiniMax P1 — refactor-phase reading ambiguity → §C step 7 explicitly lifts reading constraint for refactor only; (g) GLM P0 — "within the same session" vs OQ3 task-scoped resolution → §Phase 1 now reads "for the same task, regardless of session boundaries"; OQ3 retired (resolution applied in body). Fold convergent advisories: cost trade-off note (GLM+DeepSeek P2), worker-unavailability fallback (DeepSeek P2), Rule #3 compatibility sentence (DeepSeek P2), additional opt-out classes — generated scaffolding, vendored code (DeepSeek P2), enforcement-mechanism note (GLM P3), §Validation fallback record clause (MiniMax P2), OQ4 instance-suffix verification requirement folded into COR-1622 schema row (MiniMax P2). Discount: GLM hallucinated "~50% of rounds" advisory (not in PRP text; flagged by GLM itself). | Claude Opus 4.7 |
| 2026-05-17 | R2.5: R2 panel passed (glm 9.9, deepseek 9.0, minimax 9.05) but advisories folded before R3 quintet escalation per user request. (a) GLM P2 — §Decision Tree mermaid omitted parameter-distinct gate → added explicit `P` node before `TW`; (b) GLM P3 — opt-out branch's Rule #3 applicability implicit → appended explicit "In opt-out cases ... Rule #3 alone governs" to §Phase 1 opt-out paragraph; (c) MiniMax P3 — CHG-E vs issue #166 cross-PR ordering → §Implementation Plan dependency-order paragraph now flags the #166 reconciliation CHG as an additional prerequisite for CHG-E. Other R2 P3 advisories (DeepSeek scope-summary skim risk, git-log-enforcement no-op, fallback rationale gap; GLM test-writer-mismatch failure mode, single-model instance-suffix edge case) carried forward as known limitations — non-blocking, addressable in the amendment CHGs. | Claude Opus 4.7 |
| 2026-05-17 | R3 quintet escalation (per user request — "important change"): added codex (GPT-5.5) + gemini (3) to the panel. R3 first reviews: codex FIX 8.9, gemini FIX 6.6. R3.5 revisions address all 7 blockers across both new reviewers: (a) Codex P1 — COR-1622 schema row column mismatch → row now matches verified COR-1622 column shape `Key \| Type \| Required \| Default \| Description`; (b) Codex P1 — mermaid `B -- No --> ...` would have deleted existing `MIX{Mixed code+doc?}` chain → mermaid now shows `B -- No --> MIX` with explicit "%% existing tree continues" marker plus prose instruction to preserve every node from `MIX` onward in CHG-C2; (c) Codex P1 — §C step 1 violation detection had no remediation → added explicit `git restore` + log + re-dispatch with retry-cap escalation, plus correction that `git log --author=` doesn't differentiate workers committing through orchestrator identity (use `git status --porcelain` and worker's reported file list instead); (d) Codex P1 — implementer test-file edit unconstrained → §C step 4 now has explicit Test-file edit constraint (MUST NOT modify/delete/weaken/skip test-writer's tests; MAY add advisory new tests; orchestrator runs `git diff <test-writer-commit> -- <test-paths>` for enforcement); (e) Gemini P0 — Hard Gate OQ resolution → §Open Questions converted to §Decisions with crisp v1 choices + re-evaluation triggers; §Open Questions section retained with explicit "None — all resolved in §Decisions"; (f) Gemini P0 — Phase 8 iteration routing gap → new §C step 8 with 4-case routing (new test+impl pair re-enters split; impl-only fix to existing tests = implementer-only; test-only edit re-enters from step 1 with test-writer; doc/config = orchestrator); (g) Gemini P0 — asymmetric fallback → §Worker unavailability fallback now has symmetric branches for test-writer outage, implementer outage, and refactor-phase outage; the test-writer's commit is preserved when implementer fails (not reverted). Codex P3 advisory: §Characterization Tests heading reference corrected to "Characterization Tests (Legacy Code)". Gemini naming flag: folded as Decision 4 (keep `<test-writer-worker-agent>` for semantic precision; re-evaluate after 3 adopter usability reports). Gemini validation-metrics advisory: §Validation per-dispatch record already captures qualitative + quantitative fields; no schema change needed in v1. | Claude Opus 4.7 |
| 2026-05-17 | R4 quintet: GLM PASS 9.9, DeepSeek PASS 9.0, MiniMax PASS 9.18 (no regression); Codex FIX 9.3, Gemini FIX 8.4 (new R3.5 self-contradictions + step 8(c) deadlock). R4.5 fixes: (a) Codex P1 + GLM P2 convergent — §C step 7 said "EITHER worker" contradicting §Decision 2 ("implementer by default") → step 7 rewritten to enforce implementer-as-refactorer-default with orchestrator override only on ≤ `<worker-min-loc>` diffs; (b) Codex P1 — §C step 4 "MAY add NEW tests" contradicted enforcement "any non-empty diff fires violation" → enforcement diff check now scopes to `<test-writer-paths>` (exact file list from test-writer's commit, not a broader glob); new test files at OTHER paths are advisory and skip the diff check; (c) GLM P2 — §C step 7 didn't address whether test-file edit constraint persists through refactor → step 7 now explicitly states the edit constraint persists with narrow carve-out for structural reorganization (rename helpers, extract fixtures, reorder imports, move tests between files) but NOT weakening/removing assertions; relaxed enforcement uses test-pass-count + test-name-set comparison instead of literal diff; (d) Gemini P0 — §C step 8(c) state-machine deadlock (additive-coverage test that already passes would be unconditionally rejected by step 2's RED-must-fail gate) → cases (a) and (c) now have an explicit "local-run gate" after the test-writer's commit: if the test fails on current implementation (RED), proceed to implementer dispatch; if the test unexpectedly passes (additive coverage of behaviour already implemented), skip implementer entirely, commit, and the iteration is done; (e) Gemini P1 — redundant implementer dispatch when test already passes → solved by same local-run gate in (d); (f) Codex P2 — §Decision 3 (long-term default flip after 6 months) wasn't aligned with §Validation's "revisit the default" language (first-three-dispatches scope) → §Validation now distinguishes Decision 3's PKG-global-default track from alfred's project-level opt-in revisit; (g) Convergent advisory across GLM+DeepSeek+MiniMax (3/5) — §Validation still referenced retired "Open Question 1/2/3" labels → renamed to "Decision 1/2/3" with explicit cross-reference to each Decision's re-evaluation trigger. R4 P3 advisories carried forward: §Scope wording polish (DeepSeek), §C step 8(c) implementer re-entry state (DeepSeek), orchestrator-inline fallback loses cross-validation (DeepSeek), §Problem alfred-specific empirical evidence (GLM), Decision 4 / COR-1622 naming rationale redundancy (GLM). All five are non-blocking and addressable in amendment CHGs. | Claude Opus 4.7 |
| 2026-05-17 | R5 quintet: GLM PASS 9.9, DeepSeek PASS 9.0, MiniMax PASS 9.25, Gemini PASS 9.8 (4/5 PASS); Codex FIX 9.3 with 2 NEW R4.5 P1 blockers. R5.5 fixes: (a) Codex P1 + Gemini/DeepSeek/MiniMax convergent advisory (4/5 reviewers) — §C step 8(a)/(c) "skip implementer dispatch entirely, commit per step 6" routed test-only iterations through step 6's `feat:`/`fix:` commit path, wrong prefix → step 8 now explicit: in the local-run-gate-pass path, the test-writer's step-3 `test:` commit IS the final commit for the iteration, no step-6 commit happens; pre-existing step-3 commit happens BEFORE the local-run gate (not after), so the gate operates on the already-committed test; (b) Codex P1 — §C step 7 refactor enforcement (test-pass-count + test-name-set) cannot detect in-place assertion weakening AND false-positives on allowed file moves → step 7 enforcement reworked into two tiers: Tier 1 (automated) catches removed/moved/renamed tests via `<test-runner> --collect-only` name-set comparison + pass-count check (and now FORBIDS file moves since they alter test node IDs, removing the false-positive); Tier 2 (human review) explicitly surfaces the per-file test diff in the PR body under `### Refactor test-file changes` heading for plan-review panel + code-review bot scan; the SOP explicitly acknowledges in-place assertion weakening is detectable only by reading the diff, and gates CHG merge on Tier 2 attention; (c) Gemini P3 — §C step 8(b) unconditionally dispatched implementer → added orchestrator-inline-fix optimization (≤ `<worker-min-loc>` single-function fix routes through orchestrator, matching step 5's precedent). R5 P3 advisories carried forward: §C step 1 off-list paths clarification (Codex), §C step 8(b) examples expansion to include linter/formatter/type-check failures (Codex), test-runner output-format details for tier 1 enforcement (DeepSeek), orchestrator-inline-author dispatch-log flag (DeepSeek). All four are non-blocking and addressable in amendment CHGs. | Claude Opus 4.7 |
| 2026-05-17 | R6 quintet: **ALL 5 PASS** (GLM 9.9, DeepSeek 9.0, MiniMax 9.55, Codex 9.6, Gemini 9.9; mean 9.59). All R5 blockers closed; no new blockers; no R5.5 regressions. Carried-forward P3 advisories (alfred-specific §Problem evidence; Decision 4 ↔ COR-1622 naming redundancy; §C step 1 off-list paths clarification; §C step 8(b) examples expansion to include linter/formatter/type-check failures; test-runner output-format spec for Tier 1; orchestrator-inline-author dispatch-log flag; Tier 2 MUST-level PR-body checklist upgrade) are addressable in the amendment CHGs (A through E) rather than blocking PRP approval. Status updated Draft → Approved. PRP enters implementation phase: file CHGs A/B/C1/C2/D bundled to one PR; CHG-E lands separately after D + issue #166 reconciliation merge. | Claude Opus 4.7 |
