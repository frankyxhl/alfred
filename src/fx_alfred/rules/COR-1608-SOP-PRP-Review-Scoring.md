# SOP-1608: PRP Review Scoring

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-20
**Last reviewed:** 2026-03-20
**Status:** Active

---

## What Is It?

The scoring rubric for reviewing PRP (Proposal) documents under COR-1602. Reviewers must read this before scoring any PRP.

---

## Hard Gate

Before scoring dimensions, check: **Are all Open Questions resolved?**
- If any OQ is unresolved → return **FIX** immediately without scoring.
- Per COR-1102, all OQs must be resolved before PRP approval.

## Scoring Dimensions

| Dimension | Weight | What to check |
|-----------|--------|---------------|
| Problem Clarity | 20% | Is the pain real and specific? Not aspirational? |
| Scope Precision | 20% | In/out explicit? No ambiguity about boundaries? All affected SOPs listed? |
| Solution Completeness | 25% | Enough detail to implement without guessing? All behaviors defined? |
| Feasibility | 15% | Compatible with existing architecture? No hidden dependencies? |
| Necessity | 10% | Should this change exist at all? Is there a simpler alternative? |
| Risk Awareness | 10% | Failure modes listed? Trade-offs acknowledged? |

**Score = weighted average. Rounded to one decimal. >= 9.0 = PASS, < 9.0 = FIX.**

## Scoring Rules

1. Deductions must cite specific line/section. "Completeness: 7" without saying what's missing is not valid.
2. 10/10 means zero improvements possible. If you noted anything, it's not 10.
3. Distinguish **blocking** (affects score) vs **advisory** (noted, no deduction).
4. Do NOT deduct for issues explicitly listed as out-of-scope.
5. Cross-reference at least the source files mentioned in the artifact.
6. Check the artifact's own metadata compliance (COR-0002).
7. Scores rounded to one decimal. 8.9 is FIX, 9.0 is PASS.

## Output Format

```
### Hard Gate: [PASS/FAIL — OQs resolved?]

### Decision Matrix

| Dimension | Weight | Score | Deductions |
|-----------|--------|-------|------------|
| Problem Clarity | 20% | X/10 | specific issue |
| Scope Precision | 20% | X/10 | specific issue |
| Solution Completeness | 25% | X/10 | specific issue |
| Feasibility | 15% | X/10 | specific issue |
| Necessity | 10% | X/10 | specific issue |
| Risk Awareness | 10% | X/10 | specific issue |

**Weighted Average: X.X/10 — [PASS/FIX]**
```

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version per ALF-2208 | Frank + Claude Code |
