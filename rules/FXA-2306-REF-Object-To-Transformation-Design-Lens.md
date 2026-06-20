# REF-2306: Object-To-Transformation-Design-Lens

**Applies to:** FXA project
**Last updated:** 2026-06-20
**Last reviewed:** 2026-06-20
**Status:** Active

---

## What Is It?

A design lens, not a mandate. It reframes Alfred's model from "what objects exist
and what fields do they have" to "what *transformations* (arrows) are legal between
states, and is each arrow honest about its entry condition, exit condition,
responsible party, and evidence."

Source: the essay *从对象到转换：对 Agent 生命周期的新看法* (Freelemon, 2026-06-19).
Engineering kernel of that essay, stripped of category-theory vocabulary:

> An object is defined less by its fields than by the legal arrows in and out of
> it. A `status = published` string is not a lifecycle event unless you can say
> where it came from, who approved it, what it passed, and whether it can roll back.

This REF records how that kernel maps onto Alfred **as it already exists**, and
the two concrete gaps where the lens exposes real defects. It is the design basis
for future evolve cycles (CLD-1801 / FXA-2148). It proposes no code change by
itself — scope decisions go through PRP/CHG.

---

## Content

### 1. The lens already fits — Alfred is ~70% an "arrows" system

Alfred is not an object-CRUD system that needs converting. Its SOP-composition
layer already models typed morphisms and their composition:

| Essay concept | Alfred mechanism | Location |
|---|---|---|
| Object | `Document` / Agent | `core/document.py` |
| Morphism with typed boundary | SOP `Workflow input/output/requires/provides` | `core/schema.py` (`_WORKFLOW_FIELDS`) |
| Composition `A→B ∘ B→C ⇒ A→C` | `af plan --task` auto-chains SOPs by Task tags + requires/provides | `core/compose.py` |
| Where does failure land / branch | `Workflow branches`, `Workflow loops` | `core/workflow.py` |
| Who triggered / what evidence | COR-1402 Declare Active Process + COR-1206 Agent Activity Log | PKG |
| State honesty (allowed states) | `ALLOWED_STATUSES` per `DocType` | `core/schema.py` |

Conclusion: the essay validates the existing direction. It is **not** a reason to
rewrite SOPs in category-theory terms. The essay itself says you do not need to
"hold a category-theory meeting every time."

### 2. Gap A — status is a flat *set*, not a *transition graph*

`ALLOWED_STATUSES[CHG] = ["Proposed","Approved","In Progress","Completed","Rolled Back"]`
is a membership set. `af update --status` (`commands/update_cmd.py` →
`validate_spec_status`) checks only "is this a legal value", never "is this a legal
move *from the current value*". Today `Completed → Proposed` and
`Rolled Back → In Progress` are both accepted silently.

This is exactly the essay's "state honesty" point: a state needs an entry
condition and an exit condition, not just a name.

- **Evidence (real, not hypothetical):** FXA-2189 / FXA-2191 — "Fix invalid CHG
  status" — an illegal status value already shipped once and needed a corrective
  CHG. A transition graph would have rejected it at write time.
- **Smallest honest fix (defer to PRP):** one adjacency table per `DocType`,
  built only from that type's own `ALLOWED_STATUSES` (e.g. for PRP,
  `Draft → {Approved, Rejected}`; never an edge that mixes statuses across
  types), enforced in `af update --status`, with a `--force` escape hatch for
  migrations. ~30 LoC + one TDD test.

### 3. Gap B — morphism metadata exists but is mostly unused

The schema has supported typed SOP I/O since FXA-2204, but only **5 of ~80 SOPs**
declare `Workflow input/output`. The remaining ~75 are "one big object described
in prose" — the document-level version of the essay's anti-pattern (a wide `Order`
propped up by a `status` string instead of `DraftOrder → PaidOrder → ShippedOrder`).

- This matters **only for SOPs that actually enter `af plan` composition chains.**
  Backfilling I/O on SOPs nobody composes is metadata nobody reads — YAGNI.
- **Smallest honest fix (defer to PRP):** backfill `Workflow input/output` on the
  composable SOPs only, and have `af validate` warn (not error) when a SOP
  participates in routing/composition but declares no I/O.

### 4. What this lens does NOT justify

- ✗ Rewriting the 80 SOPs in category-theory vocabulary, or adding
  Monad/Functor/Natural-Transformation names to documents. The value is the
  *question set* ("which arrows are legal, what's the evidence"), not the jargon.
- ✗ Mass backfill of morphism metadata onto non-composable SOPs.
- ✗ Any change to `ALLOWED_STATUSES` semantics without a PRP — status transition
  rules are a behavioral contract many docs depend on.

### 5. The question set (reusable in design / review / evolve)

When modeling or reviewing any Alfred surface, ask arrows before objects:

1. What are the core states?
2. From each state, which next states are legal?
3. Which transitions are commands vs. events?
4. Which transitions are pure vs. side-effecting?
5. Which transitions require human approval?
6. Which transitions must leave an audit trail / evidence?
7. Which failures are retryable vs. blocking?
8. Which states can roll back vs. append-only?

Only after those: decide objects, tables, interfaces, UI.

---

## Change History

| Date       | Change                                                                                                                                                              | By          |
|------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------|
| 2026-06-20 | Initial version — maps "object→transformation" essay onto Alfred; records Gap A (status transition graph) + Gap B (unused morphism metadata) as evolve design basis | Claude Code |
