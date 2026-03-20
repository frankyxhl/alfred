# SOP-1102: Create Proposal

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-19
**Last reviewed:** 2026-03-19
**Status:** Active

---

## What Is It?

The process for creating and reviewing a Proposal (PRP) document. A PRP captures the design of a new feature, tool, or system change before implementation begins. It must be reviewed and approved before work starts.

---

## When to Use — Document Type Decision Table

| Question | Yes → | No → |
|----------|-------|------|
| Is this a **new feature, tool, or command**? | **PRP** | ↓ |
| Is this a **change to existing config, infra, or architecture**? | **CHG** (COR-1101) | ↓ |
| Is this a **decision that needs to be recorded** (already made)? | **ADR** (COR-1100) | ↓ |
| Is this a **bug fix or incident**? | **INC** | ↓ |
| Is this a **multi-step project plan** (not a design)? | **PLN** | ↓ |
| Otherwise | Use COR-1001 generic document creation | |

**PRP vs CHG:** PRP is for designing something that doesn't exist yet. CHG is for modifying something that already exists. If the change requires significant upfront design, start with PRP; the CHG can be filed during implementation.

**PRP vs PLN:** PRP defines *what* to build and *why*. PLN defines *how* to execute (schedule, phases, milestones). A PRP may contain an Implementation Plan section, but a standalone PLN is for coordinating execution of already-approved work.

---

## Naming Convention

```
<PREFIX>-<ACID>-PRP-<Title-With-Hyphens>.md
```

Examples:
- `FXA-2104-PRP-AF-Update-Command.md`
- `NRV-3100-PRP-Payment-Gateway-Integration.md`

---

## PRP Lifecycle

```
  Draft ──── COR-1602 Review ────► Approved ────► Implemented
    │              │                                    │
    │         FIX (< 9)                           af update
    │              │                        --status Implemented
    ▼              ▼
  Revise ◄──── feedback
    │
    │         PASS (>= 9)
    ▼
 Approved
    │
    │    or
    ▼
 Rejected ──── record reason, commit as-is
```

| Status | Meaning |
|--------|---------|
| Draft | Initial version, not yet reviewed |
| Approved | Passed COR-1602 review (both reviewers >= 9) |
| Rejected | Review concluded the proposal is unnecessary or flawed |
| Implemented | Approved and code/docs delivered |

---

## PRP Template

```markdown
# PRP-<ACID>: <Title>

**Applies to:** <PREFIX> project
**Last updated:** YYYY-MM-DD
**Last reviewed:** YYYY-MM-DD
**Status:** Draft
**Related:** <D item, other documents>
**Reviewed by:** —

---

## What Is It?

<One-paragraph summary of the proposed feature/tool/change.>

---

## Problem

<Why this is needed. What pain exists today. Be specific.>

---

## Scope

**In scope (v1):**
- <what will be built>

**Out of scope (v1):**
- <what will NOT be built, and why>

---

## Proposed Solution

### Command signature (if CLI)

\`\`\`bash
af <command> <args> [options]
\`\`\`

### Options

| Option | Description |
|--------|------------|
| `--flag` | description |

### Behaviors

<Detailed behavior descriptions, error handling, edge cases.>

---

## Open Questions

1. <Question that needs to be resolved before approval>

---

## Change History

| Date | Change | By |
|------|--------|----|
| YYYY-MM-DD | Initial version | — |
```

---

## Steps

### 1. Create the PRP document

```bash
af create prp --prefix <PREFIX> --area <AREA> --title "<Feature Name>"
```

### 2. Fill in required sections

Every PRP must contain these sections:

| Section | Purpose | Required? |
|---------|---------|-----------|
| **What Is It?** | One-paragraph summary | Yes |
| **Problem** | Why this is needed — what pain exists today | Yes |
| **Scope** | What's in v1, what's explicitly out of scope | Yes |
| **Proposed Solution** | Design details, behaviors, error handling | Yes |
| **Open Questions** | Unresolved design decisions (numbered) | Yes |
| **Document Structure Contract** | When the feature parses/writes document content | If relevant |
| **Implementation Plan** | When the implementation has multiple steps | If relevant (otherwise reference COR-1606 at implementation time) |
| **Layer Behavior** | When the feature interacts with PKG/USR/PRJ layers | If relevant |

### 3. Review via COR-1602 (Parallel Review) — strict mode

Submit the PRP to at least 2 reviewers using COR-1602.

**PRP review is a strict subset of COR-1602:** the Leader CANNOT use COR-1602's "Leader accepts the synthesis" or "max rounds reached, Leader makes final call" escape hatches. For PRP approval, the ONLY valid path is:

- **Hard gate:** All Open Questions must be resolved before review begins. Reviewers check this first — if any OQ is unresolved, return FIX without scoring dimensions.
- **Both reviewers score >= 9.0/10** using COR-1608 (PRP Review Scoring rubric) and COR-1611 (Reviewer Calibration Guide)

**If FIX:** revise based on deductions, resubmit for re-review.

**If one reviewer gives PASS and the other gives FIX:** address the FIX reviewer's deductions and resubmit. Both must pass.

**If reviewers fundamentally disagree on necessity** (as with FXA-2105): Leader may Reject, request further revision rounds, or bring in a 3rd reviewer as tiebreaker. However, Approve still requires both reviewers >= 9 — Leader cannot override this to approve.

### 4. Record the outcome

After review concludes:

- **Approved:** update Status to `Approved`, proceed to implementation
- **Rejected:** update Status to `Rejected`, record the reason and reviewer scores in the PRP, commit as-is (rejected PRP is still valuable documentation of what was considered and why)

### 5. Implement (if approved)

Follow the implementation plan in the PRP. If no implementation plan is included, use COR-1606 (Workflow Selection) to choose the appropriate workflow SOP. After implementation:

- Update PRP Status to `Implemented`
- Add implementation commit reference to Change History

---

## Quality Checklist

Before submitting for review, verify:

- [ ] Problem section explains the pain, not just the solution
- [ ] Scope explicitly states what is out of scope
- [ ] Proposed Solution has enough detail to implement without ambiguity
- [ ] Error handling is defined for all failure modes
- [ ] Open Questions are listed (even if the list is empty)
- [ ] Examples show realistic usage

---

## Example

```
Task: Design af update command
Prefix: FXA, Area: 21

1. af create prp --prefix FXA --area 21 --title "AF Update Command"
2. Fill in Problem, Scope, Proposed Solution, Open Questions
3. /team codex+gemini "review PRP-2104"
   Round 1: Codex 6.2, Gemini 8.5 → FIX
   Round 2: Codex 8.3, Gemini 9.8 → FIX (Codex)
   Round 3: Codex 9.2, Gemini 10 → PASS (both >= 9)
4. Status → Approved
5. Implement via COR-1601, commit
6. Status → Implemented
```

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-19 | Initial version, based on FXA-2104/2105 PRP experience | Frank + Claude |
| 2026-03-19 | Round 1 revision: added document type decision table, naming convention, full template, strict approval rules, COR-1606 reference | Frank + Claude |
| 2026-03-19 | Round 2 revision: fixed strict-mode contradiction (Leader cannot approve-override), unified status to Implemented, fixed naming terminology | Frank + Claude |
