# SOP-1000: Create SOP

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-14
**Last reviewed:** 2026-03-14
**Status:** Active

---

## What Is It?

The process for creating a new Standard Operating Procedure. This is the most fundamental document type in the system — all other document types follow from it.

---

## Why

SOPs ensure repeatable, consistent execution of processes. Without a standard way to create SOPs, each document would have a different structure, making the system harder to navigate and maintain.

---

## When to Use

- Creating a brand-new Standard Operating Procedure for any project
- Defining a repeatable process that team members need to follow consistently
- Documenting a workflow that has been agreed upon and should be standardized

---

## When NOT to Use

- Recording a one-time decision (use ADR per COR-1100 instead)
- Proposing a change to an existing system (use CHG per COR-1101 instead)
- Creating non-SOP document types (use COR-1001 for general document creation)

---

## Prerequisites

- Follow COR-1001 (Create Document) for naming convention and ACID numbering
- Follow COR-1302 (Maintain Document Index) after creation

---

## SOP Template

```markdown
# SOP-NNNN: <Title>

**Applies to:** <scope>
**Last updated:** YYYY-MM-DD
**Last reviewed:** YYYY-MM-DD

---

## What Is It?

<1-2 sentences describing the purpose.>

---

## Steps

1. **Step 1** — description
2. **Step 2** — description

---

## Change History

| Date | Change | By |
|------|--------|----|
| YYYY-MM-DD | Initial version | Author |
```

Add additional sections (Prerequisites, Configuration, Troubleshooting, Safety Notes) only when applicable.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-14 | Initial version | Claude Code |
| 2026-03-20 | Added Why/When to Use/When NOT to Use sections per ALF-2210 | Claude Code |
