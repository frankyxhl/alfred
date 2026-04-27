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
| `src/fx_alfred/core/dag_graph.py` | `step_row_index` tuple key uses `str`; integrate `branch_geometry` primitives inside phase-box wrapping | ~40 |
| `src/fx_alfred/core/ascii_graph.py` | `step_idx` and `step_indices` audit per Migration Impact Table (signature lines 134/360/397; iteration sites 173, 219, 265); accept `str` step IDs throughout; integrate primitive without phase-box wrapping | ~30 |
| `src/fx_alfred/core/mermaid.py` | `step_idx: str` (was `int` at line 117); emit `S2_3a`-style node IDs for sub-steps | ~10 |
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
> **Internal:** sub-step IDs (`3a`, `3b`, etc.) now flow through parser, validator, and plan-builder. `--json` output's `"index"` field format extends from `"phase.step"` (e.g. `"1.1"`) to `"phase.stepLetter"` (e.g. `"2.3a"`) — string-to-string, no schema break.

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
    siblings: list[tuple[str, str]] # [(sub_step_id, label), ...] e.g. [("3a", "pass"), ("3b", "fail")]
    sibling_texts: list[str]        # body text for each sibling box
    converges_to: str | None        # next-sequential integer step ID if auto-convergence applies; None for dangling
    converges_to_text: str | None   # body text for the convergence step (only when converges_to is not None)
    box_width: int                  # the surrounding renderer's per-step box width (e.g. _STEP_BOX_WIDTH)

@dataclass(frozen=True)
class BranchRenderOutput:
    lines: list[str]                # the full ASCII render, one string per terminal row
    parent_anchor_row: int          # row index where the parent box's bottom edge sits
    convergence_anchor_row: int | None  # row index where the convergence step's top edge sits, or None for dangling

def render_branch(input: BranchRenderInput) -> BranchRenderOutput: ...

# Internal helpers (still importable; useful for invariant tests):
def compute_column_offsets(n_siblings: int, box_width: int, gutter: int = 2) -> list[int]: ...
def render_label_row(labels: list[str], offsets: list[int], box_width: int) -> str: ...
def render_join_row(offsets: list[int]) -> str: ...
```

### Invariants (asserted in `tests/test_branch_geometry.py`)

These replace ~half of the originally-planned brittle golden ASCII tests. Goldens for the *full* output are still tested for 2-way / 3-way / dangling cases, but the geometry building blocks are tested by invariant assertion (more robust to spacing tweaks):

| # | Invariant | Test |
|---|---|---|
| I1 | `compute_column_offsets(n, w)` returns `n` strictly-increasing offsets | `test_offsets_strictly_increasing` |
| I2 | All output lines have the same visible-cell width (per `wcwidth.wcswidth`) | `test_lines_uniform_cell_width` |
| I3 | For every sibling `i`, the column at `offsets[i]` in `parent_anchor_row` is a `┬` connector | `test_tee_at_each_offset` |
| I4 | Labels are centered between adjacent tees `┬`; max-width = `(c_{i+1} - c_i) - 2` cells | `test_label_centered_between_tees` |
| I5 | Labels truncate at 12 cells with `…`; CJK chars count 2 cells via `wcwidth` | `test_cjk_label_truncation` |
| I6 | When `converges_to is None`, no `└──┼──┘` row is emitted (dangling tails) | `test_dangling_no_join` |
| I7 | When `converges_to` is set, `┼` sits at column `(offsets[0] + offsets[-1]) // 2` | `test_join_centered_on_offsets_span` |
| I8 | `parent_anchor_row` equals `0` (top of returned lines); `convergence_anchor_row` equals `len(lines) - 2` if join present | `test_anchor_rows` |
| I9 | Renderer-agnostic: function does not import or reference `dag_graph` or `ascii_graph` | `test_no_renderer_imports` |
| I10 | 4-way is the hard cap: `len(siblings) > 4` raises `ValueError` | `test_four_way_cap` |

### Phase 3 Spike Exit Criteria

Phase 3 exits only when:

1. All 10 invariant tests pass
2. `pyright src/fx_alfred/core/branch_geometry.py` clean
3. The 2-way and 3-way golden ASCII tests match expected output (1 each = 2 goldens, hand-crafted from PRP-2225 §"Geometry algorithm sketch")
4. The CJK-truncation golden test matches (1 golden)
5. Manually run the primitive on the Audit Ledger 3-way fixture from PRP-2225 — does the output look like the PRP's sketched diagram? If no, redesign before Phase 4.

If item 5 reveals a primitive-shape problem, this CHG pauses (no Phase 4 commit) and a discussion happens. Per-phase commit boundaries mean the primitive can land alone in main even if integration takes a follow-up PR.

---

## Plan

Per COR-1500 (TDD Development Workflow). Phases 3, 4, 5, 7 from the original 10-phase plan, plus 8/9/10 (docs/review/release).

