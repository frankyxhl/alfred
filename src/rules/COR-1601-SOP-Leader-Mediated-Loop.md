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
        ┌──────────────────────────────────┐
        │           Leader                 │
        │   ALL communication goes         │
        │   through Leader only            │
        └──┬────────────┬─────────────┬────┘
           │            │             │
     assign│     forward│      forward│
      task │     output │      output │
           │            │             │
           ▼            ▼             ▼
        Worker      Reviewer A    Reviewer B
           │            │             │
     output│      score │       score │
   to Leader│   to Leader│    to Leader│
           │            │             │
           ▼            ▼             ▼
        ┌──────────────────────────────────┐
        │   Leader decides next action:    │
        │   - revise (instruct Worker)     │
        │   - redirect (change approach)   │
        │   - arbitrate (resolve conflict) │
        │   - accept (task complete)       │
        └──────────────────────────────────┘
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
