# CHG-2121: Update Create Templates To Format Contract

**Applies to:** FXA project
**Last updated:** 2026-03-20
**Last reviewed:** 2026-03-20
**Status:** Completed
**Date:** 2026-03-20
**Requested by:** Frank
**Priority:** High
**Change Type:** Normal
**Related:** FXA-2116, FXA-2119, FXA-2120

---

## What

Update all 7 `af create` templates (`fx_alfred/src/fx_alfred/templates/*.md`) to comply with the Document Format Contract (COR-0002).

Templates emit **required fields + type-default optional fields only**. Other optional fields defined in COR-0002 (e.g., `Related`, `Reviewed by`, `Last executed`) are allowed in documents but not pre-populated in templates — users add them manually when needed.

### Target field layout per template

**chg.md:**
```
**Applies to:** {{PREFIX}} project
**Last updated:** {{DATE}}
**Last reviewed:** {{DATE}}
**Status:** Proposed
**Date:** {{DATE}}
**Requested by:** —
**Priority:** Medium
**Change Type:** Normal
```

**inc.md:**
```
**Applies to:** {{PREFIX}} project
**Last updated:** {{DATE}}
**Last reviewed:** {{DATE}}
**Status:** Open
**Date:** {{DATE}}
**Severity:** Medium
```

**pln.md:**
```
**Applies to:** {{PREFIX}} project
**Last updated:** {{DATE}}
**Last reviewed:** {{DATE}}
**Status:** Draft
```

**prp.md:**
```
**Applies to:** {{PREFIX}} project
**Last updated:** {{DATE}}
**Last reviewed:** {{DATE}}
**Status:** Draft
```

**sop.md:**
```
**Applies to:** {{PREFIX}} project
**Last updated:** {{DATE}}
**Last reviewed:** {{DATE}}
**Status:** Active
```

**adr.md:**
```
**Applies to:** {{PREFIX}} project
**Last updated:** {{DATE}}
**Last reviewed:** {{DATE}}
**Status:** Proposed
```

**ref.md:**
```
**Applies to:** {{PREFIX}} project
**Last updated:** {{DATE}}
**Last reviewed:** {{DATE}}
**Status:** Active
```

### Field disposition

- `Date` in chg.md and inc.md: **retained** as optional field after Status (confirmed as CHG/INC-specific optional)
- `Requested by`, `Priority`, `Change Type` in chg.md: **retained** as CHG-specific optional fields
- `Severity` in inc.md: **retained** as INC-specific optional field
- All fields use `**Key:** Value` format (no list prefix `- `)
- Field order: required fields first (Applies to → Last updated → Last reviewed → Status), then optional fields

## Why

`af create` generates documents from templates. If templates don't match the contract, every newly created document starts non-compliant and requires manual fixes. Templates must be the first thing updated after the contract is established.

## Impact Analysis

- **Systems affected:** `fx_alfred/src/fx_alfred/templates/` (7 files), `fx_alfred/tests/test_create_cmd.py`
- **Rollback plan:** `git revert` the commit

## Implementation Plan (TDD per COR-1500)

1. Write failing tests: verify each template produces documents with all required fields, correct format, correct field order
2. Run tests — confirm RED
3. Update all 7 templates per target layouts above
4. Run tests — confirm GREEN
5. Refactor if needed
6. Run full test suite — confirm no regression
7. Commit

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version | Claude Code |
| 2026-03-20 | Round 1 revision: added compliant metadata, explicit target field layouts, Date/Requested by/Priority/Change Type disposition | Claude Code |
| 2026-03-20 | Round 2 revision: clarified templates emit required + type-default optional only, other COR-0002 optional fields are allowed but not pre-populated | Claude Code |
