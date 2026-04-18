# CHG-2206: FXA 2205 Follow Ups ASCII Graph And SOP Metadata Backfills

**Applies to:** FXA project
**Last updated:** 2026-04-18
**Last reviewed:** 2026-04-18
**Status:** Completed
**Date:** 2026-04-18
**Requested by:** Frank
**Priority:** Medium
**Change Type:** Normal
**Scheduled:** ASAP
**Related:** FXA-2205 (parent PRP), PRs #43–#46 (merged rollout)

---

## What

Four small follow-ups to the FXA-2205 rollout (PRs #43–#46), bundled into a single PR for process efficiency. Each item is a small, independent addition that was surfaced during FXA-2205 demos but deferred to keep scope tight:

- **C1 — ASCII graph renderer.** Add terminal-friendly ASCII box-and-arrow output to `af plan --graph`, complementing the existing Mermaid output. `--graph` becomes dual-output (ASCII followed by fenced Mermaid). New `--graph-format=ascii|mermaid|both` flag lets users pick one when needed; default is `both`.
- **C2 — `Workflow loops` backfill on FXA-2148 Evolve-SOP.** The SOP has a documented Phase-7 Post-Push Review Loop (Steps 24→27, max 3 iterations) that was never captured in structured metadata. Without it, `af plan --graph` on Evolve-SOP produces no dashed back-edge. This CHG adds the existing `Workflow loops:` field (shipped in PR 1) to the SOP's metadata block.
- **C3 — `Task tags` backfill on FXA-2149 Evolve-CLI SOP.** Sister SOP to FXA-2148, also covers "evolve" flows but was left without `Task tags` during PR 4 (only COR-1500/1602/1608/1609/1610/1611 and FXA-2148 were tagged). `af plan --task "evolve CLI"` currently misses it — this CHG tags it.
- **C4 — `Workflow loops` backfill on FXA-2149 Evolve-CLI SOP.** Added after Gemini Round-1 review flagged that FXA-2149 has a structurally identical Phase-7 loop (Steps 27→30, max 3 iterations) that would remain invisible without metadata, leaving Evolve-CLI's graph incomplete. Parallel to C2.

---

## Why

The FXA-2205 demo run (`af plan --task "evolve CLI" --todo --graph`) surfaced three concrete UX gaps; Round-1 review surfaced a fourth:

1. **Terminal unreadable.** Mermaid is copy-pasteable into GitHub/Obsidian/mermaid.live, but in a terminal it's a wall of text users cannot visually parse. A complementary ASCII box-and-arrow rendering makes the graph legible in the same output stream and aligns with Alfred's "greppable and auditable" identity — still plain text, no new dependency.
2. **Loops invisible for Evolve-SOP.** FXA-2148's prose explicitly documents "Steps 24–27 repeat at most 3 iterations." Without `Workflow loops:` metadata the structured emission (the whole point of PR 1) is absent, and the Mermaid graph shows no back-edge. Adding the metadata closes the gap with one line.
3. **Coverage hole.** FXA-2149 Evolve-CLI is semantically "evolve"-related but has no `Task tags`. A user typing `af plan --task "evolve CLI"` reasonably expects both FXA-2148 and FXA-2149 to surface; only FXA-2148 does today.
4. **Symmetry with Evolve-SOP.** FXA-2149 carries the same Phase-7 loop as FXA-2148 (Steps 27–30 max 3). Backfilling FXA-2148 alone would leave Evolve-CLI's graph inconsistent with its sister SOP once C2 ships.

Bundling into one CHG is justified because: (a) all four changes trace back to the same FXA-2205 rollout; (b) each is small (~1–200 lines); (c) they share the same review gate (COR-1602 + COR-1609 for CHG, COR-1610 for code) so splitting would multiply process cost for proportionately little clarity. An atomic per-item PR structure is rejected for the same reason.

---

## Impact Analysis

- **Systems affected:**
  - `src/fx_alfred/core/ascii_graph.py` — NEW module (rendering logic)
  - `src/fx_alfred/commands/plan_cmd.py` — consume new renderer; add `--graph-format` flag
  - `src/fx_alfred/core/phases.py` — NEW `PhaseDict` / `StepDict` / `LoopDict` `TypedDict` definitions (see Step 4 for the contract). Canonical path (fixed, not "or equivalent"). Formalises what is currently an implicit `list[dict]` contract shared by `render_mermaid` and `_build_mermaid_phases`.
  - `src/fx_alfred/core/mermaid.py` — update signature to accept the new `TypedDict` (behavior unchanged; compile-time type-check win only).
  - `src/fx_alfred/rules/FXA-2148-SOP-Evolve-SOP.md` — one metadata line added (C2, no prose change)
  - `src/fx_alfred/rules/FXA-2149-SOP-Evolve-CLI.md` — two metadata lines added (C3 + C4, no prose change)
  - `tests/test_ascii_graph.py` — NEW module (unit tests)
  - `tests/test_plan_cmd.py` — add flag-combination tests
  - `CHANGELOG.md` — record new flag and backfills

- **NOT affected:**
  - `core/workflow.py` — unchanged
  - `core/compose.py` — unchanged (no change to `--task` resolution)
  - Any other SOP beyond FXA-2148 + FXA-2149

- **Channels affected:** none (CLI output format change only)

- **Downtime required:** No (CLI tool, no persistent state changes)

- **Backward compatibility:**
  - Default `af plan COR-XXX` (no `--graph`) — byte-identical to post-FXA-2205 output.
  - `af plan --graph` alone — output now contains an ASCII block **before** the existing fenced Mermaid block. Scripts that grep for `flowchart TD` still find it. Scripts that consume the raw output as a whole need to account for the leading ASCII; this is a **deliberate minor break** justified by the UX win. If a strict backward-compat mode is needed, `--graph-format=mermaid` restores today's output exactly.
  - `--graph --json` / `--graph --todo` / `--graph --todo --json` — all supported as today; JSON gains an `ascii_graph` sibling to `graph_mermaid`, also gated by `--graph-format`.
  - `af validate` still passes on all docs; new `Workflow loops`/`Task tags` values conform to the schema registered in PR 1/4.

- **Rollback plan:**
  - C1: revert the ascii_graph.py commit, the `phases.py` TypedDict addition, and the plan_cmd.py flag addition. `af plan --graph` reverts to Mermaid-only. `mermaid.py` reverts to plain `dict` signature. No data migration required.
  - C2: remove the `Workflow loops:` line from FXA-2148 metadata. `af plan --graph` on that SOP loses its back-edge (returns to pre-CHG state).
  - C3: remove the `Task tags:` line from FXA-2149 metadata. `af plan --task` no longer picks FXA-2149 from "evolve" tasks.
  - C4: remove the `Workflow loops:` line from FXA-2149 metadata. `af plan --graph` on FXA-2149 loses its back-edge.
  - **Rollback verification** for each item: (a) re-run `.venv/bin/pytest tests/test_plan_cmd.py -q` to confirm the revert does not break existing tests; (b) run the relevant `af plan` invocation and confirm output matches the pre-CHG state exactly (byte-diff for the affected invocations).

---

## Implementation Plan

### Phase 1 — CHG review (this document)

1. Leader dispatches Codex + Gemini (real CLI) to review this CHG against COR-1609 rubric (CHG Review Scoring). Both must score ≥ 9.0.
2. If either fails, Leader revises and re-dispatches per COR-1602 round rules (max 3 rounds).
3. On PASS, status moves to `In Progress`.

### Phase 2 — TDD implementation (per COR-1500)

4. **C1 ASCII renderer.** New file `src/fx_alfred/core/ascii_graph.py`, plus new `src/fx_alfred/core/phases.py` module that hosts the shared TypedDict contract:

   ```python
   # core/phases.py (NEW — formalises what was implicit in PR 3)
   from typing import TypedDict

   class StepDict(TypedDict):
       index: int           # 1-based within-SOP step index
       text: str            # step text (already gate-markers-cleaned per PR 2)
       gate: bool           # True if this step is a gate (⚠️)

   class LoopDict(TypedDict):
       id: str              # e.g. "review-retry"
       from_step: int       # within-SOP 1-based index
       to_step: int         # within-SOP 1-based index
       max_iterations: int
       condition: str

   class PhaseDict(TypedDict, total=False):
       # Required: currently yielded by `_build_mermaid_phases` in PR 3.
       sop_id: str          # e.g. "COR-1602" (full PREFIX-ACID form)
       steps: list[StepDict]
       loops: list[LoopDict]
       # Optional (introduced by this CHG for ASCII header rendering).
       # PR 3's `_build_mermaid_phases` does not populate this today; plan_cmd
       # adds it at render time in the ASCII path. Callers that only need
       # Mermaid output continue to work without it. If `total=False` proves
       # awkward, switch to a base TypedDict with `sop_id/steps/loops` plus
       # `NotRequired[str]` for provenance — functionally equivalent.
       provenance: str      # "always" | "auto" | "explicit"
   ```

   `render_ascii(phases: list[PhaseDict]) -> str` — pure-text renderer. Target output shape (this is the authoritative sample — any future change is a CHG):

   ```
   ┌─────────────────────────────────────────────────┐
   │  Phase 1: COR-1103 (always)                     │
   │  [1.1] Confirm routing                          │
   └──────────────────────┬──────────────────────────┘
                          ▼
   ┌─────────────────────────────────────────────────┐
   │  Phase 2: COR-1602 (auto)                       │
   │  [2.1] Leader identifies artifact               │
   │  [2.2] Dispatch Reviewers                       │
   │  [2.3] 🔁 Reviewers analyze ◄──────┐            │
   │  [2.4] Collect reviews             │            │
   │  [2.5] Synthesize                  │            │
   │  [2.6] Revise                      │            │
   │  [2.7] If iteration is on ─────────┘ max 3      │
   │  [2.8] ⚠️ Gate: all ≥ 9.0                       │
   └─────────────────────────────────────────────────┘
   ```

   Renderer conventions:
   - Phase box: top/bottom borders of equal width (minimum 50 chars, auto-expand to longest step text).
   - Header line inside phase box: `Phase N: <SOP-ID> (<provenance>)`.
   - Step line inside phase box: `[N.M] <text>` (step text truncated to fit box width; ellipsis on overflow).
   - Inter-phase arrow: `│` + `▼` glyphs centred below/above the phase box; 1 blank line between boxes.
   - Intra-SOP loop: `◄──┐` on the `to_step` line, `─────┘ max N` on the `from_step` line, with condition text optional (default `condition` text used if it fits, else "loop").
   - Gate marker: `⚠️` prefix on gate steps (preserves PR 2's gate semantics).
   - No cross-SOP connectors — loops are strictly intra-SOP per PR 1's design.

   `mermaid.py` signature migrates to accept `list[PhaseDict]` (no behavior change; import `PhaseDict` from `core/phases.py`).

   No external dependencies; pure stdlib.

5. **`--graph-format` flag in `plan_cmd.py`.**
   - Values: `ascii` | `mermaid` | `both` (default).
   - `--graph-format` without `--graph` is an error (`--graph-format` only meaningful when emitting a graph).
   - `--graph --graph-format=mermaid` yields today's behavior (Mermaid-only), guaranteeing backward compatibility for scripted consumers.
   - `--graph --graph-format=ascii` yields ASCII-only (no fenced Mermaid block).
   - `--graph` alone or `--graph --graph-format=both` yields ASCII block, then fenced Mermaid block, separated by a blank line.

6. **JSON schema.** When `--graph --json` set:
   - `graph_mermaid: "..."` — preserved as today (when format includes mermaid).
   - `ascii_graph: "..."` — NEW sibling (when format includes ascii).
   - `schema_version` stays at `"2"` (already bumped by PR 3).
   - `--graph-format=mermaid --json` emits only `graph_mermaid` (identical to today).

7. **C2 FXA-2148 backfill.** Add `**Workflow loops:** [{id: review-retry, from: 27, to: 24, max_iterations: 3, condition: "CI not green or unresolved comments"}]` to the metadata block. Loop matches the prose at Phase 7 (line 94–110) exactly. Run `af fmt --write` to canonicalise.

8. **C3 FXA-2149 Task tags backfill.** Tag values **frozen** at `[evolve, cli, refactor-cli, improve-cli]` — parallel to FXA-2148's `[evolve, sop, refactor-sop, improve-sop]`. No impl-time drift; if these prove wrong the fix is a follow-up CHG, not an in-commit adjustment.

9. **C4 FXA-2149 Workflow loops backfill.** Add `**Workflow loops:** [{id: review-retry, from: 30, to: 27, max_iterations: 3, condition: "CI not green or unresolved comments"}]` to the metadata block. Loop matches FXA-2149 Phase 7 prose (line 94, "Steps 27–30 repeat at most 3 iterations"). Run `af fmt --write` to canonicalise.

10. Tests (TDD — red first, green second):
    - `tests/test_ascii_graph.py`:
      - Core cases: single SOP / multi-SOP / intra-SOP loop / gate step / gate+loop collision / empty phases / long labels / special chars.
      - **Terminal edge cases (Gemini R1 adv):** narrow terminal width wrap (label exceeds 60 chars → truncates with ellipsis, no box overflow); multi-byte Unicode alignment (`⚠️`, CJK characters in step text must not break box framing — use `wcwidth` equivalent by consulting `str.__len__` vs visual width; if Python's stdlib doesn't provide `wcwidth`, inline a minimal width table for common glyphs in the renderer).
      - Mirror the shape of `tests/test_mermaid.py` for parity where applicable.
    - `tests/test_plan_cmd.py`: each flag combo in the matrix (`--graph`, `--graph-format=ascii/mermaid/both`, with/without `--todo` and `--json`, `--graph-format` without `--graph` errors cleanly).
    - Integration: `af plan --root . --task "evolve CLI" --graph` now surfaces both FXA-2148 and FXA-2149, and shows the back-edge on **both** SOPs' Phase 7 in the ASCII and Mermaid output.

11. Quality gates: pytest all-green, coverage on `core/ascii_graph.py` ≥ 95%, coverage on `core/phases.py` covered transitively by renderer tests (TypedDicts are declarative), ruff clean, `af validate --root .` clean.

### Phase 3 — Code review (per COR-1602 + COR-1610)

12. Leader dispatches Codex + Gemini via real CLI. Both must score ≥ 9.0.
13. Fix-or-defer any blockers per COR-1602 round rules.

### Phase 4 — PR + NRV-2506 comment triage

14. Push branch, open PR titled `feat(FXA-2205 follow-ups): ASCII graph + Evolve SOP loops + Evolve-CLI tags`.
15. Triage any `chatgpt-codex-connector[bot]` comments per NRV-2506 (Hard Rule 4: every fix requires a new Codex + Gemini review round).
16. On all-green + double PASS, notify Leader for merge.

---

## Testing / Verification

- **Per-item verification checklist** (all must pass before Approval):
  - [ ] C1: `af plan --root . --graph` (no format flag) — output contains both an ASCII block AND a ` ```mermaid ... ``` ` fenced block, separated by one blank line. `af plan --root . --graph --graph-format=mermaid` is byte-identical to pre-CHG `af plan --root . --graph`. `af plan --root . --graph --graph-format=ascii` contains no ` ```mermaid ` substring.
  - [ ] C2: `af validate --root .` clean; `af plan --root . FXA-2148 --graph --graph-format=mermaid` output contains `S3_27 -. CI not green or unresolved comments .-> S3_24` back-edge.
  - [ ] C3: `af plan --root . --task "evolve CLI" --todo` composes COR-1103(always) + COR-1402(always) + FXA-2148(auto) + FXA-2149(auto). Both FXA SOPs present.
  - [ ] C4: same demo as C3, plus Mermaid output contains back-edges for **both** FXA-2148 and FXA-2149 Phase 7.
- **Overall success:** full pytest suite green (no hard-coded count — regressions catch themselves by existing tests failing) + all new tests green; `af plan --root . --task "implement FXA-2117 PRP" --todo --graph` Success Criterion demo still passes (regression check).
- **Rollback verification:** for each of C1–C4, apply the rollback step from §Impact Analysis and confirm (a) pytest still green; (b) the affected `af plan` invocation emits the pre-CHG output byte-for-byte.

---

## Open Questions

All resolved (tracking for Hard Gate closure):

1. **RESOLVED — `--graph` default is `both`.** Leader confirmed the UX goal (terminal legibility) outweighs the narrow backward-compat cost for raw-output consumers. `--graph-format=mermaid` is provided as the explicit opt-out.
2. **RESOLVED — FXA-2149 tag values FROZEN at `[evolve, cli, refactor-cli, improve-cli]`.** No impl-time drift; divergence requires a follow-up CHG (tightened from the previous "may adjust" wording per Codex R1 advisory).
3. **RESOLVED — bundle vs atomic PRs.** Bundled per Leader direction (Frank) given shared review gate and small per-item size.
4. **RESOLVED — C4 added.** Round-1 Gemini flagged FXA-2149 loop omission; C4 adds `Workflow loops` backfill parallel to C2 before Approval.

---

## Alternatives Considered

- **Separate PRs per item (C1 / C2 / C3 / C4).** Rejected: 4× CHG+review cost for items totaling ≤ ~300 lines; shared review gate; shared regression surface; Leader explicitly asked for a single "FXA-2205 follow-ups" PR.
- **Replace Mermaid with ASCII entirely.** Rejected: Mermaid is valuable in GitHub/Obsidian/docs pipelines; removing it would break external consumers and undo the PRP §C4 design.
- **Put ASCII renderer under a separate `af plan --ascii` flag, not inside `--graph`.** Rejected: multiplies flags for the same concept; users would need to remember two flags instead of one for "show me the graph." `--graph-format` is the cleaner composition.
- **Defer C2/C3/C4 to their own CHGs.** Rejected for the same reason bundling was chosen — they are single-line metadata adds tied to the same rollout.
- **Render ASCII by shelling out to an external tool (e.g., `graph-easy`).** Rejected: introduces a runtime dependency and breaks Alfred's "zero external deps" principle. Pure Python renderer keeps the stack minimal.
- **Keep `phases: list[dict]` as untyped dict (status quo).** Rejected: PR 3 already ships this as technical debt; adding ASCII as a second consumer doubles the footprint. Promote to TypedDict now; the cost is one short file.

---

## Approval

- [ ] Reviewed by: Codex + Gemini (COR-1602 parallel, COR-1609 rubric, ≥ 9.0 required from each)
- [ ] Approved on: <YYYY-MM-DD when both reviewers PASS>

---

## Execution Log

| Date       | Action                                        | Result  |
|------------|-----------------------------------------------|---------|
| 2026-04-18 | CHG-2206 Proposed                             | Draft   |
| 2026-04-18 | R1 review: Codex 9.6 PASS / Gemini 9.4 "FIX"  | Revise  |
| 2026-04-18 | Round-2 revision addressing all R1 findings   | Ready   |
| YYYY-MM-DD | R2 review                                     | —       |
| YYYY-MM-DD | Phase 2 implementation start                  | —       |
| YYYY-MM-DD | Phase 3 code review                           | —       |
| YYYY-MM-DD | Phase 4 PR opened                             | —       |
| YYYY-MM-DD | Merged                                        | —       |

---

## Post-Change Review

_To be filled in after merge:_

- Did the change achieve its goal? (terminal legibility of `af plan --graph`; complete Evolve-SOP / Evolve-CLI graphs; `--task "evolve CLI"` coverage)
- Any unexpected side effects? (e.g., downstream scripts broken by ASCII prefix)
- Any follow-up actions? (e.g., expand `Task tags` to more SOPs once patterns are clearer)

---

## Change History

| Date       | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | By                |
|------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------|
| 2026-04-18 | Initial version | Claude (Opus 4.6) |
| 2026-04-18 | Round-1 fixes (Codex 9.6 PASS + Gemini 9.4 FIX, both real CLI): added C4 (FXA-2149 Workflow loops backfill — Gemini B2); embedded concrete ASCII output sample in §Impl Step 4 (Gemini B1); formalised shared phase contract as `TypedDict` in new `core/phases.py` (Codex A1 + Gemini adv); froze FXA-2149 tag list (Codex A2); added missing COR-1101 template sections (Scheduled, Related, Testing/Verification, Approval, Execution Log, Post-Change Review — Codex A3); added Unicode/width edge-case test spec (Gemini adv); added explicit rollback verification steps. | Claude (Opus 4.6) |
| 2026-04-18 | R2 double PASS (Gemini 9.9 + Codex 9.9, both real CLI). Advisories addressed inline: PhaseDict.provenance marked NotRequired-equivalent via total=False; pytest count gate replaced with 'full suite green'; phases.py path fixed as canonical. Status: Proposed -> Approved. | Frank (Leader, on Claude's recommendation) |
| 2026-04-18 | Shipped in fx-alfred v1.6.1 (2026-04-18) via PR #47 — ASCII graph renderer, core/phases.py TypedDict, Evolve-SOP metadata backfills (FXA-2148/2149). | Frank |
