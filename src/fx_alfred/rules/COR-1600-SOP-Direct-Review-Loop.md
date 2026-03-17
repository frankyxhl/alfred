# SOP-1600: Direct Review Loop

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-15
**Last reviewed:** 2026-03-15

---

## What Is It?

A collaboration pattern where the Worker iterates directly with Reviewers until approval, without Leader involvement in each round. The Leader only initiates the task and receives the final result.

---

## Roles

| Role | Responsibility | Count |
|------|---------------|-------|
| **Leader** | Defines the task, assigns roles, sets approval criteria, receives final result | 1 |
| **Worker** | Executes the task, revises based on feedback | 1+ |
| **Reviewer** | Reviews output, provides feedback or approval | 1+ |

Roles are not bound to specific models. Assign at invocation time.

---

## Flow

```
Leader
  │
  ├── 1. Define task + approval criteria
  ├── 2. Assign Worker and Reviewer(s)
  │
  ▼
Worker ──── produces output ────► Reviewer(s)
  ▲                                    │
  │                                    ▼
  └──── revise ◄──── feedback ◄── Approved?
                                    │
                                   Yes
                                    │
                                    ▼
                              Final result → Leader
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

## Termination Criteria

- All designated Reviewers have approved
- Or: maximum iteration count reached (default: 5 rounds), escalate to Leader

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
