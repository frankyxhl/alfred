# SOP-1604: Workflow — Competitive Parallel Exploration

**Applies to:** All projects using the COR document system
**Last updated:** 2026-04-01
**Last reviewed:** 2026-04-01
**Status:** Active

---

## What Is It?

A collaboration pattern where the same task is given to multiple Workers with different approaches or constraints, and the Leader selects the best result. Used when the optimal approach is unknown and experimentation is cheaper than analysis.

Also known as: Competitive Implementation, A/B Exploration, Spike.

**Output retention: competitive** — only the winning Worker's output is kept; others are discarded. Compare with COR-1603 (composable — all outputs are kept and integrated).

---

## Why

Choosing the wrong approach early wastes more time than exploring several approaches in parallel. This workflow front-loads discovery so the Leader can make an evidence-based decision rather than guessing.

---

## When to Use

- Optimal approach is unknown and multiple viable paths exist
- Cost of parallel exploration is lower than cost of choosing wrong approach
- Comparing implementations (performance, readability, maintainability)
- Spiking / prototyping before committing to an approach

---

## When NOT to Use

- Approach is already decided (use COR-1600 or COR-1603)
- All outputs need to be integrated together (use COR-1603 Parallel Module Implementation instead)
- Task is too large to implement multiple times
- Only one reasonable approach exists

---

## Steps

1. **Leader defines task and approach variants** — same goal, different methods or constraints
2. **Leader assigns Workers** — each Worker gets one approach variant

   **Dispatch context:** When assigning Workers, include instructions for accessing project artifacts. Since all projects using this workflow have `af` installed, include:
   - `af read <ACID>` — read a document by ID
   - `af list` — list all documents

3. **Workers execute in parallel** — each produces their result independently
4. **Leader collects all results** — compares approaches
5. **(Optional) Reviewer evaluates** — ranks or scores each variant
6. **Leader selects winner** — based on quality, performance, simplicity, or other criteria
7. **If iteration is on** — Leader sends refinement instructions to the winning Worker, optionally re-reviewed
8. **Done** — Leader adopts the winning approach

---

## Roles

| Role | Responsibility | Count |
|------|---------------|-------|
| **Leader** | Defines the task, specifies approach variants, evaluates results, selects winner | 1 |
| **Worker** | Implements one approach variant independently | 2+ |
| **Reviewer** | (Optional) Evaluates all variants against criteria | 0+ |

---

## Sequence Diagram

```
Leader      Worker A    Worker B    Worker C    Reviewer
  │            │           │           │           │
  │──approach1▶│           │           │           │
  │──approach2────────────▶│           │           │
  │──approach3────────────────────────▶│           │
  │            │           │           │           │  ← parallel exploration
  │◀──result A─│           │           │           │
  │◀──result B────────────│           │           │
  │◀──result C────────────────────────│           │
  │                                                │
  │──all results──────────────────────────────────▶│  (optional)
  │◀──ranking─────────────────────────────────────│
  │                                                │
  │  select best                                   │
  │                                                │
  │──refine───▶│           │           │           │  ← iteration (default: on)
  │◀──final────│           │           │           │
  │──review final─────────────────────────────────▶│
  │◀──PASS────────────────────────────────────────│
  │                                                │
  │  ✓ winner selected and refined                 │
  │            │           │           │           │
```

---

## Iteration Mode

**Default: on** — After selecting the winner, Leader refines it with the winning Worker until satisfied.

**To disable** (single-pass mode): set `iterate: false` when invoking the SOP.

```
/trinity glm*3 "implement LRU cache three ways"  # single pass — select winner, done
```

When off: Workers produce variants, Leader selects, done. No refinement round.

| Setting | Behavior |
|---------|----------|
| `iterate: true` (default) | Explore → Select → Refine winner → Review → ... until approved |
| `iterate: false` | Explore → Select → done (single pass) |

**Max rounds:** 2 (default, applies to refinement phase only). Configurable.

---

## Termination Criteria

- Leader selects and (optionally) refines the winning approach
- Or: Reviewer approves the refined result
- Or: maximum refinement rounds reached, Leader makes final call

---

## Review Scoring

**Pass threshold: >= 9/10.** Scores below 9 require refinement of the winning approach.

Reviewers must provide a decision matrix with per-dimension scores for each variant:

| Dimension | Variant A | Variant B | Variant C | Deductions |
|-----------|----------|----------|----------|------------|
| Correctness | | | | e.g., edge case failure |
| Performance | | | | e.g., O(n²) vs O(n) |
| Simplicity | | | | e.g., excessive complexity |
| Maintainability | | | | e.g., hard to extend |
| **Overall** | | | | **>= 9 = PASS, < 9 = FIX** |

- **PASS** (>= 9): variant accepted as winner
- **FIX** (< 9): winning variant needs refinement; deduction reasons guide the refinement

---

## Example

```
Task: Implement LRU cache
Leader: Claude Code
Workers: GLM:a (OrderedDict), GLM:b (doubly-linked list), GLM:c (functools)
Reviewer: Codex
Criteria: best balance of performance and readability

Phase 1 (parallel):
  GLM:a implements OrderedDict version → done
  GLM:b implements linked list version → done
  GLM:c implements functools.lru_cache wrapper → done

Phase 2 (evaluate):
  Codex reviews all three:
    OrderedDict: 9/10 (clean, good perf)
    Linked list: 7/10 (complex, best perf)
    functools: 6/10 (too limited)

Phase 3 (refine):
  Leader selects OrderedDict version
  GLM:a adds thread safety → Codex re-reviews → 10/10 ✓
```

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-19 | Initial version, with sequence diagram (D4), iteration mode (D3), review scoring (D9), output_retention: competitive (D6), Workflow prefix (D5) | Claude Code |
| 2026-03-20 | Migrate to standard 5W1H section structure (FXA-2133 batch 6): add Why, move When to Use / When NOT to Use after What Is It | Claude Code |
| 2026-04-01 | CHG FXA-2183: Add dispatch context with af read/af list usage to dispatch steps | Claude Code |
