# REF-2146: Evolution-Philosophy

**Applies to:** FXA project
**Last updated:** 2026-03-30
**Last reviewed:** 2026-03-30
**Status:** Active

---

## North Star: Compression as Intelligence

Same behavior, minimum code + documentation.

```
Fitness Function: same behavior / (lines of code + document words)
```

## Direction Priority

1. **Determinism first** — convert natural language logic into deterministic Python code
2. **Minimization second** — shortest unambiguous expression of the same behavior

## Evaluator Thresholds

| Parameter | Value | Notes |
|-----------|-------|-------|
| Candidate discard threshold | < 7.0 | Candidates scoring below this are dropped |
| Review pass threshold | >= 9.0 | Both Codex and Gemini must reach this |

## Evaluator Weights — Evolve-SOP

| Dimension | Weight | Measures |
|-----------|--------|---------|
| Necessity | 30% | Evidence from validate output / issues / logs |
| Consistency | 25% | No conflict with other SOPs or COR-0002 |
| Atomicity | 20% | Preserves COR-1400 (one SOP = one thing) |
| Actionability | 15% | Agent can execute the SOP more precisely after change |
| Impact | 10% | How frequently referenced; how significant the improvement |

## Evaluator Weights — Evolve-CLI

| Dimension | Weight | Measures |
|-----------|--------|---------|
| Test verifiability | 35% | pytest can cover the change; result is observable |
| Scope restraint | 30% | Change boundary is clear, does not cascade into unrelated modules |
| Backward compatibility | 20% | Existing CLI interface unchanged |
| Necessity | 15% | Concrete evidence (test failure / lint / duplication) not "feels improvable" |

## Threshold Update Policy

Thresholds and weights in this document may be updated via the standard PRP/CHG lifecycle only — not by the evolve SOPs directly. Review after the first 5–10 runs.

## Prohibited Mutation Surface

The evolve SOPs are explicitly prohibited from modifying:
- `FXA-2148-SOP-Evolve-SOP.md`
- `FXA-2149-SOP-Evolve-CLI.md`
- `FXA-2146-REF-Evolution-Philosophy.md` (this document)

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-30 | Initial version from FXA-2145 PRP (approved R9) | Frank + Claude |
