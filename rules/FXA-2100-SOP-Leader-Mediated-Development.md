# SOP-2100: Leader Mediated Development

**Applies to:** FXA project
**Last updated:** 2026-04-06
**Last reviewed:** 2026-04-06
**Status:** Active

---

## What Is It?

A Leader-mediated development workflow where GLM implements code and two independent reviewers (Codex + Gemini) evaluate in parallel. Based on COR-1601 (Leader Mediated Loop) with Claude as Leader coordinating the full cycle.

---

## Why

Separating code implementation from review, and using two independent reviewers, reduces bias and catches issues that a single reviewer would miss. The Leader-mediated pattern ensures no direct communication between coder and reviewers, preserving review independence.

---

## When to Use

- Developing new features or modifying existing code in FXA
- Any code change that requires dual review before merge
- Tasks where Leader (Claude) coordinates GLM (coder) and Codex+Gemini (reviewers)

---

## When NOT to Use

- Document-only changes in `fx_alfred/rules/` that don't need code review
- Trivial fixes where dual review is overkill (e.g., typo in a comment)
- Releasing to PyPI -- use FXA-2102 (Release To PyPI) instead

---

## Roles

| Role | Provider | Responsibility |
|------|----------|----------------|
| **Leader** | Claude | Coordinates, merges feedback, decides next action |
| **Coder** | GLM | Implements code |
| **Reviewer A** | Codex | Independent code review |
| **Reviewer B** | Gemini | Independent code review |

---

## Flow

```
                  ┌──────────────────────────┐
                  │     Leader (Claude)      │
                  │  all communication goes  │
                  │     through Leader       │
                  └──┬───────┬──────────┬────┘
                     │       │          │
               assign│  forward│    forward│
                task │  output │    output │
                     │       │          │
                     ▼       ▼          ▼
                  Coder   Rev A      Rev B
                  (GLM) (Codex)   (Gemini)
                     │       │          │
                     │       │          │
               output│  score │    score │
              to Leader│to Leader│ to Leader│
                     │       │          │
                     ▼       ▼          ▼
                  ┌──────────────────────────┐
                  │     Leader decides:      │
                  │  - revise → instruct     │
                  │    Coder with merged     │
                  │    feedback              │
                  │  - accept → both pass    │
                  │  - arbitrate → conflicts │
                  └──────────────────────────┘
```

**Key rule**: Coder and Reviewers never communicate directly. All output and feedback flows through Leader.

---

## Steps

1. **Leader assigns task to Coder** — clear deliverable, acceptance criteria
2. **Coder implements** — follows TDD (COR-1500), produces code + tests
3. **Coder submits output to Leader** — Coder does not contact Reviewers
4. **Leader forwards output to both Reviewers simultaneously** — via `/trinity codex "review <description>" gemini "review <description>"`
5. **Both Reviewers return scores to Leader** — each scores using the COR-1610 rubric:

```
| Dimension      | Weight | Codex | Gemini |
|----------------|--------|-------|--------|
| Correctness    |   25%  |   ?   |   ?    |
| Test Coverage  |   25%  |   ?   |   ?    |
| Code Style     |   15%  |   ?   |   ?    |
| Security       |   15%  |   ?   |   ?    |
| Simplicity     |   20%  |   ?   |   ?    |
```

6. **Leader collects and merges feedback** — presents combined weighted averages
7. **Leader evaluates pass/fail**:
   - **Pass**: both reviewers' weighted average >= 9.0/10
   - **Fail**: either reviewer's weighted average < 9.0
8. **If fail** — Leader merges issues from both, instructs Coder to fix. Coder revises and submits back to Leader. Repeat from step 4. If 5 rounds reached without pass, Leader makes final call.
9. **If pass** — prepare merge/push artifacts and proceed to post-push intake
10. **Post-push review intake loop (max 3 iterations)**:
   - Wait for CI + incoming PR review comments after push
   - Categorize each item as:
     - **Actionable**: valid issue requiring fix
     - **Advisory**: suggestion noted; optional change
     - **False positive**: no change needed with rationale
   - If actionable items are **mechanical** (wording/format/small refactor), fix directly, re-run tests/checks, then continue loop
   - If actionable items are **substantive**, route back to Step 4 dual-review gate before continuing
   - Exit when CI is green and no unresolved actionable items remain, or loop limit is reached (record unresolved items for human follow-up)

---

## Pass Criteria

- Both Codex AND Gemini must achieve weighted average >= 9.0/10 per COR-1610
- Maximum 5 review rounds; Leader makes final call if not reached
- Post-push intake loop must end with CI green and 0 unresolved actionable items (or explicit handoff list if loop limit reached)

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

When Codex and Gemini disagree:
- Leader evaluates both arguments on technical merit
- Leader may side with either, or propose a third approach
- Leader documents reasoning in the review summary

## Examples

```bash
# Implement a new feature
/trinity glm "implement FXA-2134 af plan command"           # GLM writes code
/trinity codex "review af plan code" gemini "review af plan code"  # Codex+Gemini review
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
| 2026-04-06 | CHG FXA-2207: Add explicit post-push review-intake loop and closure rule (max 3 iterations) | Codex |
