# CHG-2324: Declare Tier 2 Loop Back-Edges

**Applies to:** FXA project
**Last updated:** 2026-08-12
**Last reviewed:** 2026-08-12
**Status:** Proposed
**Date:** 2026-08-12
**Requested by:** Frank Xu (session request: continue the COR-1005 corpus audit with the tier-2 candidates)
**Priority:** Medium
**Change Type:** Normal
**Targets:** src/fx_alfred/rules/COR-1612-SOP-Respond-To-PR-Review-Comments.md, src/fx_alfred/rules/COR-1615-SOP-GitHub-App-PR-Review-Bot-Loop.md, src/fx_alfred/rules/COR-1802-SOP-Build-Weighted-Decision-Matrix.md

---

## What

Tier-2 retrofit from the COR-1005 corpus audit — three heterogeneous docs, each
getting its prose loop declared as `Workflow loops:` metadata:

- **COR-1612**: `{id: fix-round, from: 6, to: 1, max_iterations: 10}` — the §6
  wait→refetch cycle. Budget and exhaustion were already documented (stopping
  condition #4: 10-round nitpick-spiral fail-safe, escalate with options a/b/c);
  the step body now names the declared loop. Fully semantics-preserving.
- **COR-1615**: `{id: restart-on-push, from: 11, to: 1, max_iterations: 10}` —
  §11 "Restart after every push / Return to Step 1". ⚠️ The SOP documented **no
  cap of its own**; max 10 is adopted from COR-1612's documented 10-fix-round
  fail-safe (composed at §10; each restart follows a fix push). This is a new,
  aligned budget — flagged for owner sign-off.
- **COR-1802**: two back-edges — `anchor-rework` (4→2) and `recalibrate` (5→2).
  ⚠️ Both caps (max 2) are **newly proposed** (the doc documented the return
  paths but no counts); exhaustion paths (escalate to operator) are also new.
  Additionally, step headings are renamed `### Step N — Title` → `### N. Title`:
  the old form did not match the step parser, so `af plan COR-1802` extracted
  the column-0 sub-lists of steps 3/6 as phantom top-level steps and missed the
  real 8-step structure entirely. The rename fixes that pre-existing extraction
  defect; prose references ("return to Step 2") remain valid since numbering is
  unchanged.

## Why

Continuation of FXA-2323 (tier 1). The COR-1005 audit found these three docs
carry real iteration written as prose — invisible to `af plan`, `--graph`, and
validation (COR-1005 failure mode ①). COR-1802 additionally renders a wrong
checklist today (phantom steps), so its retrofit fixes an active defect, not
just visibility.

## Impact Analysis

- **Systems affected:** three PKG rules docs; this CHG document plus its
  FXA-0000 PRJ index row (via `af index`); one CHANGELOG Unreleased entry.
  No code paths change.
- **Consumers:** `af plan --graph` renders four new back-edges; `af plan
  COR-1802` output changes from phantom sub-list steps to the real 8 steps —
  the only behavior-visible change, and it corrects an existing error.
- **Semantics flags for review:** COR-1615's cap and COR-1802's two caps +
  exhaustion paths add previously-undocumented budgets (see ⚠️ above). COR-1612
  is purely declarative.
- **No cascade:** COR-1005/1602/1600/1601 referenced, not edited.
- **Rollback plan:** revert the three doc edits, set this CHG to Rolled Back,
  re-run `af index` so the FXA-0000 row reflects the status, and remove or
  amend the CHANGELOG Unreleased entry.

## Implementation Plan

1. Declare loops + step-body prose per member; COR-1802 heading renames.
2. Validate: `af validate` on all three, `af plan --graph` renders all four
   back-edges, `af plan COR-1802` extracts the real 8 steps, docs drift test,
   full `make check`.
3. CHANGELOG Unreleased entry; PR; COR-1615 bot loop to merge-ready.

---

## Change History

| Date       | Change          | By          |
|------------|-----------------|-------------|
| 2026-08-12 | Initial version | Claude Code |
