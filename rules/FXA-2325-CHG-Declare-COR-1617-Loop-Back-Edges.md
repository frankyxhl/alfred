# CHG-2325: Declare COR-1617 Loop Back-Edges

**Applies to:** FXA project
**Last updated:** 2026-08-12
**Last reviewed:** 2026-08-12
**Status:** Completed
**Date:** 2026-08-12
**Requested by:** Frank Xu (session request: tier-3 flagship of the COR-1005 corpus audit)
**Priority:** Medium
**Change Type:** Normal
**Targets:** src/fx_alfred/rules/COR-1617-SOP-Multi-Agent-Workflow-Loop.md

---

## What

Tier-3 retrofit of the COR-1005 audit — the twelve-phase multi-agent workflow
loop becomes machine-readable:

- **§Phases → §Steps**: the section is renamed to the parser-recognized heading
  and the twelve-phase list at its top is un-fenced into flush-left numbered
  steps (it was inside a code fence, which fence-aware extraction correctly
  ignores — so `af plan COR-1617` extracted **zero steps**). The `### Phase N`
  detail subsections are untouched: their headings do not match the step
  pattern, so they remain body content, and every intra- and cross-doc
  "§Phase N" reference stays valid.
- **Two declared back-edges**, both from Phase 9 (Triage):
  - `iterate-round` (9→8, `max_iterations: 13`): §8's "gate not met → triage →
    push R+1 → loop back". Budget and exhaustion were already fully documented:
    max 13 is the §Round-count cap **hard stop** (`<max-r-count>` 10 +
    `<max-r-count-extension>` 3 per COR-1622), matching COR-1005's definition
    of `max_iterations` as the point where exhaustion behavior fires; the
    soft-cap/extension logic (Cases A/B/C) is the in-doc contract between
    rounds 10 and 13. Purely declarative.
  - `replan-blocker` (9→4, `max_iterations: 2`): §9's "plan-review
    architectural blockers go back to phase 4". ⚠️ The return path was
    documented but carried **no count**; max 2 is newly proposed, with a new
    exhaustion sentence (second re-plan still blocked → halt and surface: the
    approach, not the plan, is likely wrong). Flagged for owner sign-off.
- **Deliberate non-declarations, recorded in the doc**: the 12→1 loop restart
  and Phase 1's idle-with-retry are runtime-paced loops whose exit is
  governance (COR-1618 consent per tick, COR-1620 stop-marker, `<idle-cap>`),
  not an iteration budget — per COR-1005 §When NOT to Use. §Phase 12 now says
  so explicitly, so future audits do not re-flag them.

## Why

COR-1617 is the corpus's flagship loop SOP, yet it was the least
machine-readable document in the audit: `af plan COR-1617` produced an empty
checklist (the only numbered list sat inside a code fence), and its two genuine
step-level back-edges existed only as prose (COR-1005 failure mode ①).

## Impact Analysis

- **Systems affected:** one PKG rules doc; this CHG plus its FXA-0000 PRJ index
  row (via `af index`); one CHANGELOG Unreleased entry. No code paths change.
- **Consumers:** `af plan COR-1617` goes from zero steps to the real 12;
  `--graph` renders both back-edges (ASCII shows one 🔁 annotation per
  from-step — an existing renderer limitation, both edges present in Mermaid).
- **Semantics flags for review:** `replan-blocker`'s max 2 + exhaustion
  sentence are new (⚠️ above). `iterate-round` is purely declarative.
- **No cascade:** COR-1618/1620/1621/1622/1602/1615 referenced, not edited;
  cross-doc "§Phase N" references remain valid (numbering unchanged).
- **Rollback plan:** revert the doc edit, set this CHG to Rolled Back, re-run
  `af index`, and remove or amend the CHANGELOG Unreleased entry.

## Implementation Plan

1. Rename §Phases → §Steps; un-fence the 12-line list; declare both loops;
   §9 loop note; §12 non-declaration rationale; Change History row.
2. Validate: `af validate COR-1617`, `af plan COR-1617` extracts 12 steps,
   `--graph` renders both back-edges, docs drift test, full `make check`.
3. CHANGELOG Unreleased entry; PR; COR-1615 bot loop to merge-ready.

---

## Change History

| Date       | Change          | By          |
|------------|-----------------|-------------|
| 2026-08-12 | Initial version | Claude Code |
| 2026-08-12 | Implemented: section renamed, 12 steps extract, both back-edges render, validation green | Claude Code |
| 2026-08-12 | Codex R1: iterate-round max 10 → 13 — COR-1005 exhaustion fires at the hard stop (soft cap + extension), not the soft cap | Claude Code |
