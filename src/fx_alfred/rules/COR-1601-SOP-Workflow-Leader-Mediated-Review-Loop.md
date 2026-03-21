# SOP-1601: Workflow — Leader Mediated Review Loop

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-19
**Last reviewed:** 2026-03-19
**Status:** Active

---

## What Is It?

A collaboration pattern where the Leader mediates every round between Worker and Reviewers. The Leader sees all feedback, can redirect the Worker, resolve conflicts, or change strategy.

---

## Why

Keeps the Leader in the loop on every iteration so they can redirect strategy, resolve conflicting feedback, and maintain control over high-stakes or ambiguous deliverables.

---

## Roles

| Role | Responsibility | Count |
|------|---------------|-------|
| **Leader** | Defines task, routes feedback, arbitrates conflicts, may redirect strategy | 1 |
| **Worker** | Executes the task, revises based on Leader's instructions | 1+ |
| **Reviewer** | Reviews output, provides feedback or approval | 1+ |

Roles are not bound to specific models. Assign at invocation time.

---

## Sequence Diagram

```
Leader        Worker      Reviewer A    Reviewer B
  │             │             │             │
  │──assign────▶│             │             │
  │◀──v1────────│             │             │
  │──review v1───────────────▶│             │
  │──review v1─────────────────────────────▶│
  │◀──8/10───────────────────│             │
  │◀──FIX─────────────────────────────────│
  │                                         │
  │──fix notes─▶│             │             │  ← iteration (default: on)
  │◀──v2────────│             │             │
  │──review v2───────────────▶│             │
  │──review v2─────────────────────────────▶│
  │◀──10/10──────────────────│             │
  │◀──10/10───────────────────────────────│
  │                                         │
  │  ✓ all approved                         │
  │             │             │             │
```

**Key rule**: Worker and Reviewer(s) never communicate directly. All output and feedback flows through Leader.

---

## Steps

1. **Leader defines task** — clear deliverable, acceptance criteria, and which reviewers must approve
2. **Leader assigns roles** — specify which agent is Worker, which are Reviewers
3. **Worker executes** — produces first version
4. **Worker sends to Leader** — Leader forwards to Reviewer(s)
5. **Reviewer(s) review** — each provides feedback and score to Leader
6. **Leader evaluates feedback** — decides next action:
   - **Revise**: send specific instructions to Worker (may filter or merge reviewer feedback)
   - **Redirect**: change approach entirely, give Worker new instructions
   - **Arbitrate**: if reviewers contradict, Leader decides which feedback to follow
   - **Accept**: override reviewers and accept as-is (with justification)
7. **If revising** — Worker revises per Leader's instructions, repeat from step 4
8. **If all approved** — task complete

---

## Iteration Mode

**Default: on** — Leader forwards feedback to Worker, Worker revises and resubmits, until all Reviewers approve or max rounds reached.

**To disable** (single-pass mode): set `iterate: false` when invoking the SOP.

```
/trinity glm "task description"  # single pass — dispatch once, no re-review
```

When off: Worker produces once, Reviewer(s) score once, Leader receives all feedback and makes final decision without further revision rounds.

| Setting | Behavior |
|---------|----------|
| `iterate: true` (default) | Worker → Leader → Review → Leader → Worker revise → ... until approved |
| `iterate: false` | Worker → Leader → Review → Leader decides (single pass) |

**Max rounds:** 5 (default). Configurable. If max rounds reached, Leader makes final call.

---

## Termination Criteria

- All designated Reviewers have approved
- Or: Leader accepts the deliverable (with justification if overriding reviewers)
- Or: maximum iteration count reached (default: 5 rounds), Leader makes final call

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
- **FIX** (< 9): must revise; Leader routes deduction reasons to Worker

---

## When to Use

- Complex or ambiguous tasks where direction may shift
- Multiple reviewers who may give conflicting feedback
- High-stakes deliverables requiring Leader oversight
- Tasks where the Leader has context that Worker and Reviewers lack

---

## When NOT to Use

- Simple, well-defined tasks with clear acceptance criteria (use COR-1600 instead)
- When Leader involvement would just add latency without value

---

## Example

```
Task: Design a new PDCA numbering system
Leader: Claude Code
Worker: GLM
Reviewers: Codex, Gemini
Criteria: Both reviewers must approve

Round 1:
  GLM produces scheme → submits to Leader
  Leader forwards to Codex and Gemini
  Codex tells Leader: "looks good"
  Gemini tells Leader: "areas overlap"
  Leader agrees with Gemini, instructs GLM to reorganize areas

Round 2:
  GLM revises → submits to Leader
  Leader forwards to Codex and Gemini
  Codex tells Leader: 9/10
  Gemini tells Leader: 8/10 "needs examples"
  Leader instructs GLM to add examples only

Round 3:
  GLM adds examples → submits to Leader
  Leader forwards to Codex and Gemini
  Codex tells Leader: 10/10
  Gemini tells Leader: 10/10
  Leader: both approved ✓ → task complete
```

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-15 | Initial version | Claude Code |
| 2026-03-17 | Fixed flow diagram and example to enforce Leader-only communication; added key rule | Claude Code |
| 2026-03-19 | Added sequence diagram (D4), iteration mode (D3), review scoring (D9), renamed with Workflow prefix (D5) | Claude Code |
| 2026-03-20 | Added Why section per ALF-2210 | Claude Code |
