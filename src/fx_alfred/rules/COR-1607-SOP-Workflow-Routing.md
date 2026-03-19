# SOP-1607: Workflow Routing

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-20
**Last reviewed:** 2026-03-20
**Status:** Active
**Related:** COR-1606, COR-1102, COR-1101, COR-1100, COR-1500

---

## What Is It?

A routing table that maps work types to their required SOP sequences. Read this at the start of any task to determine which SOPs to follow, in what order.

---

## When to Use

- At the start of any new task or session
- When unsure which SOP or document type applies to the work at hand
- Before creating any document (PRP, CHG, ADR, INC, PLN)

---

## Routing Table

| Work Type | Step 1 | Step 2 | Step 3 | Step 4 |
|-----------|--------|--------|--------|--------|
| New feature/tool | PRP (COR-1102) | Review: COR-1602 strict (mandated by COR-1102) | CHG (COR-1101) | TDD (COR-1500) |
| Existing system change | CHG (COR-1101) | Review: COR-1606 to select workflow | TDD (COR-1500) | — |
| Bug fix | INC (ALF-2300) | TDD (COR-1500) | — | — |
| Architecture decision | ADR (COR-1100) | — | — | — |
| Documentation | COR-1001 | — | — | — |
| Data migration | CHG (COR-1101) | Execute | Validate | — |
| Refactoring | CHG (COR-1101) | Review: COR-1606 to select workflow | TDD (COR-1500) | — |

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

## Steps

1. Identify the work type from the routing table
2. Read the SOP for Step 1 and follow it
3. Proceed through each subsequent step in order
4. If a Review step says "COR-1606 to select workflow", read COR-1606 to choose the appropriate review SOP
5. Skip steps marked "—"

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version, based on ALF-2205 ADR decision | Frank + Claude Code |
