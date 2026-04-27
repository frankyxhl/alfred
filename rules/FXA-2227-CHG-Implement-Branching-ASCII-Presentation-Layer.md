# CHG-2227: Implement Branching ASCII — Presentation Layer

**Applies to:** FXA project (branch geometry primitive + nested/flat ASCII renderer + Mermaid output + v1.8.0 release)
**Last updated:** 2026-04-27
**Last reviewed:** 2026-04-27
**Status:** Proposed
**Date:** 2026-04-27
**Requested by:** Frank Xu
**Priority:** Medium (no production-blocking issue; ships the user-visible feature from PRP-2225)
**Change Type:** Normal
**Targets:** PRP-2225 implementation — second of two staged CHGs
**Depends on:** CHG-2226 (must merge first — the Data Layer types are required by the renderer)

---

## What

Land the **renderer + release** for PRP-2225 (Branching ASCII In Plan Graph). Builds on CHG-2226's data-layer foundation (sub-step parser, `Workflow branches:` schema, validator cross-checks) and ships the user-visible feature: branch + auto-convergence rendering in `af plan --graph`'s nested ASCII layout, with parity in the legacy flat layout, plus Mermaid output and v1.8.0 release.

This is the *Presentation Layer* half of a 2-CHG split. CHG-2226 (Data Layer) must be merged before this CHG executes — its types are consumed throughout this CHG's surface.

## Why

CHG-2226 is intentionally behavior-neutral (internal type widening only). This CHG is where the user-facing change lands: SOPs declaring `Workflow branches:` produce branched ASCII output instead of collapsing into a linear stack. Splitting renderer geometry from data-layer widening (per Round 1 reviewer consensus) gives renderer review surface its own focused PR — geometry is a different review skill from type widening, and the v1.8.0 release ships once visible behavior is green.

## Impact

### Files to be modified

| File | Nature | Estimated LOC |
|---|---|---|
| `src/fx_alfred/core/dag_graph.py` | Integrate `branch_geometry` primitives inside phase-box wrapping. **Display ID composed at render time** as `f"{step['index']}{step.get('sub_branch', '')}"` (e.g. `"3a"`); `step_row_index` keys remain int-keyed by `step['index']` since siblings are rendered as a group through `branch_geometry.render_branch()` rather than as individual rows. **No `step_idx: str` widening, no `step_indices` audit needed** — CHG-2226 Path B keeps types int. | ~40 |
| `src/fx_alfred/core/ascii_graph.py` | Integrate `branch_geometry` primitive without phase-box wrapping. Display ID composition same pattern as `dag_graph.py`. **Existing `step_idx`/`step_indices` int typing untouched** — every existing call site stays byte-identical; sub-step rendering is keyed off the new `sub_branch` field, not off type widening. | ~30 |
| `src/fx_alfred/core/mermaid.py` | When emitting node IDs, append the optional `sub_branch` to the integer step ID: `S{phase}_{step_index}{sub_branch}` produces `S2_3a` for sub-stepped steps and `S2_3` for plain steps. **`step_idx: int` typing at `mermaid.py:117` unchanged.** | ~10 |
| `src/fx_alfred/CHANGELOG.md` | v1.8.0 entry covering the user-visible feature | small |
| `pyproject.toml` | Version bump 1.7.1 → 1.8.0; add `wcwidth` to `dependencies` | small |
| `CLAUDE.md` (project root) | One-paragraph note on `Workflow branches:` syntax; reference PRP-2225 | small |
| `src/fx_alfred/rules/COR-1202-SOP-Compose-Session-Plan.md` | One-line mention that `af plan --graph` now renders branches when SOP metadata declares them | small |

### New files

| File | Purpose | Estimated LOC |
|---|---|---|
| `src/fx_alfred/core/branch_geometry.py` | Shared branch+convergence primitive used by both `nested` and `flat` renderers | ~100 |
| `tests/test_branch_geometry.py` | Invariant tests + golden tests for the primitive | ~150 |
| `tests/fixtures/branches_4way.md` | 4-way branch (renderer hard cap) | small |
| `tests/fixtures/branches_dangling.md` | Terminal branch (no next-sequential integer) | small |
| `tests/fixtures/branches_cjk.md` | CJK labels exercising `wcwidth` truncation | small |
| `tests/fixtures/branches_with_loops.md` | Branch + loop in same SOP — renderer test | small |

