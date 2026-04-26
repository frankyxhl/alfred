# SOP-1609: CHG Review Scoring

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-20
**Last reviewed:** 2026-03-20
**Status:** Active
**Task tags:** [review, chg-review, scoring]

---

## What Is It?

The scoring rubric for reviewing CHG (Change Request) documents under COR-1602. Also used as the fallback rubric for PLN, ADR, design, and other non-PRP/non-Code artifacts.

---

## Scoring Dimensions

| Dimension | Weight | What to check |
|-----------|--------|---------------|
| Correctness | 25% | Does the change do what it claims? Aligns with PRP (if any)? |
| Completeness | 25% | What/Why/Impact/Plan all filled? Edge cases covered? |
| TDD Plan Quality | 20% | Test cases enumerated? RED-GREEN-REFACTOR sequence clear? (N/A for non-code CHGs) |
| Consistency | 15% | Follows COR-0002 format? Uses existing helpers/patterns? |
| Rollback Safety | 15% | Rollback plan realistic? Side effects addressed? |

**Score = weighted average. Rounded to one decimal. >= 9.0 = PASS, < 9.0 = FIX.**

For non-code CHGs where TDD is not applicable, redistribute the 20% TDD weight equally to Completeness (35%) and Consistency (25%).

## Scoring Rules

Same as COR-1608:
1. Deductions must cite specific line/section.
2. 10/10 means zero improvements possible.
3. Distinguish blocking vs advisory.
4. Do NOT deduct for out-of-scope issues.
5. Cross-reference source files mentioned in the artifact.
6. Check COR-0002 metadata compliance.
7. Rounded to one decimal. 8.9 is FIX, 9.0 is PASS.

## Output Format

```
### Decision Matrix

| Dimension | Weight | Score | Deductions |
|-----------|--------|-------|------------|
| Correctness | 25% | X/10 | specific issue |
| Completeness | 25% | X/10 | specific issue |
| TDD Plan Quality | 20% | X/10 | specific issue (or N/A) |
| Consistency | 15% | X/10 | specific issue |
| Rollback Safety | 15% | X/10 | specific issue |

**Weighted Average: X.X/10 — [PASS/FIX]**
```

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version per FXA-2221 | Frank + Claude Code |
