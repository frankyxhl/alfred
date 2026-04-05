# SOP-1103: Workflow Routing

**Applies to:** All projects using the COR document system
**Last updated:** 2026-04-02
**Last reviewed:** 2026-04-02
**Status:** Active
**Related:** COR-1607 (deprecated, replaced by this document)
**Workflow input:** proposal:draft
**Workflow output:** task:routed

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
COR-1201 ──────────► Load/create today's Discussion Tracker, set next_d
     │
     ▼
af guide ──────────► Read routing (PKG → USR → PRJ)
     │
     ▼
Identify task ─────► Match PRIMARY ROUTE (1-8)
     │
     ▼
af plan <SOPs> ────► Generate checklist
     │
     ▼
COR-1606 ──────────► Select workflow (if multi-agent work needed)
     │
     ▼
Execute ───────────► Follow checklist step by step
     │                  (TDD overlay if code changes: COR-1500)
     ▼
Commit ────────────► af validate → Session End
```

---

## Intent-Based Router

```
═══ ALWAYS (every session, every task) ═══

• COR-1201: Load today's Discussion Tracker — search for today's file, read max DN, auto-increment on new topics (see COR-1201 Session Start Protocol)
• COR-1402: Declare 📋 active SOP before work and on every transition
• COR-1103: Route the task before reading detailed SOPs (skip if caller already provides explicit SOP)
• af plan:  Before every response — decide if task needs a checklist; if task has clear steps or spans multiple SOPs, run af plan <SOP_IDs> before proceeding

═══ PRIMARY ROUTE (stop at first match) ═══

Note: "Pure document management" (branch 1) means managing reference
material (REF, Glossary, Index) — NOT creating lifecycle documents
like PRP, CHG, ADR, PLN, INC. Those match branches 2-6.

1. Pure document management? (REF, Glossary, SOP creation, metadata update)
   ├── New SOP               → COR-1000
   ├── New reference doc     → COR-1001
   └── Update existing doc   → COR-1300

2. Something broken/failing/unexpected?
   ├── Bug/incident          → INC (project-level SOP)
   └── Fix requires system change → INC + CHG (COR-1101)

3. New capability/design that doesn't exist yet?
   └── PRP (COR-1102) → Review (COR-1602 strict) → CHG (COR-1101)

4. Execution coordination needed for approved/in-progress work?
   └── PLN (af create pln) — use for roadmaps, phased plans, multi-team coordination

5. Change to existing system/config/architecture?
   NOTE: If the change requires significant upfront design, start with
   PRP (COR-1102) first; file CHG during implementation.
   ├── Standard (pre-approved per referenced SOP) → CHG (COR-1101), no review
   ├── Normal  → CHG (COR-1101) → COR-1606 (select workflow) [+ COR-1500 overlay if code changes]
   ├── Emergency → CHG (COR-1101) → Execute → Post-approval within 24h
   └── Data migration → CHG (COR-1101, specify change type) → Execute → Validate

6. Record a durable decision already made?
   └── ADR (COR-1100)

7. Track/discuss a topic within this session?
   └── COR-1201 (Discussion Tracking)
       D new <topic> → create new D item
       D list → show all D items

8. None of the above?
   └── Ask one clarifying question, or flag ⚠️ no matching SOP

═══ OVERLAYS (apply after primary route) ═══