### Dependencies

**One new runtime dep: `wcwidth`** (pure-Python, MIT, ~2KB). Required for cell-width-correct label truncation (12-cell cap) in CJK terminals. `unicodedata.east_asian_width` is **not** a substitute — it doesn't handle combining marks, zero-width, or ambiguous-width consistently for terminal rendering. `wcwidth` is the de facto Python solution; widely-used transitive dep already.

### CHANGELOG (v1.8.0 entry)

Adds a feature-release entry with this shape:

> **`af plan --graph` now renders forward branches.** SOPs declaring `Workflow branches:` (e.g. `from: 2; to: [{id: 3a, label: pass}, {id: 3b, label: fail}]`) render as horizontal branches with edge labels, sibling step-boxes, and auto-detected convergence — instead of collapsing into a linear stack. Both `nested` (default) and `flat` layouts support branches. Mermaid output emits `S2_3a`-style node IDs.
>
> **New runtime dep:** `wcwidth` (cell-width-correct label truncation; required for CJK).
>
> **Internal:** sub-step IDs (`3a`, `3b`, etc.) flow through parser, validator, and plan-builder via the additive `StepDict.sub_branch` field landed in CHG-2226 (Path B / two-field architecture). No type-widening migration; `phases[].steps[].index` remains `int`. `todo[].index` format extends from `"phase.step"` (e.g. `"1.1"`) to `"phase.stepLetter"` (e.g. `"2.3a"`) — string-to-string, non-breaking.

### Documentation

