# CHG-2194: Simplify-Fmt-Metadata-Order-Comparison

**Applies to:** FXA project
**Last updated:** 2026-04-04
**Last reviewed:** 2026-04-04
**Status:** Proposed
**Date:** 2026-04-04
**Requested by:** —
**Priority:** Medium
**Change Type:** Normal

---

## What

Replace `[id(mf) for mf in ...] == [id(mf) for mf in ...]` with `ordered_fields == parsed.metadata_fields` in `src/fx_alfred/commands/fmt_cmd.py` line 60. Update the comment on line 59 to reflect the new comparison.

## Why

PRP FXA-2193 (approved: Codex 9.7, Gemini 10.0). The `id()`-based comparison is non-idiomatic and harder to understand. Direct list equality using dataclass `__eq__` is semantically equivalent and more Pythonic.

## Impact Analysis

- **Systems affected:** `af fmt` command (metadata ordering normalization)
- **Rollback plan:** `git revert <commit>`

## Implementation Plan

1. Write test asserting current behavior of `normalize_metadata_order` (TDD Red — verify test exercises the comparison path)
2. Replace lines 59-60 in `fmt_cmd.py` (TDD Green)
3. Run `pytest` + `ruff check` (TDD Refactor/verify)

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-04 | Initial version | — |
