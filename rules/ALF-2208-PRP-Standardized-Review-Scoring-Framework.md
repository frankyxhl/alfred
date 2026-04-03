# PRP-2208: Standardized Review Scoring Framework

**Applies to:** ALF project
**Last updated:** 2026-03-20
**Last reviewed:** 2026-03-20
**Status:** Implemented
**Related:** COR-1602, COR-1103

---

## What Is It?

A standardized scoring framework for COR-1602 reviews, with per-artifact-type scoring rubrics and a shared reviewer calibration guide. Ensures consistent, reproducible review quality regardless of which reviewer (Codex, Gemini, etc.) is used.

---

## Problem

During today's session implementing FXA-2116, ALF-2205, and ALF-2206, we observed:

1. **Inconsistent dimensions** — Gemini used 7 weighted dimensions one round, 4 the next. Codex used 5 dimensions with a different schema. No two reviews used the same rubric.
2. **Score inflation** — Gemini frequently gave 10/10 across all dimensions, while Codex scored the same artifact 5-8/10. The gap isn't about strictness — it's about undefined standards.
3. **Artifact-blind scoring** — The same 4-dimension rubric (Correctness/Completeness/Clarity/Consistency) was used for PRP, CHG, and code reviews, but these artifacts have fundamentally different quality criteria.
4. **No reviewer calibration** — Reviewers receive the artifact and a generic "score using this matrix" prompt. No guidance on common pitfalls, what to cross-reference, or how strict to be.

COR-1602 defines the review process (parallel dispatch, >= 9 to pass, max 3 rounds) but not the scoring content. This PRP fills that gap.

## Scope

**In scope:**
- 3 COR-level scoring rubric SOPs (one per artifact type: PRP, CHG, Code)
- 1 COR-level reviewer calibration guide (shared by all reviewers)
- Update COR-1602: replace existing 4-dimension matrix with artifact-specific rubric references
- Update COR-1102: clarify that Open Questions is a hard gate, not a scored dimension
- Update COR-1103: add scoring rubric selection to OVERLAYS

