# SOP-2148: Evolve-SOP

**Applies to:** FXA project
**Last updated:** 2026-03-30
**Last reviewed:** 2026-03-30
**Status:** Active
**Task tags:** [evolve, sop, refactor-sop, improve-sop]

---

## What Is It?

An automated self-improvement procedure that periodically discovers improvements to alfred SOPs and documents, evaluates candidates using a weighted rubric, implements approved changes through the standard PRP/CHG lifecycle, and opens a PR for human review.


## Why

Alfred SOPs currently improve only through manual human-initiated sessions. This SOP closes the feedback loop by running a Generator → Evaluator cycle against live signals (validation output, GitHub Issues, content analysis), ensuring continuous compression toward the "Compression as Intelligence" north star.

---

## When to Use

- Operator wants to run a SOP improvement cycle manually (Phase 1)
- Scheduled via cron (Phase 2)


## When NOT to Use

- An evolve PR is already open (`gh pr list --label evolve` returns results — skip run)
- Operator is mid-session with uncommitted changes to `alfred_ops/rules/`


## Prerequisites

- `gh auth login` pre-configured
- `/trinity` USR-layer skill available (Codex + Gemini reviewers)
- `af` installed and accessible with `--root /path/to/fx_alfred`


## Steps

### Phase 0: Guard checks

1. **Check for open evolve PR** — run `gh pr list --label evolve`. If any open PR exists, print "evolve PR already open — skipping" and exit.
2. **Read Evolution Philosophy** — `af --root /path/to/fx_alfred read FXA-2146`. Load thresholds and weights.

### Phase 1: Create run log

3. **Create run log REF** —
   ```bash
   af --root /path/to/fx_alfred create ref --prefix FXA --area 21 --title "Evolve-Run-YYYYMMDD-HHMMSS"
   ```
   Record the assigned ACID. All subsequent findings are appended to this file.

### Phase 2: Collect signals (Generator input)

4. **Document health** — `af --root /path/to/fx_alfred validate --json`. Record issues.
5. **Content analysis** — Read all SOPs via `af --root /path/to/fx_alfred list --type SOP --json`, then `af --root /path/to/fx_alfred read <ACID>` for each. Check for logic gaps, ambiguity, or drift vs COR-0002.
6. **GitHub Issues** — `gh issue list --label agent-input --json number,title,body`. Record relevant issues.
7. **Session logs** — Optional: scan Claude Code session history for SOP violation patterns. Skip if unavailable.

### Phase 3: Generate candidates

8. **Generator role** — Produce a list of improvement candidates based on signals collected. Each candidate must include: target SOP, proposed change, evidence source.

### Phase 4: Evaluate candidates (Evaluator role)

9. **Switch to Evaluator role** (skeptical by default). Score each candidate using Evolve-SOP weights from FXA-2146:
   - Necessity 30% / Consistency 25% / Atomicity 20% / Actionability 15% / Impact 10%
10. **Discard candidates scoring < 7.0**. Record scores and discards in the run log.
11. **If no candidates pass** — update run log with "no-op: no candidate reached threshold", leave file as uncommitted working-tree file, exit.

### Phase 5: Implement (for each passing candidate)

12. **Open GitHub issue** — `gh issue create --title "evolve: <change-title>" --label evolve`
13. **Create branch** — `git checkout -b chore/<issue-number>-evolve-sop-YYYYMMDD`
14. **Create PRP** — `af --root /path/to/fx_alfred create prp --prefix FXA --area 21 --title "<change-title>"`
15. **Fill PRP** with candidate details (problem, proposed change, evidence).
16. **Review PRP** — dispatch via `/trinity codex "Review PRP <ACID>" gemini "Review PRP <ACID>"`. Both must score >= 9.0. If either fails, revise PRP and re-dispatch following COR-1602 round rules.
17. **Create CHG** — `af --root /path/to/fx_alfred create chg --prefix FXA --area 21 --title "<change-title>"`
18. **Implement change** using Claude's built-in tools (Read, Write, Edit).
19. **Hard gate** — `af --root /path/to/fx_alfred validate`. Must pass with 0 issues on modified documents. If it fails, fix and re-run.
20. **Code review** — dispatch via `/trinity codex "Review CHG <ACID> implementation" gemini "Review CHG <ACID> implementation"`. Both must score >= 9.0. If either fails, revise and re-dispatch following COR-1602 round rules.

