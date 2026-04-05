# PRP-2101: Extract-H1-Extraction-Regex-To-Parser

**Applies to:** FXA project
**Last updated:** 2026-04-05
**Last reviewed:** 2026-04-05
**Status:** Draft

---

## What Is It?

Consolidate the duplicate H1 regex by adding named capture groups to the existing `H1_PATTERN` in `parser.py`, then removing the local `_H1_EXTRACT` from `validate_cmd.py`.

---

## Problem

`validate_cmd.py:31` defines `_H1_EXTRACT = re.compile(r"^# ([A-Z]{3})-(\d{4}): .+$")` — a capturing regex for extracting type_code and ACID from H1 lines. `parser.py:61` already defines `H1_PATTERN = re.compile(r"^# [A-Z]{3}-\d{4}: .+$")` — a non-capturing variant of the same pattern for format validation.

Two regex patterns matching the same H1 format creates divergence risk: if the H1 format contract changes, both must be updated independently.

## Proposed Solution

1. **Update `H1_PATTERN` in `parser.py:61`** to use named capture groups: `r"^# (?P<type_code>[A-Z]{3})-(?P<acid>\d{4}): .+$"`. Adding named groups is backward-compatible — all existing `.match()` boolean checks continue to work identically.
2. **Remove `_H1_EXTRACT`** from `validate_cmd.py:31`.
3. **Update `validate_cmd.py` lines 147–150** to use `H1_PATTERN.match()` (already imported) instead of `_H1_EXTRACT.match()`, and switch from `.group(1)`/`.group(2)` to `.group("type_code")`/`.group("acid")`.

**One pattern, zero duplication.**

**Files changed:** `src/fx_alfred/core/parser.py`, `src/fx_alfred/commands/validate_cmd.py`

**Out of scope:** No changes to `document.py:75` or `parser.py:77` — those call sites use `.match()` for boolean checks only, unaffected by named groups.

## Test Plan

- Existing `tests/test_validate_cmd.py` exercises H1 mismatch detection (type_code and ACID extraction). These tests cover the extraction call site and verify the named-group switch.
- Add one new unit test in `tests/test_parser.py` confirming `H1_PATTERN` returns correct named groups (`type_code`, `acid`) for a sample H1 line.
- Run full `pytest` suite to confirm no regressions across all 4 call sites (`validate_cmd.py:143`, `validate_cmd.py:168`, `parser.py:77`, `document.py:75`).

## Risks

Low blast radius: `H1_PATTERN` is used at 4 call sites across 3 files (`validate_cmd.py`, `parser.py`, `document.py`). All existing call sites use `.match()` for boolean checks — adding named groups does not change match behavior, only adds `.group("name")` access. The private `_H1_EXTRACT` name has no external consumers (confirmed by grep). Full test suite validates all call sites.

## Open Questions

None.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-05 | Initial version | — |
| 2026-04-05 | R2: consolidate into H1_PATTERN (Codex 8.9 FIX, Gemini 7.0 FIX feedback) | Claude Code |