**Out of scope:**
- Changing the review process itself (still COR-1602, still >= 9, still max 3 rounds)
- Reviewer-specific prompt engineering (that's skill-level, not SOP-level)
- Automated scoring tools
- Per-reviewer SOPs (single shared calibration guide instead)

## Proposed Solution

### 4 new COR-level SOPs

#### COR-1608: PRP Review Scoring

Dimensions specific to proposal quality:

| Dimension | Weight | What to check |
|-----------|--------|---------------|
| Problem Clarity | 20% | Is the pain real and specific? Not aspirational? |
| Scope Precision | 20% | In/out explicit? No ambiguity about boundaries? All affected SOPs listed? |
| Solution Completeness | 25% | Enough detail to implement without guessing? All behaviors defined? |
| Feasibility | 15% | Compatible with existing architecture? No hidden dependencies? |
| Necessity | 10% | Should this change exist at all? Is there a simpler alternative? |
| Risk Awareness | 10% | Failure modes listed? Trade-offs acknowledged? |

**Hard gate (checked before scoring):** All Open Questions must be resolved per COR-1102. If any OQ is unresolved, the review returns FIX without scoring.

**Score = weighted average of dimensions above. >= 9 = PASS, < 9 = FIX.**

**Scoring rules (apply to all rubrics):**
- Deductions must cite specific line/section. "Completeness: 7" without saying what's missing is not valid.
- 10/10 means zero improvements possible. If you noted anything, it's not 10.
- Distinguish blocking (affects score) vs advisory (noted, no deduction).
- Do NOT deduct for issues explicitly listed as out-of-scope.
- Cross-reference at least the source files mentioned in the artifact.
- Check the artifact's own metadata compliance (COR-0002).
- Scores rounded to one decimal. 8.9 is FIX, 9.0 is PASS.

#### COR-1609: CHG Review Scoring

Dimensions specific to change request quality:

| Dimension | Weight | What to check |
|-----------|--------|---------------|
| Correctness | 25% | Does the change do what it claims? Aligns with PRP (if any)? |
| Completeness | 25% | What/Why/Impact/Plan all filled? Edge cases covered? |
| TDD Plan Quality | 20% | Test cases enumerated? RED-GREEN-REFACTOR sequence clear? |
| Consistency | 15% | Follows COR-0002 format? Uses existing helpers/patterns? |
| Rollback Safety | 15% | Rollback plan realistic? Side effects addressed? |

**Scoring rules:** Same as COR-1608 (cite deductions, 10 = zero improvements, blocking vs advisory, cross-reference source files, check COR-0002).

#### COR-1610: Code Review Scoring

Dimensions specific to code quality:

| Dimension | Weight | What to check |
|-----------|--------|---------------|
| Correctness | 25% | Logic correct? Handles edge cases? No regressions? |
| Test Coverage | 25% | All new behavior has tests? Tests test behavior not implementation? |
| Code Style | 15% | Consistent with existing codebase? Linter clean? |
| Security | 15% | No injection, no secrets, no unsafe operations? |
| Simplicity | 20% | Minimal code for the task? No over-engineering? No premature abstraction? |

**Scoring rules:** Same as COR-1608.

#### COR-1611: Reviewer Calibration Guide

Shared calibration guide for all reviewers (Codex, Gemini, or any future model). Replaces per-reviewer guides to ensure symmetric review standards.

**All reviewers must:**
1. Read the artifact-specific rubric (COR-1608/1609/1610) before scoring
2. Cross-reference source files mentioned in the artifact (if artifact references no files, note this and skip)
3. Cite file:line or section for every deduction
4. Distinguish blocking (affects score) vs advisory (no score impact)
5. Do NOT deduct for issues explicitly listed as out-of-scope
6. Score 10 only when zero improvements are possible
7. Check artifact's own metadata compliance (COR-0002)
8. If Round N-1 feedback was not addressed, flag it explicitly
9. List at least one improvement suggestion even on a passing review (advisory, no deduction)

**Common pitfalls to avoid:**
- Inflating scores to avoid conflict (if you noted issues, score accordingly)
- Deducting for wording/style when meaning is clear
- Requiring changes that contradict the artifact's stated out-of-scope
- Over-indexing on minor issues while missing structural problems

### Updates to existing SOPs

#### COR-1602 update

**Replace** the existing "Review Scoring" section (current 4-dimension matrix at lines 96-110) with:

```markdown
## Review Scoring

**Pass threshold: >= 9/10.** Scores below 9 require revision.

Before scoring, select the appropriate rubric based on artifact type:
- PRP (Proposal) → COR-1608
- CHG (Change Request) → COR-1609
- Code → COR-1610
- Other (PLN, ADR, design, etc.) → use COR-1609 (CHG rubric) as fallback

All reviewers must follow COR-1611 (Reviewer Calibration Guide).

Score = weighted average of the rubric's dimensions, rounded to one decimal.
- **PASS** (>= 9.0): approved
- **FIX** (< 9.0): Leader revises based on deduction reasons
```

The current Correctness/Completeness/Clarity/Consistency matrix is **replaced**, not preserved alongside. The new rubrics subsume those dimensions with artifact-specific granularity.

#### COR-1102 update

Two changes:

1. In the "PRP Lifecycle" section, add:
```
**Hard gate:** All Open Questions must be resolved before review begins.
Reviewers must check this first — if any OQ is unresolved, return FIX
without scoring dimensions.
```

2. Replace "the standard decision matrix" reference (line 173) with:
```
Reviewers must provide scores using COR-1608 (PRP Review Scoring rubric)
and follow COR-1611 (Reviewer Calibration Guide).
```

This ensures COR-1102 points to the new rubric instead of the removed COR-1602 matrix.

#### COR-1103 update

Add to OVERLAYS section:

```
• Review scoring rubric    → COR-1608 (PRP) / COR-1609 (CHG) / COR-1610 (Code)
• Reviewer calibration     → COR-1611
```

### How it flows in practice

```
Leader dispatches review:
│
├── Hard gate: Open Questions resolved? (PRP only)
│   └── No → return FIX immediately
│
├── Select rubric by artifact type:
│   ├── PRP → COR-1608
│   ├── CHG → COR-1609
│   └── Code → COR-1610
│
├── Include COR-1611 calibration guide
│
└── Reviewer receives: artifact + rubric + calibration guide
    └── Output: per-dimension scores + weighted average + deductions with citations
```

## Open Questions

None. All design decisions resolved:
- Reviewer guides merged into single COR-1611 (symmetric standards)
- COR-1602 matrix replaced (not wrapped)
- COR-1102 and COR-1103 explicitly updated
- Open Questions is a hard gate, not a weighted dimension
- "Necessity" dimension added to PRP rubric to cover over-engineering disagreements

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version based on session observations | Frank + Claude Code |
| 2026-03-20 | Round 1 revision: OQ as hard gate not dimension, replace COR-1602 matrix not wrap, add COR-1102/1103 updates, merge reviewer guides into single COR-1611, add Necessity dimension, shared scoring rules, resolve all OQs | Claude Code |
| 2026-03-20 | Round 2 revision: added fallback rubric for PLN/ADR/design, fixed COR-1102 stale "standard decision matrix" reference, fixed "per-reviewer" wording in intro | Claude Code |