- `CLAUDE.md` (project root) — one paragraph noting `Workflow branches:` exists; reference PRP-2225 for design rationale and CHG-2227 for implementation
- `COR-1202-SOP-Compose-Session-Plan.md` — one-line addition to "What Is It?" mentioning branch rendering; existing example body remains valid (it's a linear flow)
- No new SOPs needed

### Rollback

**Per-phase commit boundaries** (same pattern as CHG-2226). Phase 3 ships as a self-contained primitive with its own tests; if Phase 4 (nested integration) reveals the primitive shape is wrong, the integration commit reverts cleanly without touching the primitive. Final v1.8.0 release commit is reversible via `gh release delete v1.8.0` + branch revert + version bump back to 1.7.1.

---

## Phase 3 Primitive API Contract

Both Round 1 reviewers flagged that "Phase 3 builds a primitive; Phase 4+5 integrate" is too vague to validate before integration commits to the shape. Locking the contract here so reviewers can score Phase 3 independently and Phase 4/5 reviews can verify against a concrete API.

### Module: `src/fx_alfred/core/branch_geometry.py`

Public API (5 functions, all pure — no I/O, no global state):

```python
@dataclass(frozen=True)
class BranchRenderInput:
    parent_step_text: str           # the parent step's body (already truncated to box width)
    siblings: list[BranchTarget]    # from core/workflow.py (CHG-2226): NamedTuple(parent: int, branch: str, label: str)
                                    # e.g. [BranchTarget(3, "a", "pass"), BranchTarget(3, "b", "fail")]
                                    # The primitive composes the display ID f"{parent}{branch}" → "3a" internally.
    sibling_texts: list[str]        # body text for each sibling box (positional with siblings)
    converges_to: int | None        # next-sequential integer step number if auto-convergence applies; None for dangling
                                    # (str sub-step convergence targets are out of scope per PRP-2225 + CHG-2226)
    converges_to_text: str | None   # body text for the convergence step (only when converges_to is not None)
    box_width: int                  # the surrounding renderer's per-step box width (e.g. _STEP_BOX_WIDTH)

@dataclass(frozen=True)
class BranchRenderOutput:
    lines: list[str]                # the full ASCII render, one string per terminal row
    parent_anchor_row: int          # row index where the parent box's bottom edge sits
    convergence_anchor_row: int | None  # row index where the convergence step's top edge sits, or None for dangling
    step_anchor_rows: dict[str, int]  # {sub_step_id: middle_row_of_that_sibling_box}; e.g. {"3a": 5, "3b": 5, "3c": 5}
                                      # Required by dag_graph.py to place loop right-side tracks against sibling rows.
                                      # Caller (renderer) MUST use these row indices to anchor any annotations
                                      # (loops, gates, ⚠ markers) at the correct vertical position.

def render_branch(input: BranchRenderInput) -> BranchRenderOutput: ...

# Internal helpers (still importable; useful for invariant tests):
def compute_column_offsets(n_siblings: int, box_width: int, gutter: int = 2) -> list[int]: ...
def render_label_row(labels: list[str], offsets: list[int], box_width: int) -> str: ...
def render_join_row(offsets: list[int]) -> str: ...
```

### Label-slot semantics (clarified per Codex Round 1 #2)

There are **N labels for N edges** (one per outgoing branch arrow). The geometry has N column offsets `c_1..c_N`, with `┬` connectors at each. Labels print on the row between the parent's bottom border and the sibling boxes' top borders:

```
            parent box
└──┬──────┬──────┬──┘    ← parent_anchor_row
   │      │      │
  pass   fail  retry     ← label row: N labels, one per edge
   ▼      ▼      ▼
 [3a]   [3b]   [3c]      ← sibling boxes
```

**Each label centers at column `c_i`** (above the `┬` directly under it). Max-width per label = `min(c_i - prev_boundary, next_boundary - c_i) * 2 - 2` cells via `wcwidth`, with **concrete boundary formulas** (per Codex Round 2 #4):

```
prev_boundary[i] = (c_{i-1} + c_i) // 2    if i ≥ 2   else 0                        # mid-point with previous tee, or left edge
next_boundary[i] = (c_i + c_{i+1}) // 2    if i < N   else box_total_width - 1      # mid-point with next tee, or right edge of render
```

`box_total_width` = the full render width (length in cells of any line in `BranchRenderOutput.lines`; per invariant I2, all lines have uniform cell width). Empty labels render as blank in their slot. All labels empty → label row omitted entirely (one fewer row in output).

The earlier "centered between adjacent tees" framing is replaced: labels center *under* their tees, with collision avoidance against neighbors limiting the max-width. This matches mermaid-ascii's typography (which CHG-2227 borrows visually).

### Invariants (asserted in `tests/test_branch_geometry.py`)

These replace ~half of the originally-planned brittle golden ASCII tests. Goldens for the *full* output are still tested for 2-way / 3-way / dangling cases, but the geometry building blocks are tested by invariant assertion (more robust to spacing tweaks):

| # | Invariant | Test |
|---|---|---|
| I1 | `compute_column_offsets(n, w)` returns `n` strictly-increasing offsets | `test_offsets_strictly_increasing` |
| I2 | All output lines have the same visible-cell width (per `wcwidth.wcswidth`) | `test_lines_uniform_cell_width` |
| I3 | For every sibling `i`, the column at `offsets[i]` in `parent_anchor_row` is a `┬` connector | `test_tee_at_each_offset` |
| I4 | **N labels for N edges:** each label centers at column `c_i` (above the `┬`); max-width per label = `min(c_i - prev_boundary, next_boundary - c_i) * 2 - 2` cells via `wcwidth`. Empty label leaves slot blank; all-empty labels collapse the label row entirely. | `test_n_labels_centered_at_tees`, `test_empty_label_blank_slot`, `test_all_empty_labels_collapse_row` |
| I5 | Labels truncate at 12 cells with `…`; CJK chars count 2 cells via `wcwidth` | `test_cjk_label_truncation` |
| I6 | When `converges_to is None`, no `└──┼──┘` row is emitted (dangling tails) | `test_dangling_no_join` |
| I7 | When `converges_to` is set, `┼` sits at column `(offsets[0] + offsets[-1]) // 2` | `test_join_centered_on_offsets_span` |
| I8 | `parent_anchor_row` equals `0` (top of returned lines); `convergence_anchor_row` equals `len(lines) - 2` if join present | `test_anchor_rows` |
| I9 | Renderer-agnostic: function does not import or reference `dag_graph` or `ascii_graph` | `test_no_renderer_imports` |
| I10 | 4-way is the hard cap: `len(siblings) > 4` raises `ValueError` | `test_four_way_cap` |
| I11 | `step_anchor_rows` contains exactly one entry per sibling, keyed by sub-step ID; each value points to the middle row of that sibling's box (where `│ text │` body sits) | `test_step_anchor_rows_one_per_sibling`, `test_step_anchor_row_is_box_middle` |

### ASCII coordinate diagram (per Codex advisory)

The geometry math above maps to this layout (for a 3-way branch with offsets `c_1=4, c_2=11, c_3=18`):

```
col:   0    4         11          18
       └────┬─────────┬───────────┬────┘   ← parent_anchor_row (┬ at c_1, c_2, c_3)
            │         │           │
           pass     fail        retry      ← label row (centered at each c_i)
            ▼         ▼           ▼        ← arrow row
          ┌───┐    ┌────┐       ┌─────┐
          │3a │    │ 3b │       │ 3c  │    ← sibling boxes (top borders)
          │...│    │... │       │...  │    ← sibling middle rows = step_anchor_rows
          └─┬─┘    └──┬─┘       └──┬──┘    ← sibling bottom borders
            │         │            │
            └─────────┼────────────┘       ← join row: ┼ at (c_1+c_3)//2 = 11
                      ▼
                 [convergence step]        ← convergence_anchor_row
```

`step_anchor_rows = {"3a": 5, "3b": 5, "3c": 5}` if all sibling box bodies are single-row; varies if any sibling has multi-row body content.

### Phase 3 Spike Exit Criteria

Phase 3 exits only when:

1. All 11 invariant tests pass (I1–I11)
2. `pyright src/fx_alfred/core/branch_geometry.py` clean
3. **6 hand-crafted golden tests match** (per Codex Round 1 #3 — replaces R1's 3 goldens + manual eyeball):
   - 2-way simple (`branches_2way.golden.txt`)
   - 3-way simple (`branches_3way.golden.txt`) — Audit Ledger pattern from PRP-2225 §"Problem"
   - 4-way at hard cap (`branches_4way.golden.txt`)
   - Dangling tails (`branches_dangling.golden.txt`)
   - CJK truncation (`branches_cjk.golden.txt`)
   - Audit Ledger end-to-end (`branches_audit_ledger.golden.txt`) — full pipeline output, hand-crafted from PRP-2225 §"Geometry algorithm sketch" (PRP-2225:105–109) with siblings/labels/convergence as authored in the worked example. Note: PRP-2225 does NOT contain a rendered "after" output (only the "before" linearization at PRP-2225:27–40 + the algorithm sketch); this golden is the implementer's first commitment of what the rendered output looks like, validated against the algorithm rules. Phase 4's nested-integration test re-asserts the same output through the full renderer stack.

If any of the 6 goldens fail, Phase 3 pauses and a discussion happens before Phase 4 commits. **No "manual eyeball" gate.**

If any of the 17 tests (11 invariants + 6 goldens) fails, this CHG pauses (no Phase 4 commit). Per-phase commit boundaries mean the primitive can land alone in main even if integration takes a follow-up PR.

---

## Plan

Per COR-1500 (TDD Development Workflow). Phases 3, 4, 5, 7 from the original 10-phase plan, plus 8/9/10 (docs/review/release).

### Phase 3 — Branch geometry primitive (`core/branch_geometry.py` — NEW)

**RED:**
- 11 invariant tests above (`tests/test_branch_geometry.py` — I1 through I11)
- 6 hand-crafted golden tests: 2-way simple, 3-way simple, 4-way at hard cap, dangling tails, CJK truncation, Audit Ledger end-to-end (per §"Phase 3 Spike Exit Criteria")

**GREEN:** Implement the 5 public functions per the API contract above. Hand-craft goldens from PRP-2225 §"Geometry algorithm sketch" (PRP-2225:105–109).

**REFACTOR:** Run invariant I9 (no renderer imports) — primitive must be standalone. Sweep for any accidentally-leaked global state.

**Exit:** All 17 tests pass (11 invariants I1–I11 + 6 goldens listed in §"Phase 3 Spike Exit Criteria"); commit: `branch_geometry: primitive with invariants + 6 goldens`.

### Phase 4 — `dag_graph.py` nested integration

**RED:**
- `tests/test_dag_graph.py::test_nested_3way_with_convergence` — full SOP → ASCII golden file matching `branches_audit_ledger.golden.txt` (Phase 3 commits the golden; Phase 4 re-asserts identical output through the full renderer stack)
- `tests/test_dag_graph.py::test_nested_branches_plus_loops` — branch + loop in same SOP (no interaction; loops still render as right-side tracks)
- `tests/test_dag_graph.py::test_nested_dangling_branch` — terminal branch (no convergence) renders correctly inside phase box
- `tests/test_dag_graph.py::test_nested_legacy_unchanged` — every existing nested-layout test stays green

**GREEN:** Detect a branch group in the phase's step list (sub-step `index` matches `Workflow branches.from + 1` AND `step.get("sub_branch")` is set); when detected, call `render_branch(...)` from `branch_geometry` with `BranchTarget` siblings constructed from the matching step entries; wrap result in phase-box borders. **`step_row_index` keys remain int-typed by `step['index']`** — siblings are rendered as a group (occupying their parent integer's row range) rather than as individual rows. **No widening of int-keyed structures.** Per CHG-2226's renderer-readiness gate (`_BRANCHES_RENDERER_READY = False`), Phase 4 also flips this flag to `True` as a deliverable so `af validate` accepts `Workflow branches:` once renderer ships.

**Exit:** Nested-layout tests pass; existing v1.7.0 nested tests stay green.

### Phase 5 — `ascii_graph.py` flat integration

**RED:**
- `tests/test_ascii_graph.py::test_flat_3way_with_convergence` — same SOP renders branches via shared primitive without phase-box wrapping
- `tests/test_ascii_graph.py::test_flat_legacy_unchanged` — every existing flat-layout test stays green

**GREEN:** Detect branch groups (same pattern as Phase 4 — `index + sub_branch` pair from CHG-2226's `StepDict`); call `render_branch(...)` directly without phase-box wrapping. **No `step_idx`/`step_indices` widening** — CHG-2226 Path B keeps int typing throughout `ascii_graph.py`. Existing call sites at `ascii_graph.py:174/176/266/360` continue reading `step["index"]` as int; sub-step rendering is keyed off the new `sub_branch` field that those sites ignore unless explicitly read. Refactor any duplication between flat and nested into the primitive itself.

**Exit:** Flat-layout tests pass; existing flat tests stay green.

### Phase 7 — Mermaid output

**RED:**
- `tests/test_mermaid.py::test_mermaid_with_substeps` — sub-stepped SOP emits `S2_3a[...]` etc.
- `tests/test_mermaid.py::test_mermaid_legacy_unchanged` — every existing mermaid test stays green

**GREEN:** Append the optional `sub_branch` to the existing integer step ID when emitting Mermaid node identifiers: `S{phase}_{step['index']}{step.get('sub_branch', '')}` produces `S2_3a` for sub-stepped steps and `S2_3` for plain. **`step_idx: int` typing at `mermaid.py:117` unchanged.** Emit valid Mermaid IDs (replace any `.` or non-alphanumeric in display strings with `_`).

**Exit:** Mermaid tests pass; existing tests green.

### Phase 8 — Documentation + version bump

- v1.8.0 entry in `src/fx_alfred/CHANGELOG.md` (per "CHANGELOG" subsection above)
- `pyproject.toml`: `version = "1.7.1" → "1.8.0"`; add `"wcwidth"` to `dependencies`
- `CLAUDE.md`: one-paragraph note about `Workflow branches:`
- `COR-1202`: one-line mention in "What Is It?"

### Phase 9 — Multi-model code review (COR-1602 + COR-1610)

Codex + Gemini in parallel against the implementation PR diff; both must score ≥ 9.0 per COR-1611. Up to 3 rounds.

### Phase 10 — Release (FXA-2102)

Per FXA-2102: tests + lint + pyright clean → **manual smoke test** (per Gemini Round 1 advisory): run `af plan --task "..." COR-1500 COR-1602 --todo --graph --root .` in a real interactive terminal (iTerm2 / macOS Terminal / Linux gnome-terminal), confirm the branching output renders correctly with the locally-installed pre-release wheel before tagging. Specifically eyeball: (a) the 3-way Audit Ledger fixture output matches the goldens, (b) CJK terminal handles label truncation visibly, (c) flat layout produces the same branch shape sans phase-box borders. Only if smoke test passes → `gh release create v1.8.0 --title "v1.8.0" --notes "..."` → GH Actions PyPI publish → `pipx upgrade fx-alfred` to verify.

---

## Test Plan Summary

| Phase | New tests | Total at end of phase |
|---|---:|---:|
| Pre-CHG baseline (assumes CHG-2226 merged: ~741) | — | ~741 |
| Phase 3 (geometry primitive) | ~17 (11 invariants + 6 goldens — 2-way / 3-way / 4-way / dangling / CJK / Audit Ledger) | ~758 |
| Phase 4 (nested integration) | ~4 | ~762 |
| Phase 5 (flat integration) | ~2 | ~764 |
| Phase 7 (Mermaid) | ~2 | ~766 |

**Total estimated new tests in this CHG: ~25.** Combined with CHG-2226's ~22, total new tests: ~47.

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Phase 3 primitive shape proves wrong during Phase 4 integration | Spike exit criteria (above) require all 17 tests (11 invariants + 6 goldens) to pass before Phase 4 commits; the Audit Ledger end-to-end golden (`branches_audit_ledger.golden.txt`) commits Phase 3 to a concrete output shape that Phase 4 re-asserts. The primitive can land alone in main if the integration takes a follow-up PR. No manual-verification gate. |
| Goldens-against-hand-crafted-ASCII are brittle to formatting tweaks (Gemini Round 1 critique) | 11 of 17 Phase-3 tests are *invariant* assertions (offsets, cell widths, connector presence, label centering rule, anchor rows, etc.), not full-string goldens. 6 goldens remain — basic sanity (2-way, 3-way), edge cases (4-way cap, dangling), CJK truncation, and the Audit Ledger PRP fixture (replaces R1's manual-eyeball spike exit). |
| `wcwidth` adds runtime dep that some downstream environments lack | `wcwidth` is pure-Python with zero deps of its own; pip-installable in any environment that already runs `fx-alfred`. Codex Round 1 explicitly endorsed this dep |
| `dag_graph.py` + `ascii_graph.py` integrations conflict (shared primitive, two consumers) | Phase 5 refactors any duplication back into the primitive itself; primitive's Phase-3 invariant I9 (no renderer imports) prevents accidental coupling |
| v1.8.0 release fails on PyPI (build/publish flake) | FXA-2102 has explicit recovery steps; pre-release runs lint+pyright+tests on commit, so failure surfaces before tagging |
| Multi-model review divergence on the implementation PR | Hard cap 3 rounds per FXA-2218 budget; if persistent disagreement, escalate per COR-1601 |

---

## Approval

- [ ] Approved by: <reviewer> on <date>

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-27 | Initial CHG drafted as the second of two staged CHGs implementing PRP-2225. Covers branch geometry primitive (new file), nested + flat ASCII renderer integration, Mermaid output, docs + CHANGELOG, version bump v1.7.1 → v1.8.0, and PyPI release. Phase 3 primitive API contract locked here so Round 2 reviewers can score it independently of integration. ~13 new tests in Phase 3 (10 invariants + 3 goldens) replace the original "many hand-crafted golden ASCII tests" (Gemini Round 1 critique). Spike exit criteria explicit. Per-phase commit boundaries throughout. | Frank + Claude Code |
| 2026-04-27 | Round 1 review: Codex 8.4 FIX, Gemini 9.6 PASS. Round 2 revisions per Codex feedback: (1) `BranchRenderOutput` extended with `step_anchor_rows: dict[str, int]` for loop-track placement; (2) label-slot semantics rewritten — N labels for N edges (not N-1 between tees); each label centers at column `c_i` with collision-avoidance max-width; empty/all-empty handled; (3) 4-way and dangling goldens added (was 3 goldens, now 6); (4) Phase 3 spike exit criterion #5 ("manual eyeball") promoted to programmatic golden against PRP-2225's Audit Ledger fixture; (5) ASCII coordinate diagram added beside invariants for visual clarity. Plus Gemini advisory: manual smoke test added to Phase 10 before `gh release create`. Test count grows from ~21 to ~25 in this CHG (~46 across both CHGs). | Frank + Claude Code |
| 2026-04-27 | Round 2 review: Codex 8.7 FIX, Gemini 9.8 PASS. Round 3 revisions per Codex 8.7 feedback (Gemini already PASS, no regression-risk changes): (1) test count drift reconciled across §"Phase 3 Spike Exit Criteria" (11 inv + 6 goldens), §"Phase 3 RED" (11 invariants), §"Phase 3 Exit" (17 tests), §"Risks" (no manual verification); (2) stale "manual verification" wording removed from Risks row; (3) "PRP-2225 §Worked example" was fictional — replaced with explicit attribution: golden is hand-crafted from PRP-2225 §"Geometry algorithm sketch" (PRP-2225:105–109), Phase 4 re-asserts the same output through the full renderer stack; (4) label-slot boundary formula made concrete: `prev_boundary[i] = (c_{i-1}+c_i)//2 if i≥2 else 0; next_boundary[i] = (c_i+c_{i+1})//2 if i<N else box_total_width-1`. Plus rearchitecture sync with CHG-2226 Path B: `BranchRenderInput.siblings` now uses `BranchTarget` NamedTuple (`parent: int`, `branch: str`, `label: str`) from CHG-2226; primitive composes display ID `f"{parent}{branch}"` internally. `converges_to: int | None` (was `str | None`) since sub-step cross-SOP convergence targets remain out of scope. CHANGELOG entry's "Internal" note rewritten to reflect Path B (additive `sub_branch` field, no type-widening migration). | Frank + Claude Code |
| 2026-04-27 | Round 3 review: Codex 9.1 PASS, Gemini 7.8 FIX (regressed -2.0 from R2). Gemini caught a critical Path B sync defect — Round 3 updated the API contract + CHANGELOG to match Path B but **left the §Files-modified table + Phase 4/5/7 GREEN steps describing the rejected Path A migration** ("step_idx: str", "str-keyed step_row_index", "Audit per CHG-2226 Migration Impact Table" — Path B has no such table). Internal contradiction: implementer following CHG literally would execute the migration the architecture rejects. **Round 4 fixes (this revision):** (1) Files-modified rows for `dag_graph.py`, `ascii_graph.py`, `mermaid.py` rewritten — display ID composed at render time as `f"{step['index']}{step.get('sub_branch', '')}"`; existing int-keyed structures unchanged. (2) Phase 4 GREEN — keeps `step_row_index` int-keyed; siblings rendered as a group via `render_branch()`; Phase 4 also flips CHG-2226's `_BRANCHES_RENDERER_READY` flag to `True` as a deliverable so `af validate` accepts `Workflow branches:` once renderer ships. (3) Phase 5 GREEN — explicitly states no `step_idx` widening; existing call sites at `ascii_graph.py:174/176/266/360` continue reading int. (4) Phase 7 GREEN — `step_idx: int` typing at `mermaid.py:117` unchanged; sub-step suffix appended at node-ID emit time only. (5) Phase 3 RED text updated from "3 goldens" to "6 goldens" matching Spike Exit Criteria. (6) Stale "item 4" reference at line 196 fixed. (7) R2 parenthetical in Test Plan Summary updated. | Frank + Claude Code |
