# PRP-2217: ASCII DAG nested graph layout for af plan graph

**Applies to:** FXA project
**Last updated:** 2026-04-19
**Last reviewed:** 2026-04-19
**Status:** Draft

---

## What Is It?

A proposal to promote FXA-2212 (an evolve-seed REF recording the idea of an opt-in DAG ASCII
renderer) to a **manually-driven feature PRP** that makes a nested DAG layout the default output
of `af plan --graph` in ASCII mode. Scope is ASCII-only — Mermaid renderer unchanged. Cross-SOP
loops become expressible via an extension to `Workflow loops:` metadata. Issue #58, branch
`feat/fxa-2212-dag-graph-layout`.

---

## Problem

The current `af plan --graph` ASCII renderer emits one big box per SOP, stacked vertically with `▼`
connectors. Intra-SOP loops render with a right-side vertical track inside the phase box. This
works for simple linear plans, but hides structure users care about:

### Pain point 1 — plan structure is flattened to "a stack of monoliths"

With the current format, every composition looks linear regardless of internal shape. A 2-SOP
composition of COR-1500 (TDD, 3 steps) + COR-1602 (review, 3 steps) renders:

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

User reported (2026-04-19, after v1.6.2 ships): this reads as two monolithic blocks with an arrow
between them, not as a DAG. Individual steps have no visual identity.

### Pain point 2 — cross-SOP loops cannot be expressed

`Workflow loops:` metadata today has `from: int, to: int` — both indices refer to the **same** SOP.
In practice, some loops span SOPs: "if review fails (COR-1602 step 3), go back to TDD Red
(COR-1500 step 1)". Today this relationship can only be documented in SOP prose, not in the
graph. An automated `af plan --graph` on such a composition produces a graph that's structurally
incomplete.

### Pain point 3 — the FXA-2212 seed REF lingered unused

FXA-2212 captured the design idea on 2026-04-19 after user feedback on PR #52. Per its own policy,
the seed expected to be re-scored by Evolve-CLI. The FXA-2213 run cold-scored it at 6.05 and
discarded; the user then manually promoted to PRP rather than wait for a second cold discard —
explicit acknowledgement that DAG layout is PRP-class (new module + new flag + new metadata) and
was never a natural evolve candidate.

## Proposed Solution

### Decisions locked during brainstorming (2026-04-19)

| Axis | Decision | Rationale |
|---|---|---|
| Scope | **A** — cross-phase loop edges only; no fork/join | Fork/join needs new SOP metadata to mark parallel steps; defer to a separate PRP |
| Granularity | **c-hybrid** — outer phase-box contains inner step-boxes | Faithful to FXA-2212 mockup; preserves SOP-level grouping |
| Default strategy | **c-default** — `nested` is the default; `--graph-layout=flat` restores today's format | Matches user's "默认" intent; provides one-flag escape for downstream consumers |
| Metadata extension | **a-extend** — `Workflow loops.to` accepts int (intra, unchanged) or `"PREFIX-ACID.step"` string (cross-SOP, new) | Backward-compatible type union; no schema version bump |
| Mermaid counterpart | **out of scope** — `--graph-layout` is ASCII-only; Mermaid stays flat | User explicit: "Mermaid 大部分时间用不到，如果需要 efforts 太大的话，可以去掉" |

### Component 1 — data model

`core/workflow.LoopSignature` gains a wider `to_step` type, plus accompanying edits to its own
parser and validator in the same module:

```python
@dataclass
class LoopSignature:
    id: str
    from_step: int
    to_step: int | str          # was: int
    max_iterations: int
    condition: str = ""

    def is_cross_sop(self) -> bool:
        return isinstance(self.to_step, str)

    def cross_sop_target(self) -> tuple[str, str, int] | None:
        """Return (prefix, acid, step_idx) for cross-SOP refs, else None."""
        if not self.is_cross_sop():
            return None
        m = CROSS_SOP_REF.match(self.to_step)
        if m is None:
            raise MalformedDocumentError(...)
        return m.group("prefix"), m.group("acid"), int(m.group("step"))
```

**Critical accompanying edits** (missed in PRP R1, caught by reviewers):

- `workflow.py:263-266` — the existing `to_step` int guard must be loosened. New logic: accept
  int (existing path) **or** a string that matches `CROSS_SOP_REF`. Any other value (float, list,
  quoted digit string like `"27"`) raises `MalformedDocumentError`.
