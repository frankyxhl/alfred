# Design: COR-1005 — Engineer Workflow Loops

**Date:** 2026-08-11
**Status:** Approved (implemented on branch feat/cor-1005-engineer-workflow-loops)
**Note:** Relocated from `docs/superpowers/specs/` — `scripts/build_docs.py` rmtree's `docs/`. Content identical to the user-approved version.
**Scope decision:** Narrow — authoring-time loop design inside a single SOP. Runtime loop governance stays in COR-1617/1620/1624–1627 (pointers only, no duplication). The wide "full loop-engineering discipline" scope (LangChain four-layer stack: agent core / verification / event-driven / hill-climbing) was explicitly rejected.

## Problem

The `af` engine already executes non-sequential SOPs: `Workflow loops:` metadata (back-edges with `id / from / to / max_iterations / condition`, including cross-SOP targets `PREFIX-ACID.step`) and `Workflow branches:` metadata (forward branches `3a/3b` with edge labels) are parsed, validated, and rendered by `af plan --graph`. The corpus also has many SOPs that *run* specific loops (COR-1617, COR-1620, COR-1624–1627, COR-1503, COR-1600/1601).

What is missing is an SOP that teaches authors **how to design a loop** when writing an SOP. COR-1000 (Create SOP) says nothing about `Workflow loops/branches`, exit criteria, or iteration budgets. Result: only one bundled SOP (COR-1602) declares a machine-readable loop; every other iterative process is authored as prose ("repeat as needed"), invisible to the planner, the graph renderer, and validation.

## Deliverable

New PKG document `src/fx_alfred/rules/COR-1005-SOP-Engineer-Workflow-Loops.md`.

### Metadata

- **Applies to:** All projects using the COR document system
- **Tags:** workflow, loop
- **Related:** COR-1000 (Create SOP — the parent authoring flow), COR-1602 (reference consumer of `Workflow loops:`), COR-1617 (Multi-Agent Workflow Loop), COR-1620 (Self-Pacing Loop Primitives), COR-1624/1625/1626 (Loop autonomy ladder)
- **Disposition:** inherit-only

### Why section — three failure modes this SOP closes

1. **Prose loops** — iteration written as narrative ("repeat until reviewers are satisfied") is invisible to `af plan`, `--graph`, and `af validate`; the checklist renders as a straight line that does not match real execution.
2. **Unbounded loops** — no `max_iterations` means no cost ceiling; a non-converging loop spins.
3. **Success-only exits** — a loop whose only exit is the success condition has no defined behavior when the budget is exhausted; non-convergence stalls the workflow.

### Steps section (author-facing)

1. **Choose the control-flow shape.** Decision test:
   - Steps always run once, in order → plain sequential steps.
   - One decision point fans out to alternative next steps → `Workflow branches:` (forward branch, labeled edges).
   - A later step can send execution back to an earlier step → `Workflow loops:` (back-edge).
   - The loop body is a reusable process in its own right → separate SOP + cross-SOP back-edge (`PREFIX-ACID.step`).
2. **Design both exits.** Every loop needs (a) an observable success condition and (b) a defined exhaustion path — what happens when `max_iterations` is reached (escalate to a human, degrade, explicitly abandon). A loop with only a success exit is a design defect.
3. **Set the `max_iterations` budget.** Derive from per-iteration cost × expected convergence; state the exhaustion behavior from step 2 in the step body.
4. **Write the `condition` predicate.** Must be observable and decidable (e.g. "iteration is on and not all reviewers approve"). Anti-pattern: "until satisfied".
5. **Author the metadata.** Exact syntax with examples:

   ```
   **Workflow loops:** [{id: review-retry, from: 7, to: 3, max_iterations: 3, condition: "iteration is on and not all reviewers approve"}]
   ```

   Cross-SOP form: `to: COR-1602.3`. Branch form:

   ```
   **Workflow branches:**
     - from: 2
       to:
         - {id: 3a, label: pass}
         - {id: 3b, label: fail}
   ```

   Sub-steps are authored as `3a.` / `3b.` headings; every edge carries a label.
6. **Verify.** `af plan --graph` — the rendered flowchart must match the intended control flow; `af validate` must pass (schema enforces the five required loop keys).
7. **Assign runtime governance (pointer only).** Pick the loop's autonomy rung per COR-1624/1625/1626; long-running self-paced loops use COR-1620 primitives. This SOP does not restate their content.

### Guard rails

- `condition` must be observable — no subjective prose predicates.
- Every branch edge must carry a `label`.
- The exhaustion behavior for every loop must be written in the step body, not implied.

## Companion changes (same PR, each its own surface)

1. **COR-1000** — one pointer line in Steps: steps that iterate or branch → design them per COR-1005.
2. **COR-1103** — one intent-router row: "design an SOP with loops/branches" → COR-1005.
3. **PRJ CHG document** — records the addition per repo convention (pattern: FXA-2234).
4. **CHANGELOG** — entry under `## Unreleased`. (README version bullets are added by the release-bump PR per repo convention — not this PR.)
5. **COR-0000 Document Index** — new row for COR-1005; `af validate` green; any bundled-rules drift-guard tests CI enforces.

## Non-goals

- No changes to `workflow.py` or any engine code — documentation-only PR.
- No coverage of verification-loop / event-driven / hill-climbing architecture layers.
- No new tags in the controlled vocabulary (reuses `workflow`, `loop`).

## References

- LangChain, "The Art of Loop Engineering" — four-layer loop stack; exit criteria via rubrics.
- cobusgreyling/loop-engineering — phased autonomy L1/L2/L3 (already covered by COR-1624–1626), verification ownership, cost visibility.
