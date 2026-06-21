# CHG-2310: Implement Evolve Engine SOP Refactor

**Applies to:** FXA project
**Last updated:** 2026-06-21
**Last reviewed:** 2026-06-21
**Status:** Proposed
**Related:** FXA-2308, FXA-2309, FXA-2146, FXA-2148, FXA-2149, GitHub issue #234
**Date:** 2026-06-21
**Requested by:** Frank Xu
**Priority:** Medium
**Change Type:** Normal

---

## What

Implement `FXA-2308` by extracting the duplicated Evolve-SOP / Evolve-CLI workflow into shared engine `FXA-2309`, then reducing `FXA-2148` and `FXA-2149` to compact public entry-point wrappers.


## Why

The two evolve SOPs had the same guard, signal, candidate, review, PR, and post-push loop skeleton. This change keeps their operational differences explicit while moving common behavior and new evidence-rigor rules into one engine.


## Impact Analysis

- **Systems affected:** FXA evolve documentation, `af plan` output for `FXA-2148` and `FXA-2149`, workflow-loop metadata, and `FXA-2146` prohibited mutation surface.
- **Behavior preserved:** phase order, skip gate, run log, signal sources, scoring thresholds by reference, candidate cardinality, no-op disposition, review gates, hard gates, PR flow, post-push loop limit, and completion checklist intent.
- **Intentional behavior update:** `FXA-2149` source root now uses the current top-level repo layout `src/fx_alfred/`; stale nested `fx_alfred/` path assumptions are removed.
- **Governance update:** `FXA-2146` now protects the new engine and scopes the mutation prohibition to autonomous evolve runs, while still allowing explicitly named human-authored PRP/CHG changes.
- **Rollback plan:** revert `FXA-2309`, restore pre-change `FXA-2148`, `FXA-2149`, and the old `FXA-2146` prohibited surface, then regenerate/repair `FXA-0000`.


## Implementation Plan

1. Create `FXA-2309-SOP-Evolve-Engine.md` with the shared 9-phase engine.
2. Rewrite `FXA-2148` as an Evolve-SOP wrapper with local integer `Workflow loops`.
3. Rewrite `FXA-2149` as an Evolve-CLI wrapper with local integer `Workflow loops` and current `src/fx_alfred/` source root.
4. Update `FXA-2146` prohibited mutation surface without changing weights or thresholds.
5. Keep `FXA-0000` in the 4-column index format and add rows for `FXA-2308`, `FXA-2309`, and `FXA-2310`.
6. Verify `af validate`, `af plan`, `af plan --graph`, `wc -l -w`, and `git diff --stat`.


## Behavior Equivalence Checklist

- Phase order and phase names: preserved through `FXA-2309` Phase 0-8.
- Workflow loop metadata: preserved as one local `review-retry` loop per entry point, max 3.
- Guard checks and skip conditions: preserved.
- Prerequisites: preserved in wrapper profiles.
- Signal sources and source roots: preserved, except CLI source root intentionally updated to `src/fx_alfred/`.
- Thresholds and weight tables: referenced from `FXA-2146`, not duplicated.
- Candidate cardinality: `FXA-2148` each passing candidate; `FXA-2149` top passing candidate.
- No-op disposition: `FXA-2148` leaves run log uncommitted; `FXA-2149` commits/pushes no-op run log to `main`.
- Branch naming: preserved by wrapper profiles.
- PRP/CHG and review gates: preserved by engine Phase 5.
- Implementation sequence: document lifecycle for SOP, TDD for CLI.
- Hard gate: `af validate` for SOP, pytest + ruff for CLI.
- Post-push comment categories and loop limit: preserved.
- Substantive-fix escalation: SOP returns to code review gate; CLI returns to hard gate.
- Mechanical-fix boundary: preserved per instance.
- PR body source: run-log summary preserved.
- Completion checklist rows: preserved, including CLI README check.
- Prohibited actions and mutation guard: strengthened with `FXA-2309`.


## Rigor Coverage Checklist

- Signal provenance fields: source, collection method, trust rating, trust reason, improvement path.
- Trust scale: high / medium / low with anchors.
- Candidate evidence fields: concrete example, evidence source, evidence rating, skepticism note.
- Evidence scale: strong / medium / weak with anchors.
- Ledger rule: cite ledger evidence when available; state unavailable rather than inventing it.
- Scoring impact: low-trust or weak-evidence candidates cannot pass without separate direct evidence.


## Verification

Record these before merge:

```bash
af validate --root /Users/frank/Projects/alfred
af plan FXA-2148 --root /Users/frank/Projects/alfred
af plan FXA-2149 --root /Users/frank/Projects/alfred
af plan --graph FXA-2148 --root /Users/frank/Projects/alfred
af plan --graph FXA-2149 --root /Users/frank/Projects/alfred
wc -l -w rules/FXA-2148-SOP-Evolve-SOP.md rules/FXA-2149-SOP-Evolve-CLI.md
wc -l -w rules/FXA-2309-SOP-Evolve-Engine.md rules/FXA-2148-SOP-Evolve-SOP.md rules/FXA-2149-SOP-Evolve-CLI.md
git diff --stat
```

Current local verification:

- `af validate --root /Users/frank/Projects/alfred`: 304 docs, 0 issues, 1 pre-existing `FXA-2271` CTX warning.
- `af plan FXA-2148 --root /Users/frank/Projects/alfred`: renders the 11-step Evolve-SOP wrapper.
- `af plan FXA-2149 --root /Users/frank/Projects/alfred`: renders the 11-step Evolve-CLI wrapper.
- `af plan --graph FXA-2148 --root /Users/frank/Projects/alfred`: renders one local `review-retry` loop, Step 10 to Step 9, max 3.
- `af plan --graph FXA-2149 --root /Users/frank/Projects/alfred`: renders one local `review-retry` loop, Step 10 to Step 9, max 3.
- Baseline `FXA-2148` + `FXA-2149`: 346 lines / 2927 words.
- Post-refactor `FXA-2309` + `FXA-2148` + `FXA-2149`: 305 lines / 2661 words.
- Targeted tests: `PYTHONPATH=src uv run pytest tests/test_workflow_loops.py tests/test_index_cmd.py -q` passed, 99 tests.
- Lint: `uv run ruff check .` passed.

## Change History

| Date       | Change                                                             | By    |
|------------|--------------------------------------------------------------------|-------|
| 2026-06-21 | Initial implementation CHG for FXA-2308 Evolve Engine SOP refactor | Codex |
