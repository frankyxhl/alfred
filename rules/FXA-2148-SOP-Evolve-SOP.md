# SOP-2148: Evolve-SOP

**Applies to:** FXA project
**Last updated:** 2026-06-29
**Last reviewed:** 2026-06-21
**Status:** Active
**Tags:** evolution, loop
**Workflow loops:** [{id: review-retry, from: 10, to: 9, max_iterations: 3, condition: "CI not green or unresolved comments"}]
**Task tags:** [evolve, sop, refactor-sop, improve-sop]

---

## What Is It?

Entry point for running the FXA SOP/document evolve loop. It applies the shared `FXA-2309` Evolve Engine with the Evolve-SOP instance profile.


## Why

Alfred SOPs improve through reviewed document changes. This wrapper keeps the SOP-specific signals, gates, and no-op behavior close to the public entry point while delegating common engine behavior to `FXA-2309`.

---

## When to Use

- Operator wants to run an SOP improvement cycle manually.
- Scheduled SOP/document evolution needs the Evolve-SOP profile.


## When NOT to Use

- An evolve PR is already open; skip the run.
- Operator is mid-session with uncommitted changes to FXA rules.
- The target is CLI implementation rather than SOP/document behavior; use `FXA-2149`.


## Steps

1. **Start engine** — Read `FXA-2309` and run it with `instance_id: evolve-sop`.
2. **Apply prerequisites and skip conditions** — Require `gh auth`, Trinity review capability, and `af`. Skip if `gh pr list --label evolve` returns an open PR or if the operator is mid-session with uncommitted FXA/rules changes.
3. **Use SOP signal profile** — First read the mandatory activity ledger, then collect `af validate --json`, SOP content analysis, GitHub issues labeled `agent-input`, optional session-log signals, and optional experience-axis signals (method: `FXA-2293`; do not propose 11-star candidates).
4. **Use SOP evaluation profile** — Use `FXA-2146` Evolve-SOP weights. Preserve the `FXA-2146` candidate discard threshold and review pass threshold by reference.
5. **Use SOP candidate cardinality** — Implement each passing candidate, not only the top candidate.
6. **Use SOP implementation profile** — Create an evolve issue, branch `chore/<issue-number>-evolve-sop-YYYYMMDD`, PRP, CHG, hard gate, and implementation review through the document lifecycle.
7. **Use SOP no-op disposition** — If no candidate passes, write `no-op: no candidate reached threshold` to the run log, leave the run log uncommitted in the working tree, print the completion checklist with skipped rows, and exit.
8. **Use SOP hard and review gates** — Hard gate is `af validate` with 0 issues on modified documents. Review gates use the applicable COR rubrics and must satisfy the current `FXA-2146` review pass threshold.
9. **Open or resume PR and enter post-push loop** — Open the PR with the run-log summary if no PR exists yet. On loop re-entry, use the existing PR, wait for CI and automated reviews, categorize comments, and apply only mechanical fixes: doc wording, formatting, and metadata.
10. **Check loop exit or retry** — If CI is not green or actionable comments remain, loop to Step 9 for at most 3 total iterations. If a fix is substantive, stop and rerun the code review gate before returning to the loop.
11. **Print SOP run checklist** — Print every checklist row with explicit status: guard, run log, signals, candidates, PRP review, hard gate, code review, PR URL, post-push loop, and skipped rows.

### Instance profile

- `entry_sop_acid`: `FXA-2148`
- `prerequisites`: `gh auth`, Trinity review capability, `af`
- `skip_conditions`: open evolve PR exists; uncommitted FXA/rules changes exist
- `mandatory_ordered_signal_sources`: activity ledger before optional session-log scanning
- `signal_sources`: `af validate`, SOP content analysis, GitHub issues, optional session logs, optional experience-axis signals
- `source_roots`: `rules/`
- `weight_table_ref`: `FXA-2146` Evolve-SOP weights
- `hard_gate`: `af validate`
- `implementation_mode`: document lifecycle through PRP/CHG
- `candidate_cardinality`: each passing candidate
- `phase_conditional_substeps`: optional experience-axis signals in Phase 2
- `workflow_loop_spec`: local `review-retry` loop from Step 10 to Step 9, max 3
- `escalation_target_gate`: implementation review gate
- `noop_disposition`: leave no-op run log uncommitted
- `branch_name_pattern`: `chore/<issue-number>-evolve-sop-YYYYMMDD`
- `pr_body_template`: run-log summary with signals, scores, and change
- `mechanical_fix_boundary`: doc wording, formatting, metadata
- `working_directory_overrides`: repo root
- `mutation_guard`: autonomous runs must not modify `FXA-2146`, `FXA-2309`, `FXA-2148`, or `FXA-2149`

---

## Examples

```bash
claude -p "Follow FXA-2148 for one Evolve-SOP run"
```

---

## Change History

| Date       | Change                                                                                                                                                                           | By              |
|------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------|
| 2026-03-30 | Initial version from FXA-2145 PRP (approved R9), CHG FXA-2147                                                                                                                    | Frank + Claude  |
| 2026-03-30 | D1: move gh issue create + git checkout to start of Phase 5 (before PRP); D3: fix af where identifier in example                                                                 | Frank + Claude  |
| 2026-04-01 | CHG FXA-2174: Define "review gate" in Prohibited Actions                                                                                                                         | Claude Code     |
| 2026-04-06 | CHG FXA-2110: Add Phase 7 Completion Checklist — mandatory post-run audit trail                                                                                                  | Frank + Claude  |
| 2026-04-06 | CHG FXA-2111: Add Phase 7 Post-Push Review Loop; renumber Checklist to Phase 8                                                                                                   | Frank + Claude  |
| 2026-05-17 | issue #183: insert optional experience-axis signal step; cascade-renumber later phases and workflow loops; implements Option B from PRP-2293 (FXA-2293).                         | Claude Opus 4.7 |
| 2026-06-21 | FXA-2307: Phase 2 now reads the activity ledger before optional session-log scanning and records never-used SOPs, `af plan --task` zero-match gaps, and per-SOP usage frequency. | Codex           |
| 2026-06-21 | FXA-2310: Compress into an Evolve-SOP wrapper over shared engine FXA-2309 while preserving SOP-specific signals, gates, no-op disposition, and review loop.                      | Codex           |
