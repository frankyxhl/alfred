# PRP-2225: Branching ASCII In Plan Graph

**Applies to:** FXA project (`af plan --graph` ASCII renderer)
**Last updated:** 2026-04-27
**Last reviewed:** 2026-04-27
**Status:** Draft
**Related:** FXA-2217, FXA-2218, COR-1202

---

## What Is It?

Extend the nested-ASCII renderer in `src/fx_alfred/core/dag_graph.py` (shipped in v1.7.0 via FXA-2217 / FXA-2218) so that a SOP step with multiple labeled outgoing edges renders as a horizontal branch with edge labels and sibling step-boxes — instead of collapsing into a linear stack and losing the branch semantics.

Scope cut: **Mid** — sub-step numbering (`3a`/`3b`/`3c`), labeled edges, **auto-detected convergence from step sequence** (renderer infers `3a/3b/3c → 4` from `## Steps` ordering and draws the join). Explicit `joins:` metadata for non-default convergence (terminal siblings; non-adjacent join targets) and a single-column terminal-width fallback are **deferred to Cut 3 / Full**.

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

1. **New SOP metadata field `Workflow branches:`** — sibling to `Workflow loops`. Topology AND labels live in metadata (per Round 2 OQ-3 revision). Schema:
   ```yaml
   Workflow branches:
     - from: 2                    # integer step ID
       to:
         - {id: 3a, label: pass}
         - {id: 3b, label: fail}
         - {id: 3c, label: escalate}
   ```
   Each `to` entry is a dict with `id` (sub-step ID, regex `\d+[a-z]`) and optional `label` (string, max 12 cells via `wcwidth` — see Risks). Validation: `from` must reference an existing integer step; each `to.id` must reference an existing sub-step; sub-step IDs must follow `\d+[a-z]` regex (single suffix letter, max 26 siblings — purely a syntactic upper bound; renderer hard-caps at 4); the leading integer of every `to.id` must be one greater than `from` (e.g., `from: 2` requires siblings `3a`/`3b`/etc — not `2a`/`2b`).

2. **Step prose stays clean** — sub-step text in `## Steps` is normal step body, no embedded `[label]` syntax. The earlier Round 1 inline-label proposal was rejected on Round 2 review: `[GATE]` is already a parsed token in `core/steps.py:49` (detected anywhere in step text, not just at start), so `[pass]` would collide; and embedding renderer hints in instruction prose violates the metadata-as-topology principle that `Workflow loops` already follows.
   ```
   3a. 五类 No Silent 检查
   3b. Entry 完整性检查
   3c. Challenge 入口
   ```

