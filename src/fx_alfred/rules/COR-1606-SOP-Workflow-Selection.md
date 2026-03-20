# SOP-1606: Workflow — Selection

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-19
**Last reviewed:** 2026-03-19
**Status:** Active

---

## What Is It?

A decision process for choosing the right collaboration workflow (COR-1600 through COR-1605) based on task characteristics. Use this SOP before starting any multi-agent task to select the appropriate pattern.

---

## Decision Tree

```
Does the artifact already exist and only need review?
│
├── YES → COR-1602 (Multi Model Parallel Review)
│
└── NO → How many Workers are needed?
          │
          ├── ONE Worker
          │   │
          │   └── Does the Leader need to mediate every round?
          │       │
          │       ├── YES → COR-1601 (Leader Mediated Review Loop)
          │       │         • Complex/ambiguous tasks
          │       │         • Reviewers may conflict
          │       │         • Leader has unique context
          │       │
          │       └── NO  → COR-1600 (Direct Review Loop)
          │                 • Simple, well-defined tasks
          │                 • Straightforward feedback
          │
          └── MULTIPLE Workers
              │
              └── Are Workers doing the SAME task or DIFFERENT tasks?
                  │
                  ├── SAME task (different approaches)
                  │   → COR-1604 (Competitive Parallel Exploration)
                  │     • output_retention: competitive (only winner kept)
                  │     • Optimal approach unknown
                  │
                  ├── DIFFERENT tasks (different modules)
                  │   │
                  │   └── Do tasks depend on each other's output?
                  │       │
                  │       ├── YES (sequential dependency)
                  │       │   → COR-1605 (Sequential Pipeline)
                  │       │     • Stage-by-stage handoff
                  │       │     • Each stage needs previous output
                  │       │
                  │       └── NO (independent)
                  │           → COR-1603 (Parallel Module Implementation)
                  │             • output_retention: composable (all kept)
                  │             • Independent modules, unified review
                  │
                  └── UNSURE → Start with COR-1601 (Leader Mediated)
                               Leader can redirect mid-task
```

---

## Quick Reference Table

| SOP | Pattern | Workers | Output | Key Signal |
|-----|---------|---------|--------|------------|
| COR-1600 | Direct Review Loop | 1 | single | Simple task, no Leader mediation needed |
| COR-1601 | Leader Mediated Review Loop | 1 | single | Complex task, Leader arbitrates feedback |
| COR-1602 | Multi Model Parallel Review | 0 | review only | Artifact exists, need diverse perspectives |
| COR-1603 | Parallel Module Implementation | 2+ | composable | Independent modules, all outputs kept |
| COR-1604 | Competitive Parallel Exploration | 2+ | competitive | Same task, different approaches, pick winner |
| COR-1605 | Sequential Pipeline | 2+ | chained | Stages depend on each other's output |

---

## Dynamic Escalation Rules

Workflows can escalate during execution:

| From | To | Trigger |
|------|----|---------|
| COR-1600 | COR-1601 | Reviewer conflict that Lead Reviewer cannot resolve |
| COR-1603 | COR-1605 | Discovered dependency between "independent" modules |
| COR-1604 | COR-1600 | Winner selected, now needs dedicated refinement |
| COR-1602 | COR-1601 | Review findings require a Worker to implement changes |

---

## Common Combinations

Some tasks require chaining multiple workflows:

| Phase | Workflow | Purpose |
|-------|----------|---------|
| Plan | COR-1602 | Review the plan with multiple models |
| Implement | COR-1603 | Parallel module development |
| Review | COR-1602 | Final review of combined output |

Example: FXA-2107 used COR-1602 (plan review) → COR-1603 (parallel implementation) → COR-1602 (final review).

---

## Steps

1. **Identify task characteristics** — artifact exists? how many workers? same or different tasks? dependencies?
2. **Walk the decision tree** — follow the branches to reach a recommended SOP
3. **Validate with quick reference table** — confirm the key signal matches your task
4. **Check escalation rules** — know when to switch workflows mid-execution
5. **Begin** — invoke the selected workflow SOP

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-19 | Initial version, based on Codex decision tree proposal | Claude Code |