• Code changes              → COR-1500 (TDD: RED → GREEN → REFACTOR)
• PRP approval              → COR-1602 strict (both reviewers >= 9)
• New SOP/doc created       → Review via COR-1600 (Direct Review) at minimum
• Before any multi-agent work → COR-1606 (select review or implementation workflow)
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
COR-1606: Before any multi-agent work → select workflow (COR-1600–1605) based on task characteristics
COR-1101: Existing system/config change → CHG with What, Why, Impact, Plan; Standard changes are pre-approved (no review)
COR-1500: Code change → TDD overlay (RED→GREEN→REFACTOR) applied on top of selected workflow
COR-1100: Durable decision already made → ADR, write immediately
PLN: Execution coordination for approved/in-progress work → PLN before starting multi-phase or multi-agent implementation
COR-1300: Existing document edit → af update, update Last updated + Change History; never delete, deprecate instead (COR-1301)
COR-1000/1001: New SOP → COR-1000; new document → af create (COR-1001) with correct prefix, ACID, type, template
COR-1201: Session start → load today's Discussion Tracker (af list --type ref), read max DN, auto-increment; D new/list/show/start/done/defer/archive
COR-1608/1609/1610: Review scoring — PRP → 1608, CHG → 1609, Code → 1610; always use weighted rubric
COR-1611: Reviewer calibration — cite deductions, 10 = zero improvements, blocking vs advisory
Reading an SOP: af read → What + Why → When to Use → When NOT → Prerequisites → Pitfalls → Steps (COR-1402 each step)
```

---

## Workflow Selection

When a step says "COR-1606 to select workflow", read COR-1606 and choose based on context:

**Iterative review loops** (worker builds/revises → reviewer evaluates → loop):

| Workflow | SOP | When to use |
|----------|-----|-------------|
| Direct Review Loop | COR-1600 | Simple changes, single reviewer sufficient |
| Leader Mediated Review | COR-1601 | Complex changes needing leader judgment |

**Parallel evaluation** (artifact exists → multiple reviewers score independently → leader merges if pass):

| Workflow | SOP | When to use |
|----------|-----|-------------|
| Multi Model Parallel Review | COR-1602 | Significant changes, multiple models evaluate in parallel |

**Implementation coordination** (multiple workers build in parallel or sequence):

| Workflow | SOP | When to use |
|----------|-----|-------------|
| Parallel Module Implementation | COR-1603 | Independent modules that can be built simultaneously |
| Competitive Parallel Exploration | COR-1604 | Multiple approaches explored in parallel, pick best |
| Sequential Pipeline | COR-1605 | Steps with hard dependencies, each feeds the next |

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
| 2026-03-22 | Golden Rules: add COR-1606 line; clarify COR-1500 as TDD overlay; rename section to "Workflow Selection" | Frank + Claude Code |
| 2026-03-22 | Fix R1 review issues: update OVERLAYS "Choose review workflow" → "Select workflow"; expand Workflow Selection table to include COR-1603–1605 | Claude Code |
| 2026-03-22 | Fix R2 review issue: sequence diagram Review (1602) → COR-1606 for code changes | Claude Code |
| 2026-03-22 | Fix R2 Codex issues: router branch 4 "Review (COR-1606)" → "COR-1606 (select workflow)"; COR-1602 table removes overstated >=9; COR-1606 Golden Rule "Before any multi-agent work" | Claude Code |
| 2026-03-22 | Fix R3 Gemini issues: sequence diagram — COR-1606 before TDD (correct order); clean up session-end loop → linear Commit → af validate → Session End | Claude Code |
| 2026-03-22 | Fix R3 Codex issue: Workflow Selection table headers — "Review workflows" → "Review & revision loops"; "Implementation workflows" → "Implementation coordination" | Claude Code |
| 2026-03-22 | Fix R4 Gemini issue: Branch 4 Normal — TDD shown as sequential step, now marked as overlay: "COR-1606 [+ COR-1500 overlay if code changes]" | Claude Code |
| 2026-03-22 | Fix R4 Codex issue: diagram Doc/SOP branch — add af update path for existing docs; review only mandatory for new docs | Claude Code |
| 2026-03-22 | Fix R5 Codex issues: diagram TDD shown as overlay notation; ALWAYS COR-1103 note "skip if caller provides SOP"; OVERLAYS COR-1606 → "Normal/significant changes" | Claude Code |
| 2026-03-22 | Fix R6 Codex issue: add standalone PLN route (branch 4); renumber branches 4-7 → 5-8; update note "branches 2-6" | Claude Code |
| 2026-03-22 | Fix R7 Gemini issues: PLN branch remove wrong COR-1001 ref → af create pln; add PLN Golden Rule | Claude Code |
| 2026-03-22 | Fix R6 main Codex issues: unify OVERLAYS COR-1606/COR-1500 labels; split COR-1602 into Parallel evaluation section (no Worker role) | Claude Code |
| 2026-03-22 | Fix R7 Codex issues: diagram "(1-7)" → "(1-8)"; "Code change?" → "Normal code change? (branches 3-5)"; Doc/SOP adds "New SOP: COR-1000" | Claude Code |
| 2026-03-22 | Fix R8 Codex issues: diagram completely simplified — COR-1606 before Execute; removed branching detail that belongs in router section | Claude Code |
| 2026-03-22 | R9 review: Gemini 10.0/10 PASS, Codex 9.4/10 PASS. Merged. | Claude Code |
| 2026-04-02 | ALWAYS section: add COR-1201 Discussion Tracker as mandatory session-start step; Golden Rules: expand COR-1201 to include load + auto-increment | Frank + Claude Code |
| 2026-04-02 | R1 fix: Workflow Sequence diagram — add COR-1201 as first step before af guide | Frank + Claude Code |
