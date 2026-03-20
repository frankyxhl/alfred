# SOP-1610: Code Review Scoring

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-20
**Last reviewed:** 2026-03-20
**Status:** Active

---

## What Is It?

The scoring rubric for reviewing code changes under COR-1602.

---

## Scoring Dimensions

| Dimension | Weight | What to check |
|-----------|--------|---------------|
| Correctness | 25% | Logic correct? Handles edge cases? No regressions? |
| Test Coverage | 25% | All new behavior has tests? Tests test behavior not implementation? |
| Code Style | 15% | Consistent with existing codebase? Linter clean? |
| Security | 15% | No injection, no secrets, no unsafe operations? |
| Simplicity | 20% | Minimal code for the task? No over-engineering? No premature abstraction? |

**Score = weighted average. Rounded to one decimal. >= 9.0 = PASS, < 9.0 = FIX.**

## Scoring Rules

Same as COR-1608:
1. Deductions must cite specific file:line.
2. 10/10 means zero improvements possible.
3. Distinguish blocking vs advisory.
4. Do NOT deduct for out-of-scope issues.
5. Cross-reference the actual source files being reviewed.
6. Run or verify test results before scoring.
7. Rounded to one decimal. 8.9 is FIX, 9.0 is PASS.

## Output Format

```
### Decision Matrix

| Dimension | Weight | Score | Deductions |
|-----------|--------|-------|------------|
| Correctness | 25% | X/10 | file:line — specific issue |
| Test Coverage | 25% | X/10 | specific issue |
| Code Style | 15% | X/10 | specific issue |
| Security | 15% | X/10 | specific issue |
| Simplicity | 20% | X/10 | specific issue |

**Weighted Average: X.X/10 — [PASS/FIX]**
```

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version per ALF-2208 | Frank + Claude Code |
