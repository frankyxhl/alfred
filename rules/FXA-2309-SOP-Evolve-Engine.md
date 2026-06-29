# SOP-2309: Evolve Engine

**Applies to:** FXA project
**Last updated:** 2026-06-29
**Last reviewed:** 2026-06-21
**Status:** Active
**Tags:** evolution, maintain

---

## What Is It?

Shared engine for FXA evolve workflows. Entry-point SOPs such as `FXA-2148` and `FXA-2149` keep the instance-specific wrapper, while this engine defines the common guard, signal, candidate, evaluation, implementation, review, PR, post-push loop, and completion-checklist behavior.


## Why

`FXA-2148` and `FXA-2149` had duplicated workflow prose. A shared engine preserves behavior with less documentation, adds evidence rigor once, and gives future evolve instances one place to reuse the same governance pattern.

---

## When to Use

- An evolve entry-point SOP tells the operator to execute this engine with a declared instance profile.
- A new FXA evolve variant needs the same generator/evaluator/review loop.


## When NOT to Use

- Running an evolve loop directly without an entry-point SOP and instance profile.
- Changing `FXA-2146` weights or thresholds; use a separate human-authored PRP/CHG for that.
- Autonomous runs that would modify `FXA-2146`, `FXA-2309`, `FXA-2148`, or `FXA-2149`.


## Steps

### Phase 0: Guard checks

1. **Load instance profile** — Read the entry-point SOP and capture: `instance_id`, prerequisites, skip conditions, signal sources, source roots, weight table, hard gate, implementation mode, candidate cardinality, conditional substeps, workflow loop spec, escalation target gate, no-op disposition, branch pattern, PR body template, completion checklist rows, mechanical-fix boundary, mutation guard, and working-directory overrides.
2. **Run skip checks** — Apply the instance skip conditions. If an evolve PR is already open, print the instance skip message and exit.
3. **Load philosophy** — Read `FXA-2146`. Treat its weights and thresholds as authoritative; this engine may quote them only as examples.
4. **Check protected docs** — Before any mutation, inspect `git diff --name-only`, `git diff --cached --name-only`, and the branch-base diff. If an autonomous evolve run includes a protected document, create a GitHub issue with the protected paths and abort. This is a policy/audit guard, not a sandbox.

### Phase 1: Create run log

5. **Create run log REF** — Create an FXA REF run log and record its ACID. Append all signals, candidate scores, decisions, reviews, and final checklist results there.

### Phase 2: Collect signals

6. **Collect ordered signals** — Collect signals in this order: mandatory ledger/source-of-truth reads first when declared, then instance `signal_sources`, then `phase_conditional_substeps`.
7. **Record signal provenance** — For every signal record `source`, `collection_method`, `trust_rating`, `trust_reason`, and `improvement_path`.
8. **Rate signal trust** — Use `high` for direct, fresh, reproducible evidence; `medium` for local evidence requiring interpretation; `low` for weak, stale, anecdotal, speculative, or unavailable evidence.

### Phase 3: Generate candidates

9. **Generate candidates** — Produce improvement candidates from collected signals. Each candidate must include a target, proposed change, at least one concrete supporting example, `evidence_source`, `evidence_rating`, and `skepticism_note`.
10. **Rate candidate evidence** — Use `strong` for directly observed failures, ledger rows, command output, or exact excerpts; `medium` for patterns supported by multiple local observations; `weak` for limited inference.
11. **Handle missing ledger evidence** — For ledger-derived or ledger-eligible signals, cite the ledger row when available. If it is unavailable, state `ledger evidence unavailable`, use the next-best source, and downgrade evidence strength unless another direct source exists. Never invent evidence.

### Phase 4: Evaluate candidates

12. **Score candidates** — Score with the instance `weight_table_ref` from `FXA-2146`. Low-trust signals and weak-evidence candidates must affect scoring; a candidate supported only by low/weak evidence cannot pass unless a separate direct source upgrades it.
13. **Discard weak candidates** — Discard candidates below the `FXA-2146` candidate discard threshold. Record scores and discards in the run log.
14. **No-op exit** — If no candidate passes, follow the instance `noop_disposition`, fill remaining checklist rows as skipped, and exit.

### Phase 5: Implement

15. **Create issue and branch** — Create the evolve issue and branch using the instance branch pattern.
16. **Create and review PRP** — Create a PRP for the selected candidate(s). Review under the configured PRP review gate; revise until the gate passes or stop.
17. **Create CHG** — Create the implementation CHG.
18. **Run implementation sub-template** — Apply the instance `implementation_mode`: document-lifecycle edits for Evolve-SOP, TDD red/green/refactor for Evolve-CLI, or another declared sub-template for future instances.
19. **Apply cardinality** — Execute Phase 5 for each passing candidate or only the top candidate according to `candidate_cardinality`.
20. **Run hard gate** — Run the instance hard gate and fix failures before proceeding.
21. **Run implementation review gate** — Dispatch implementation review. Revise until the gate passes or stop.

### Phase 6: Git / PR

22. **Re-check protected docs** — Before commit/push, rerun the protected-document diff checks from Phase 0.
23. **Commit and push** — Commit the reviewed changes and push the branch.
24. **Open PR** — Open a PR using the instance PR body template and run-log summary.

### Phase 7: Post-push review loop

25. **Wait for CI and reviews** — Wait after PR open or each fix-push, then collect CI status and review comments.
26. **Categorize comments** — Mark comments as actionable, advisory, or false positive.
27. **Apply mechanical fixes only** — If actionable comments are inside `mechanical_fix_boundary`, fix, rerun the hard gate, commit, and push.
28. **Escalate substantive fixes** — If a fix exceeds the mechanical boundary, stop the loop and return to the instance `escalation_target_gate`.
29. **Check loop exit** — Exit when CI passes and there are zero unresolved actionable comments, or when the loop limit is reached. If unresolved items remain, list them for human review.

### Phase 8: Completion checklist

30. **Print checklist** — Print every instance checklist row with explicit status. Mark skipped rows as `SKIPPED` with a reason.
31. **Report compression/evidence results when applicable** — For evolve-engine refactors, report `wc -l -w`, `git diff --stat`, behavior-equivalence checklist results, rigor-coverage checklist results, and `af plan --graph` topology results.

### Protected surface

Autonomous evolve runs must not modify:

- `FXA-2146-REF-Evolution-Philosophy.md`
- `FXA-2309-SOP-Evolve-Engine.md`
- `FXA-2148-SOP-Evolve-SOP.md`
- `FXA-2149-SOP-Evolve-CLI.md`

A human-authored PRP/CHG that explicitly names one of those documents may modify the named document through normal review.

---

## Examples

```bash
af plan FXA-2148 --root /Users/frank/Projects/alfred
af plan FXA-2149 --root /Users/frank/Projects/alfred
```

---

## Change History

| Date       | Change                                            | By    |
|------------|---------------------------------------------------|-------|
| 2026-06-21 | Initial engine extracted from FXA-2148 / FXA-2149 | Codex |
