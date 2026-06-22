# PRP-2308: Evolve Engine SOP Refactor

**Applies to:** FXA project
**Last updated:** 2026-06-21
**Last reviewed:** 2026-06-21
**Status:** Draft
**Related:** FXA-2146, FXA-2148, FXA-2149, FXA-2307, GitHub issue #234, GitHub PR #235
**Reviewed by:** Claude Code R4, Codex R4, Trinity GLM R4, Trinity MiniMax R3, Trinity DeepSeek R3

---

## What Is It?

Design proposal for GitHub issue #234:

<https://github.com/frankyxhl/alfred/issues/234>

Extract the duplicated Evolve-SOP / Evolve-CLI workflow skeleton into a new parameterized `Evolve-Engine` SOP, then rewrite `FXA-2148` and `FXA-2149` as compact public entry-point SOPs.

The refactor must preserve the operational behavior of the two evolve loops while adding two rigor requirements to the shared engine:

- signal provenance and trustworthiness during Signal collection;
- concrete supporting examples plus self-skepticism rating during Candidate generation.

Issue #233 is complete via PR #235, merge commit `2485957e941899ca84486e4b0123eeba11fa071c`, so issue #234 can rely on the usage-ledger foundation delivered there.

---

## Problem

`FXA-2148-SOP-Evolve-SOP.md` and `FXA-2149-SOP-Evolve-CLI.md` share the same 9-phase skeleton:

1. Phase 0: Guard checks.
2. Phase 1: Create run log.
3. Phase 2: Collect signals.
4. Phase 3: Generate candidates.
5. Phase 4: Evaluate candidates.
6. Phase 5: Implement.
7. Phase 6: Git / PR.
8. Phase 7: Post-push review loop.
9. Phase 8: Completion checklist.

They differ in instance parameters and a few behavior details:

- signal sources and source roots;
- prerequisites and skip conditions;
- evaluator weight table from `FXA-2146`;
- hard gate;
- implementation mode;
- mutation guard;
- candidate execution cardinality;
- no-op run-log disposition;
- completion checklist rows;
- post-push workflow loop step numbers.

The duplication conflicts with `FXA-2146`'s "Compression as Intelligence" principle and will get worse if a third evolve variant is added later.

The current evolve process also has two rigor gaps:

- signals can be scored without an explicit provenance/trustworthiness check;
- candidate conclusions can be generated without citing concrete supporting examples.

Current compression baseline must be measured with:

```bash
wc -l -w rules/FXA-2148-SOP-Evolve-SOP.md rules/FXA-2149-SOP-Evolve-CLI.md
```

Baseline from the pre-refactor branch:

- `FXA-2148`: 176 lines / 1538 words.
- `FXA-2149`: 170 lines / 1389 words.
- Combined current instance docs: 346 lines / 2927 words.

---

## Proposed Solution

### New Engine SOP

Create the shared engine as:

`FXA-2309-SOP-Evolve-Engine.md`

The engine owns the shared 9-phase workflow:

- guard checks;
- run log creation;
- Signal phase;
- Candidate phase;
- Evaluate phase;
- Implement phase;
- Git / PR;
- post-push review loop;
- completion checklist.

The engine must reference `FXA-2146` thresholds and weights by source, not duplicate them as a competing source of truth. Threshold wording may quote the current values only as non-normative examples; `FXA-2146` remains authoritative.

### Public Entry-Point SOPs

Keep `FXA-2148` and `FXA-2149` as public SOP entry points. They must retain the required SOP sections and enough `Steps` content for `af plan FXA-2148` and `af plan FXA-2149` to remain useful.

This PRP does not add engine-resolution tooling to `af plan`. Therefore each instance must keep a short phase-level wrapper checklist in `Steps`, delegate detailed repeated prose to `FXA-2309`, and list the instance parameters needed to execute the engine.

Behavior equivalence is judged by the executable documented procedure and wrapper checklist, not by requiring `af plan` to inline expanded engine steps automatically.

### Engine Parameter Contract

The engine must support these instance parameters:

- `instance_id`;
- `entry_sop_acid`;
- `prerequisites`;
- `skip_conditions`;
- `signal_sources`;
- `source_roots`;
- `weight_table_ref`;
- `hard_gate`;
- `implementation_mode`;
- `candidate_cardinality`;
- `phase_conditional_substeps`;
- `workflow_loop_spec`;
- `escalation_target_gate`;
- `noop_disposition`;
- `branch_name_pattern`;
- `pr_body_template`;
- `completion_checklist_rows`;
- `mechanical_fix_boundary`;
- `mutation_guard`;
- `working_directory_overrides`.