3. **Extend step-ID parsing** — accepts `\d+[a-z]?` for sub-step support. All-integer SOPs (every existing SOP in the corpus) keep working unchanged. Storage shifts from `frozenset[int]` to `frozenset[str]` with `str(int)` for legacy entries. The `--json` output's step-ID type changes from `int` to `str` — documented as a v1.8.0 breaking note for any downstream JSON consumer.

   **Migration Impact Table** — every consumer of `step_indices` and integer step IDs that needs auditing. Pre-verified by Codex Round 1 review:

   | File:line | Current type | New type | Migration action | Test coverage |
   |---|---|---|---|---|
   | `core/workflow.py:332` `_parse_step_indices` | `frozenset[int] \| None` | `frozenset[str] \| None` | Convert match group via `str(int)` for legacy; emit `\d+[a-z]?` strings for sub-steps | New test: SOP with mixed `1, 2, 3a, 3b, 4` parses to `{"1","2","3a","3b","4"}` |
   | `core/workflow.py:185` `CROSS_SOP_REF` | `r"^...\.(?P<step>\d+)$"` | `r"^...\.(?P<step>\d+[a-z]?)$"` | Cross-SOP loop targets can reference sub-steps too | New test: `COR-1500.3a` parses cleanly |
   | `core/workflow.py:206` `cross_sop_target()` returns `tuple[str, str, int]` | `tuple[str, str, str]` | Return step as string | Existing tests must update int→str expectation |
   | `core/workflow.py:393` `loop.from_step not in step_indices` | int-vs-int | str-vs-str | Coerce `loop.from_step` to `str` at comparison; OR change `LoopSignature.from_step: int` to `str` (preferred — matches new schema) | Membership-check regression test |
   | `core/workflow.py:425` `loop.to_step not in step_indices` | int-vs-int | str-vs-str | Same as above | Same |
   | `commands/validate_cmd.py:325` membership check | int | str | Same coercion strategy | Add SOP fixture with sub-step in `Workflow loops.to` |
   | `commands/plan_cmd.py:191` `_classify_step(step_idx: int)` parameter; **iteration sites at lines 208–209** `loop_to_steps.get(step_idx)` / `loop_from_steps.get(step_idx)` | int | str | Change parameter type; both dict accesses become `str`-keyed | Plan-builder unit test with sub-step IDs |
   | `commands/plan_cmd.py:278/283/344` plan-builder dict keying | `dict[int, LoopSignature]` | `dict[str, LoopSignature]` | Re-key on plan construction; affects `--todo` and `--graph` output | Same as above; snapshot test |
   | `core/ascii_graph.py` — int-indexed step iteration. **Signature lines: 134/360/397; loop bodies / iteration sites: 173, 219, 265.** All 15 hits found via `git grep -n step_idx src/fx_alfred/core/ascii_graph.py` need auditing, not just the cited 3. | int | str (with `str.isdigit()` shortcut where legacy hot path matters) | Touch every loop bound that assumes `range(1, n+1)`; review every `for i, step_idx in enumerate(step_indices)` (e.g. line 173) | Render fixture: SOP with `1, 2, 3a, 3b, 4` exercising all 15 hits |
   | `core/dag_graph.py:158` `step_row_index[(phase_num, step["index"])] = ...` | tuple key uses int | tuple key uses str | Update key construction; affects loop annotation positioning | Render test: SOP with sub-step that has loop annotation |
   | `core/phases.py:23` `StepDict.index: int` TypedDict field | int | str | Update TypedDict field; ripples through every consumer (already covered above) | Type-check sweep (`pyright src/`) |
   | `core/mermaid.py:117` `step_idx: int = step["index"]` | int | str | Mermaid emits same string IDs in node labels (e.g. `S2_3a`); minimal change since Mermaid IDs are already strings concatenated with `_` | Mermaid-output snapshot test for sub-stepped SOP |
   | `core/steps.py:45/59` step-line regex `(\d+)\.` | int (cast on line 47) | str | Extend regex to `(\d+[a-z]?)`; drop the `int(...)` cast on line 47; `gate` detection unchanged | Existing gate tests run; add sub-step gate test |
   | `commands/validate_cmd.py:28` imports `parse_top_level_step_indices` (returns `frozenset[int]` per `core/steps.py:70`); **call site at line 324** `target_step_indices = parse_top_level_step_indices(steps_section)` then `if t_step not in target_step_indices` | int | str | The helper return type changes (covered under steps.py:70); the call site at line 324 then compares string-vs-string instead of mixed | Add SOP fixture with sub-step in `Workflow loops.to` (cross-SOP target) |
   | `core/workflow.py` parse-time `Workflow loops.from / to` int validation (current type checks in `parse_workflow_loops` near line 281) | int | str-or-int (legacy ints accepted; new sub-step strings accepted) | Update parser type guard to accept both; emit canonical `str` form internally | Parser tests for both formats |
   | `--json` output (cli emit path) | int step IDs | str step IDs | `--json-legacy-step-ids` shim for one minor cycle: emits ints; sub-step entries emitted as `{"id": 3, "branch_letter": "a"}` so consumers don't lose information silently | Snapshot test for both legacy and new `--json` shapes |

   **Self-audit guarantee** (per MEMORY note `feedback_widening_refactor_self_audit.md`): before dispatching the implementation PR for review, run `git grep -nE "step_indices|step_idx|isinstance\(.*step.*int\)|\.step.*int|range\(.*step"` over `src/fx_alfred/` and audit every additional hit not in the table above.

