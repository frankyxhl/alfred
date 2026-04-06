# SOP-2149: Evolve-CLI

**Applies to:** FXA project
**Last updated:** 2026-03-30
**Last reviewed:** 2026-03-30
**Status:** Active

---

## What Is It?

An automated self-improvement procedure that periodically discovers improvements to the `fx_alfred` Python codebase, evaluates candidates using a weighted rubric, implements approved changes following alfred's own document lifecycle (TDD: red → green → refactor), and opens a PR for human review.

## Why

The `fx_alfred` CLI currently improves only through manual human-initiated sessions. This SOP closes the feedback loop by running a Generator → Evaluator cycle against live signals (test failures, lint output, coverage gaps, source analysis), applying the "Compression as Intelligence" principle continuously.

---

## When to Use

- Operator wants to run a CLI improvement cycle manually (Phase 1)
- Scheduled via cron (Phase 2)

## When NOT to Use

- An evolve PR is already open (`gh pr list --label evolve` returns results — skip run)
- Tests are currently failing for unrelated reasons (fix first)

## Prerequisites

- `gh auth login` pre-configured
- `/trinity` USR-layer skill available (Codex + Gemini reviewers)
- `af` installed and accessible with `--root /path/to/fx_alfred`
- `pytest-json-report` and `pytest-cov` installed in `fx_alfred` virtual environment

## Steps

### Phase 0: Guard checks

1. **Check for open evolve PR** — `gh pr list --label evolve`. If any open PR exists, print "evolve PR already open — skipping" and exit.
2. **Read Evolution Philosophy** — `af --root /path/to/fx_alfred read FXA-2146`. Load thresholds and weights.

### Phase 1: Create run log

3. **Create run log REF** —
   ```bash
   af --root /path/to/fx_alfred create ref --prefix FXA --area 21 --title "Evolve-Run-YYYYMMDD-HHMMSS"
   ```
   Record the assigned ACID. All subsequent findings are appended to this file.

### Phase 2: Collect signals (Generator input)

> **Working directory:** Run steps 4–6 from inside `fx_alfred/` (relative to alfred repo root). `cd fx_alfred` before starting.

4. **Test failures** — `.venv/bin/pytest --json-report --json-report-file=/tmp/pytest-report.json`. Record failures.
5. **Code quality** — `.venv/bin/ruff check --output-format=json src/ > /tmp/ruff-report.json`. Record issues.
6. **Coverage gaps** — `.venv/bin/pytest --cov=fx_alfred --cov-report=json --cov-report=term-missing`. Record uncovered paths.
7. **Source analysis** — Read `fx_alfred/src/fx_alfred/`, identify duplication, missing edge handling, or dead code.
8. **SOP vs code gap** — `af --root /path/to/fx_alfred list --type SOP --json`, then `af --root /path/to/fx_alfred read <ACID>` for each. Compare Steps section vs actual CLI implementation.

### Phase 3: Generate candidates

9. **Generator role** — Produce a list of improvement candidates based on signals. Each candidate must include: target file/module, proposed change, evidence source (test failure / lint issue / duplication / coverage gap).

### Phase 4: Evaluate candidates (Evaluator role)

10. **Switch to Evaluator role** (skeptical by default). Score each candidate using Evolve-CLI weights from FXA-2146:
    - Test verifiability 35% / Scope restraint 30% / Backward compatibility 20% / Necessity 15%
11. **Discard candidates scoring < 7.0**. Record scores and discards in the run log.
12. **If no candidates pass** — update run log with "no-op: no candidate reached threshold", commit and push run log to main, exit.

### Phase 5: Implement (top candidate, TDD)

13. **Open GitHub issue** — `gh issue create --title "evolve: <change-title>" --label evolve`
14. **Create branch** — `git checkout -b chore/<issue-number>-evolve-cli-YYYYMMDD`
15. **Create PRP** — `af --root /path/to/fx_alfred create prp --prefix FXA --area 21 --title "<change-title>"`
16. **Fill PRP** with candidate details (problem, proposed change, evidence).
17. **Review PRP** — dispatch via `/trinity codex "Review PRP <ACID>" gemini "Review PRP <ACID>"`. Both must score >= 9.0. If either fails, revise PRP and re-dispatch following COR-1602 round rules.
18. **Create CHG** — `af --root /path/to/fx_alfred create chg --prefix FXA --area 21 --title "<change-title>"`
19. **TDD — Red**: Write failing test(s) first. Run `pytest` to confirm failure.
20. **TDD — Green**: Implement minimum code to make tests pass. Run `pytest`.
21. **TDD — Refactor**: Clean up without breaking tests. Run `pytest` + `ruff check`.
22. **Hard gate** — `pytest` must pass 100% + `ruff check` must return 0 issues. If either fails, fix before proceeding.
23. **Code review** — dispatch via `/trinity codex "Review CHG <ACID> implementation" gemini "Review CHG <ACID> implementation"`. Both must score >= 9.0. If either fails, revise and re-dispatch following COR-1602 round rules.