`implementation_mode` is a Phase 5 sub-template selector, not a catch-all. `candidate_cardinality`, `phase_conditional_substeps`, `escalation_target_gate`, `noop_disposition`, `completion_checklist_rows`, and `working_directory_overrides` must remain separate parameters.

The instance declarations must explicitly preserve:

- `FXA-2148`: optional experience-axis signal step, PRP/CHG document lifecycle, implement each passing candidate, `af validate` hard gate, no-op run log left uncommitted in the working tree.
- `FXA-2149`: current top-level repo layout, pytest/ruff/coverage signal steps, TDD red/green/refactor, implement top candidate only, pytest + ruff hard gate, README check row, no-op run log committed and pushed to `main`.

### Thin Instance Targets

Rewrite `FXA-2148` as an `Evolve-SOP` entry-point SOP:

- signal sources: `af validate`, SOP content analysis, GitHub issues, activity ledger/session logs, optional experience-axis signals;
- weight table: `FXA-2146` Evolve-SOP weights;
- hard gate: `af validate`;
- implementation mode: document lifecycle through PRP/CHG;
- candidate cardinality: each passing candidate;
- escalation target gate: if a post-push fix is substantive, stop the loop and re-run the code review gate;
- no-op disposition: update the run log with `no-op: no candidate reached threshold`, leave it as an uncommitted working-tree file, and exit;
- working directory overrides: default `.`;
- mutation guard: autonomous evolve runs may not modify `FXA-2146`, `FXA-2309`, `FXA-2148`, or `FXA-2149`.

Rewrite `FXA-2149` as an `Evolve-CLI` entry-point SOP:

- signal sources: pytest, ruff, coverage, source analysis, SOP-vs-code gap analysis;
- source root: `src/fx_alfred/`;
- weight table: `FXA-2146` Evolve-CLI weights;
- hard gate: pytest + ruff;
- implementation mode: TDD red/green/refactor;
- candidate cardinality: top candidate;
- escalation target gate: if a post-push fix is substantive, stop the loop and re-run the hard gate;
- no-op disposition: update the run log with `no-op: no candidate reached threshold`, commit and push the run log to `main`, and exit;
- completion checklist rows: include README check;
- working directory overrides: default repo root; no `fx_alfred/` directory is assumed in the current top-level layout;
- mutation guard: autonomous evolve runs may not modify `FXA-2146`, `FXA-2309`, `FXA-2148`, or `FXA-2149`.

### Governance Boundary

The implementation must edit `FXA-2146` only to reconcile the prohibited mutation surface with this refactor. It must not change `FXA-2146` weights, scoring thresholds, review thresholds, or philosophy.

The intended `FXA-2146` amendment is limited to its `Prohibited Mutation Surface` section:

- add `FXA-2309-SOP-Evolve-Engine.md` to the protected list;
- replace the absolute "The evolve SOPs are explicitly prohibited from modifying" wording with wording that says autonomous evolve runs are prohibited from modifying the protected list, while a human-authored PRP/CHG that explicitly names one of those documents may modify the named document through normal review.

The engine must include this self-mutation contract:

- Autonomous evolve runs must not modify `FXA-2146`, `FXA-2309`, `FXA-2148`, or `FXA-2149`.
- A human-authored PRP/CHG that explicitly names an engine or instance SOP may modify that named SOP.
- `FXA-2146` may be modified only by a separate human-authored PRP/CHG explicitly targeting `FXA-2146`, except the narrow prohibited-surface reconciliation allowed by this PRP.
- During autonomous evolve runs, the protected-document check must run as the first Phase 0 guard before any mutation work begins and again before commit/push.
- The check must inspect `git diff --name-only`, `git diff --cached --name-only`, and the branch-base diff for protected engine, instance, or philosophy documents.
- `Escalate` means create a GitHub issue that includes the protected diff paths and abort the evolve run; it does not mean log and continue.
- This is a policy and audit guard, not a sandbox. It relies on the same trust model as the current prose prohibition; a malicious edit could remove the guard, but the SOP must make that a reviewable governance violation.

### Rigor Guardrails

In the engine's Signal phase, every signal must record:

