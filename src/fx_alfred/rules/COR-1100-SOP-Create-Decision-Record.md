# SOP-1100: Create Decision Record

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-12
**Last reviewed:** 2026-03-12

---

## What Is It?

An Architecture / Any Decision Record (ADR) captures a decision made during a session, along with its context, alternatives considered, and consequences. ADRs provide a traceable history of why things are the way they are.

---

## When to Use

- A design or architecture choice is made
- A policy or convention is established or changed
- A sync/copy decision affects multiple projects
- A naming convention or workflow is agreed upon
- Any decision worth explaining to your future self

## When NOT to Use

- Routine operations covered by an existing SOP
- Bug fixes (use INC instead)
- Temporary or trivial choices with no lasting impact

---

## Naming Convention

```
<PREFIX>-<NNNN>-ADR-<YYYYMMDD><Dn>-<Short-Description>.md
```

- **PREFIX** — project prefix (e.g., COR, ALF)
- **NNNN** — sequential number in the business layer ADR area
- **YYYYMMDD** — date the decision was made
- **Dn** — decision sequence number for that day (D1, D2, D3, ...)
- **Short-Description** — kebab-case summary of the decision

Examples:
- `COR-6001-ADR-20260312D1-Adopt-Johnny-Decimal.md`
- `ALF-6001-ADR-20260312D1-Bella-Skip-SOP-1001.md`
- `ALF-6002-ADR-20260312D2-Fix-Bella-1004-Conflict.md`
- `ALF-6003-ADR-20260312D3-Introduce-ADR-Document-Type.md`

**Note:** Area is user-chosen and is not bound to any specific type. See COR-1001 for authoritative numbering rules.

---

## ADR Template

```markdown
# ALF-NNNN-ADR-YYYYMMDDD#: <Short Description>

- **Date:** YYYY-MM-DD
- **Status:** Proposed | Accepted | Superseded | Deprecated
- **Related:** <ALF-NNNN, ALF-NNNN, ...>

---

## Context

What prompted this decision? What problem or question came up?

---

## Options Considered

- **Option A:** <description>
- **Option B:** <description>
- **Option C:** <description> _(if applicable)_

---

## Decision

What was decided and by whom.

---

## Rationale

Why this option was selected over the alternatives.

---

## Consequences

- What changes as a result of this decision
- What needs to be updated (SOPs, configs, other docs)
- Any trade-offs accepted

---

## Change History

| Date | Change | By |
|------|--------|----|
| YYYY-MM-DD | Initial version | Author |
```

---

## Quick Create Shortcut

To create a new ADR, just say **"new D"** (or "新建一个 D"). The agent will:

1. Check today's date
2. Find the last Dn for today (`ls docs/*-ADR-<today>*`)
3. Assign the next sequential number (e.g., if D3 exists, the new one is D4; if it's a new day, start at D1)
4. Ask for the topic or create it directly if context is clear

---

## Steps (Manual)

1. **Determine the next number** — `ls docs/*-ADR-*` to find the next available number
2. **Determine today's sequence** — check how many ADRs already exist for today's date (`ls docs/*-ADR-<today>*`), use the next Dn
3. **Create the file** — use the naming convention and template above
4. **Fill in all sections** — keep it concise; a good ADR can be as short as 10 lines
5. **Save to `docs/`** — place the file in the project's `docs/` directory

---

## Language Policy

All ADR documents must be written in English. Team discussions may happen in any language, but the recorded document is always in English for consistency and searchability.

---

## Safety Notes

- Write the ADR as close to the decision moment as possible — context fades fast
- If a decision is later reversed, do not delete the original ADR; create a new one that supersedes it and update the original's status to "Superseded"
- Keep ADRs factual, not aspirational

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-12 | Initial version | Claude Code |
| 2026-03-12 | Added quick create shortcut convention | Claude Code |
| 2026-03-14 | PDCA + Johnny Decimal migration: renamed from ALF-1005 to COR-1000 | Claude Code |
