# PRP-2225: Branching ASCII In Plan Graph

**Applies to:** FXA project (`af plan --graph` ASCII renderer)
**Last updated:** 2026-04-27
**Last reviewed:** 2026-04-27
**Status:** Draft
**Related:** FXA-2217, FXA-2218, COR-1202

---

## What Is It?

Extend the nested-ASCII renderer in `src/fx_alfred/core/dag_graph.py` (shipped in v1.7.0 via FXA-2217 / FXA-2218) so that a SOP step with multiple labeled outgoing edges renders as a horizontal branch with edge labels and sibling step-boxes — instead of collapsing into a linear stack and losing the branch semantics.

Scope cut: **Mid** — sub-step numbering (`3a`/`3b`/`3c`), labeled edges, no convergence (joins). Convergence (Cut 3 / Full) deferred to a follow-up PRP if the Mid renderer holds up.

Architectural choice: **Hand-roll the geometry; study mermaid-ascii's Go source as a visual-style reference; no runtime dependency on it.** This is "Solution B" from the FXA-2225 design discussion (2026-04-27 D-tracker).

---

## Problem

Today (`af` 1.7.1), the nested ASCII renderer stacks every step vertically, regardless of how many outgoing edges it has. A SOP with a decision point — say `Audit Ledger Gate` fanning out to "五类 No Silent / Entry 完整性 / Challenge 入口" — collapses to:

```
┌─────────────────────────┐
│ 2. Audit Ledger Gate    │
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ 3a. 五类 No Silent       │   ← 3b, 3c stacked sequentially below
└────────────┬────────────┘      losing parallelism
             ▼                   losing edge labels (五类/Entry/Challenge)
┌─────────────────────────┐
│ 3b. Entry 完整性          │
└────────────┬────────────┘
             ▼
... (everything linearized)
```

The Mermaid output (`af plan --graph-format=mermaid`) renders correctly when GitHub/Obsidian renders it, but the ASCII output — which is what runs in the terminal — fundamentally cannot represent decision branches.

**Why it matters now:**
- COR-1202 ("Compose Session Plan") is the canonical entry point for `af plan --graph`. The user surfaced (2026-04-27) that the ASCII output is harder to read than equivalent hand-drawn Unicode-box diagrams precisely because it can't show decisions.
- Every COR SOP that has a real branch (COR-1500 TDD red/green/refactor decision; COR-1602 review-pass/review-fix; COR-1103 routing decisions) currently misrepresents itself in `--graph` output.
- The schema already supports `Workflow loops` (back-edges); forward branches are the symmetric missing primitive.

---

## Scope

**In scope (Mid):**

1. **New SOP metadata field `Workflow branches:`** — sibling to `Workflow loops`. Topology only; labels live inline in `## Steps` text (per OQ-3 resolution). Schema:
   ```yaml
   Workflow branches:
     - from: 2                    # integer step ID
       to: [3a, 3b, 3c]            # list of sub-step IDs (regex \d+[a-z])
   ```
   Validation: `from` must reference an existing integer step; each `to` entry must reference an existing sub-step; sub-step IDs must follow `\d+[a-z]` regex (single suffix letter, max 26 siblings — purely a syntactic upper bound; renderer hard-caps at 4); the leading integer of every `to` must be one greater than `from` (e.g., `from: 2` requires siblings `3a`/`3b`/etc — not `2a`/`2b`).

2. **Inline edge labels in step prose** (per OQ-3 resolution) — sibling step text uses `Na. [label] step description`. Parser extracts the bracketed prefix as the edge label; the rest is the step body rendered inside the box. Corpus audit (2026-04-27) confirmed zero existing steps start with `[`, so the syntax is collision-free.
   ```
   3a. [pass] 五类 No Silent 检查
   3b. [fail] Entry 完整性检查
   3c. [escalate] Challenge 入口
   ```
   Label cap: 12 visible chars, truncated with `…` past that. Empty `[]` allowed (renders branch with no label).

