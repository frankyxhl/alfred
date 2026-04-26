# PRP-2134: AF Plan Command Workflow Checklist

**Applies to:** FXA project
**Last updated:** 2026-03-21
**Last reviewed:** 2026-03-21
**Status:** Implemented
**Reviewed by:** Codex 9.0, Gemini 9.9 (Round 3)
**Related:** COR-1103, COR-1402, FXA-2223, D3 (FXA-2128)

---

## What Is It?

A new `af plan` command that generates a session checklist from declared SOPs. Before starting work, the agent declares which SOPs it will follow; `af plan` reads those SOPs, extracts their Steps sections, and outputs a todo checklist. This makes every step visible and unskippable — including review gates.

## Why

During this session, the agent skipped COR-1602 review before committing FXA-2132 and FXA-2133. The SOPs existed and the golden rules said "all code changes must go through review" — but in the rush of batch processing, the review step was forgotten. A checklist generated from the actual SOP Steps would have made the review step explicitly visible.

---

## Problem

1. **SOPs are advisory** — The agent reads them at route time but can forget individual steps during execution
2. **No session-level tracking** — COR-1402 declares the active SOP but doesn't track which steps have been completed
3. **Review gates are invisible** — Review is a step within COR-1602 but gets lost when multiple SOPs are chained
4. **Batch processing breaks discipline** — When doing 8 batches of migration, the agent forms a "dispatch → commit → next" rhythm and skips intermediate steps

## Scope

**In scope:**
- New `af plan` CLI command
- Reads SOP documents, extracts `## Steps` section
- Outputs a numbered checklist per SOP
- Supports multiple SOPs in sequence: `af plan COR-1102 COR-1602 COR-1101`
- Integration with `af guide` — decision tree points to SOPs, `af plan` turns them into a checklist
- Update `af guide` output — append a note at the end: "First time? Run `af plan --init` to see suggested prompts for your agent config"

**Out of scope:**
- Persistent checklist state (tracking completion across commands)
- Interactive checkbox toggling
- Automated step verification (checking if a step was actually done)
- Modifying any existing SOP content

## Proposed Solution

### Command signature

```bash
af plan SOP_ID [SOP_ID ...] [--root DIRECTORY]   # default: LLM-optimized output
af plan --human SOP_ID [SOP_ID ...] [--root DIR]  # human-readable format
af plan --init                                     # output suggested prompts for agent config
```

### Three modes

**Default (no flag):** Output optimized for LLM consumption — structured instruction prompt with phases, hard stops (⚠️), rules, and COR-1402 transition markers. The LLM reads this and uses it as its workflow instruction for the session.

**`--human`:** Human-readable format — cleaner formatting, no LLM instruction language. For the user to review the plan.

**`--init`:** Outputs suggested prompt snippets that the LLM or user can add to their agent configuration file (CLAUDE.md, agent.md, system prompt, etc.). Does NOT modify any file directly — just prints suggestions. Different LLMs and agent architectures may need different prompts, so this provides options:

```
# Suggested prompts for your agent configuration

Add ONE of the following to your agent's instruction file:

## Option A: Minimal
Before any work, run `af plan <SOP_IDs>` and follow the output.

## Option B: With routing
Before any work:
1. Run `af guide --root <project-root>` to determine which SOPs apply
2. Run `af plan <SOP_IDs>` to generate workflow instructions
3. Follow each step. Do not skip review gates.

## Option C: Full
Before any work:
1. Run `af guide --root <project-root>` to see routing (PKG → USR → PRJ)
2. From the decision tree, identify which SOPs apply to this task
3. Run `af plan <SOP_IDs>` to generate step-by-step workflow
4. Follow each step, declaring active SOP at transitions
5. Do not commit code without completing review steps
6. At session end, use the plan output as completion checklist
```

### Default mode behavior (LLM-optimized)

1. For each SOP_ID, resolve the document using `scan_or_fail()` + `find_or_fail()`
2. Verify document type is SOP (`doc.type_code == "SOP"`)
3. Parse document content, extract:
   - `## What Is It?` — one-line summary
   - `## Steps` — the numbered steps
4. Output formatted checklist

### Output format (default: LLM-optimized)

