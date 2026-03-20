# SOP-1603: Workflow — Parallel Module Implementation

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-19
**Last reviewed:** 2026-03-19
**Status:** Active

---

## What Is It?

A collaboration pattern where multiple Workers develop different modules or tasks concurrently, followed by a unified review. The Leader coordinates the split, and a Reviewer (or the Leader) validates the combined result.

Also known as: Multi-Module Development, Divide and Conquer.

**Output retention: composable** — all Worker outputs are kept and integrated into the final result. Compare with COR-1604 (competitive — only the winner is kept).

---

## Why

Reduces wall-clock time by running independent modules in parallel, then validating the combined result in a single review pass.

---

## Roles

| Role | Responsibility | Count |
|------|---------------|-------|
| **Leader** | Splits the work, assigns modules, coordinates merge, receives final result | 1 |
| **Worker** | Implements one module/task independently | 2+ |
| **Reviewer** | Reviews the combined output after all Workers complete | 0+ (Leader can review) |

---

## Sequence Diagram

```
Leader      Worker A    Worker B    Worker C    Reviewer
  │            │           │           │           │
  │──module1──▶│           │           │           │
  │──module2──────────────▶│           │           │
  │──module3──────────────────────────▶│           │
  │            │           │           │           │  ← parallel work
  │◀──done─────│           │           │           │
  │◀──done────────────────│           │           │
  │◀──done────────────────────────────│           │
  │                                                │
  │──review all───────────────────────────────────▶│
  │◀──findings────────────────────────────────────│
  │                                                │
  │──fix A────▶│           │           │           │  ← iteration (default: on)
  │──fix C────────────────────────────▶│           │
  │◀──done─────│           │           │           │
  │◀──done────────────────────────────│           │
  │──re-review────────────────────────────────────▶│
  │◀──PASS────────────────────────────────────────│
  │                                                │
  │  ✓ all modules accepted                        │
  │            │           │           │           │
```

---

## Steps

1. **Leader splits work** — define independent modules/tasks with clear boundaries
2. **Leader assigns Workers** — each Worker gets one module
3. **Workers execute in parallel** — each produces their deliverable independently
4. **Leader collects results** — waits for all Workers to complete
5. **Leader dispatches review** — sends combined output to Reviewer(s)
6. **Reviewer(s) review** — evaluate the combined result, flag issues per module
7. **If issues found and iteration is on** — Leader routes fixes back to the relevant Worker(s), re-review after fixes
8. **If all approved** — task complete

---

## Iteration Mode

**Default: on** — After review, Leader dispatches fixes to relevant Workers, then re-reviews until approved.

**To disable** (single-pass mode): set `iterate: false` when invoking the SOP.

```
/team plan --sop 1603 --no-iterate "implement auth, order, payment modules"
```

When off: Workers produce, Reviewer scores, Leader receives results as-is.

| Setting | Behavior |
|---------|----------|
| `iterate: true` (default) | Parallel work → Review → Fix → Re-review → ... until approved |
| `iterate: false` | Parallel work → Review → done (single pass) |

**Max rounds:** 3 (default). Configurable.

---

## Termination Criteria

- Reviewer(s) approve the combined result
- Or: Leader accepts (with justification)
- Or: maximum iteration count reached (default: 3 rounds), Leader makes final call

---

## Review Scoring

**Pass threshold: >= 9/10.** Scores below 9 require revision.

Reviewers must provide a decision matrix with per-dimension scores:

| Dimension | Score (1-10) | Deductions |
|-----------|-------------|------------|
| Correctness | | e.g., logic error in module A |
| Completeness | | e.g., missing integration between modules |
| Clarity | | e.g., unclear interface contract |
| Consistency | | e.g., inconsistent patterns across modules |
| **Overall** | | **>= 9 = PASS, < 9 = FIX** |

- **PASS** (>= 9): no revision needed, approved
- **FIX** (< 9): Leader routes deduction reasons to relevant Worker(s)

---

## Prerequisites

- Work must be decomposable into independent modules with minimal shared state
- Clear interface contracts between modules (if they interact)

---

## When to Use

- Multiple independent modules or features to implement
- Work can be cleanly divided without shared mutable state
- Time-sensitive tasks where parallelism saves wall-clock time

---

## When NOT to Use

- Tightly coupled work where one module depends on another's output
- Single indivisible task (use COR-1600 or COR-1601)
- When module boundaries are unclear (split first, then use this SOP)
- When only one approach should survive (use COR-1604 Exploration instead)

---

## Example

```
Task: Implement FXA-2107 Code Quality Refactoring (3 steps)
Leader: Claude Code
Workers: Coder A (Step 1: source.py), Coder B (Step 2: Traversable fix)
Reviewer: Codex + Gemini (after all steps done)

Phase 1 (parallel):
  Coder A creates core/source.py → done
  Coder B fixes Traversable protocol → done

Phase 2 (sequential, depends on Phase 1):
  Coder C refactors find_document() → done

Phase 3 (review):
  Codex + Gemini review all changes → 2 minor fixes found
  Workers fix → re-review → PASS ✓
```

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-19 | Initial version, with sequence diagram (D4), iteration mode (D3), review scoring (D9), output_retention: composable (D6), Workflow prefix (D5) | Claude Code |
| 2026-03-20 | Added Why section per ALF-2210 | Claude Code |
