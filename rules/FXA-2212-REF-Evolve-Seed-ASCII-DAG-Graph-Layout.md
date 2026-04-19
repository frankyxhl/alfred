# REF-2212: Evolve-Seed-ASCII-DAG-Graph-Layout

**Applies to:** FXA project
**Last updated:** 2026-04-19
**Last reviewed:** 2026-04-19
**Status:** Active
**Tags:** evolve-seed, graph, cli, deferred

---

## What Is It?

A seed record for the next FXA-2149 (Evolve-CLI) run: add an opt-in DAG layout to `af plan --graph`
(`--graph-layout=dag`) that renders parallel / fork / join semantics and cross-phase loop edges
explicitly, instead of the current line-of-boxes layout.

Parked as a REF (not a PRP) because Evolve-CLI should re-score it cold against its own rubric.
Seeded by user feedback after the FXA-2211 PR merged (PR #52).

---

## Content

### Motivation — where the linear layout hides structure

Current `af plan --graph` ASCII output is one phase-box per SOP, stacked vertically with `▼`.
Loop edges are rendered **inside** the phase box with `◄──┐` / `──┘ max N`.

Two kinds of workflow structure are invisible in this layout:

1. **Parallel / fork-join inside a SOP.** COR-1602 (Multi-Model Parallel Review) dispatches to
   Codex + Gemini concurrently. Today the steps render as though they are sequential —
   `[2.1] Dispatch to Codex` appears on the line above `[2.2] Dispatch to Gemini`, not beside it.
2. **Cross-phase loops.** When an SOP's `Workflow loops` metadata points at a step in a **previous**
   phase (e.g. review fail → back to TDD Red), the edge can't be drawn inside the receiving box.
   Today's fallback is an inline annotation `→ back to N.M`.

### Demo — effect of the proposed DAG layout

Using COR-1500 (TDD) + COR-1602 (parallel review) as the concrete case:

#### Current `--graph-format=ascii` (linear phase boxes)

```text
┌──────────────────────────────────────────────┐
│ Phase 1: COR-1500 (TDD)                      │
│ [1.1] Red: write failing test                │
│ [1.2] Green: make it pass                    │
│ [1.3] Refactor                               │
└────────────────────┬─────────────────────────┘
                     ▼
┌──────────────────────────────────────────────┐
│ Phase 2: COR-1602 (parallel review)          │
│ [2.1] Dispatch to Codex    ◄───────┐         │
│ [2.2] Dispatch to Gemini           │         │
│ [2.3] Both must >= 9.0    ─────────┘ max 3   │
└──────────────────────────────────────────────┘
```

→ 2.1 and 2.2 look sequential (they're parallel); the review-fail loop can't leave phase 2 to point
back at 1.1.

#### Proposed `--graph-layout=dag` (fork / join / cross-phase track)

```text
           ┌───────────────────┐
           │ 1.1 Red           │
           └─────────┬─────────┘
                     ▼
           ┌───────────────────┐
           │ 1.2 Green         │
           └─────────┬─────────┘
                     ▼
           ┌───────────────────┐
           │ 1.3 Refactor      │ ◄───────────┐
           └─────────┬─────────┘             │
                     │                       │
             ┌───────┴───────┐ fork          │
             ▼               ▼               │
   ┌──────────────┐  ┌──────────────┐        │
   │ 2.1 Codex    │  │ 2.2 Gemini   │        │
   └──────┬───────┘  └──────┬───────┘        │
          │                 │                │
          └────────┬────────┘ join           │
                   ▼                         │
          ┌─────────────────┐                │
          │ 2.3 Gate ≥ 9.0  │ ───────────────┘
          └─────────────────┘   max 3 if either fails
```

→ fork `┬` / join `┴` make parallelism explicit; the cross-phase loop edge uses a right-side
vertical track instead of inline text.

### Proposed change scope

- **New file:** `src/fx_alfred/core/dag_graph.py` — DAG layout renderer
- **Edit:** `src/fx_alfred/commands/plan_cmd.py` — add `--graph-layout=linear|dag` (default `linear`
  for backward compat with existing tests and terminal habits)
- **Tests:** `tests/test_dag_graph.py` — snapshot tests for a few canonical shapes: pure linear,
  single fork+join, cross-phase loop, fork+cross-phase loop
- **Out of scope:** Mermaid renderer (`core/mermaid.py`) stays as-is; this is ASCII-only
- **Out of scope:** mutation of `core/ascii_graph.py` behaviour at default settings

### Evolve-CLI score (self-estimated, to be re-scored at run time)

Weights per FXA-2146: TV 35% / SR 30% / BC 20% / Nec 15%.

| Dim                | Score | Reason                                                                                                    |
|--------------------|------:|-----------------------------------------------------------------------------------------------------------|
| Test verifiability |     7 | Snapshot tests viable but ASCII alignment is fiddly; regression on `┬/┴/├/┤/┼` at odd widths is a real risk |
| Scope restraint    |     6 | New module + new flag + test file; not a one-liner, but isolated behind opt-in flag                       |
| Backward compat    |    10 | New flag, default unchanged; existing ASCII tests untouched                                               |
| Necessity          |     6 | User feedback (not a defect); semantic visibility gain is real but not urgent                             |
| **Weighted**       | **7.0** | Borderline — expect real run to land 6.5–7.5 after concrete measurement                                 |

Candidate is right at the 7.0 threshold. A real Evolve-CLI run's Evaluator will likely be stricter
on **Necessity** (no defect signal, pure ergonomics) and may discard. Recording here anyway so the
idea doesn't vanish.

### How to feed this into the next Evolve-CLI run

FXA-2149 Phase 2 signals do not include REF files. Two realistic paths:

1. **Manual seed:** at the start of the next Evolve-CLI session, explicitly list this REF in the
   Generator's candidate set alongside the auto-collected signals. (Human / orchestrator action.)
2. **Promote to PRP Draft:** if we decide ahead of time that the idea is worth a design review,
   skip the Evolve-CLI funnel entirely and file `af create prp --title "ASCII DAG graph layout"`.
   This is heavier but sidesteps the threshold risk.

Default handling: **option 1**. Stay as REF until the next Evolve-CLI run; let the Evaluator score
it cold. If discarded twice, bump to PRP and drive it manually.

### Related

- FXA-2211 — prior CHG that closed three edge-arm coverage gaps (PR #52) — user feedback on its
  merge surfaced this idea
- `src/fx_alfred/core/ascii_graph.py` — current renderer, line-of-phase-boxes layout
- `src/fx_alfred/commands/plan_cmd.py` — hosts the `--graph-format` option today
- COR-1602, COR-1603, COR-1604, COR-1605 — SOPs whose parallel / branching semantics are the
  primary beneficiaries of DAG layout

---

## Change History

| Date       | Change                                                        | By             |
|------------|---------------------------------------------------------------|----------------|
| 2026-04-19 | Initial version — seed recorded after FXA-2211 merge feedback | Frank + Claude |
