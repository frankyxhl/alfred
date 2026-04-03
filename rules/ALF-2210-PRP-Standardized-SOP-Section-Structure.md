# PRP-2210: Standardized SOP Section Structure

**Applies to:** ALF project
**Last updated:** 2026-03-20
**Last reviewed:** 2026-03-20
**Status:** Implemented
**Related:** COR-1000, COR-0002, COR-1103

---

## What Is It?

Standardize the section structure for all SOP documents, so the AI agent (and humans) can predictably navigate any SOP. Also provides a "How to Read an SOP" guide for COR-1103, and updates the `af create sop` template to match.

---

## Problem

Current state:

1. **SOP template is minimal** — Only 3 sections: What Is It?, Steps, Change History
2. **Actual SOPs vary wildly** — COR-1500 has 17 sections, COR-1101 has 16, FXA-2127 has 4
3. **No standard for "When to Use"** — Some SOPs have it, some don't. Agent can't reliably check applicability.
4. **Agent doesn't know how to execute an SOP** — Decision tree says "go to COR-1500" but there's no guide for "read What Is It → check When to Use → follow Steps"
5. **No section ordering contract** — Some SOPs put Steps before Examples, others after. Agent can't assume section order.

## Scope

**In scope:**
- Define required vs optional SOP sections with ordering (5W1H)
- "Examples" required for complex SOPs (SOPs with Prerequisites or > 5 Steps)
- Update `af create sop` template to include all required sections
- Add "How to Read and Execute an SOP" guide to COR-1103 golden rules
- Update COR-1000 (Create SOP) to reference the new section contract
- Restructure all existing SOPs to comply (completion criterion: `af validate` returns 0 SOP section issues for all SOP documents across all layers)
- Update `af validate` to check required SOP sections (presence only; section ordering is advisory, not machine-validated)
- Update COR-1103: add "How to Read an SOP" to Golden Rules section, add "SOP section compliance" to OVERLAYS section

