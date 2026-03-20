# SOP-1400: Atomic SOP Principle

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-20
**Last reviewed:** 2026-03-14
**Status:** Active

---

## What Is It?

A fundamental design principle: every SOP must do exactly one thing. If an SOP covers more than one responsibility, it should be split into separate documents.

---

## Why

Multi-responsibility SOPs become hard to reference, hard to update, and create ambiguity about when they apply.

---

## When to Use

- When creating a new SOP — verify it covers exactly one responsibility
- When reviewing an existing SOP — check for scope creep
- When a single SOP keeps growing with unrelated steps

---

## When NOT to Use

- When two steps are genuinely inseparable parts of one atomic operation
- When splitting would create SOPs too trivial to stand alone

---

## Rule

- One SOP = one atomic operation
- If you find yourself adding a second responsibility to an existing SOP, create a new SOP instead
- If two SOPs always run together, they are still separate documents — create a third SOP that sequences them if needed

---

## How to Check

Ask yourself:
1. Can I describe this SOP's purpose in one sentence without using "and"?
2. Could someone skip part of this SOP and still complete a meaningful task?

If the answer to #1 is no, or #2 is yes — split it.

---

## Examples

| Violation | Fix |
|-----------|-----|
| "Create Document and Update Index" | Split into COR-1100 (Create Document) + COR-1302 (Maintain Index) |
| "Record Incident and Notify Team" | Split into Record Incident + Notify Team |

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-14 | Initial version | Claude Code |
| 2026-03-20 | Added Why/When to Use/When NOT to Use sections per ALF-2210 | Claude Code |