4. **Renderer extension** — when a phase contains a step with a matching `Workflow branches` entry, the layout draws:
   - `└──┬──┬──┬──┘` connector below the parent step
   - Edge label (from `to[i].label`) printed above each branch arrow, **centered between adjacent connector tees** (between `┬` at `c_i` and `┬` at `c_{i+1}`), max-width = `(c_{i+1} - c_i) - 2` cells via `wcwidth`. The first label centers between the parent box's left border and `c_2`; the last label centers between `c_{N-1}` and the parent box's right border. Truncated to 12 cells with `…` per `wcwidth`. (Single rule replacing the earlier "centered under each tee" framing — confirmed unambiguous Round 3.)
   - Sibling step-boxes side-by-side, each with `▼` drop above
   - **Auto-detected convergence** (per revised OQ-4): if `## Steps` has the next sequential integer step after the branch group (e.g., `3a, 3b, 3c, 4`), the renderer infers convergence and draws a `└──┼──┘` join connector + `▼` arrow into step 4.
   - **Dangling tails** only when no next sequential integer step exists in `## Steps` after the branch group — those siblings render with no continuation arrow (genuinely terminal flow). When a next integer step *does* exist, convergence is mandatory in Mid (no opt-out); authors who want terminal-but-step-N+1-exists must wait for Cut 3's `joins: null` per-tail flag.

   **Geometry algorithm sketch** (avoids "redesign at coding time" — Gemini Round 1 fix #3): given N siblings rendered at column offsets `c_1..c_N` (column `c_i` is the center of sibling box `i`):
   - Top connector tees (`┬`) anchor at each `c_i`; horizontal `─` runs fill `[c_1, c_N]` along one row immediately below the parent box's bottom border (`└…┘` becomes `└──┬──┬──┬──┘` with `┬` at each `c_i`).
   - Edge labels print on the row between the connector and the sibling box top — centered between adjacent connector tees, max-width = `(c_{i+1} - c_i) - 2` *cells* (cell-width via `wcwidth`, NOT character count — CJK labels count 2 cells per char).
   - Sibling boxes width = `max(text_len(s_i), label_len(l_i)) + 2*padding`, separated by 2-cell gutter.
   - Convergence join `┼` placement: `(c_1 + c_N) // 2`, on a single horizontal `─` row below sibling boxes; `└…┘` corners terminate at `c_1` and `c_N` respectively.

   **Auto-convergence edge-case handling** (Codex Round 1 concern #3, validated by the validator, not the renderer):
   - **Skipped next-integer** (`3a, 3b, 3c, 5` — no step 4): `af validate` rejects with `"Workflow branches.from=2: convergence target step 4 missing; siblings 3a/3b/3c have no next-sequential integer"`. Renderer never sees this case.
   - **Non-contiguous siblings** (`3a, 4, 3b`): `af validate` rejects with `"sub-step 3b appears at step-position 5 in ## Steps but should be contiguous with 3a (position 3)"`. Renderer never sees this.
   - **Convergence to a `[GATE]` step** (e.g., next step has gate marker): allowed; renderer draws the join into the gate step normally — gate semantics are independent of branching.
   - **Multiple branch points in one SOP** (`from: 2; from: 6`): renderer iterates each branch group independently; no interaction.

5. **`af plan --todo` output** — flat TODO retains `3a`/`3b`/`3c` labels in `[CHK]` numbering (e.g., `- [ ] 3a [SOP-XXXX] [pass] 五类 No Silent`). Inline label preserved in TODO text.

6. **`flat` layout supports branches** (per OQ-5 resolution) — `--graph-layout=flat` is a long-term contract, not a deprecation track. Branch+convergence geometry is extracted as a shared primitive in `dag_graph.py` (or new `core/branch_geometry.py`); `nested` wraps the primitive in phase boxes, `flat` uses it directly without the outer wrapper. Both renderers produce branch output. Refactor cost ~80–100 LOC of factoring; not full duplication.

7. **`af validate` cross-checks** — `from` references existing integer step; each `to.id` references an existing sub-step; sub-step IDs are well-formed (`\d+[a-z]`); leading integer of every `to.id` equals `from + 1`; no orphan sub-steps (every `Xa`/`Xb` mentioned in `## Steps` must appear in some `Workflow branches.to` list); siblings are contiguous in `## Steps` (no integer steps interleaved); label cell-width via `wcwidth.wcswidth()` ≤ 12. Mid scope does **not** validate convergence — render-time rule is purely "is there a next-sequential integer step after the branch group? converge : dangle." Cut 3 will add `joins:` validation.

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
| Capability over-fit | mermaid-ascii solves the *general* DAG-layout problem (edge crossings, mixed graph types). Mid scope is much narrower: known parent → labeled siblings → auto-detected next-sequential convergence. Realistic Mid implementation cost (per Scope §3-§7 + Risks reconciled Round 3): **~150–250 LOC** spanning step-ID parser widening, branch geometry (column offsets, tee placement, label centering, convergence join), `wcwidth` truncation, validator rules, and the shared-primitive factoring for `flat`/`nested`. Well below mermaid-ascii's full layout engine but explicitly *not* the "30-40 lines" framing used in Round 1/2 (Round 2 reviewers correctly flagged that estimate as undercooked). |

### Why not skip the feature entirely (Mermaid-only fallback)

Both reviewers Round 1 flagged the simpler alternative not addressed: emit a one-line ASCII fallback like `(this SOP has branches — render with --graph-format=mermaid)` for any SOP carrying `Workflow branches:`, and skip the geometry investment entirely. Considered and rejected:

- **The terminal IS the workflow surface.** `af plan --graph` is invoked at session start to load the plan into the agent's working memory. Telling the agent "render this SOP elsewhere" defeats the SOP-loading-into-context loop. The Mermaid output requires an external renderer (GitHub, Obsidian, Mermaid.live) — fine for documentation, useless mid-session in a terminal.
- **The corpus impact is real, not edge-case.** COR-1500 (TDD red/green/refactor), COR-1602 (review pass/fix), COR-1103 (routing), and the FXA series with multi-path checks all carry implicit branches today. A Mermaid-only fallback means every one of these SOPs renders an unhelpful one-liner in `af plan --graph` output for the foreseeable future.
- **Asymmetry with `Workflow loops`.** Loops render in ASCII today (FXA-2218); branches are the symmetric primitive. Refusing to render branches in ASCII would be the only place in the schema where one direction (back-edges) renders fully and the other (forward-edges) doesn't.

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

**OQ-3: Edge-label source.** *(Round 1: inline in step prose; **Round 2 revised → labels in metadata via `to: [{id, label}]` dicts**)*

Round 1 chose inline `Na. [label] step description`, with corpus grep showing zero collisions on `^N\.\s\[`. **Round 2 review surfaced a hard fact:** `core/steps.py:49` already detects `[GATE]` *anywhere in step text*, not just at start. An inline `[pass]` at the start of a sub-step body would collide with the existing parser's gate-detection scan, and a `[GATE]` anywhere in any sub-step body would shadow the intended label. The corpus grep was too narrow.

Round 2 also accepted the structural critique: embedding renderer hints inside human-readable instruction prose violates the metadata-as-topology principle that `Workflow loops` already follows. The "duplication" argument used to reject `labels:` in Round 1 doesn't survive — `to: [3a, 3b, 3c]` already lives in two surfaces (metadata + `## Steps`); adding `labels:` adjacent to `to:` doesn't add new duplication.

Final schema: `to: [{id: 3a, label: pass}, {id: 3b, label: fail}]`. Single source of truth for both topology and labels; no parser collision; step prose stays clean.

**OQ-3 sub-question (label cell-width):** label cap = 12 cells via `wcwidth.wcswidth(label)` (NOT character count). CJK characters render 2 cells wide, so a 6-char Chinese label like `通过失败处理理` is 14 cells — truncated to 11 cells + `…`. Adds `wcwidth` dependency (small, pure-Python, MIT, already a transitive dep of many projects).

**OQ-4: How is convergence handled in Mid scope?** *(resolved → auto-detect from sequence; defended against Round 2 inconsistency challenge)*

Resolution: the renderer **auto-detects convergence** from the step sequence — if `## Steps` lists a next sequential integer step after the branch group (e.g., `3a, 3b, 3c, 4`), it infers "all siblings converge to 4" and draws a `└──┼──┘` join + `▼` arrow. No new metadata required; the common case works natively in Mid. Cut 3's `joins:` field is deferred and narrower (only needed for non-default cases: terminal-but-implied-convergent siblings, convergence to non-adjacent steps).

**Round 2 challenge from Gemini reviewer:** OQ-1 rejected "auto-detect from prose" as brittle (citing FXA-2218); OQ-4's resolution then *infers* convergence from `## Steps` ordering, which is also inference. Internally inconsistent.

**Defense (kept resolution):** The two cases are categorically different.
- **OQ-1 prose inference** = parsing natural-language sentences (e.g., "If validation passes, go to step 4") to extract topology. Fragile because English/Chinese/etc. has many phrasings for the same intent.
- **OQ-4 sequence inference** = reading the *position of structured tokens* (`3a`/`3b`/`3c`/`4`) in the `## Steps` enumeration. The "structure" being inferred is the existence of a step numbered `N+1` after sub-steps `Na`/`Nb`/etc. — not natural-language meaning.

Validator strength: every edge case Codex flagged (skipped-integer, non-contiguous, gate-target) is rejected at `af validate` time, not silently inferred (see Scope item 4 — "Auto-convergence edge-case handling"). Renderer only sees well-formed cases. So the inference is bounded to one rule (`{N}a/Nb/Nc... → {N+1}` if both exist) with all violations caught upstream.

**Decision (Round 2 outcome):** defense accepted by Gemini Round 2 ("the validator-catches-everything argument + the structured-position-vs-prose distinction does hold under scrutiny"); auto-convergence stays in Mid. The previously-documented fallback (drop auto-convergence; ship `joins:` as Cut 3 first) is no longer in play for this PRP.

**OQ-5: `--graph-layout=flat` interaction.** *(resolved → render branches in flat too, via shared primitive)*

Frank confirmed `flat` is a long-term contract, not a deprecation track. Initial draft recommended (β) graceful degradation under the assumption `flat` was on its way out. With `flat` permanent, the answer flips: branch+convergence rendering must work in both layouts.

Implementation cost is *not* full duplication — branch geometry (sibling spacing, edge labels, join connectors) is extracted as a shared primitive (likely new `core/branch_geometry.py` or factored into `dag_graph.py`). `nested` wraps the primitive in phase boxes; `flat` uses it directly without the outer wrapper. Estimated additional cost vs nested-only: ~80–100 LOC of factoring + a flat-specific wrapper, not 270.

The factoring is also healthy on its own merits — v1.7.0's `dag_graph.py` has primitives that should already be extractable; this PRP is a forcing function for that cleanup.

---

## Risks

| Risk | Mitigation |
|---|---|
| Step-ID type change `int → str` blast radius across `step_indices` consumers (per MEMORY `feedback_widening_refactor_self_audit.md`) | Migration Impact Table in Scope item 3 enumerates every known consumer with file:line + migration action + test coverage. Pre-PR sweep: `git grep -nE "step_indices\|step_idx\|isinstance.*int.*step\|range\(.*step"` over `src/` audits any consumer not in the table. |
| `--json` output's `step` type changes from `int` to `str` | `--json-legacy-step-ids` shim emits ints (sub-step entries emitted as `{"id": 3, "branch_letter": "a"}` — no information loss); shim valid for one minor cycle (v1.8.x), removed at v1.9.0. Pre-removal sweep of `~/.alfred/` for consumer scripts; CHANGELOG notice in v1.8.0 release. |
| Width math fails on terminals < 80 chars (4 siblings × ~18-cell boxes ≈ 80 cells minimum) | Document 80-cell minimum-width assumption explicitly. When `shutil.get_terminal_size().columns < 80` and a SOP has branches, `af plan --graph` emits a one-line stderr warning (`warning: terminal < 80 cells; branchy SOP output may truncate. Use --graph-format=mermaid for narrow terminals`) and renders best-effort with truncation. **Single-column fallback rendering is deferred to Cut 3** (it's a separate renderer mode and doesn't belong in Mid scope). |
| Edge label truncation (12-cell cap) hides crucial branching semantics | `wcwidth`-aware truncation with `…`; validator emits warning when any label > 12 cells (encourages authors to choose terser labels rather than relying on truncation). Full label always preserved in `--json` output for tooling. |
| Auto-detected convergence misfires when author wants terminal siblings but a next sequential integer step exists | Validator rejects this case: if `Workflow branches` declares `to: [3a, 3b, 3c]` AND step `4` exists in `## Steps`, the convergence is *implied* — author cannot opt out in Mid. To opt out, ship Cut 3 (`joins: null` for terminal siblings); until then, restructure SOP. Documented as Mid limitation. |
| Auto-convergence "structured-position inference" originally challenged as inconsistent with OQ-1 anti-prose-inference (Gemini Round 1) | Defense in OQ-4 accepted by Gemini Round 2. No further mitigation needed; auto-convergence stays in Mid. |
| Multi-model review divergence between Codex and Gemini on auto-convergence (Round 2 expected) | Both must score ≥ 9.0 per COR-1611. If a reviewer holds < 9.0 on auto-convergence specifically (vs other dimensions), apply the OQ-4 fallback (drop auto-convergence; defer to Cut 3) and re-dispatch. Hard cap: 3 review rounds per FXA-2218 budget. |

---

## Approval

- [ ] Approved by: <reviewer> on <date>

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-27 | Initial draft per Q0=Option-1, OQ-1=Option-A, scope-cut=Mid, architecture=Solution-B (hand-roll + study mermaid-ascii). | Frank + Claude Code |
| 2026-04-27 | Resolved OQ-2..5: regex `\d+[a-z]`; inline labels via `[label]` prefix (corpus audit confirmed zero collisions); auto-detect convergence in Mid (revised — was "render below widest"); flat layout supports branches via shared geometry primitive. Updated Scope, Risks, removed obsolete Cut-3 deferral framing. | Frank + Claude Code |
| 2026-04-27 | Round 2 revisions per multi-model review (Codex 8.1 FIX, Gemini 8.1 FIX). **OQ-3 flipped: labels move from inline step prose to metadata `to: [{id, label}]` dicts** — forced by `[GATE]` collision in `core/steps.py:49` (parser detects `[GATE]` anywhere in text, would shadow inline `[label]`); also accepted Gemini's category-error reframe. Added Migration Impact table (Scope item 3) with 8+ specific consumer sites pre-verified by Codex. Added geometry algorithm sketch (Scope item 4). Added validator edge-case rules for skipped/non-contiguous/gate convergence. Added "Why not Mermaid-only fallback" subsection (Necessity). OQ-4 auto-convergence kept and explicitly defended (structured-position inference vs natural-language prose inference); fallback path documented. `wcwidth`-based 12-cell label cap. | Frank + Claude Code |
| 2026-04-27 | Round 3 cleanup per multi-model review (Codex 8.8 FIX, Gemini 8.75 FIX). Mechanical fixes only — no design changes. (1) Migration Impact table extended with 4 missing consumer rows (`phases.py:23`, `dag_graph.py:158`, `mermaid.py:117`, `workflow.py` parse-time validation), iteration-site citations added for `ascii_graph.py` (173/219/265 alongside signature lines), `plan_cmd.py:208/209` and `validate_cmd.py:28/324` added. (2) Scope summary line 15 rewritten — drops misleading "no convergence" framing. (3) Terminal/dangling-tail behavior reconciled across Scope §4, validator §7, and Risks. (4) Label placement collapsed to one rule ("centered between adjacent connector tees, max-width = `(c_{i+1} - c_i) - 2` cells"). (5) Single-column terminal-width fallback explicitly deferred to Cut 3 (was scope-creep into Risks). (6) "30-40 lines of math" claim replaced with honest "~150-250 LOC" estimate per Round 2 reviewer feedback. (7) OQ-4 fallback "decision deferred" wording removed (decision is now made: kept). | Frank + Claude Code |
