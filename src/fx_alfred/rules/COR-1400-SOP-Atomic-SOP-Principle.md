# SOP-1400: Atomic SOP Principle

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-14
**Last reviewed:** 2026-03-14
**Status:** Active

---

## What Is It?

A fundamental design principle: every SOP must do exactly one thing. If an SOP covers more than one responsibility, it should be split into separate documents.

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
