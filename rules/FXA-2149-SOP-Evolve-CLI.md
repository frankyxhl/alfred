# SOP-2149: Evolve-CLI

**Applies to:** FXA project
**Last updated:** 2026-06-21
**Last reviewed:** 2026-06-21
**Status:** Active
**Tags:** evolution
**Workflow loops:** [{id: review-retry, from: 10, to: 9, max_iterations: 3, condition: "CI not green or unresolved comments"}]
**Task tags:** [evolve, cli, refactor-cli, improve-cli]

---

## What Is It?

Entry point for running the FXA CLI/code evolve loop. It applies the shared `FXA-2309` Evolve Engine with the Evolve-CLI instance profile.


## Why

The `fx_alfred` CLI improves through reviewed, testable code changes. This wrapper keeps CLI-specific signals, TDD gates, and no-op behavior close to the public entry point while delegating common evolve behavior to `FXA-2309`.

---

## When to Use

- Operator wants to run a CLI improvement cycle manually.
- Scheduled CLI/code evolution needs the Evolve-CLI profile.


## When NOT to Use

- An evolve PR is already open; skip the run.
- Tests are failing for unrelated reasons; fix the baseline first.
- The target is SOP/document behavior rather than CLI implementation; use `FXA-2148`.


## Steps

1. **Start engine** — Read `FXA-2309` and run it with `instance_id: evolve-cli`.
2. **Apply prerequisites and skip conditions** — Require `gh auth`, Trinity review capability, `af`, pytest, pytest-json-report, pytest-cov, and ruff. Skip if `gh pr list --label evolve` returns an open PR.
3. **Use CLI signal profile** — Collect pytest JSON output, ruff JSON output, coverage output, source analysis under `src/fx_alfred/`, and SOP-vs-code gap analysis.
4. **Use CLI evaluation profile** — Use `FXA-2146` Evolve-CLI weights. Preserve the `FXA-2146` candidate discard threshold and review pass threshold by reference.
5. **Use CLI candidate cardinality** — Implement the top passing candidate only.
6. **Use CLI implementation profile** — Create an evolve issue, branch `chore/<issue-number>-evolve-cli-YYYYMMDD`, PRP, CHG, and then run TDD red/green/refactor.
7. **Use CLI no-op disposition** — If no candidate passes, write `no-op: no candidate reached threshold` to the run log, commit and push the run log to `main`, print the completion checklist with skipped rows, and exit.
8. **Use CLI hard and review gates** — Hard gate is pytest 100% pass plus `ruff check` with 0 issues. Review gates use the applicable COR rubrics and must satisfy the current `FXA-2146` review pass threshold.
9. **Open or resume PR and enter post-push loop** — Open the PR with the run-log summary if no PR exists yet. On loop re-entry, use the existing PR, wait for CI and automated reviews, categorize comments, and apply only mechanical fixes: test ordering, variable names, doc wording, and style.
10. **Check loop exit or retry** — If CI is not green or actionable comments remain, loop to Step 9 for at most 3 total iterations. If a fix is substantive, stop and rerun the hard gate plus implementation review gate before returning to the loop.
11. **Print CLI run checklist** — Print every checklist row with explicit status: guard, run log, signals, candidates, PRP review, hard gate, README check, code review, PR URL, post-push loop, and skipped rows.

### Instance profile

- `entry_sop_acid`: `FXA-2149`
- `prerequisites`: `gh auth`, Trinity review capability, `af`, pytest, pytest-json-report, pytest-cov, ruff
- `skip_conditions`: open evolve PR exists; unrelated test failures exist
- `signal_sources`: pytest JSON output, ruff JSON output, coverage output, source analysis, SOP-vs-code gap analysis
- `source_roots`: `src/fx_alfred/`
- `weight_table_ref`: `FXA-2146` Evolve-CLI weights
- `hard_gate`: pytest + ruff
- `implementation_mode`: TDD red/green/refactor
- `candidate_cardinality`: top passing candidate
- `phase_conditional_substeps`: none
- `workflow_loop_spec`: local `review-retry` loop from Step 10 to Step 9, max 3
- `escalation_target_gate`: hard gate plus implementation review gate
- `noop_disposition`: commit and push no-op run log to `main`
- `branch_name_pattern`: `chore/<issue-number>-evolve-cli-YYYYMMDD`
- `pr_body_template`: run-log summary with signals, scores, and change
- `completion_checklist_rows`: include README check
- `mechanical_fix_boundary`: test ordering, variable names, doc wording, style
- `working_directory_overrides`: repo root; do not assume a top-level `fx_alfred/` directory
- `mutation_guard`: autonomous runs must not modify `FXA-2146`, `FXA-2309`, `FXA-2148`, or `FXA-2149`

---

## Examples

```bash
claude -p "Follow FXA-2149 for one Evolve-CLI run"
```

---

## Change History

| Date       | Change                                                                                                                                                                                                                 | By             |
|------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------|
| 2026-03-30 | Initial version from FXA-2145 PRP (approved R9), CHG FXA-2147                                                                                                                                                          | Frank + Claude |
| 2026-03-30 | D1: move gh issue create + git checkout to start of Phase 5; D2: add working directory note to Phase 2; D3: fix af where identifier in example                                                                         | Frank + Claude |
| 2026-04-01 | CHG FXA-2174: Define "review gate" in Prohibited Actions                                                                                                                                                               | Claude Code    |
| 2026-04-04 | Step 12: commit+push run log on no-op; Phase 5: "top candidate" not "for each" (retro FXA-2195)                                                                                                                        | Claude Code    |
| 2026-04-06 | CHG FXA-2107: Add Phase 7 Completion Checklist — mandatory post-run audit trail                                                                                                                                        | Frank + Claude |
| 2026-04-06 | CHG FXA-2111: Add Phase 7 Post-Push Review Loop; renumber Checklist to Phase 8                                                                                                                                         | Frank + Claude |
| 2026-06-21 | FXA-2310: Compress into an Evolve-CLI wrapper over shared engine FXA-2309, update source root to current `src/fx_alfred/` layout, and preserve CLI-specific TDD gates, no-op disposition, README row, and review loop. | Codex          |