3. **Extend step-ID parsing** — `core/parser.py`'s step-index extraction (and the `step_indices: frozenset[int]` slot in `core/workflow.py:332`) accepts `\d+[a-z]?`. All-integer SOPs (every existing SOP in the corpus) keep working unchanged. Storage shifts from `frozenset[int]` to `frozenset[str]` with `str(int)` for legacy entries. The `--json` output's step-ID type changes from `int` to `str` — documented as a v1.8.0 breaking note for any downstream JSON consumer.

4. **Renderer extension** — when a phase contains a step with a matching `Workflow branches` entry, the layout draws:
   - `└──┬──┬──┬──┘` connector below the parent step
   - Inline edge label (extracted from sibling step prose) printed above each branch arrow, centered under the connector tee
   - Sibling step-boxes side-by-side, each with `▼` drop above
   - **Auto-detected convergence** (per revised OQ-4): if `## Steps` has the next sequential integer step after the branch group (e.g., `3a, 3b, 3c, 4`), the renderer infers convergence and draws a `└──┼──┘` join connector + `▼` arrow into step 4. No new metadata required.
   - **Dangling tails** only when no next sequential step exists (terminal branch) — those siblings render with no continuation arrow.

5. **`af plan --todo` output** — flat TODO retains `3a`/`3b`/`3c` labels in `[CHK]` numbering (e.g., `- [ ] 3a [SOP-XXXX] [pass] 五类 No Silent`). Inline label preserved in TODO text.

6. **`flat` layout supports branches** (per OQ-5 resolution) — `--graph-layout=flat` is a long-term contract, not a deprecation track. Branch+convergence geometry is extracted as a shared primitive in `dag_graph.py` (or new `core/branch_geometry.py`); `nested` wraps the primitive in phase boxes, `flat` uses it directly without the outer wrapper. Both renderers produce branch output. Refactor cost ~80–100 LOC of factoring; not full duplication.

7. **`af validate` cross-checks** — branches reference existing steps; sub-step IDs are well-formed; the leading integer of `to` entries equals `from + 1`; no orphan sub-steps (every `Xa`/`Xb` mentioned in `## Steps` must appear in some `Workflow branches.to` list); inline-label syntax (`[...]`) parses without ambiguity.

**Out of scope (this PRP):**

