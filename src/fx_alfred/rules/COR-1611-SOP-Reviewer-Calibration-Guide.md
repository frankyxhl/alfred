# SOP-1611: Reviewer Calibration Guide

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-20
**Last reviewed:** 2026-03-20
**Status:** Active
**Task tags:** [review, calibration]

---

## What Is It?

Shared calibration guide for all COR-1602 reviewers (Codex, Gemini, or any future model). Ensures symmetric review standards regardless of which model performs the review.

---

## Before Scoring

1. Read the artifact-specific rubric:
   - PRP → COR-1608
   - CHG → COR-1609
   - Code → COR-1610
   - Other → COR-1609 (fallback)
2. Read this calibration guide (COR-1611)
3. For PRP reviews: check the Hard Gate (Open Questions resolved?) first

## Mandatory Rules

1. **Cross-reference source files** mentioned in the artifact. If artifact references no files, note this and skip.
2. **Cite file:line or section** for every deduction. Unsupported deductions are not valid.
3. **Distinguish blocking vs advisory.** Blocking affects the score. Advisory is noted but does not deduct.
4. **Do NOT deduct** for issues explicitly listed as out-of-scope in the artifact.
5. **Score 10 only** when zero improvements are possible. **Hard rule:** if you noted ANY advisory or improvement for a dimension, that dimension's maximum score is 9.8. If you noted a blocking issue, maximum is 9.0. A final weighted average of 10.0 is only valid if every individual dimension is 10.0 with zero notes.
6. **Check COR-0002 compliance** of the artifact itself (metadata format, required fields, Status value).
7. **Flag unaddressed Round N-1 feedback** explicitly. If the previous round's blocking issues were not resolved, note this.
8. **List at least one improvement suggestion** even on a passing review (advisory, no deduction).
9. **Round scores to one decimal.** 8.9 is FIX, 9.0 is PASS.

## Common Pitfalls to Avoid

| Pitfall | How to avoid |
|---------|-------------|
| Inflating scores to avoid conflict | If you noted issues, score accordingly |
| Deducting for wording/style when meaning is clear | Focus on substance, not prose |
| Requiring changes that contradict out-of-scope | Read the Scope section first |
| Over-indexing on minor issues while missing structural problems | Score structural issues higher |
| Giving 10/10 as default | 10 means "I cannot improve this" — prove it. Any noted advisory → max 9.8 |
| Asymmetric standards | Apply the same rubric and rules regardless of which model you are |

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version per FXA-2221. Merged from separate Codex/Gemini guides into single shared guide. | Frank + Claude Code |
