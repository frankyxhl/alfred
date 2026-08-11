# SOP-1005: Engineer Workflow Loops

**Applies to:** All projects using the COR document system
**Last updated:** 2026-08-11
**Last reviewed:** 2026-08-11
**Status:** Active
**Tags:** workflow, loop
**Related:** COR-1000 (Create SOP — the parent authoring flow), COR-1602 (reference consumer of `Workflow loops:`), COR-1617 (Multi-Agent Workflow Loop — runtime umbrella), COR-1620 (Self-Pacing Loop Primitives — runtime pacing), COR-1624 / COR-1625 / COR-1626 (Loop autonomy ladder — runtime governance)
**Workflow loops:** [{id: fix-authoring, from: 7, to: 5, max_iterations: 3, condition: "af validate fails or the rendered graph does not match the intended control flow"}]
**Disposition:** inherit-only

---

## What Is It?

The design discipline for non-sequential SOPs: when and how to author loops
(back-edges) and branches (labeled forward forks) into an SOP's Steps so the
control flow is machine-readable — rendered by `af plan --graph` and enforced
by `af validate` — instead of buried in prose.

This SOP governs *authoring time*. Running a loop (pacing, wakeups, autonomy)
is governed by the runtime SOPs listed under Related.

---

## Why

Three failure modes recur when iteration is authored as prose:

1. **Prose loops** — "repeat until reviewers are satisfied" is invisible to the
   planner, the graph renderer, and validation; the generated checklist renders
   as a straight line that does not match real execution.
2. **Unbounded loops** — a loop without `max_iterations` has no cost ceiling;
   when it does not converge, it spins.
3. **Success-only exits** — a loop whose only exit is its success condition has
   no defined behavior when the iteration budget is exhausted; non-convergence
   stalls the whole workflow.

---

## When to Use

- Authoring or revising an SOP whose steps iterate (retry, review-fix, poll) or
  fork on a decision
- Converting an existing prose loop ("repeat as needed") into declared metadata
- Splitting a loop body into its own SOP and wiring a cross-SOP back-edge

## When NOT to Use

- Straight-line SOPs — plain numbered steps need no loop metadata
- Runtime pacing of a *running* loop (wakeups, stop markers, cadence) — COR-1620
- Deciding how much autonomy a running loop gets — COR-1624 / COR-1625 / COR-1626

---

## Steps

1. **Choose the control-flow shape.** Apply the first matching rule:
   - Steps always run once, in order → plain sequential steps; stop here.
   - One decision point fans out to alternative next steps → forward branch
     (`Workflow branches:`).
   - A later step can send execution back to an earlier step → loop
     (`Workflow loops:`).
   - The loop body is a reusable process in its own right → author it as its own
     SOP and target it with a cross-SOP back-edge (`to: PREFIX-ACID.step`).

2. **Design both exits.** Every loop needs two exits, decided before any syntax
   is written:
   - a *success condition* — the observable state that ends iteration, and
   - an *exhaustion path* — what happens when `max_iterations` is reached
     without success: escalate to a human, degrade to a defined fallback, or
     explicitly abandon. A loop with only a success exit is a design defect.

3. **Set the iteration budget.** Choose `max_iterations` from per-iteration cost
   × expected convergence (review loops in this corpus converge in 2–3 rounds;
   COR-1602 uses 3). State the step 2 exhaustion behavior in the body of the
   loop's `from` step — not only in metadata.

4. **Write the condition predicate.** `condition` states when the loop *repeats*.
   It must be observable and decidable by the executing agent — e.g.
   `"iteration is on and not all reviewers approve"` (COR-1602). Anti-patterns:
   "until satisfied", "as needed", "if necessary".

5. **Author the metadata.** Loop form (all five keys required —
   `id`, `from`, `to`, `max_iterations`, `condition`):

   ```
   **Workflow loops:** [{id: review-retry, from: 7, to: 3, max_iterations: 3, condition: "iteration is on and not all reviewers approve"}]
   ```

   Cross-SOP back-edge: `to: COR-1602.3`. The reference format is strict:
   exactly three uppercase letters, hyphen, four digits, dot, integer step
   (`PREFIX-ACID.step`).

   Branch form — every edge carries a `label`; targets are sub-step IDs
   (digits + one letter). This inline form is the one the parser accepts;
   a multi-line YAML block is not read by `_BOLD_FIELD` and silently parses
   as an empty list:

   ```
   **Workflow branches:** [{from: 2, to: [{id: 3a, label: pass}, {id: 3b, label: fail}]}]
   ```

6. **Write the step bodies.** Branch targets are authored as their own numbered
   lines (`3a.` / `3b.`) standing in place of the plain numbered step — not as
   sub-headings nested under it. The `from` step of every loop spells out the
   repeat action and the exhaustion behavior in prose matching the metadata.

7. **Verify.** Run `af validate` (schema check: required loop keys and types,
   branch declarations, cross-SOP loop targets) and `af plan --graph <ID>`; the
   rendered flowchart must match the control flow you intended in step 1. Note
   `af validate` does not currently check intra-SOP loop step references,
   back-edge direction, or that `max_iterations` is positive — the graph
   inspection is your guard for those. On failure, return to step 5
   (loop `fix-authoring`, max 3 rounds); if still failing, re-examine the
   intended flow with a human reviewer — the design, not the syntax, is usually
   wrong.

8. **Assign runtime governance.** Before the SOP's loop runs unattended anywhere,
   pick its autonomy rung per COR-1624 (L1 report-only) / COR-1625 (L2 gated) /
   COR-1626 (L3 unattended, Draft). Long-running self-paced loops use the
   COR-1620 primitives. This SOP intentionally does not restate their content.

---

## Guard Rails

- `condition` must be observable — no subjective prose predicates.
- Every branch edge must carry a `label`.
- Every loop's exhaustion behavior must be written in the step body, not implied.
- Do not duplicate runtime-governance content from COR-1617/1620/1624–1627 —
  point to it.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-08-11 | Initial version (FXA-2322) | Claude Code |