- `source`: command, file, issue, ledger row, session log, or human observation;
- `collection_method`: exact command or read path when available;
- `trust_rating`: `high`, `medium`, or `low`;
- `trust_reason`: one sentence explaining freshness, directness, and reproducibility;
- `improvement_path`: how to collect a better signal next time.

Signal trust anchors:

- `high`: direct, fresh, reproducible project evidence, such as command output, test output, issue body, or ledger row;
- `medium`: project-local evidence that requires interpretation, such as content analysis or session-log summary;
- `low`: weak, stale, anecdotal, speculative, or unavailable evidence.

In the engine's Candidate phase, every candidate must record:

- at least one concrete supporting example;
- `evidence_source`, preferably a real usage-ledger row when the signal is ledger-derived or ledger-eligible;
- `evidence_rating`: `strong`, `medium`, or `weak`;
- `skepticism_note`: one sentence arguing against the candidate.

Candidate evidence anchors:

- `strong`: directly observed failure, ledger row, reproducible command output, or exact document/code excerpt;
- `medium`: plausible pattern supported by multiple local observations but not a direct failure;
- `weak`: inferred improvement with limited evidence.

The implementation must ban invented evidence. If ledger evidence is expected but unavailable, the candidate must state `ledger evidence unavailable`, use the next-best source, and downgrade evidence strength unless another direct source exists.

Low-trust signals and weak-evidence candidates must affect evaluation, not merely be recorded. A candidate supported only by `low` trust or `weak` evidence must be capped below the pass threshold unless a separate direct source upgrades the evidence. The CHG must state which rubric dimension absorbs this downgrade, such as Necessity for Evolve-SOP or Test verifiability for Evolve-CLI.

### Compression Gate

The implementation must compute and report:

- pre-refactor line/word count for `FXA-2148` + `FXA-2149` using `wc -l -w`;
- post-refactor line/word count for `FXA-2309` + `FXA-2148` + `FXA-2149` using the same command;
- `git diff --stat` for changed/new docs;
- a behavior-equivalence checklist;
- a rigor-coverage checklist.

The hard compression target from issue #234 is negative or neutral net documentation size across the engine plus the two instances. A neutral diff is acceptable only when the CHG explicitly explains which new governance or evidence guardrails consumed the budget.

Suggested soft budget:

- engine: about 1000-1200 words;
- each instance: about 250-400 words.

This is a budget, not a hard acceptance criterion.

---

## Behavior Equivalence Checklist

The CHG must explicitly compare old vs new behavior for:

- phase order and phase names;
- workflow loop metadata, using local integer step numbers in the thin entry-point wrapper SOPs so `af plan FXA-2148` and `af plan FXA-2149` work as single-document commands;
- `af plan --graph` topology for one bounded `review-retry` loop per entry point;
- guard checks and skip conditions;
- prerequisites;
- signal sources and source roots;
- evaluate thresholds and weight-table references;
- candidate cardinality;
- no-op disposition;
- branch naming;
- PRP/CHG creation and review gates;
- implementation sequence;
- hard gate;
- post-push comment categories and loop limit;
- post-push substantive-fix escalation target gate;
- mechanical-fix boundary;
- PR body source;
- completion checklist rows;
- prohibited actions and mutation guard.

Any intentional behavior change must be called out as such and must have an issue #234 rationale.

---

## Acceptance Criteria

- New `FXA-2309-SOP-Evolve-Engine.md` captures the shared 9-phase workflow, human gates, review loop, completion checklist structure, and threshold references from `FXA-2146`.
- `FXA-2148` and `FXA-2149` remain public SOP entry points and declare only instance-specific behavior plus compact delegation to the engine.
- `FXA-2146` weights, scoring thresholds, review thresholds, and philosophy are not modified.
- The `FXA-2146` edit is limited to prohibited-surface reconciliation and is justified in the CHG.
- Signal provenance fields are required and use the `high` / `medium` / `low` trust scale.
- Candidate evidence fields are required and use the `strong` / `medium` / `weak` evidence scale.
- Ledger evidence is mandatory for ledger-derived or ledger-eligible signals when a relevant ledger row is available; unavailable ledger evidence is stated explicitly and cannot be invented.
- The self-mutation contract protects `FXA-2146`, `FXA-2309`, `FXA-2148`, and `FXA-2149` during autonomous evolve runs.
- Behavior equivalence is documented using the checklist above.
- Compression is measured with `wc -l -w` and `git diff --stat`, and is negative or neutral across the engine plus the two instances.
- `af plan FXA-2148` and `af plan FXA-2149` remain useful as entry-point checklists through short phase-level wrapper steps, with detailed repeated prose delegated to the engine.
- `af index` is run or verified, and `rules/FXA-0000-REF-Document-Index.md` remains in the 4-column `ACID | Type | Title | Status` format.
- `af validate --root /Users/frank/Projects/alfred` passes with 0 issues, except the pre-existing `FXA-2271` CTX warning.

