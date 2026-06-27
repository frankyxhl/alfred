# SOP-1402: Declare Active Process

**Applies to:** All projects using the COR document system
**Last updated:** 2026-06-26
**Last reviewed:** 2026-06-26
**Status:** Active
**Always included:** true
**Disposition:** inherit-only

---

## What Is It?

A rule requiring the agent to explicitly declare the active process for every user-visible task. The declaration names the SOP being followed, or states that no formal SOP applies. This ensures traceability, helps the user understand what process is driving the work, and surfaces gaps where no SOP exists.

---

## Why

- The user always knows which process is being followed
- Gaps in the SOP system become visible immediately
- Repeated "no matching SOP" flags feed into COR-1200 (Session Retrospective) as improvement candidates

---

## When to Use

- At the start of every user-visible task
- At the start of every task that follows a documented SOP
- When switching from one SOP to another mid-task
- When executing a plan-driven workflow (SOP + PLN + Phase)

---

## When NOT to Use

- For private/internal sub-steps that do not produce user-visible work
- When the user explicitly asks to skip process declarations

---

## Rule

### 1. Before starting any user-visible task, declare the active process

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

**No formal SOP applies** (quick answer or uncovered task):
```
📋 COR-1402 Declare Active Process → no formal task SOP
```

The declaration must include all applicable dimensions:

| Dimension | When to include | Example |
|-----------|----------------|---------|
| **SOP** (process) | Always | `COR-1500-SOP` |
| **PLN** (plan) | When executing a plan | `NRV-2207-PLN` |
| **Phase / Step** | When the plan has phases | `Phase 2.5 BDD + Coverage` |

**Chat surface (mandatory).** In conversational/chat surfaces, emit the active-process declaration as the **first line of every reply**, before any other content — unless a declared SOP mandates a specific opening (e.g. COR-1208's session-startup sanity-check report, or COR-1207's unfamiliarity statement), in which case the COR-1402 line immediately follows that mandated preamble. Re-state it on every turn — including continuation, clarification, and quick-answer turns — so the active process is always visible. Keep it to one line when space is tight, but never omit it; for quick answers or uncovered tasks use the one-line no-formal-SOP form `📋 COR-1402 Declare Active Process → no formal task SOP`.

### 2. When switching processes, declare each transition

```
📋 COR-1000 Create SOP → COR-1001 Create Document → COR-1302 Maintain Document Index
```

### 3. When no SOP exists, flag it

```
⚠️ No matching SOP. Suggest creating one.
```

### 4. When the task is complete, confirm which SOPs were used

If the task produced a checklist or release/PR handoff, include whether the COR-1402 declaration opened every reply and was updated at phase transitions.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-15 | Initial version | Claude Code |
| 2026-03-16 | Added plan-driven declaration format (SOP + PLN + Phase) based on field usage | Claude Code |
| 2026-03-20 | Added When to Use/When NOT to Use sections, reordered Why section per FXA-2223 | Claude Code |
| 2026-06-26 | Require active-process content for every user-visible task, including no-formal-SOP cases | Claude Code |
| 2026-06-26 | Mandate active-process line as first line of every chat reply (chat-surface hardening) | Claude Code |
| 2026-06-26 | Add session-start/zoom-out exception: COR-1402 line follows a SOP-mandated opening preamble. | Claude Code |