### Phase 6: Git / PR

24. **Commit changes** — stage modified/new files, `git commit`
25. **Push branch** — `git push -u origin <branch>`
26. **Open PR** — `gh pr create --title "evolve: <change-title>" --body "<run log summary: signals, scores, change>"` — body auto-populated from run log REF

### Phase 7: Post-Push Review Loop

> **Loop limit:** Steps 27–30 repeat at most **3 iterations** in total (counting both CI-wait retries and actionable-fix cycles). If the limit is reached, go to Step 31.

27. **Wait for CI + automated reviews** — sleep 3 minutes after PR is opened (or after each fix-push), then:
    ```bash
    gh pr checks <PR-number>
    gh api --paginate repos/{owner}/{repo}/pulls/<PR-number>/comments
    ```
28. **Categorize each review comment:**
    - **Actionable** — valid issue, fix it
    - **Advisory** — noted, no code change needed (reply explaining why)
    - **False positive** — reply with reasoning, no change
29. **If CI is not green** — go to Step 27 (counts as one iteration).
30. **If actionable items exist:**
    a. Fix the issues — fixes must be **mechanical** (test ordering, variable names, doc wording, style). If a fix requires substantive logic changes, stop the loop and re-run Phase 5 Step 23 (code review gate) instead.
    b. Re-run hard gate (`pytest` must pass 100% + `ruff check` must return 0 issues)
    c. Commit + push
    d. Go to Step 27.
31. **Exit loop** when: CI passes AND 0 unresolved actionable comments, OR max iterations reached. If unresolved items remain, list them in the completion checklist for human review.

### Phase 8: Completion Checklist

32. **Display checklist** — After all phases complete (or on early exit at Step 12), print the following checklist with results filled in. Every item must show an explicit status — never omit silently.

```
## Evolve-CLI Run Checklist

- [ ] **Guard: no open evolve PR** — <PASS/FAIL>
- [ ] **Run log created** — <ACID>
- [ ] **Signals collected**
  - Tests: <N passed, N failed>
  - Ruff: <N issues>
  - Coverage: <N%>
- [ ] **Candidates evaluated** — <N generated, N passed, N discarded>
- [ ] **PRP review gate** — Codex <score> / Gemini <score> — <PASS/FIX>
- [ ] **Hard gate (pytest + ruff)** — <PASS/FAIL>
- [ ] **README check** — <UPDATED commit SHA / N/A: reason>
- [ ] **Code review gate** — Codex <score> / Gemini <score> — <PASS/FIX>
- [ ] **PR opened** — <URL>
- [ ] **Post-push review loop** — <N iterations, N comments fixed / N advisory / N false positive>
```

If a step was skipped due to early exit (e.g., no candidate passed), mark remaining items as `— SKIPPED (reason)`.

### Prohibited actions

- Must not modify `FXA-2148-SOP-Evolve-SOP.md`, `FXA-2149-SOP-Evolve-CLI.md`, or `FXA-2146-REF-Evolution-Philosophy.md`
- Must not bypass hard gate (pytest + ruff) or review gate
  - **review gate** = both reviewers (Codex + Gemini) score >= 9.0 per the applicable rubric (COR-1608 for PRP, COR-1609 for CHG, COR-1610 for code)
- Source path: `fx_alfred/src/fx_alfred/` (relative to alfred repo root)

---

## Examples

```bash
# Manual run — Phase 1
claude -p "Follow the SOP at $(af --root /path/to/fx_alfred where FXA-2149)"
```

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-30 | Initial version from FXA-2145 PRP (approved R9), CHG FXA-2147 | Frank + Claude |
| 2026-03-30 | D1: move gh issue create + git checkout to start of Phase 5; D2: add working directory note to Phase 2; D3: fix af where identifier in example | Frank + Claude |
| 2026-04-01 | CHG FXA-2174: Define "review gate" in Prohibited Actions | Claude Code |
| 2026-04-04 | Step 12: commit+push run log on no-op; Phase 5: "top candidate" not "for each" (retro FXA-2195) | Claude Code |
| 2026-04-06 | CHG FXA-2107: Add Phase 7 Completion Checklist — mandatory post-run audit trail | Frank + Claude |
| 2026-04-06 | CHG FXA-2111: Add Phase 7 Post-Push Review Loop; renumber Checklist to Phase 8 | Frank + Claude |