---

## Verification Plan

Run and record:

```bash
af validate --root /Users/frank/Projects/alfred
af plan FXA-2148 --root /Users/frank/Projects/alfred
af plan FXA-2149 --root /Users/frank/Projects/alfred
af plan --graph FXA-2148 --root /Users/frank/Projects/alfred
af plan --graph FXA-2149 --root /Users/frank/Projects/alfred
wc -l -w rules/FXA-2148-SOP-Evolve-SOP.md rules/FXA-2149-SOP-Evolve-CLI.md
wc -l -w rules/FXA-2309-SOP-Evolve-Engine.md rules/FXA-2148-SOP-Evolve-SOP.md rules/FXA-2149-SOP-Evolve-CLI.md
git diff --stat
```

Also verify:

- `af index` produces no unintended format migration;
- `Workflow loops` metadata remains parseable and uses local integer step numbers in each thin entry-point wrapper SOP;
- `af plan --graph FXA-2148` and `af plan --graph FXA-2149` preserve the one-loop review-retry topology;
- `FXA-0000` includes any new document row with Status intact;
- the behavior-equivalence checklist is present in the CHG;
- the rigor-coverage checklist is present in the CHG.

---

## Review Plan

Plan review uses a multi-model panel because this is high-risk governance compression.

Reviewers:

- Claude Code;
- Codex;
- Trinity GLM;
- Trinity MiniMax;
- Trinity DeepSeek.

Ask each reviewer:

- Does the PRP preserve behavior while compressing duplication?
- Are the engine parameters sufficient, or are important instance differences hidden?
- Are the provenance and evidence-grounding guardrails precise enough?
- Does the self-mutation exception stay inside human-approved governance and keep `FXA-2146` weights and thresholds immutable?
- What blockers must be fixed before implementation?

Implementation may start only after all blocking plan-review findings are folded in or explicitly rejected with a reason. Final plan approval requires no unresolved blockers from any reviewer and a PASS / >=9.0 score where the reviewer emits a score.

---

## Review Findings Folded In

Round 1 plan review found blockers from Claude Code, Codex, Trinity GLM, Trinity MiniMax, and Trinity DeepSeek. This revision folds in:

- explicit `af plan` / thin-instance tooling boundary;
- `FXA-2309` concrete engine ACID;
- 9-phase wording;
- `wc -l -w` measurement protocol and corrected baseline;
- explicit issue #233 / PR #235 dependency wording;
- no-op disposition as an engine parameter;
- source roots, prerequisites, skip conditions, workflow loops, and checklist rows as engine parameters;
- strict self-mutation governance contract;
- trust and evidence rating scales;
- ledger-evidence rule;
- `FXA-0000` 4-column index preservation requirement.
- replacement of unsupported symbolic workflow-loop references with validator-supported loop metadata choices;
- mandatory narrow `FXA-2146` prohibited-surface reconciliation;
- staged and branch-base protected-document diff checks;
- scoring impact for low-trust and weak-evidence candidates.
- exact `FXA-2146` prohibited-surface amendment intent;
- Phase 0 and pre-commit timing for protected-document checks;
- explicit escalation semantics;
- Phase 5 sub-template semantics for `implementation_mode`;
- per-phase `working_directory_overrides`;
- `escalation_target_gate`;
- `af plan --graph` topology verification.
- current top-level `src/fx_alfred/` source layout for Evolve-CLI;
- local integer `Workflow loops` in thin entry-point wrappers.

---

## Open Questions

None.

---

## Change History

| Date       | Change                                                                  | By    |
|------------|-------------------------------------------------------------------------|-------|
| 2026-06-21 | Draft plan for issue #234 plan review                                   | Moth  |
| 2026-06-21 | Fold in five-reviewer blockers before implementation readiness decision | Codex |
