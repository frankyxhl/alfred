# SOP-1601: Leader Mediated Loop

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-15
**Last reviewed:** 2026-03-15

---

## What Is It?

A collaboration pattern where the Leader mediates every round between Worker and Reviewers. The Leader sees all feedback, can redirect the Worker, resolve conflicts, or change strategy.

---

## Roles

| Role | Responsibility | Count |
|------|---------------|-------|
| **Leader** | Defines task, routes feedback, arbitrates conflicts, may redirect strategy | 1 |
| **Worker** | Executes the task, revises based on Leader's instructions | 1+ |
| **Reviewer** | Reviews output, provides feedback or approval | 1+ |

Roles are not bound to specific models. Assign at invocation time.

---

## Flow

```
        ┌─────────────────────────────────┐
        │            Leader               │
        │  (sees everything, arbitrates)  │
        └──┬──────────────────────────┬───┘
           │                          ▲
     assign task              feedback + scores
     + instructions                   │
           │                          │
           ▼                          │
        Worker ── produces output ── Reviewer(s)
           ▲                          │
           │                          ▼
           └── Leader's decision: ── Approved?
               - revise (with guidance)    │
               - change direction         Yes
               - accept as-is              │
                                           ▼
                                     Task complete
```

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

## Termination Criteria

- All designated Reviewers have approved
- Or: Leader accepts the deliverable (with justification if overriding reviewers)
- Or: maximum iteration count reached (default: 5 rounds), Leader makes final call

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

Round 1: GLM proposes scheme → Codex likes it, Gemini says "areas overlap"
Leader: agrees with Gemini, tells GLM to reorganize areas
Round 2: GLM revises → Codex 9/10, Gemini 8/10 "needs examples"
Leader: tells GLM to add examples only, rest is good
Round 3: GLM adds examples → Codex 10/10, Gemini 10/10 ✓
Task complete
```

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-15 | Initial version | Claude Code |
