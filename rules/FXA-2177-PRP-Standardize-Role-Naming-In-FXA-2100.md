# PRP-2177: Standardize-Role-Naming-In-FXA-2100

**Applies to:** FXA project
**Last updated:** 2026-04-01
**Last reviewed:** 2026-04-01
**Status:** Approved

---

## What Is It?

Standardize role naming in FXA-2100 (Leader Mediated Development) to eliminate the Droid/GLM/Coder collision.

---

## Problem

FXA-2100 uses three different terms for the same role:
- "Droid" in the description ("Droid implements code") and Roles table ("**Coder** | Droid")
- "GLM" in the "When to Use" section ("coordinates GLM (coder)") and Examples (`/trinity glm`)
- "Coder" as the role name in the Roles table

COR-1601 (the parent pattern) uses "Worker" as the generic role. The mixed terminology creates confusion about whether these are different entities or the same one.

## Proposed Solution

Align FXA-2100 with COR-1601 terminology:

1. **Role name = "Coder"** (domain-specific specialization of COR-1601 "Worker")
2. **Provider = "GLM"** (the `/trinity` provider used in commands)
3. Remove "Droid" from prose — replace with "GLM" where referring to the provider, "Coder" where referring to the role

Specific changes to `rules/FXA-2100-SOP-Leader-Mediated-Development.md`:
- "What Is It?" line: "Droid implements code" → "GLM implements code"
- Roles table Provider column: "Droid" → "GLM"
- Flow diagram: "(Droid)" → "(GLM)"

**No logic changes.** Terminology-only fix. All step numbers, pass criteria, and scoring remain identical.

**Files changed:** `rules/FXA-2100-SOP-Leader-Mediated-Development.md` only.

**No SOPs affected** besides FXA-2100 itself. A grep for "Droid" across `rules/` finds one other occurrence: FXA-2101 (a CHG record) has "Droid" in its Change History table as a historical entry — this is not modified (Change History records are immutable). Out-of-scope: COR-layer documents (read-only PKG, not modifiable by this project).

## Risk

- **Downstream references.** If any scripts, agent prompts, or external documentation reference "Droid" as a role name, they would become inconsistent. Mitigation: grep `rules/` for "Droid" to confirm no other documents use the term before implementing.
- **Rollback.** Revert the single file via `git checkout HEAD -- rules/FXA-2100-*.md`. Terminology-only change; no behavioral impact.

## Open Questions

None.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-01 | Initial version | — |
| 2026-04-01 | R1: Add Risk section, explicit scope boundary for "Droid" references (Gemini feedback) | Claude Code |
