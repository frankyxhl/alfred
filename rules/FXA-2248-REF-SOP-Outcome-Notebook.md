# REF-2248: SOP Outcome Notebook

**Applies to:** FXA project
**Last updated:** 2026-05-06
**Last reviewed:** 2026-05-06
**Status:** Draft
**Related:** COR-1402 (declare active SOP), COR-1602 (multi-model write-time review — this REF complements with use-time recording), FXA-2230 (Approved Agent Activity Log Protocol — this notebook is the zero-code, manually-maintained counterpart; graduate to a `sop.outcome` event extension of `alfred.activity/v1` when row count justifies the engineering)
**Inspired by:** EvoMap (https://evomap.ai) — Capsule `outcome.score` concept. Marketplace mechanics out of scope.
**Supersedes:** withdrawn FXA-2248-PRP-SOP-Outcome-Log. The PRP proposed a 290-LoC `af report` / `af stats` system over a custom JSONL log. Round-3 multi-model review (4 real-CLI reviewers — GLM-5.1, Codex GPT-5.5, Gemini-3.1, DeepSeek) converged on a simpler conclusion: at single-operator volume the structured system is dominated by a hand-maintained markdown table. This REF is that table's contract.

---

## What Is It?

A documented contract for a markdown table that the operator manually appends to whenever they finish a SOP-driven task. Captures the same `outcome.score` data the withdrawn PRP proposed — date, SOP ACID, task, 0..1 score, freeform outcome note — but as a zero-code, append-by-hand artifact rather than a CLI subsystem.

The actual table lives at the `## Records` section below. This is both the **format contract** and the **first instance**. If a second, layered notebook is ever needed (e.g. a USR-layer personal notebook), it follows the same schema and references this REF as authority.

---

## Why a Notebook, Not a System

Round-3 review reached convergent conclusions:

1. The withdrawn PRP itself admitted (§4.7) that **<60% sustained report rate makes aggregate stats meaningless**, and a single-operator project realistically sees ~20% — so the structured aggregation never pays off.
2. **FXA-2230-PRP-Agent-Activity-Log-Protocol (Approved 2026-05-02) already provides** the JSONL infrastructure (storage at `rules/logs/`, atomic ≤4096-byte append, schema validation, archival, scanner-skip). Building a parallel `state/evolution-log.jsonl` was duplication. When this notebook graduates to a structured form, it will be a `sop.outcome` event added to FXA-2230's `alfred.activity/v1` schema — not a parallel system.
3. The data being captured is **inherently low-frequency, low-volume, and reflective**. A few rows per active month fits a markdown table cleanly. Aggregation is a one-shot `awk`/`grep`, not a persistent index.

DeepSeek's r3 verdict was the cleanest: *"Simpler alternative never explored: a markdown table queryable via `grep`. Zero-code notebook is the honest path."* This REF takes that path.

---

## Table Schema

A SOP Outcome Notebook is a single markdown table with the following columns, in this order:

| Column | Type | Required | Definition |
|---|---|---|---|
| Date | ISO 8601 (YYYY-MM-DD) | yes | Date the SOP was applied (typically same as row-add date) |
| SOP | PREFIX-ACID | yes | The SOP that was followed (e.g. `COR-1500`). The operator verifies it resolves to a real document at row-add time; no automated validation. |
| Task | string | yes | Free-form task identifier or one-line description (e.g. `FXA-2150` or `fix import bug`). Required so per-SOP rate analysis is possible later — not optional. |
| Score | float in [0, 1] | yes | Operator's assessment of "did following this SOP produce a useful outcome on this task?" Not "is the SOP well-written" — that is COR-1602's job. Not "did the task succeed" — orthogonal. The question is specifically about the SOP's contribution. |
| Outcome | one-line string | yes | Short freeform note describing what happened. Required for every row (no extremes-only rule, to avoid score-clustering bias raised in r2 Gemini-3 review). |
| By | string | optional | Human-readable authorship if multiple agents share the notebook. Default: the agent that filled the row. Empty cells use `—` (em-dash). |

The table sits under a `## Records` heading. Newest row at the bottom (chronological append). No row deletion; corrections are new rows referring to the prior row in `Outcome`.

---

## Filling Contract

**When to add a row.** After a task that meaningfully invoked at least one SOP. "Meaningfully" = the SOP's steps influenced the work, not merely declared via COR-1402 and ignored. One row per `(SOP, Task)` pair; multiple SOPs on one task means multiple rows.

**When to skip.** Trivial tasks with no SOP invocation (one-line typo, version bump). For the case where a SOP was declared but the operator silently took a different path: **do not skip — record the divergence as a low-score row with an explanatory note** ("SOP declared, step 3 unworkable, manual approach taken"). The divergence record is the most informative kind of row.

**Score guidance** (anchors, not enforcement):

- `1.0` — SOP followed end-to-end, outcome better than expected. Rare.
- `0.8` — SOP followed cleanly, expected outcome.
- `0.5` — SOP partially followed; some friction or skipped steps but useful overall.
- `0.3` — SOP attempted, mostly didn't apply or got in the way.
- `0.0` — SOP declared but not actually followed, or actively counter-productive.

Operator-internal scale; the value of consistency over time exceeds the absolute value of any single rating.

**Outcome note.** One short line, ≤ 100 chars typical. The keyword that mattered, not a full report. Examples:

- `step 3 skipped, manual TDD`
- `routing decision wrong, fell back to COR-1606`
- `clean run, no friction`
- `divergence — see row 2026-04-15 COR-1500`

---

## Query Patterns

Aggregation is one-shot, run on demand:

```bash
NOTEBOOK="fx_alfred/rules/FXA-2248-REF-SOP-Outcome-Notebook.md"

# all rows for a SOP
grep -E "^\| 2[0-9-]+ \| COR-1500 \|" "$NOTEBOOK"

# rows with score ≤ 0.5 (problem candidates)
awk -F'|' '/^\| 2[0-9-]+ /{ gsub(/ /,"",$5); if ($5 <= 0.5) print }' "$NOTEBOOK"

# row count by SOP, descending
awk -F'|' '/^\| 2[0-9-]+ /{ gsub(/ /,"",$3); print $3 }' "$NOTEBOOK" | sort | uniq -c | sort -rn

# average score by SOP
awk -F'|' '/^\| 2[0-9-]+ /{ gsub(/ /,"",$3); gsub(/ /,"",$5); s[$3]+=$5; n[$3]++ } END { for (k in s) printf "%-12s %.2f (%d)\n", k, s[k]/n[k], n[k] }' "$NOTEBOOK" | sort -k2n
```

No persistent indexer, no `af stats` command. If `awk` becomes awkward (~50+ rows), that is the signal to graduate to FXA-2230's structured emit — at that scale, the data volume justifies the infrastructure.

---

## Decommission Criteria

This REF is an experiment in operator habit. Two outcomes:

- **Failed experiment.** Fewer than 5 rows over 3 consecutive months from an active operator. Archive this file with a single closing row explaining the decommission, then remove the REF. The cost was the experiment itself; no LoC was sunk.
- **Successful experiment.** ≥ 50 rows with sustained adds, OR a clear pattern emerges that has produced a concrete SOP edit. Propose a graduation PRP that adds `event: "sop.outcome"` to FXA-2230's `alfred.activity/v1` schema (or its v2 successor) and migrates the markdown rows in.

Reviewers who graded the withdrawn PRP raised four convergent concerns this REF inherits and accepts:

1. **Self-policing failure (DeepSeek r3, GLM-5.1 r3).** Same operator who underuses the notebook is the one who notices. Mitigation: review against the criteria above at every COR-1200 (Session Retrospective) — that procedure already runs periodically.
2. **Lifecycle gaps on SOP rename/delete (Gemini-3, DeepSeek r3).** A renamed SOP leaves orphan rows. Acceptable for v1: rows are preserved with their original ACID; if a future query needs unification, a manual rename pass on the markdown is trivial.
3. **No schema versioning (DeepSeek r3).** Acceptable: a markdown table can absorb new columns without breaking old rows (empty cells = `—`). Versioning becomes meaningful only at the JSONL graduation step.
4. **Filesystem atomicity (DeepSeek r3, GLM-5.1 r3).** Single-operator markdown editing has no concurrency surface. Out of scope at the notebook stage.

---

## Records

| Date | SOP | Task | Score | Outcome | By |
|---|---|---|---|---|---|

*(Empty. First row added on first SOP-driven task after this REF is approved.)*

---

## Change History

| Date | Change | By |
|---|---|---|
| 2026-05-06 | Initial REF, supersedes withdrawn FXA-2248-PRP-SOP-Outcome-Log. Round-3 multi-model review (Gemini-3.1 9.1 PASS, GLM-5.1 8.0 FIX, DeepSeek 6.9 FIX, Codex GPT-5.5 6.1 FIX) converged on Path Y: zero-code markdown notebook over 290-LoC structured-JSONL system. Codex's FXA-2230-reuse argument and DeepSeek's markdown-table alternative both lead to this artifact; the user chose Path Y as the most aligned with alfred's document-first, framework-agnostic philosophy. | Claude Code (Opus 4.7) |
