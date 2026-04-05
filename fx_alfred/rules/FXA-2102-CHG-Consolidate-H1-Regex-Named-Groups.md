# CHG-2102: Consolidate-H1-Regex-Named-Groups

**Applies to:** FXA project
**Last updated:** 2026-04-05
**Last reviewed:** 2026-04-05
**Status:** Proposed
**Date:** 2026-04-05
**Requested by:** —
**Priority:** Medium
**Change Type:** Normal

---

## What

Add named capture groups to `H1_PATTERN` in `parser.py` and remove the duplicate `_H1_EXTRACT` regex from `validate_cmd.py`. Per PRP FXA-2101 (Codex 9.4, Gemini 10.0).

## Why

Two regex patterns match the same H1 format (`parser.py:61` non-capturing, `validate_cmd.py:31` capturing). Adding named groups to `H1_PATTERN` consolidates into one pattern, eliminating divergence risk.

## Impact Analysis

- **Systems affected:** `src/fx_alfred/core/parser.py`, `src/fx_alfred/commands/validate_cmd.py`
- **Rollback plan:** Revert the two file changes; restore `_H1_EXTRACT` in validate_cmd.py

## Implementation Plan

1. Update `H1_PATTERN` in `parser.py:61` to `r"^# (?P<type_code>[A-Z]{3})-(?P<acid>\d{4}): .+$"`
2. Remove `_H1_EXTRACT` from `validate_cmd.py:31`
3. Update `validate_cmd.py:147` to use `H1_PATTERN.match()` with `.group("type_code")` / `.group("acid")`
4. Add unit test for named groups in `tests/test_parser.py`
5. Run full pytest + ruff

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-05 | Initial version | — |