### Phase 6: Git / PR

21. **Commit changes** — stage modified/new files, `git commit`
22. **Push branch** — `git push -u origin <branch>`
23. **Open PR** — `gh pr create --title "evolve: <change-title>" --body "<run log summary: signals, scores, change>"` — body auto-populated from run log REF

### Phase 7: Post-Push Review Loop

> **Loop limit:** Steps 24–27 repeat at most **3 iterations** in total (counting both CI-wait retries and actionable-fix cycles). If the limit is reached, go to Step 28.

24. **Wait for CI + automated reviews** — sleep 3 minutes after PR is opened (or after each fix-push), then:
    ```bash
    gh pr checks <PR-number>
    gh api --paginate repos/{owner}/{repo}/pulls/<PR-number>/comments
    ```
25. **Categorize each review comment:**
    - **Actionable** — valid issue, fix it
    - **Advisory** — noted, no code change needed (reply explaining why)
    - **False positive** — reply with reasoning, no change
26. **If actionable items exist:**
    a. Fix the issues — fixes must be **mechanical** (doc wording, formatting, metadata). If a fix requires substantive content changes, stop the loop and re-run Phase 5 Step 20 (code review gate) instead.
    b. Re-run hard gate (`af --root /path/to/fx_alfred validate` must pass with 0 issues on modified documents)
    c. Commit + push
27. **Check CI** — if CI is not green and no fixes were pushed in Step 26, go to Step 24 (counts as one iteration). If fixes were pushed in Step 26, go to Step 24 (CI will re-run on the new push).
28. **Exit loop** when: CI passes AND 0 unresolved actionable comments, OR max iterations reached. If unresolved items remain, list them in the completion checklist for human review.

### Phase 8: Completion Checklist

29. **Display checklist** — After all phases complete (or on early exit at Step 11), print the following checklist with results filled in. Every item must show an explicit status — never omit silently.

```
## Evolve-SOP Run Checklist

- [ ] **Guard: no open evolve PR** — <PASS/FAIL>
- [ ] **Run log created** — <ACID>
- [ ] **Signals collected**
  - af validate: <N issues>
  - Content analysis: <N SOPs reviewed>
  - GitHub Issues: <N relevant>
- [ ] **Candidates evaluated** — <N generated, N passed, N discarded>
- [ ] **PRP review gate** — Codex <score> / Gemini <score> — <PASS/FIX>
- [ ] **Hard gate (af validate)** — <PASS/FAIL>
- [ ] **Code review gate** — Codex <score> / Gemini <score> — <PASS/FIX>
- [ ] **PR opened** — <URL>
- [ ] **Post-push review loop** — <N iterations, N comments fixed / N advisory / N false positive>
```

If a step was skipped due to early exit (e.g., no candidate passed), mark remaining items as `— SKIPPED (reason)`.

### Prohibited actions

- Must not modify `FXA-2148-SOP-Evolve-SOP.md`, `FXA-2149-SOP-Evolve-CLI.md`, or `FXA-2146-REF-Evolution-Philosophy.md`
- Must not bypass hard gate or review gate
  - **review gate** = both reviewers (Codex + Gemini) score >= 9.0 per the applicable rubric (COR-1608 for PRP, COR-1609 for CHG, COR-1610 for code)

---

## Examples

```bash
# Manual run — Phase 1
claude -p "Follow the SOP at $(af --root /path/to/fx_alfred where FXA-2148)"
```

---

## Change History

| Date       | Change                                                                                                           | By             |
|------------|------------------------------------------------------------------------------------------------------------------|----------------|
| 2026-03-30 | Initial version from FXA-2145 PRP (approved R9), CHG FXA-2147                                                    | Frank + Claude |
| 2026-03-30 | D1: move gh issue create + git checkout to start of Phase 5 (before PRP); D3: fix af where identifier in example | Frank + Claude |
| 2026-04-01 | CHG FXA-2174: Define "review gate" in Prohibited Actions                                                         | Claude Code    |
| 2026-04-06 | CHG FXA-2110: Add Phase 7 Completion Checklist — mandatory post-run audit trail                                  | Frank + Claude |
| 2026-04-06 | CHG FXA-2111: Add Phase 7 Post-Push Review Loop; renumber Checklist to Phase 8                                   | Frank + Claude |
