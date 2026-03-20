# SOP-1600: Workflow — Direct Review Loop

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-19
**Last reviewed:** 2026-03-19
**Status:** Active

---

## What Is It?

A collaboration pattern where the Worker iterates directly with Reviewers until approval, without Leader involvement in each round. The Leader only initiates the task and receives the final result.

---

## Why

Reduces Leader bottleneck on straightforward tasks by letting Workers and Reviewers iterate directly, freeing the Leader to focus on higher-level coordination.

---

## Roles

| Role | Responsibility | Count |
|------|---------------|-------|
| **Leader** | Defines the task, assigns roles, sets approval criteria, receives final result | 1 |
| **Worker** | Executes the task, revises based on feedback | 1+ |
| **Reviewer** | Reviews output, provides feedback or approval | 1+ |

Roles are not bound to specific models. Assign at invocation time.

**Lead Reviewer:** When multiple Reviewers are assigned, one must be designated as Lead Reviewer. If Reviewers give conflicting feedback, the Lead Reviewer's judgment takes precedence. If conflict cannot be resolved, escalate to COR-1601 (Leader Mediated Review Loop).

---

## Sequence Diagram

```
Leader    Worker    Reviewer A    Reviewer B
  │         │           │             │
  │──task──▶│           │             │
  │         │──v1──────▶│             │
  │         │──v1────────────────────▶│
  │         │◀──7/10────│             │
  │         │◀──6/10─────────────────│
  │         │                         │
  │         │──v2──────▶│             │  ← iteration (default: on)
  │         │──v2────────────────────▶│
  │         │◀──9/10────│             │
  │         │◀──10/10────────────────│
  │         │                         │
  │         │──v3──────▶│             │
  │         │──v3────────────────────▶│
  │         │◀──10/10───│             │
  │         │◀──10/10────────────────│
  │         │                         │
  │◀──done──│           │             │
  │         │           │             │
```

---

## Steps

1. **Leader defines task** — clear deliverable, acceptance criteria, and which reviewers must approve
2. **Leader assigns roles** — specify which agent is Worker, which are Reviewers
3. **Worker executes** — produces first version of the deliverable
4. **Worker sends to Reviewer(s)** — directly, not through Leader
5. **Reviewer(s) review** — each provides feedback or approval with a score
6. **If not all approved** — Worker revises based on feedback, sends again (repeat step 5)
7. **If all approved** — Worker sends final result to Leader
8. **Leader confirms** — task complete

---

## Iteration Mode

**Default: on** — Worker automatically revises based on Reviewer feedback and resubmits until all Reviewers approve or max rounds reached.

**To disable** (single-pass mode): set `iterate: false` when invoking the SOP.

```
/team plan --sop 1600 --no-iterate "task description"
```

When off: Worker produces once, Reviewer(s) score once, Leader receives result as-is regardless of scores.

| Setting | Behavior |
|---------|----------|
| `iterate: true` (default) | Worker → Review → Revise → Review → ... until approved |
| `iterate: false` | Worker → Review → done (single pass) |

**Max rounds:** 5 (default). Configurable. If max rounds reached without approval, escalate to Leader.

---

## Termination Criteria

- All designated Reviewers have approved
- Or: maximum iteration count reached (default: 5 rounds), escalate to Leader

---

## Review Scoring

**Pass threshold: >= 9/10.** Scores below 9 require revision.

Reviewers must provide a decision matrix with per-dimension scores:

| Dimension | Score (1-10) | Deductions |
|-----------|-------------|------------|
| Correctness | | e.g., logic error in step 3 |
| Completeness | | e.g., missing edge case handling |
| Clarity | | e.g., ambiguous variable naming |
| Consistency | | e.g., inconsistent with existing patterns |
| **Overall** | | **>= 9 = PASS, < 9 = FIX** |

- **PASS** (>= 9): no revision needed, approved
- **FIX** (< 9): must revise; deduction reasons guide the revision

---

## When to Use

- Simple, well-defined tasks
- Feedback is straightforward (fix X, add Y)
- Reviewers are unlikely to contradict each other

---

## When NOT to Use

- Task direction might need to change mid-way (use COR-1601 instead)
- Reviewers may give conflicting feedback requiring arbitration
- High-stakes deliverables where Leader needs visibility into each iteration

---

## Example

```
Task: Write a TDD Development Workflow SOP
Leader: Claude Code
Worker: GLM
Reviewers: Codex, Gemini
Criteria: Both reviewers must give 10/10

Round 1: GLM writes draft → Codex 8/10, Gemini 7/10
Round 2: GLM revises → Codex 9/10, Gemini 9/10
Round 3: GLM revises → Codex 10/10, Gemini 10/10 ✓
Final result → Claude Code
```

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-15 | Initial version | Claude Code |
| 2026-03-19 | Added sequence diagram (D4), iteration mode (D3), review scoring (D9), Lead Reviewer rule (D10), renamed with Workflow prefix (D5) | Claude Code |
| 2026-03-20 | Added Why section per ALF-2210 | Claude Code |