**Out of scope:**
- Standardizing non-SOP document types (PRP, CHG, ADR already have their own templates)
- Content requirements within sections (that's per-SOP)

## Proposed Solution

### Standard SOP Section Structure

Follows the 5W1H pattern (What, Why, When, Where/Who, How):

```
# SOP-ACID: Title

**Metadata** (per COR-0002)

---

## What Is It?                    ← REQUIRED (WHAT): one-paragraph summary
## Why                            ← REQUIRED (WHY): why this SOP exists, what problem it solves
## When to Use                    ← REQUIRED (WHEN): bullet list of triggers
## When NOT to Use                ← REQUIRED (WHEN-NOT): bullet list of exclusions
## Prerequisites                  ← OPTIONAL (WHO/WHERE): what must be true before starting
## Steps                          ← REQUIRED (HOW): numbered steps to execute
## Examples                       ← CONDITIONALLY REQUIRED: worked example (required if Prerequisites or > 5 Steps)
## Common Pitfalls                ← OPTIONAL: what to avoid
## Safety Notes                   ← OPTIONAL: irreversible actions, warnings
## Change History                 ← REQUIRED: table (per COR-0002)
```

**5W1H mapping:**

| 5W1H | SOP Section | Required? |
|------|-------------|-----------|
| What | What Is It? | Yes |
| Why | Why | Yes |
| When | When to Use / When NOT to Use | Yes |
| Where/Who | Prerequisites, Metadata (Applies to) | Optional |
| How | Steps | Yes |

**Rules:**
- Required sections must appear in every SOP (machine-validated by `af validate`)
- Optional sections appear only when relevant
- Section order should follow the list above (advisory, human-enforced, not machine-validated)
- Additional custom sections (e.g., Quality Checklist) go between Steps and Examples

### Agent "How to Read an SOP" Guide

Add to COR-1103 Golden Rules section:

```
When the decision tree points you to a SOP:
1. af read <SOP-ACID>
2. Read "What Is It?" + "Why" — understand the purpose before acting.
3. Check "When to Use" — does it match the current task? If not, re-route.
4. Check "When NOT to Use" — is there an exclusion? If yes, re-route.
5. Check "Prerequisites" (if present) — are they met? If not, fulfill them first.
6. Check "Common Pitfalls" (if present) — know what to avoid.
7. Follow "Steps" in order, declaring 📋 COR-1402 at each step.
```

### Template Update

Update `fx_alfred/src/fx_alfred/templates/sop.md`:

```markdown
# SOP-{{ACID}}: {{TITLE}}

**Applies to:** {{PREFIX}} project
**Last updated:** {{DATE}}
**Last reviewed:** {{DATE}}
**Status:** Active

---

## What Is It?

<one-paragraph summary of what this SOP covers>

## Why

<why this SOP exists, what problem it solves>

---

## When to Use

- <trigger condition>

## When NOT to Use

- <exclusion condition>

## Steps

1. **Step 1** — description

---

## Change History

| Date | Change | By |
|------|--------|----|
| {{DATE}} | Initial version | — |
```

### `af validate` SOP Section Checking

Add to `validate_cmd.py`: for SOP documents, check presence of required sections:

| Section | Required? | Validation rule |
|---------|-----------|-----------------|
| What Is It? | Always | `## What Is It?` heading exists |
| Why | Always | `## Why` heading exists |
| When to Use | Always | `## When to Use` heading exists |
| When NOT to Use | Always | `## When NOT to Use` heading exists |
| Steps | Always | `## Steps` heading exists |
| Examples | Conditional | Required if document has `## Prerequisites` or Steps section has > 5 numbered items |
| Change History | Always | Already validated by existing COR-0002 check |

Report missing required sections as validation issues. Section ordering is NOT validated (advisory only).

### Rollout Sequencing

Migration must complete BEFORE enabling the new validate gate to avoid repo-wide breakage:

```
Step 1: Update af create sop template (new SOPs are compliant from birth)
Step 2: Migrate all existing SOPs (backfill required sections)
Step 3: Run af validate — confirm 0 SOP section issues
Step 4: Enable af validate SOP section checking in code
Step 5: Release new version
```

### Migration

All existing SOPs must be restructured to comply. No grandfathering. Use `af list --type SOP` to get the full inventory.

Backfill priority:
1. **Why** — new section, most SOPs don't have it. Quick to write.
2. **When to Use** — most critical gap. Many SOPs don't have it.
3. **When NOT to Use** — second most critical. Prevents misapplication.
4. **Examples** — required for complex SOPs (COR-1500, COR-1101, COR-1102 etc.)
5. **Custom sections** — existing custom sections (e.g., COR-1500's "AI-Assisted TDD Protocol") kept as additional sections between Steps and Examples.

### COR-1103 Decision Tree Update

Add to PRIMARY ROUTE or OVERLAYS:
```
• SOP section compliance → af validate checks required sections (What/Why/When/Steps)
```

Add to Golden Rules:
```
Reading an SOP: af read → What Is It? + Why → When to Use → When NOT to Use → Prerequisites → Common Pitfalls → Steps (COR-1402 each step)
```

## Risks

1. **Migration effort** — 30+ COR SOPs need backfill. Mitigated by: most need only Why + When to Use (short).
2. **Low-quality backfills** — "Check the box" Why/When sections with no real content. Mitigated by: review via COR-1602 for non-trivial SOPs.
3. **Complex SOP restructuring** — COR-1500 (17 sections) and COR-1101 (16 sections) may resist the standard ordering. Mitigated by: custom sections allowed between Steps and Examples, ordering is advisory not machine-enforced.
4. **Temporary af validate breakage** — If validate gate is enabled before migration completes, all existing SOPs fail. Mitigated by: rollout sequencing (migrate first, enable gate last).
5. **Validator false positives** — Complex SOPs with unusual section names (e.g., "## The Cycle: Red-Green-Refactor" in COR-1500) might confuse heading detection. Mitigated by: validate only checks for presence of required heading text, not absence of custom headings.

## Open Questions

None. All resolved:
- OQ1: Examples required for complex SOPs (has Prerequisites or > 5 Steps) → **RESOLVED**
- OQ2: All existing SOPs restructured, no grandfathering → **RESOLVED**
- OQ3: af validate checks required SOP sections → **RESOLVED, moved into scope**

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version based on session observations | Frank + Claude Code |
| 2026-03-20 | Round 1 revision: resolved all OQs (Examples conditional, restructure all, validate in scope), added Risk section, af validate SOP checking, COR-1103 update plan | Claude Code |
| 2026-03-20 | Round 2 revision: added rollout sequencing, explicit COR-1103 insertion points, ordering = advisory not machine-validated, completion criterion, validator breakage + false positive risks, af list --type SOP for inventory | Claude Code |