### Phase 3 — Branch geometry primitive (`core/branch_geometry.py` — NEW)

**RED:**
- 10 invariant tests above (`tests/test_branch_geometry.py`)
- 3 hand-crafted golden tests (2-way simple, 3-way simple, CJK truncation)

**GREEN:** Implement the 5 public functions per the API contract above. Hand-craft goldens from PRP-2225 §"Geometry algorithm sketch".

**REFACTOR:** Run invariant I9 (no renderer imports) — primitive must be standalone. Sweep for any accidentally-leaked global state.

**Exit:** All 13 tests pass; spike-exit-criteria item 5 manually verified; commit: `branch_geometry: primitive with invariants + 3 goldens`.

### Phase 4 — `dag_graph.py` nested integration

**RED:**
- `tests/test_dag_graph.py::test_nested_3way_with_convergence` — full SOP → ASCII golden file matching the Audit Ledger example from PRP §"Worked example"
- `tests/test_dag_graph.py::test_nested_branches_plus_loops` — branch + loop in same SOP (no interaction; loops still render as right-side tracks)
- `tests/test_dag_graph.py::test_nested_dangling_branch` — terminal branch (no convergence) renders correctly inside phase box
- `tests/test_dag_graph.py::test_nested_legacy_unchanged` — every existing nested-layout test stays green

**GREEN:** Replace integer-keyed `step_row_index` with str-keyed; call `render_branch(...)` from `branch_geometry` for any phase containing a branch group; wrap result in phase-box borders.

**Exit:** Nested-layout tests pass; existing v1.7.0 nested tests stay green.

### Phase 5 — `ascii_graph.py` flat integration

**RED:**
- `tests/test_ascii_graph.py::test_flat_3way_with_convergence` — same SOP renders branches via shared primitive without phase-box wrapping
- `tests/test_ascii_graph.py::test_flat_legacy_unchanged` — every existing flat-layout test stays green

**GREEN:** Audit `step_idx` / `step_indices` per CHG-2226's Migration Impact Table (signature lines 134/360/397; iteration sites 173/219/265); call `render_branch(...)` directly without phase-box wrapping. Refactor any duplication between flat and nested into the primitive itself.

**Exit:** Flat-layout tests pass; existing flat tests stay green.

### Phase 7 — Mermaid output

**RED:**
- `tests/test_mermaid.py::test_mermaid_with_substeps` — sub-stepped SOP emits `S2_3a[...]` etc.
- `tests/test_mermaid.py::test_mermaid_legacy_unchanged` — every existing mermaid test stays green

**GREEN:** `step_idx: str` at `mermaid.py:117`; emit valid Mermaid IDs for sub-steps (replace any `.` or non-alphanumeric with `_`).

**Exit:** Mermaid tests pass; existing tests green.

### Phase 8 — Documentation + version bump

- v1.8.0 entry in `src/fx_alfred/CHANGELOG.md` (per "CHANGELOG" subsection above)
- `pyproject.toml`: `version = "1.7.1" → "1.8.0"`; add `"wcwidth"` to `dependencies`
- `CLAUDE.md`: one-paragraph note about `Workflow branches:`
- `COR-1202`: one-line mention in "What Is It?"

### Phase 9 — Multi-model code review (COR-1602 + COR-1610)

Codex + Gemini in parallel against the implementation PR diff; both must score ≥ 9.0 per COR-1611. Up to 3 rounds.

### Phase 10 — Release (FXA-2102)

Per FXA-2102: tests + lint + pyright clean → `gh release create v1.8.0 --title "v1.8.0" --notes "..."` → GH Actions PyPI publish → `pipx upgrade fx-alfred` to verify.

---

## Test Plan Summary

| Phase | New tests | Total at end of phase |
|---|---:|---:|
| Pre-CHG baseline (assumes CHG-2226 merged: ~741) | — | ~741 |
| Phase 3 (geometry primitive) | ~13 (10 invariants + 3 goldens) | ~754 |
| Phase 4 (nested integration) | ~4 | ~758 |
| Phase 5 (flat integration) | ~2 | ~760 |
| Phase 7 (Mermaid) | ~2 | ~762 |

**Total estimated new tests in this CHG: ~21.** Combined with CHG-2226's ~21, total new tests: ~42. (Original 10-phase plan estimated ~48; the 2-CHG split is slightly more parsimonious because the spike exit criteria replace some golden tests with structural invariants.)

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Phase 3 primitive shape proves wrong during Phase 4 integration | Spike exit criteria (above) require manual verification before Phase 4 commits; the primitive can land alone in main if the integration takes a follow-up PR |
| Goldens-against-hand-crafted-ASCII are brittle to formatting tweaks (Gemini Round 1 critique) | 10 of 13 Phase-3 tests are *invariant* assertions (offsets, cell widths, connector presence, label centering rule), not full-string goldens. Only 3 goldens remain — for the most basic sanity checks |
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
