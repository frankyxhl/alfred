# CHG-2290: COR-1619 Decision Tree Two-Worker Branch

**Applies to:** FXA project
**Last updated:** 2026-05-17
**Last reviewed:** 2026-05-17
**Status:** Approved
**Related:** PRP-1507 (Two-Worker TDD Dispatch — design source), GitHub issue #175, CHG-2289 (CHG-C1 — sub-section the new branch routes into), CHG-2287 (CHG-A — Worker assignment rule), CHG-2291 (CHG-D — `<test-writer-worker-agent>` parameter the new `P` node gates on)
**Date:** 2026-05-17
**Requested by:** @frankyxhl
**Priority:** Medium
**Change Type:** Normal
**Targets:** src/fx_alfred/rules/COR-1619-SOP-Orchestrator-vs-Worker-Dispatch.md §Decision Tree (mermaid block)

---

## What

**Post-R3 final form** (after PR #177 codex bot P2 finding, see Change History R3): the mermaid flowchart in `src/fx_alfred/rules/COR-1619-SOP-Orchestrator-vs-Worker-Dispatch.md` §Decision Tree is **unchanged from its pre-PRP-1507 state** (byte-for-byte preservation of the original tree from `A` through all leaves). The two-worker routing is expressed as a **prose overlay paragraph** added below the existing `<worker-min-loc>` paragraph that explains when the worker dispatch follows §Two-Worker TDD Dispatch instead of §Worker Dispatch Contract. The overlay applies *after* the tree picks a WORKER leaf (W1/W2/W3/W4) and is OFF when `<test-writer-worker-agent>` is unset, equal to `<worker-agent>`, or any opt-out class matches. Orchestrator-direct leaves (O1/O2/O3/O4) are explicitly excluded.

*Earlier R1 form* (replaced after R3 review) inserted two mermaid gating nodes (`P`, `TW`) ahead of the existing `B` head; codex bot caught at R3 that this incorrectly intercepted orchestrator-direct routings (e.g., `G --Yes--> O3`) by forcing them through the TW gate, conflicting with COR-1500's wording "when the RED phase is dispatched to `<worker-agent>`". The prose-overlay form is the correct surface for the two-worker decision because the rule layers on top of the existing routing rather than gating it.

CHG-C2 is a separate CLD-1802 surface from CHG-C1 (the §Two-Worker TDD Dispatch sub-section): §Decision Tree is a distinct heading region from §Worker Dispatch Contract, so the two edits are filed as separate CHGs even though both target COR-1619 and land in the same PR.

## Why

The existing decision tree assumes a single `<worker-agent>` and routes implementation tasks through one lane. With PRP-1507's two-worker split landing, adopters who set `<test-writer-worker-agent>` distinct need a tree branch that asks the parameter-gate question *before* the existing single-worker tree applies. Without this branch, an orchestrator reading COR-1619 §Decision Tree gets no hint that two-worker dispatch is even an option — the tree silently routes through node `B` regardless.

The new `P` node ("`<test-writer-worker-agent>` set distinct from `<worker-agent>`?") and `TW` node ("Two-worker TDD applicable? (substantive code, no opt-out class matches)") together gate entry into the new TW1 leaf ("TWO-WORKER TDD — see §Two-Worker TDD Dispatch"). The "No" branches of `P` and `TW` both fall through to the existing `B` head, preserving every existing routing decision for adopters who do not set the parameter and for tasks that match an opt-out class. PRP-1507 R3.5 (Codex P1) closed the chain-preservation risk by adding an explicit "%% existing tree continues unchanged from MIX onward" marker plus the prose instruction that CHG-C2's implementation must re-include the full chain verbatim.

## Out of Scope

- Editing §Worker Dispatch Contract or §Verification or §Guard Rails or §Examples — separate surfaces in the same file; only the Change History row gains one entry covering the file-wide bundle.
- Editing COR-1500 — separate file, separate CHGs (A, B).
- Editing COR-1622 — separate file, separate CHG (D).
- Renaming `B`, `MIX`, `H0`, `H`, `C`, `D`, `E`, `F`, `G` or any leaf node — the entire chain from `MIX` onward is preserved verbatim per PRP-1507 §Proposed Solution line 156.
- Modifying the prose paragraph below the mermaid block ("The `<worker-min-loc>` parameter (default 30) sets the LoC threshold …") — that paragraph stays as-is; the new `P` / `TW` nodes are entirely above it.
- Modifying the §Edge cases not in the tree sub-section — none of the four edge cases interact with the two-worker split.

## Impact Analysis

- **Systems affected:** `src/fx_alfred/rules/COR-1619-SOP-Orchestrator-vs-Worker-Dispatch.md` §Decision Tree mermaid block only (~10 lines of mermaid source replaced; the preserved chain is byte-for-byte identical from `MIX` onward).
- **Behavioural impact:** Adopters who leave `<test-writer-worker-agent>` unset see the tree behave identically — the new `P` node's "No" branch routes straight to the existing `B` node, and the entire downstream tree is unchanged. Adopters who set the parameter distinct see a new top-level routing path: `P --Yes--> TW`, and from `TW` either `TW1` (two-worker dispatch, routes to §Two-Worker TDD Dispatch sub-section landed by CHG-C1) or `B` (when an opt-out class matches, falling back to the existing tree).
- **Compatibility:** Backwards-compatible. Every existing route through `B → MIX → … → leaf` is preserved bit-identical.
- **Risk surface:** Low. The patch is a localised mermaid edit; the diff against pre-edit is small (insert 4 lines, add `P` and `TW` decisions, no existing node touched). Two prior PRP R-rounds (R2.5 GLM P2 and R3.5 Codex P1) caught chain-preservation risks and added explicit verbatim-preservation language.
- **Rollback plan:** Revert this commit. The mermaid block reverts to the pre-CHG single-worker tree; CHG-C1's sub-section becomes unreferenced but does not break (it remains as documentation; adopters who set `<test-writer-worker-agent>` and read CHG-C1 directly still get the contract, but the tree no longer routes them there).

## Acceptance Criteria

- A1: The mermaid `flowchart TD` block in `src/fx_alfred/rules/COR-1619-SOP-Orchestrator-vs-Worker-Dispatch.md` §Decision Tree starts with `A[Implementation task] --> P{"<test-writer-worker-agent> set distinct from <worker-agent>?"}` (or the HTML-entity-encoded `&lt;/&gt;` form per mermaid syntax in PRP-1507 line 146).
- A2: New nodes `P` and `TW` exist and route per PRP-1507 §Proposed Solution lines 144–154:
  - `P -- No --> B{Generated file regen only?}`
  - `P -- Yes --> TW{Two-worker TDD applicable? (substantive code, no opt-out class matches)}`
  - `TW -- Yes --> TW1[TWO-WORKER TDD<br/>see §Two-Worker TDD Dispatch]`
  - `TW -- No --> B`
- A3: The existing chain (`B`, `MIX`, `H0`, `H`, `C`, `D`, `E`, `F`, `G`) and all existing leaves (`O1`, `O2`, `O3`, `O4`, `W1`, `W2`, `W3`, `W4`) are preserved byte-for-byte from `MIX` onward. Verified via `diff` of the pre-edit and post-edit mermaid block, restricted to lines containing `MIX`, `H0`, `H{`, `C{`, `D{`, `E{`, `F{`, `G{`, `O1[`, `O2[`, `O3[`, `O4[`, `W1[`, `W2[`, `W3[`, `W4[`, and the `-- Yes -->` / `-- No -->` edges from each of those nodes — every such line is identical before and after.
- A4: The prose paragraph immediately below the mermaid block (starting "The `<worker-min-loc>` parameter (default 30) sets the LoC threshold …") is unchanged.
- A5: A new TW1 leaf is added with the label `TWO-WORKER TDD<br/>see §Two-Worker TDD Dispatch` referencing the sub-section landed by CHG-C1 / FXA-2289.
- A6: `Last updated` and `Last reviewed` in COR-1619 frontmatter are updated to 2026-05-17 (one update per file covers both CHG-C1 and CHG-C2).
- A7: A Change History row dated 2026-05-17 referencing CHG-C2 (FXA-2290) and PRP-1507 is appended.
- A8: `af validate --root /Users/frank/Projects/alfred` reports 0 issues after the edit.
- A9: This CHG document (`rules/FXA-2290-CHG-COR-1619-Decision-Tree-Two-Worker-Branch.md`) exists, has `Status: Proposed` on creation and is moved to `Status: Completed` in the merge commit.

## Implementation Plan

1. Open `src/fx_alfred/rules/COR-1619-SOP-Orchestrator-vs-Worker-Dispatch.md`.
2. Locate the `flowchart TD` mermaid block under `## Decision Tree`.
3. Replace the head edge `A[Implementation task] --> B{Generated file regen only?}` with the new pair of gating edges:
   - `A[Implementation task] --> P{"<test-writer-worker-agent> set distinct from <worker-agent>?"}`
   - `P -- No --> B{Generated file regen only?}`
   - `P -- Yes --> TW{Two-worker TDD applicable? (substantive code, no opt-out class matches)}`
   - `TW -- Yes --> TW1[TWO-WORKER TDD<br/>see §Two-Worker TDD Dispatch]`
   - `TW -- No --> B`
   Use the HTML-entity-encoded `&lt;`/`&gt;`/`<br/>` form per PRP-1507 line 146 inside node labels.
4. Confirm every existing edge and node from `MIX` through to all leaves is preserved verbatim (no insertion, deletion, reorder, or rename).
5. Update `Last updated` and `Last reviewed` to 2026-05-17 if not already updated by CHG-C1 in the same editing pass.
6. Append a Change History row dated 2026-05-17 referencing CHG-C2 (FXA-2290) and PRP-1507.
7. Run `af validate --root /Users/frank/Projects/alfred`; expect 0 issues.
8. Diff the pre-edit and post-edit mermaid block to verify the chain-preservation invariant (PRP-1507 §Proposed Solution line 156).

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-17 | Initial version — drafted as CHG-C2 of PRP-1507 §Implementation Plan, bundled with CHG-A/B/C1/D in PR closing issue #175 | Claude Opus 4.7 |
| 2026-05-17 | R1 plan-review panel (alfred triad, gemini substituted for minimax which hit usage limit): glm 9.86, deepseek 10.0, gemini 10.0 — PASS, blocking == []. P3 advisory (GLM): TW node label uses double-quotes vs PRP plain text — required for valid mermaid syntax (parentheses in label break the parser without quoting); semantic content identical. P3 advisory: soft revert coupling with CHG-C1 — both rollback plans acknowledge. Status moved Proposed → Approved. | Claude Opus 4.7 |
| 2026-05-17 | R3 (PR #177 codex bot P2): the head-of-tree P + TW mermaid gating nodes intercepted ALL substantive code tasks before the existing orchestrator-vs-worker decision was made, incorrectly routing some orchestrator-direct paths (e.g., a small single-file change with 2 functions and <5 tests would reach G-Yes → O3 in the old tree, but the new head routed it through TW first) and conflicting with COR-1500's wording "when RED is dispatched to `<worker-agent>`". Restructured: mermaid head restored to its original `A → B` (full chain preservation byte-for-byte); two-worker gate moved to a prose overlay paragraph below the tree that applies *after* the existing tree picks a WORKER leaf (W1/W2/W3/W4). Orchestrator-direct leaves (O1-O4) are explicitly excluded from the overlay. | Claude Opus 4.7 |
