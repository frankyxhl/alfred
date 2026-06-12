# Task: Independent code review — FXA-2303 `af export` implementation diff (COR-1610 CODE rubric)

Unique session marker: FXA2303-GLM-CODEREVIEW-R1-7c4e91

You are an independent code reviewer. Review the feature-implementation diff packaged in:

- `.review-packs/FXA-2303-code-review-pack.md` — READ THIS FIRST. It contains the review request, the pinned COR-1610 rubric, verification evidence, four special-attention asks, and the FULL diff vs main.

Cross-reference the spec:

- `rules/FXA-2303-PRP-AF-Export-Single-File-Runbook.md` — the Approved PRP whose 11 Specified Behaviors this diff claims to implement verbatim. Read it and audit the diff against it.

You may also read the actual repo source (`src/fx_alfred/`, `tests/`) to verify surrounding context beyond the diff hunks. Do NOT modify any files — this is a read-only review.

## Rubric — COR-1610 CODE (pinned; do NOT use any PRP rubric)

| Dimension | Weight |
|-----------|--------|
| Correctness | 25% |
| Test Coverage | 25% |
| Code Style | 15% |
| Security | 15% |
| Simplicity | 20% |

Scoring rules:
- Score each dimension 0-10 with a one-line justification; every deduction must cite `file:line`.
- Classify each finding BLOCKING or ADVISORY.
- No out-of-scope deductions — the PRP's Out-of-scope list governs scope.
- Weighted average = Σ(weight × score), rounded to one decimal. Recompute the arithmetic before printing it.
- Verdict: weighted average >= 9.0 → PASS, else FIX.

## Special attention (must be answered explicitly)

(a) **Per-behavior audit**: walk the PRP's 11 Specified Behaviors one by one — for each, state OK / mis-implemented / silently narrowed, with evidence (`file:line`). Pay particular attention to the selection-algebra edge: explicit `--type`/`--status` REPLACE that dimension's default gate (PRP D4 framing) rather than ANDing with it — confirm this reading matches the PRP text itself.
(b) **150-line function ratchet**: verify every new function in the diff complies with the 150-line ratchet.
(c) **`_load_corpus` tradeoff**: it reads the ENTIRE corpus (293 docs) up front even when exporting 1 positional doc — assess this simplicity-vs-IO tradeoff against the PRP's single-read-cache requirement; is it compliant, and is it the right call?
(d) **`guide_cmd` refactor**: confirm guide behavior is byte-equivalent after the refactor onto `core/routing` (including the `role` variable retained for the JSON payload).

## Required output (in this order)

1. **Per-behavior audit** — table over the 11 PRP behaviors: behavior → verdict (OK / mis-implemented / narrowed) → evidence.
2. **Special-attention answers** — (a)–(d) explicitly.
3. **Decision Matrix** — markdown table: Dimension | Weight | Score (0-10) | Weighted | Justification.
4. **Weighted average** (one decimal) and **verdict** (PASS / FIX).
5. **Findings** — BLOCKING list and ADVISORY list; each entry: `file:line` — description — why it matters.
6. **Structured result block** — end your reply with exactly one fenced JSON block:

```json
{
  "decision": "PASS",
  "weighted_score": 0.0,
  "blocking": ["..."],
  "advisories": ["..."],
  "confidence": 0.0
}
```

where `decision` is `"PASS"` or `"FIX"`, `weighted_score` is your recomputed weighted average, `blocking`/`advisories` are string lists (may be `[]`), and `confidence` is 0.0-1.0.