- **Explicit `joins:` metadata** for non-default convergence (terminal branches that *should* converge but don't follow next-sequential pattern; convergence to non-adjacent step). Strictly additive — adds `joins:` field — can ship as FXA-22XX once Mid auto-convergence proves out. The auto-detected case in (4) covers ~80% of expected use.
- **Author-drawn DAGs inside SOP markdown bodies** (Q0 option 2 from the brainstorm). Different surface entirely.
- **Mermaid output changes** — `mermaid.py` already handles branches via `A --> B & C` syntax. No change needed there.
- **mermaid-ascii Go binary as runtime dependency** — explicitly rejected (see "Approach" below).
- **Width-aware rendering** — fixed-width sibling boxes for v1; auto-shrink/wrap deferred.
- **More than 4-way branches** — v1 hard-caps at 4 siblings; > 4 falls back to linear-with-inline-labels (each sibling on its own line, label inline).

---

## Approach

### Why hand-roll, not depend on mermaid-ascii

mermaid-ascii (https://github.com/AlexanderGrooff/mermaid-ascii — Go, MIT, 1.3K⭐, actively maintained) is mature and would solve the layout problem. Three reasons we don't take a runtime dependency on it:

| Concern | Detail |
|---|---|
| Dependency shape | `fx-alfred` is pure-Python / pip-installable; adding a Go binary breaks that posture (CI matrix grows; locked-down environments break; Docker images grow; binary distribution cross-platform). |
| Loss of nested phase-box layout | v1.7.0's identity is the per-SOP outer phase box containing inner step-boxes. Mermaid TD/LR layouts are flat — no analogue. Switching renderers loses that visual structure. |
| Capability over-fit | mermaid-ascii solves the *general* DAG-layout problem (edge crossings, mixed graph types). Mid scope is far narrower: known parent → labeled siblings → continue below widest. ~30-40 lines of math, not a layout engine. |

### What we DO borrow from mermaid-ascii

Read `mermaid-ascii/pkg/graph/` Go source for visual-style reference only — specifically:

- Labeled-edge rendering pattern (e.g., `├─label►│`) — their typography for placing a label inline along an arrow
- Connector tee/junction characters (specifically how they handle the `┬`/`┴`/`┼` corners in dense layouts)
- Box-padding defaults (`paddingX`, `paddingY`, `borderPadding` defaults)

Estimated study time: ~30-60 min before implementation begins. Pure inspiration, zero code lift, no licensing concern.

### Implementation order (TDD per COR-1500)

1. **Red:** add fixture SOP with branching metadata; expected-ASCII golden file; failing test
2. **Green (parser):** extend step-ID regex + storage; existing tests stay green
3. **Green (validator):** new cross-checks for `Workflow branches`
4. **Green (renderer):** branch geometry; new tests for 2-way, 3-way, 4-way branches; `--todo` output for sub-step IDs
5. **Refactor:** consolidate any duplication between linear-stack path and branch path in `dag_graph.py`
6. **Docs:** CHANGELOG entry; update COR-1202 to mention branching support; update FXA-2217's "graph-layout" docs

### Multi-model review (COR-1602)

Codex + Gemini in parallel, COR-1608 (PRP rubric) → COR-1610 (Code rubric on the implementation PR). Both ≥ 9.0 to land. Two rounds expected.

---

## Open Questions

All five OQs were resolved 2026-04-27 in the design discussion. Recorded here for traceability and so reviewers can audit the reasoning rather than re-litigate from scratch.

**OQ-1: Auto-detect or explicit metadata?** *(resolved → explicit)*

Option A (explicit `Workflow branches:`) chosen over Option B (auto-detect from prose) and Option C (hybrid). Reasons: (1) `Workflow loops` already established the explicit-metadata precedent for graph topology; (2) auto-detect on prose is the brittleness FXA-2218 explicitly rejected for cross-SOP loops; (3) backfill cost is bounded — only SOPs with implicit branches need updating, the rest stay linear.

**OQ-2: Sub-step ID regex.** *(resolved → `\d+[a-z]`)*

Chosen over `\d+[a-z]+` (overkill — `3aa`/`3ab` has no use case beyond 4 siblings, which we hard-cap anyway) and `\d+\.[a-z]` (dotted form collides with the existing flat-TODO `phase.step` numbering convention). Single suffix letter, max 26 siblings — purely a syntactic upper bound; renderer hard-caps at 4. Matches how Frank wrote the demo metadata. Storage in `core/workflow.py` shifts from `frozenset[int]` to `frozenset[str]`; legacy integer steps stored as `str(int)`.

**OQ-3: Edge-label source.** *(resolved → inline in step prose)*

Chosen: option (b) — labels embedded inline as `Na. [label] step description`. The `[bracket-prefix]` is parsed as the edge label; the rest is the step body. Chosen over (a) `labels:` field in metadata (rejected because it duplicates information across two surfaces — the step number is in `## Steps` AND `Workflow branches.to`; coupling labels to topology by name was felt to be more error-prone than coupling labels to the steps they describe) and (c) no labels (rejected — labels are the readability feature that motivated this PRP).

**Sub-question (resolved by corpus audit 2026-04-27):** square-bracket prefix `[label]` chosen over `(label)` and `label:`. Corpus grep over `rules/*.md` and `src/fx_alfred/rules/*.md` returned **zero existing steps** starting with `[`, so the syntax is collision-free. Label cap: 12 visible chars, truncated with `…` past that.

**OQ-4: How is convergence handled in Mid scope?** *(resolved → auto-detect from sequence)*

Initial draft proposed (i) "render below widest sibling" — *revised on second look* because (i) encodes a falsehood (visually says "step 4 follows 3a" when it follows all three).

Resolution: the renderer **auto-detects convergence** from the step sequence — if `## Steps` lists a next sequential integer step after the branch group (e.g., `3a, 3b, 3c, 4`), it infers "all siblings converge to 4" and draws a `└──┼──┘` join + `▼` arrow. No new metadata required; the common case ("branches reconverge to next sequential step") works natively in Mid.

The deferred Cut 3 `joins:` field is now narrower — only needed for non-default cases: terminal branches that should converge but don't follow next-sequential pattern, or convergence to non-adjacent steps. Estimated to cover ~20% of branchy SOPs; the auto-detected case covers ~80%.

**OQ-5: `--graph-layout=flat` interaction.** *(resolved → render branches in flat too, via shared primitive)*

Frank confirmed `flat` is a long-term contract, not a deprecation track. Initial draft recommended (β) graceful degradation under the assumption `flat` was on its way out. With `flat` permanent, the answer flips: branch+convergence rendering must work in both layouts.

Implementation cost is *not* full duplication — branch geometry (sibling spacing, edge labels, join connectors) is extracted as a shared primitive (likely new `core/branch_geometry.py` or factored into `dag_graph.py`). `nested` wraps the primitive in phase boxes; `flat` uses it directly without the outer wrapper. Estimated additional cost vs nested-only: ~80–100 LOC of factoring + a flat-specific wrapper, not 270.

The factoring is also healthy on its own merits — v1.7.0's `dag_graph.py` has primitives that should already be extractable; this PRP is a forcing function for that cleanup.

---

## Risks

| Risk | Mitigation |
|---|---|
| Step-ID regex change breaks downstream consumers parsing `--json` output expecting `int` step IDs | Document the type change as a v1.8.0 note in CHANGELOG; add a deprecation-shim option `--json-legacy-step-ids` that coerces back to int (drops sub-step suffixes) for one minor cycle; only known consumer is `af` itself |
| Width math fails on terminals < 80 chars | Document minimum-width assumption; truncate gracefully; test against 80/120 widths |
| Inline edge labels wider than the column gutter overflow into adjacent siblings | Hard cap labels at 12 visible chars with `…` truncation (per OQ-3 sub-resolution); validator warns if any author's bracket exceeds the cap |
| Auto-detected convergence misfires when author intends siblings to be terminal but next sequential step exists | Add `[end]` inline marker (or empty branch terminator convention) so authors can opt out; OR document that "if you want terminal siblings, restructure so next sequential step doesn't exist" |
| Inline-label syntax conflicts with future SOP authors writing `[X]` for unrelated reasons (markdown checkboxes, citations, etc.) | Validator rejects `[label]` at start of step body if the step is *not* a sub-step in any `Workflow branches.to`; corpus audit confirmed zero current collisions but new authors get a clear error |
| Multi-model review divergence between Codex (likely "ship Mid") and Gemini (likely "do Full now") | Per COR-1611, both must score ≥ 9.0. The auto-convergence resolution narrows the gap considerably — Mid now handles the common convergence case natively, so Gemini's "ship Full" pressure is much weaker. If still blocked, escalate to a Leader call per COR-1601 |

---

## Approval

- [ ] Approved by: <reviewer> on <date>

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-27 | Initial draft per Q0=Option-1, OQ-1=Option-A, scope-cut=Mid, architecture=Solution-B (hand-roll + study mermaid-ascii). | Frank + Claude Code |
| 2026-04-27 | Resolved OQ-2..5: regex `\d+[a-z]`; inline labels via `[label]` prefix (corpus audit confirmed zero collisions); auto-detect convergence in Mid (revised — was "render below widest"); flat layout supports branches via shared geometry primitive. Updated Scope, Risks, removed obsolete Cut-3 deferral framing. | Frank + Claude Code |
