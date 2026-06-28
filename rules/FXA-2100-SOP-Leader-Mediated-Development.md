# SOP-2100: Leader Mediated Development

**Applies to:** FXA project
**Last updated:** 2026-06-28
**Last reviewed:** 2026-03-17
**Status:** Active
**Tags:** workflow, implement

---

## What Is It?

A Leader-mediated development workflow where a single implementation subagent (the `coder` agent) writes code and three independent reviewers (GLM + DeepSeek + MiniMax) evaluate in parallel. Based on COR-1601 (Leader Mediated Loop) with Claude as Leader coordinating the full cycle.

---

## Why

Separating code implementation from review, and using three independent reviewers, reduces bias and catches issues that a single reviewer would miss. The Leader-mediated pattern ensures no direct communication between coder and reviewers, preserving review independence.

---

## When to Use

- Developing new features or modifying existing code in FXA
- Any code change that requires independent review before merge
- Tasks where Leader (Claude) coordinates the implementation subagent (coder) and GLM + DeepSeek + MiniMax (reviewers)

---

## When NOT to Use

- Document-only changes in `fx_alfred/rules/` that don't need code review
- Trivial fixes where independent review is overkill (e.g., typo in a comment)
- Releasing to PyPI -- use FXA-2102 (Release To PyPI) instead

---

## Roles

| Role | Provider | Responsibility |
|------|----------|----------------|
| **Leader** | Claude | Coordinates, merges feedback, decides next action |
| **Coder** | Subagent (`coder`) | Implements code under TDD |
| **Reviewer A** | GLM (`trinity-glm`) | Independent code review |
| **Reviewer B** | DeepSeek (`trinity-deepseek`) | Independent code review |
| **Reviewer C** | MiniMax (`trinity-minimax`) | Independent code review |

---

## Flow

```
              ┌──────────────────────────────┐
              │       Leader (Claude)        │
              │  all communication flows     │
              │       through Leader         │
              └─┬──────┬──────┬──────┬───────┘
                │      │      │      │
          assign│ fwd  │ fwd  │ fwd  │
            task│output│output│output│
                ▼      ▼      ▼      ▼
             Coder   Rev A  Rev B  Rev C
           (coder)  (GLM)(DeepSeek)(MiniMax)
                │      │      │      │
          output│ score│ score│ score│
         toLeader│  to  │  to  │  to  │
                │Leader│Leader│Leader│
                ▼      ▼      ▼      ▼
              ┌──────────────────────────────┐
              │       Leader decides:        │
              │  - revise → instruct Coder   │
              │    with merged feedback      │
              │  - accept → all pass         │
              │  - arbitrate → conflicts     │
              └──────────────────────────────┘
```

**Key rule**: Coder and Reviewers never communicate directly. All output and feedback flows through Leader.

---

## Steps

1. **Leader assigns task to Coder** — clear deliverable, acceptance criteria
2. **Coder implements** — follows TDD (COR-1500), produces code + tests
3. **Coder submits output to Leader** — Coder does not contact Reviewers
4. **Leader forwards output to all three Reviewers simultaneously** — spawns `trinity-glm`, `trinity-deepseek`, and `trinity-minimax` as parallel review subagents (via the `/trinity` skill or the Agent tool)
5. **All three Reviewers return scores to Leader** — each scores using the COR-1610 rubric:

```
| Dimension      | Weight | GLM | DeepSeek | MiniMax |
|----------------|--------|-----|----------|---------|
| Correctness    |   25%  |  ?  |    ?     |    ?    |
| Test Coverage  |   25%  |  ?  |    ?     |    ?    |
| Code Style     |   15%  |  ?  |    ?     |    ?    |
| Security       |   15%  |  ?  |    ?     |    ?    |
| Simplicity     |   20%  |  ?  |    ?     |    ?    |
```

6. **Leader collects and merges feedback** — presents combined weighted averages
7. **Leader evaluates pass/fail**:
   - **Pass**: all three reviewers' weighted average >= 9.0/10
   - **Fail**: any reviewer's weighted average < 9.0
8. **If fail** — Leader merges issues from all three, instructs Coder to fix. Coder revises and submits back to Leader. Repeat from step 4. If 5 rounds reached without pass, Leader makes final call. Leader may also arbitrate a reviewer's sub-9.0 score down per COR-1621 severity triage when the residual finding is out-of-scope or pre-existing — documenting the rationale.
9. **If pass** — task complete

---

## Pass Criteria

- All three reviewers (GLM, DeepSeek, MiniMax) must achieve weighted average >= 9.0/10 per COR-1610
- Maximum 5 review rounds; Leader makes final call if not reached
- Leader may arbitrate severity disagreements per COR-1621 (e.g., a sub-9.0 score resting solely on a pre-existing or out-of-scope finding)

---

## Review Prompt Template

```
[CODE REVIEW REQUEST] Review <description>.
Read these source files: <file list>
Score using COR-1610 rubric (Correctness 25%, Test Coverage 25%, Code Style 15%, Security 15%, Simplicity 20%). Output the decision matrix.
List any issues.

[OPTIONAL — include when reviewing documents managed by project-specific tools]
[TOOL CONTEXT] This project uses the `af` CLI for document management:
- Read a document: af --root <project-root> read <ACID>
- List documents: af --root <project-root> list
- Validate documents: af --root <project-root> validate
Use these commands to locate referenced documents.
```

When dispatching reviews for projects with specialized CLIs (e.g., `af` for fx_alfred), include a Tool Context block so reviewers can access referenced documents. Omit for pure code reviews where standard file reads suffice.

---

## Conflict Resolution

When reviewers disagree:
- Leader evaluates each argument on technical merit
- Leader may side with any reviewer, or propose a different approach
- Leader documents reasoning in the review summary

## Examples

```bash
# Implement a new feature — Leader spawns one implementation subagent
Agent(subagent_type="coder", "implement FXA-2134 af plan command")

# Review — Leader spawns three reviewers in parallel
Agent(subagent_type="trinity-glm", "review af plan code")
Agent(subagent_type="trinity-deepseek", "review af plan code")
Agent(subagent_type="trinity-minimax", "review af plan code")
```

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-17 | Initial version | Claude Code |
| 2026-03-20 | FXA-2133: Add Why, When to Use, When NOT to Use sections (5W1H migration) | Claude Code |
| 2026-03-21 | Added Examples section | Claude Code |
| 2026-03-30 | CHG FXA-2154: Fix Step 4 `/ask` → `/trinity`, add round-limit guard to Step 8 | Claude Code |
| 2026-04-01 | CHG FXA-2174: Align scoring with COR-1610 (4 dims → 5 weighted dims), update pass criteria to weighted average | Claude Code |
| 2026-04-01 | CHG FXA-2180: Standardize role naming — replace Droid with GLM in description, roles table, and flow diagram | Claude Code |
| 2026-04-01 | CHG FXA-2181: Add optional Tool Context block to Review Prompt Template for project-specific CLI instructions | Claude Code |
| 2026-06-28 | Issue #249: correct workflow to actual practice — Coder = single subagent (`coder`); Reviewers = GLM + DeepSeek + MiniMax (3, replacing Codex + Gemini); update roles, flow, steps, scoring matrix, pass criteria, conflict resolution, examples; add COR-1621 arbitration note | Claude Code |