- `workflow.py:315-380` — `validate_loops`'s intra-SOP membership + back-edge direction checks
  must be **gated on `isinstance(loop.to_step, int)`**. For cross-SOP refs, these intra-SOP
  checks are meaningless (the target step lives in a different SOP); skip them. Cross-SOP
  validation happens elsewhere (D2/D3 in `af validate`, D4 in `af plan`).

**Quoted-digit-string ambiguity.** YAML can produce string values that look numeric (e.g.,
`to: "27"`). This must **not** be silently coerced to int 27 nor silently treated as a cross-SOP
ref. Policy: if `to` is a string and does not match `CROSS_SOP_REF`, raise
`MalformedDocumentError` with a diagnostic like `"Workflow loops[0].to: quoted digit string '27'
is not a valid cross-SOP reference; use int 27 for intra-SOP loops"`.

**Storage invariant:** the string form is stored exactly as authored (e.g., `"COR-1500.3"`).
Parsing into `(prefix, acid, step_idx)` is lazy at accessor call. Round-trip through `af fmt`
preserves the exact text. Type annotation stays `int | str`; no `Union` widening of storage.

### Component 2 — validation (D1–D4 from FXA-2216)

#### D1 — Parser regex (`core/workflow.py`, corrected in R3)

New module-level constant **in `core/workflow.py`** (where `parse_workflow_loops` consumes it —
R2 mis-assigned this to `core/parser.py`; `parse_workflow_loops` actually lives at
`core/workflow.py:205`):

```python
CROSS_SOP_REF = re.compile(r"^(?P<prefix>[A-Z]{3})-(?P<acid>\d{4})\.(?P<step>\d+)$")
```

During `parse_workflow_loops`, if `Workflow loops[i].to` is a string, validate the regex.
Malformed strings raise `MalformedDocumentError` with the SOP ID + loop index + offending value.
`core/parser.py` is **not modified** by this PRP.

#### D2 — `af validate` target-SOP-exists check

`commands/validate_cmd.py` gains a new post-scan cross-reference pass:

```
for each SOP in corpus:
    for each loop in SOP.workflow_loops:
        if loop.is_cross_sop():
            prefix, acid, step_idx = loop.cross_sop_target()
            if not any(d.prefix == prefix and d.acid == acid for d in docs):
                issues.append(f"{SOP.id} Workflow loops[{i}].to references "
                              f"{prefix}-{acid} — no such SOP in corpus")
```

Exit 1 with the diagnostic; same flow as existing validate failures.

#### D3 — `af validate` step-in-range check

Follows D2: if target SOP resolved, count its numbered steps and reject if `step_idx < 1` or
`step_idx > len(steps)`.

```
ERROR: COR-1500.99 — step index 99 out of range (COR-1500 has 10 steps)
```

**Shared-helper relocation** (caught by R1 Gemini reviewer): the step-counting helper today lives
at `src/fx_alfred/commands/plan_cmd.py:129` as `_parse_steps_for_json`. If `validate_cmd.py`
imports it from there, we introduce a `commands → commands` cross-dependency that violates
today's architecture (core functions in `core/`, command wiring in `commands/`).

**Fix:** extract `_parse_steps_for_json` into a new module `src/fx_alfred/core/steps.py`.
Re-export it from `plan_cmd.py` via a module-level `from fx_alfred.core.steps import
_parse_steps_for_json` (or inline import) so existing `plan_cmd.py` call sites continue to work
without churn. `validate_cmd.py` imports from `core/steps.py` directly. This is a standalone
mechanical refactor (should land as its own commit before the D2/D3 logic to keep diffs small).

#### D2 + D3 architectural note — `af validate` gains its first cross-corpus pass

Today `validate_cmd.py` validates each document **in isolation** (metadata keys, Status enum,
Change History table shape). D2 and D3 are the **first cross-reference checks** in `af validate`
— they require a corpus-wide lookup (target SOP existence) and a body re-parse (target step
count).

**Design:**

```python
# Existing per-document pass stays as-is. New post-scan pass added:

all_docs_by_id = {(d.prefix, d.acid): d for d in scan_results}

for doc in scan_results:
    for i, loop in enumerate(_extract_workflow_loops(doc)):
        if not loop.is_cross_sop():
            continue
        prefix, acid, step_idx = loop.cross_sop_target()
        target = all_docs_by_id.get((prefix, acid))
        if target is None:
            issues[doc.id].append(f"Workflow loops[{i}].to references "
                                  f"{prefix}-{acid} — no such SOP in corpus")
            continue
        steps = _parse_steps_for_json(target.body)
        if not (1 <= step_idx <= len(steps)):
            issues[doc.id].append(f"Workflow loops[{i}].to = "
                                  f"{loop.to_step!r} — step index out of range "
                                  f"({prefix}-{acid} has {len(steps)} steps)")
```