```
# Session Workflow — Follow each phase in order. Do not skip any step.

## Phase 1: COR-1102 (Create Proposal)
What: Process for creating and reviewing a PRP document.

- [ ] 1. Create the PRP document
- [ ] 2. Fill in required sections
  □ 3. Review via COR-1602 (Parallel Review)
- [ ] 4. Record the outcome
- [ ] 5. Implement (if approved)

## Phase 2: COR-1602 (Multi Model Parallel Review)
What: Multiple Reviewers independently analyze the same input in parallel.

- [ ] 1. Leader identifies artifact
- [ ] 2. Leader dispatches Reviewers (use COR-1608/1609/1610 rubric + COR-1611 calibration)
- [ ] 3. Reviewers analyze independently
- [ ] 4. Leader collects all reviews
- [ ] 5. Leader synthesizes
- [ ] 6. Leader revises artifact
- [ ] 7. If iteration → resubmit
- [ ] 8. If all approve → done
⚠️ DO NOT PROCEED TO NEXT PHASE WITHOUT PASSING REVIEW

## Phase 3: COR-1500 (TDD Development Workflow)
What: Red-Green-Refactor cycle for test-driven development.

- [ ] 1. RED: Write a failing test
- [ ] 2. Run test — confirm FAIL
- [ ] 3. GREEN: Write minimum code to pass
- [ ] 4. Run all tests — confirm ALL PASS
- [ ] 5. REFACTOR: Clean up
- [ ] 6. Run all tests — confirm still PASS

## RULES
- Complete each checkbox before moving to the next phase
- Declare 📋 active SOP at every phase transition (COR-1402)
- ⚠️ marks hard stops — do not proceed until condition is met
- If stuck, ask one clarifying question before proceeding
```

### Output format (`--human`)

Same content but with cleaner formatting for human reading:
- Uses `□` instead of `- [ ]`
- Uses `═══` separators instead of `##` headings
- No RULES section or ⚠️ markers

### Step extraction logic

Implemented as `extract_section(body, heading)` in `core/parser.py` for reuse by other commands.

1. Search for the target heading using `re.search(rf"^## {heading}\s*$", body, re.MULTILINE)` or `re.search(rf"^### {heading}\s*$", body, re.MULTILINE)` (fallback for H3-style SOPs)
2. Extract text from after the heading until the next heading of same or higher level, or end of body
3. Find numbered items matching EITHER `^\d+\.` (plain numbered) OR `^### \d+\.` (H3 numbered) — both formats exist in current SOPs
4. For each item, extract the first line as the step summary
5. If heading found but no numbered items detected, show the raw section text as-is (best-effort fallback)
6. If no matching heading found at all, output "(no Steps section found)"

**Heading search order:** `## Steps` → `## Rule` → `## Concepts` → fallback to first `## ` after When NOT to Use (for SOPs that use non-standard main content headings).

**Session-always SOPs:** `af plan` does NOT auto-include COR-1402/COR-1103. The caller must explicitly declare all SOPs to plan. This keeps the command simple and predictable.

### Integration with `af guide`

The workflow becomes:

```
Session start:
1. af guide --root <project>           → see routing + decision tree
2. Identify which SOPs apply           → from decision tree branches
3. af plan COR-1102 COR-1602 COR-1500 → generate checklist
4. Follow the checklist                → review steps are explicit
```

### Error handling

| Scenario | Behavior |
|----------|----------|
| SOP not found | Error: "Document not found: COR-9999" |
| Document is not SOP type | Warning: "FXA-2116 is PRP, not SOP. Skipping." |
| SOP has no Steps section | Note: "(no Steps section found)" with raw body fallback |
| Malformed document | Show SOP ID + parse error, continue to next SOP (same pattern as `guide_cmd.py`) |
| No arguments | Error: "Usage: af plan SOP_ID [SOP_ID ...]" |

## Risks

1. **Step format heterogeneity** — SOPs use different step formats (`1.` vs `### 1.` vs non-standard headings). Mitigated by: multi-format regex, heading search order, raw text fallback when no numbered items found.
2. **Stale checklists** — Checklist is a snapshot, SOP may change after plan is generated. Mitigated by: `af plan` always reads live SOPs, not cached.
3. **Agent still skips steps** — Checklist is visible but agent may still skip. Mitigated by: checklist makes skipping conscious rather than accidental.
4. **Malformed documents** — SOPs with parse errors could crash the command. Mitigated by: catch `MalformedDocumentError`, show error, continue to next SOP.

## Implementation Notes (from COR-1602 review advisories)

- COR-1500 fallback: first section after "When NOT to Use" is `## Prerequisites`, not `## The Cycle`. Use heading search order, not positional fallback.
- `af guide` should append: "First time? Run `af plan --init` to see suggested prompts for your agent config"
- `--init` suggested prompts should include "Recommended Location" header (e.g., "Add to CLAUDE.md under ## Workflow")
- Consider `--json` flag for parity with other `af` commands (future enhancement)
- Step extraction should also handle bulleted lists (`-`, `*`) in addition to numbered items (future enhancement)

## Open Questions

None. All design decisions resolved:
- Command name: `af plan` (short, clear intent)
- Default output: LLM-optimized instruction prompt (primary user is LLM)
- `--human`: human-readable format
- `--init`: outputs suggested prompts for agent config (does not modify files)
- Step extraction: multi-format (plain + H3), with fallback
- Non-SOP documents: skipped with warning

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-21 | Initial version based on D3 discussion | Frank + Claude Code |
| 2026-03-21 | Round 1 revision: multi-format step extraction (plain + H3), extract_section in parser.py, MalformedDocumentError handling, session-always SOPs not auto-included, raw text fallback, heading search order | Claude Code |
| 2026-03-21 | Added 3 modes: default (LLM-optimized), --human (readable), --init (suggested prompts). LLM is primary user, not human. | Frank + Claude Code |
