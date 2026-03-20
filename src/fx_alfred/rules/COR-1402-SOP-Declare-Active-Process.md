# SOP-1402: Declare Active Process

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-15
**Last reviewed:** 2026-03-15
**Status:** Active

---

## What Is It?

A rule requiring the agent to explicitly declare which SOP is being followed at every step of a task. This ensures traceability, helps the user understand what process is driving the work, and surfaces gaps where no SOP exists.

---

## Rule

### 1. Before starting any task, declare the active process

**Simple task** (single SOP, no plan):
```
📋 COR-1000 Create SOP
```

**Plan-driven task** (SOP + plan + phase):
```
📋 <SOP-ACID> (<SOP Name>) ▶ <PLN-ACID> <Phase/Step>
```

Example:
```
📋 COR-1500-SOP (TDD Workflow) ▶ ALF-2200-PLN Phase 3 API Integration
```

The declaration must include all applicable dimensions:

| Dimension | When to include | Example |
|-----------|----------------|---------|
| **SOP** (process) | Always | `COR-1500-SOP` |
| **PLN** (plan) | When executing a plan | `NRV-2207-PLN` |
| **Phase / Step** | When the plan has phases | `Phase 2.5 BDD + Coverage` |

### 2. When switching processes, declare each transition

```
📋 COR-1000 Create SOP → COR-1001 Create Document → COR-1302 Maintain Document Index
```

### 3. When no SOP exists, flag it

```
⚠️ No matching SOP. Suggest creating one.
```

### 4. When the task is complete, confirm which SOPs were used

---

## Why

- The user always knows which process is being followed
- Gaps in the SOP system become visible immediately
- Repeated "no matching SOP" flags feed into COR-1200 (Session Retrospective) as improvement candidates

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-15 | Initial version | Claude Code |
| 2026-03-16 | Added plan-driven declaration format (SOP + PLN + Phase) based on field usage | Claude Code |
