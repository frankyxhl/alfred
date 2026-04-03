# CHG-2169: Deduplicate Plan Cmd Phase Formatters

**Applies to:** FXA project
**Last updated:** 2026-04-01
**Last reviewed:** 2026-04-01
**Status:** Proposed
**Date:** 2026-04-01
**Requested by:** —
**Priority:** Medium
**Change Type:** Normal

---

## What

Merge `_format_phase_llm` and `_format_phase_human` in `plan_cmd.py` into a single `_format_phase` function. Callers pass pre-built `heading`, `summary_prefix`, and `checkbox` strings. PRP: FXA-2168 (approved R2: Codex 9.2, Gemini 9.6).

## Why

Two functions share ~80% logic (extract steps, parse items, format checkboxes, handle fallback). Only heading style, summary prefix, and checkbox format differ. Merging reduces ~20 lines and eliminates divergence risk per "Compression as Intelligence" (FXA-2146).

## Impact Analysis

- **Systems affected:** `fx_alfred/src/fx_alfred/commands/plan_cmd.py` only
- **Rollback plan:** `git revert <commit>`

## Implementation Plan

1. TDD Red: Add exact-output snapshot tests for both LLM and human modes (including fallback paths)
2. TDD Green: Replace `_format_phase_llm` + `_format_phase_human` with `_format_phase`; update callers
3. TDD Refactor: Clean up, run full test suite + ruff
4. Hard gate: pytest 100% pass, ruff 0 issues

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-01 | Initial version | — |
