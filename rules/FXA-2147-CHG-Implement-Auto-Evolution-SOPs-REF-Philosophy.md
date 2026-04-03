# CHG-2147: Implement-Auto-Evolution-SOPs-REF-Philosophy

**Applies to:** FXA project
**Last updated:** 2026-03-30
**Last reviewed:** 2026-03-30
**Status:** Completed
**Date:** 2026-03-30
**Requested by:** Frank
**Priority:** Medium
**Change Type:** Normal

---

## What

Implement Phase 1 deliverables from approved PRP FXA-2145:

1. `FXA-2146-REF-Evolution-Philosophy.md` — Evolution north star document (ACID pre-assigned)
2. `FXA-2148-SOP-Evolve-SOP.md` — Evolve-SOP procedure (ACID assigned here: 2148)
3. `FXA-2149-SOP-Evolve-CLI.md` — Evolve-CLI procedure (ACID assigned here: 2149)

Also: add `pytest-json-report` and `pytest-cov` to `fx_alfred/pyproject.toml` optional dependencies.

## Why

PRP FXA-2145 approved (R9: Gemini 9.8 + Codex 9.1). Phase 1 establishes the automated self-improvement feedback loop for alfred SOPs and CLI code, following the "Compression as Intelligence" principle.

## Impact Analysis

- **Systems affected:** `alfred_ops/rules/` (3 new documents), `fx_alfred/pyproject.toml` (2 new optional deps)
- **Rollback plan:** Delete the 3 new documents; revert pyproject.toml change

## Implementation Plan

1. Create `FXA-2146-REF-Evolution-Philosophy.md` with north star content from PRP
2. Create `FXA-2148-SOP-Evolve-SOP.md` with full SOP procedure
3. Create `FXA-2149-SOP-Evolve-CLI.md` with full SOP procedure
4. Add `pytest-json-report` and `pytest-cov` to `fx_alfred/pyproject.toml`
5. Run `af validate --root fx_alfred` — hard gate, must pass
6. Dispatch Codex + Gemini code review via `/trinity` (both >= 9.0)

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-30 | Initial version, ACIDs assigned: REF=2146, SOP-Evolve-SOP=2148, SOP-Evolve-CLI=2149 | Frank + Claude |