No parallelisation needed (validation is O(docs × loops × 1), usually 100s of loops total
across the corpus; `_parse_steps_for_json` is cheap).

#### D4 — `af plan` composition + direction checks

During `af plan` execution, after the compose phase resolves the SOP ordering, every cross-SOP
loop gets two new runtime checks:

```
# Composition check: target must be in the composed plan
if target_sop_id not in composed_plan:
    raise click.ClickException(
        f"{source} Workflow loops[{i}].to = {loop.to_step!r} "
        f"— {target_sop_id} not in composed plan "
        f"(add positionally: af plan {source} {target_sop_id} ...)"
    )

# Direction check: target must come BEFORE source in composed order
if composed_order[target_sop_id] >= composed_order[source]:
    raise click.ClickException(
        f"{source} Workflow loops[{i}].to = {loop.to_step!r} "
        f"— target SOP precedes source; back-edges only"
    )
```

### Component 3 — ASCII renderer

New module `core/dag_graph.py` implements the nested layout. Existing `core/ascii_graph.py`
remains the flat-layout renderer; `plan_cmd.py` dispatches based on the new `--graph-layout` flag.

**Reuse vs. net-new** (revised per R1 — original PRP overstated reuse):

- **Reused from `ascii_graph.py`:** the visual-width / padding / truncation primitives only —
  `_visual_width`, `_pad_visual`, `_truncate_visual`, plus glyph constants (`┌`, `└`, etc.).
- **Net-new in `dag_graph.py`:**
  - Outer-box-and-inner-box nested drawing (no precedent — today's `_apply_loop_track` is an
    intra-box overlay, not nested boxes).
  - Cross-SOP track routing: tracks that exit one phase-box, span the inter-phase gutter, and
    re-enter the target phase-box at the target step's row.
  - Track column packing: non-overlapping cross-SOP loops share a column; overlapping loops
    stack columns from the right inward.
  - Width budget arithmetic: the outer box must reserve columns for (a) the widest inner
    step-box, (b) intra-SOP tracks, (c) cross-SOP tracks, (d) gutters. `ascii_graph.py`'s
    width budget is simpler (just content + single track).

**Flag:**

```python
@click.option(
    "--graph-layout",
    type=click.Choice(["nested", "flat"], case_sensitive=False),
    default="nested",
    help="ASCII graph layout: 'nested' (default, step-boxes inside phase-boxes with cross-SOP tracks) or 'flat' (legacy, one phase-box per SOP).",
)
```

**Nested rendering structure** (per-SOP):

```text
┌────────────────────────────────────────────────────────┐
│ Phase 2: COR-1602 (parallel review)                    │
│                                                        │
│  ┌───────────────────────┐ ◄──────┐                    │
│  │ 2.1 Dispatch Codex    │        │                    │
│  └───────────┬───────────┘        │                    │
│              ▼                    │                    │
│  ┌───────────────────────┐        │                    │
│  │ 2.2 Dispatch Gemini   │        │                    │
│  └───────────┬───────────┘        │                    │
│              ▼                    │                    │
│  ┌───────────────────────┐        │                    │
│  │ 2.3 Gate ≥ 9.0        │ ───────┘ max 3              │
│  └───────────────────────┘                             │
└────────────────────────────────────────────────────────┘
```

**Cross-SOP rendering:** when a loop's `to` points to a different SOP, the track extends **outside
the phase box** and continues up through the gap between SOPs to land on the target step's box:

```text
┌────────────────────────────────────────────────────────┐
│ Phase 1: COR-1500 (TDD)                                │
│                                                        │
│  ┌───────────────────────┐ ◄──────────────────┐        │
│  │ 1.3 Refactor          │                    │        │
│  └───────────────────────┘                    │        │
└───────────────────────────────────────────────┼────────┘
                                                │
┌───────────────────────────────────────────────┼────────┐
│ Phase 2: COR-1602                             │        │
│                                               │        │
│  ┌───────────────────────┐                    │        │
│  │ 2.3 Gate ≥ 9.0        │ ───────────────────┘ max 3  │
│  └───────────────────────┘                             │
└────────────────────────────────────────────────────────┘
```

