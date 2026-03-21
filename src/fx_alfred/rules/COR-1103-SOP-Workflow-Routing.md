# SOP-1103: Workflow Routing

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-22
**Last reviewed:** 2026-03-20
**Status:** Active
**Related:** COR-1607 (deprecated, replaced by this document)

---

## What Is It?

The session-start routing SOP. Read this at the beginning of every task to determine which SOPs to follow, in what order. Contains an intent-based router and golden rules extracted from all COR SOPs.

---

## Why

Ensures every task follows the correct SOP from the start, preventing wasted effort from following the wrong workflow.

---

## When to Use

- At the start of any new task or session
- When unsure which SOP or document type applies to the work at hand
- Before creating any document (PRP, CHG, ADR, INC, PLN)

---

## When NOT to Use

- Mid-task when you have already routed and are following a specific SOP
- For tasks that have an explicit SOP reference provided by the caller

---

## Workflow Sequence

```
Session Start
     │
     ▼
af guide ──────────► Read routing (PKG → USR → PRJ)
     │
     ▼
Identify task ─────► Match PRIMARY ROUTE (1-7)
     │
     ▼
af plan <SOPs> ────► Generate checklist
     │
     ▼
Execute ───────────► Follow checklist step by step
     │                  │
     │            ┌─────┴──────┐
     │            ▼            ▼
     │       Code change?   Doc/SOP?
     │            │            │
     │         TDD (1500)   af create
     │            │            │
     │         Review       Review
     │         (1602)       (1600)
     │            │            │
     │            └─────┬──────┘
     │                  ▼
     │              Commit
     │                  │
     ▼                  ▼
Session End ───► af validate → commit
```

---

## Intent-Based Router

```
═══ ALWAYS (every session, every task) ═══

• COR-1402: Declare 📋 active SOP before work and on every transition
• COR-1103: Route the task before reading detailed SOPs
• af plan:  Before every response — decide if task needs a checklist; if task has clear steps or spans multiple SOPs, run af plan <SOP_IDs> before proceeding

═══ PRIMARY ROUTE (stop at first match) ═══

Note: "Pure document management" (branch 1) means managing reference
material (REF, Glossary, Index) — NOT creating lifecycle documents
like PRP, CHG, ADR, PLN, INC. Those match branches 2-5.

1. Pure document management? (REF, Glossary, SOP creation, metadata update)
   ├── New SOP               → COR-1000
   ├── New reference doc     → COR-1001
   └── Update existing doc   → COR-1300

2. Something broken/failing/unexpected?
   ├── Bug/incident          → INC (project-level SOP)
   └── Fix requires system change → INC + CHG (COR-1101)

3. New capability/design that doesn't exist yet?
   └── PRP (COR-1102) → Review (COR-1602 strict) → CHG (COR-1101)
       └── Execution coordination needed? → PLN

4. Change to existing system/config/architecture?
   NOTE: If the change requires significant upfront design, start with
   PRP (COR-1102) first; file CHG during implementation.
   ├── Standard (pre-approved per referenced SOP) → CHG (COR-1101), no review
   ├── Normal  → CHG (COR-1101) → Review (COR-1606 to select) → TDD (COR-1500)
   ├── Emergency → CHG (COR-1101) → Execute → Post-approval within 24h
   └── Data migration → CHG (COR-1101, specify change type) → Execute → Validate

5. Record a durable decision already made?
   └── ADR (COR-1100)

6. Track/discuss a topic within this session?
   └── COR-1201 (Discussion Tracking)
       D new <topic> → create new D item
       D list → show all D items

7. None of the above?
   └── Ask one clarifying question, or flag ⚠️ no matching SOP

═══ OVERLAYS (apply after primary route) ═══

• Code behavior changes     → COR-1500 (TDD: RED → GREEN → REFACTOR)
• PRP approval              → COR-1602 strict (both reviewers >= 9)
• New SOP/doc created       → Review via COR-1600 (Direct Review) at minimum
• Choose review workflow    → COR-1606
• Compound task (A AND B)   → Split into sub-routes, COR-1402 each transition
• Confidence < 90%          → Ask one clarifying question before proceeding
• Background agents running → Proactively report progress on every user message (check output file sizes, show line counts)
• Review scoring rubric    → COR-1608 (PRP) / COR-1609 (CHG) / COR-1610 (Code) + COR-1611 (calibration)
• SOP section compliance   → af validate checks required sections (What/Why/When to Use/When NOT/Steps)
```

---

## Golden Rules

Essential rules from COR SOPs. Read these at session start; only read the full SOP when executing that specific workflow.

```
COR-1402: Always declare 📋 active SOP before work and when switching
COR-1102: New capability/design → PRP; no implementation until COR-1602 strict approval
COR-1101: Existing system/config change → CHG with What, Why, Impact, Plan; Standard changes are pre-approved (no review)
COR-1500: Any code behavior change → failing test first, then green, then refactor
COR-1100: Durable decision already made → ADR, write immediately
COR-1300: Existing document edit → af update, update Last updated + Change History; never delete, deprecate instead (COR-1301)
COR-1000/1001: New SOP → COR-1000; new document → af create (COR-1001) with correct prefix, ACID, type, template
COR-1201: Track discussion items with D new/list/show/start/done/defer/archive
COR-1608/1609/1610: Review scoring — PRP → 1608, CHG → 1609, Code → 1610; always use weighted rubric
COR-1611: Reviewer calibration — cite deductions, 10 = zero improvements, blocking vs advisory
Reading an SOP: af read → What + Why → When to Use → When NOT → Prerequisites → Pitfalls → Steps (COR-1402 each step)
```

---

## Review Workflow Selection

When a step says "COR-1606 to select workflow", read COR-1606 and choose based on context:

| Workflow | SOP | When to use |
|----------|-----|-------------|
| Direct Review Loop | COR-1600 | Simple changes, single reviewer sufficient |
| Leader Mediated Review | COR-1601 | Complex changes needing leader judgment |
| Multi Model Parallel Review | COR-1602 | Significant changes, both reviewers must score >= 9 |

**Exception:** PRP review always uses COR-1602 strict mode (mandated by COR-1102). The leader cannot override to approve — both reviewers must pass.

---

## Creating Routing Documents for USR / PRJ Layers

To create a routing document, follow **COR-1004** (Create Routing Document).

`af guide` scans three layers for documents matching `*-SOP-Workflow-Routing*.md`. PKG is bundled. Run `af guide --root <project-root>` to verify all layers appear.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version, replaces COR-1607. Intent-based router + golden rules per ALF-2205 PRP | Frank + Claude Code |
| 2026-03-20 | Added USR/PRJ routing doc creation guide | Frank + Claude Code |
| 2026-03-20 | Added Why/When NOT to Use sections per ALF-2210 | Claude Code |
| 2026-03-21 | Added workflow sequence diagram, af plan to ALWAYS, new SOP review overlay | Claude Code |
| 2026-03-22 | Clarified af plan ALWAYS rule: per-response decision, not just session-start | Frank + Claude Code |
| 2026-03-22 | Reduced "Creating Routing Documents" section to pointer → COR-1004 | GLM |
