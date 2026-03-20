# SOP-1103: Workflow Routing

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-20
**Last reviewed:** 2026-03-20
**Status:** Active
**Related:** COR-1607 (deprecated, replaced by this document)

---

## What Is It?

The session-start routing SOP. Read this at the beginning of every task to determine which SOPs to follow, in what order. Contains an intent-based router and golden rules extracted from all COR SOPs.

---

## When to Use

- At the start of any new task or session
- When unsure which SOP or document type applies to the work at hand
- Before creating any document (PRP, CHG, ADR, INC, PLN)

---

## Intent-Based Router

```
═══ ALWAYS (every session, every task) ═══

• COR-1402: Declare 📋 active SOP before work and on every transition
• COR-1103: Route the task before reading detailed SOPs

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

6. None of the above?
   └── Ask one clarifying question, or flag ⚠️ no matching SOP

═══ OVERLAYS (apply after primary route) ═══

• Code behavior changes     → COR-1500 (TDD: RED → GREEN → REFACTOR)
• PRP approval              → COR-1602 strict (both reviewers >= 9)
• Choose review workflow    → COR-1606
• Compound task (A AND B)   → Split into sub-routes, COR-1402 each transition
• Confidence < 90%          → Ask one clarifying question before proceeding
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

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version, replaces COR-1607. Intent-based router + golden rules per ALF-2205 PRP | Frank + Claude Code |