**Track column allocation:** each cross-SOP loop reserves its own right-side column. Intra-SOP
loops reserve a column only within their own phase-box. Multiple loops in the same column sharing
the same `from → to` span reuse the column; non-overlapping loops stack vertically.

**Terminal width adaptation:** default assumed width is 100 columns (widens beyond the current 80
to accommodate inner boxes + track columns). On `os.get_terminal_size()` less than the required
minimum (computed from widest inner box + number of track columns), the renderer **degrades
gracefully to inline fallback** on the narrow loops (similar to today's behaviour), preferring
intra-SOP loops to keep track treatment when space is tight.

### Component 4 — Mermaid (minimal defensive edit — PRP R1 claim "unchanged" was wrong)

**R1 reviewers both caught this:** widening `LoopSignature.to_step` to `int | str` would break
`core/mermaid.py:131-136`, which currently does:

```python
for step_idx, lp in loop_from_steps.items():
    from_nid = _node_id(phase_idx, lp.from_step)
    to_nid = _node_id(phase_idx, lp.to_step)           # ← breaks: to_step may be str
    cond = _sanitize_condition(lp.condition)
    lines.append(f"  {from_nid} -. {cond} .-> {to_nid}")
```

For a cross-SOP `to_step="COR-1500.3"`, this generates an invalid Mermaid node ID like
`p1_COR-1500.3`, producing malformed Mermaid output (not a Python crash, but broken rendering
downstream). Claiming "Mermaid is unchanged" was factually wrong.

**Fix:** `render_mermaid` type-checks and **skips** cross-SOP loops (`mermaid.py:131-136`):

```python
for step_idx, lp in loop_from_steps.items():
    if lp.is_cross_sop():
        continue                       # explicit skip; emit a single comment line
    from_nid = _node_id(phase_idx, lp.from_step)
    to_nid = _node_id(phase_idx, lp.to_step)
    cond = _sanitize_condition(lp.condition)
    lines.append(f"  {from_nid} -. {cond} .-> {to_nid}")
```

**User-visible note.** When the composition contains at least one cross-SOP loop and
`--graph-format` includes mermaid (`mermaid` or `both`), Mermaid emits a one-line comment
`%% (cross-SOP loops omitted — Mermaid layout is ASCII-only in this release)` immediately
before the first back-edge, so a user reading the exported Mermaid knows the graph is
incomplete relative to the ASCII output. No other edits to `mermaid.py`.

**Scope remains ASCII-first:** the flat Mermaid output for intra-SOP loops is unchanged.
Extending Mermaid to render cross-SOP edges (via `subgraph` blocks) remains a follow-up PRP
per user decision.

### Component 5 — plan_cmd output contract (missed in R1)

Widening `LoopSignature.to_step` to `int | str` also silently garbles today's `plan_cmd.py`
output interpolations. Two sites need explicit fixes:

**Site 1 — human TODO output (`plan_cmd.py:249-250`):**

```python
# Current (breaks for cross-SOP):
text = f"{text} — 🔁 if {loop_from_sig.condition} → back to {phase_num}.{loop_from_sig.to_step} (max {loop_from_sig.max_iterations})"
```

For cross-SOP `to_step="COR-1500.3"`, this produces garbled text `"back to 2.COR-1500.3"`.

**Fix:** branch on `isinstance(to_step, int)`:

```python
if isinstance(loop_from_sig.to_step, int):
    target = f"{phase_num}.{loop_from_sig.to_step}"
else:
    target = loop_from_sig.to_step                # already "PREFIX-ACID.step" form
text = f"{text} — 🔁 if {loop_from_sig.condition} → back to {target} (max {loop_from_sig.max_iterations})"
```

**Site 2 — JSON `loops[]` array (`plan_cmd.py:651-657`):**

```python
# Current:
"from": f"{phase_num}.{loop.from_step}",
"to": f"{phase_num}.{loop.to_step}",             # ← also garbles for cross-SOP
```

**Fix:** same branch — intra-SOP stays as dotted `{phase}.{step}`, cross-SOP emits the raw
`"PREFIX-ACID.step"` string. This makes the JSON shape a polymorphic string (existing consumers
already parse it as a string; the addition is a new lexical form).

**Site 3 — loop-to marker map typed contract (`plan_cmd.py:201, 279, 343`) — R3 addition:**

```python
# plan_cmd.py:201 — function signature
def _classify_step(
    ...,
    loop_to_steps: dict[int, LoopSignature],   # stays int-only; see fix below
    ...
)

# plan_cmd.py:279, :343 — dict comprehensions
loop_to_steps = {loop.to_step: loop for loop in loops}   # current — widens key to int | str
```

Problem: widening `LoopSignature.to_step` to `int | str` silently widens the dict key type,
violating the `dict[int, LoopSignature]` annotation at line 201 and breaking `pyright src/`
(FXA-2208 release gate).

**Fix:** filter cross-SOP loops out of the **intra-SOP loop-to-target map** — these markers only
make sense for intra-SOP loop targets (the `◄──` glyph decorates a step inside the same phase
that a later step jumps back to):

```python
# plan_cmd.py:279, :343 — filter to int keys only
loop_to_steps = {loop.to_step: loop for loop in loops if isinstance(loop.to_step, int)}
```

Cross-SOP loops still render — but through the new `dag_graph.py` cross-SOP track machinery,
not through `loop_to_steps`. The existing typed contract at line 201 (`dict[int,
LoopSignature]`) stays intact.

**Site 4 — `core/phases.py:28-43` documentation `LoopDict` — R3 addition:**

`core/phases.py` defines a **documentation-only** `LoopDict` TypedDict (explicitly noted in its
class docstring as "retained above as a documentation-only shape mirror used by earlier design
notes"). The runtime path uses `LoopSignature` directly. Update the `to_step: int` annotation to
`to_step: int | str` and extend the docstring to note the cross-SOP case. No runtime impact; a
documentation-consistency fix to keep pyright from complaining if anything ever imports from this
shape mirror.

**Site 5 — `core/ascii_graph.py` (flat renderer) — R3 addition:**

`core/ascii_graph.py:165` already has `if not isinstance(to_step, int) or not
isinstance(from_step, int): continue`. This is a pre-existing type-narrowing guard that was
added for malformed SOP metadata. With the R2 widening, this guard **correctly and silently
skips cross-SOP loops** in flat layout — which is the desired behaviour under
`--graph-layout=flat` (flat layout is legacy and has no concept of cross-SOP rendering). **No
code edit required** in ascii_graph.py; existing guard handles the widening for free. This is
called out here so reviewers don't expect an edit in the Affected Touchpoints table.

### Rollout

- `pyproject.toml` version bump deferred to the release SOP that follows PR merge (not part of this PRP).
- CHANGELOG entry (drafted during CHG): "New feature: ASCII DAG nested layout default for `af plan --graph`; `--graph-layout=flat` restores legacy. `Workflow loops.to` now accepts cross-SOP `\"PREFIX-ACID.step\"` references."
- Backward compatibility: every SOP file in the corpus today uses `to: int` — zero SOP file edits required. Downstream consumers pinned on flat ASCII format add `--graph-layout=flat` (one flag).

### Testing strategy

- **Parser/validator (D1–D4):** new unit tests in `tests/test_workflow.py` (for `parse_workflow_loops` + `validate_loops`), `tests/test_validate_cmd.py` (for cross-corpus D2/D3), `tests/test_plan_cmd.py` (for runtime D4). Cover each error message, each happy path, each edge case (index boundary, missing SOP, wrong-order composition, quoted digit string rejection).
- **Renderer:** snapshot tests in `tests/test_dag_graph.py` covering: single-SOP linear, two-SOP with intra-SOP loop, two-SOP with cross-SOP loop, three-SOP chain, narrow-terminal degradation, multi-loop column allocation, cross-SOP + intra-SOP interaction in same phase.
- **plan_cmd output contract:** tests in `tests/test_plan_cmd.py` for (a) human TODO suffix with cross-SOP loop, (b) JSON `loops[].to` shape with cross-SOP loop.
- **Mermaid skip behaviour:** tests in `tests/test_mermaid.py` that a cross-SOP loop is silently skipped and the `%% (cross-SOP loops omitted...)` comment is emitted exactly once.
- **`--graph-layout=flat`:** preserve at least 5 existing snapshots from `tests/test_ascii_graph.py` (reroute under the flag) so legacy format stays pinned.
- **TDD approach:** write failing test first (Red), implement until it passes (Green), refactor. For cross-SOP loops specifically, write unit tests of `LoopSignature.cross_sop_target()` and `parse_workflow_loops` regex edge cases **before** the renderer consumes them.
- **Hard gate:** `pytest -q` passes all (~700+ tests), `ruff check .` clean, `pyright src/` 0 errors, `af validate` 0 issues.

### Snapshot regeneration protocol (expanded per R1)

Making `--graph-layout=nested` default means ~40 existing ASCII snapshots will change shape. The
CHG cannot simply "regenerate all and review the final diff" — that invites silent acceptance of
wrong output. Protocol:

1. **Before regeneration**, move every current `test_ascii_graph.py` snapshot test that will
   change under nested-default to a new file `test_ascii_graph_flat.py` and decorate each with
   `@pytest.mark.parametrize("layout", ["flat"])` so it continues to pin today's exact output.
   These serve as the **legacy baseline** — they must stay green throughout the CHG work.
2. **Regenerate** snapshots for the `nested` default in a dedicated commit (subject: `test:
   regenerate nested-layout snapshots`). Each regenerated snapshot's diff is inspected
   individually against a **golden-case checklist**:
   - Outer phase-box borders intact?
   - Inner step-boxes aligned?
   - Intra-SOP tracks render at correct column?
   - Cross-SOP tracks (if any) leave the right phase-box and re-enter at correct row?
   - No trailing whitespace drift?
   - Visual width within the assumed terminal budget?
3. **Trinity code review** of the regeneration commit includes explicit sign-off that every
   snapshot diff was inspected, not bulk-accepted. Reviewers should block if they see any
   snapshot where the regenerated output contains unrendered glyphs, misaligned boxes, or
   visible artifacts.
4. **Mermaid**: confirm that running `af plan <SOPs> --graph --graph-format=mermaid` on at least
   one composition with a cross-SOP loop emits the expected `%% (cross-SOP loops omitted...)`
   comment and does not emit invalid node IDs.

### Affected touchpoints (concrete file list, R2 addition)

| Path | Change |
|---|---|
| `src/fx_alfred/core/workflow.py:263-266` | Loosen int guard on `to_step`; accept int or CROSS_SOP_REF-matching string |
| `src/fx_alfred/core/workflow.py:315-380` (`validate_loops`) | Gate intra-SOP membership + back-edge checks on `isinstance(to_step, int)` |
| `src/fx_alfred/core/workflow.py` (`LoopSignature`) | Widen `to_step: int` → `int \| str`; add `is_cross_sop()`, `cross_sop_target()` |
| `src/fx_alfred/core/workflow.py` (module-level) | Add `CROSS_SOP_REF` regex constant (R3: was mis-attributed to `parser.py` in R2) |
| `src/fx_alfred/core/steps.py` | **New** — extract `_parse_steps_for_json` from `plan_cmd.py:129` |
| `src/fx_alfred/commands/plan_cmd.py:129` | Re-export `_parse_steps_for_json` from `core/steps.py` |
| `src/fx_alfred/commands/plan_cmd.py:249-250` | Branch text interpolation on intra vs cross-SOP |
| `src/fx_alfred/commands/plan_cmd.py:279, :343` | Filter dict comprehension: `if isinstance(loop.to_step, int)` to keep `loop_to_steps` typed `dict[int, LoopSignature]` (R3) |
| `src/fx_alfred/commands/plan_cmd.py:651-657` | Branch JSON `loops[].to` emission on intra vs cross-SOP |
| `src/fx_alfred/commands/plan_cmd.py` (near flags) | Add `--graph-layout={nested,flat}`, default `nested` |
| `src/fx_alfred/commands/validate_cmd.py` | Add post-scan cross-reference pass for D2/D3 |
| `src/fx_alfred/core/mermaid.py:131-136` | Skip cross-SOP loops; emit `%% (cross-SOP omitted)` comment |
| `src/fx_alfred/core/phases.py:28-43` (`LoopDict`) | Update documentation-only TypedDict `to_step: int` → `int \| str` + docstring note (R3) |
| `src/fx_alfred/core/dag_graph.py` | **New** — nested ASCII renderer |
| `src/fx_alfred/core/ascii_graph.py` | No code edit — existing `isinstance(to_step, int)` guard at line 165 already silently skips cross-SOP loops when routed under `--graph-layout=flat` (R3) |
| `tests/test_workflow.py` | New tests for widened parser + validator |
| `tests/test_validate_cmd.py` | New cross-corpus D2/D3 tests |
| `tests/test_plan_cmd.py` | New D4 runtime + output-contract tests |
| `tests/test_dag_graph.py` | **New** — snapshot tests for the nested renderer |
| `tests/test_ascii_graph_flat.py` | **New** — legacy baseline snapshots (moved from `test_ascii_graph.py` under `--graph-layout=flat`) |
| `tests/test_mermaid.py` | New test: cross-SOP loop skip + comment emission |

### Scope boundaries

**In scope:** parser regex, LoopSignature type widening, af validate cross-ref checks, af plan composition+direction checks, new dag_graph.py module, --graph-layout flag on `af plan --graph`, snapshot tests, backward-compat for legacy flat format.

**Out of scope:**

- Fork/join visualisation (originally option B; deferred — requires new `Workflow parallel:` metadata design).
- Mermaid subgraph support (user-descoped).
- Terminal width auto-detection beyond a single `os.get_terminal_size()` call; renderer will not reflow dynamically on window resize.
- Cycle detection across cross-SOP loops (same rationale as today — `max_iterations` bounds runtime).
- SOP migration: no existing SOP is modified to use a cross-SOP loop. If a documentation pass later finds a natural cross-SOP loop case (e.g., COR-1602 → COR-1500), it lands in a separate CHG driven by the SOP owner, not as part of this PRP.

### Risks

- **Snapshot test churn.** Making nested the default means ~40 existing snapshot tests break. Mitigation: regenerate the snapshots in the CHG Red phase; diff review via trinity code review ensures regeneration didn't silently accept wrong output.
- **Rendering complexity.** Outer-box width math has to account for inner-box width + track columns + gutters. Risk: off-by-one in glyph alignment at edge widths. Mitigation: the existing `ascii_graph.py` already has a mature visual-width-aware layout; `dag_graph.py` reuses those primitives rather than reinventing.
- **Cross-SOP track column explosion.** A pathological plan with many cross-SOP loops (say 10+) could run out of horizontal space. Mitigation: column packing algorithm shares columns for non-overlapping loops; inline-fallback kicks in when columns exceed terminal width.
- **Mermaid drift.** With Mermaid frozen at flat-layout semantics, someone reading an HTML/Markdown export sees a different topology than the terminal ASCII. Mitigation: documented in the rollout note; revisit in a follow-up PRP if it becomes a pain point.
- **Metadata design lock-in.** Once `"PREFIX-ACID.step"` ships as public syntax for cross-SOP loops, extending it later (e.g., to name-based or anchor-based refs) is a breaking change. Mitigation: the dotted-string form is intentionally minimal and mirrors the existing ACID identifier scheme already used by `af read PREFIX-ACID`; unlikely to need replacement.

## Open Questions

None. All scope-shaping questions were settled during brainstorming (see FXA-2216 D1–D4 and
brainstorming log in conversation 2026-04-19). Implementation details (track column packing
algorithm, exact glyph choices for cross-SOP track, snapshot regeneration order) are deferred to
the CHG.

---

## Change History

| Date       | Change                                                                                                                                      | By             |
|------------|---------------------------------------------------------------------------------------------------------------------------------------------|----------------|
| 2026-04-19 | Initial version                                                                                                                             | —              |
| 2026-04-19 | Fill full design from 2026-04-19 brainstorming: scope A + c-grain + c-default + a-metadata + D1–D4 validation layers + ASCII-only renderer | Frank + Claude |
| 2026-04-19 | R1 → R2 fixes (Codex 8.67 / Gemini 8.8, both FIX): add affected-touchpoints list; correct Mermaid claim (not "unchanged" — skip + comment); specify workflow.py int-guard + validate_loops patches; relocate `_parse_steps_for_json` to `core/steps.py`; architect `validate_cmd` cross-corpus pass; add plan_cmd output contract (Component 5); add quoted-digit rejection rule; rewrite renderer reuse claim; expand snapshot regeneration protocol | Frank + Claude |
| 2026-04-19 | R2 → R3 fixes (Codex 8.93 FIX / Gemini 10.0 PASS): move `CROSS_SOP_REF` constant from `core/parser.py` to `core/workflow.py` (R2 mis-attribution); add `plan_cmd.py:279, :343` dict-comprehension filter; add `core/phases.py:28-43` documentation TypedDict update; add explicit note that `core/ascii_graph.py` needs no code edit (existing type guard) | Frank + Claude |
