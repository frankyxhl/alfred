# CHG-2103: Add --root Option and Fix List Spacing

**Applies to:** FXA project
**Last updated:** 2026-03-17
**Last reviewed:** 2026-03-17
**Status:** Approved
**Date:** 2026-03-17
**Requested by:** Frank
**Priority:** Low
**Change Type:** Normal
**Scheduled:** 2026-03-17
**Related:** FXA-2100-SOP (Leader Mediated Development)

---

## What

1. Add `--root` option to all scan-based commands (`list`, `read`, `status`, `create`, `index`) to specify a custom project root instead of cwd.
2. Change `af list` output from tab-separated to space-aligned.

---

## Why

1. Users need to scan documents in other directories without cd-ing (e.g., `af list --root alfred_ops`).
2. Tab alignment renders inconsistently across terminals.

---

## Impact Analysis

- **Systems affected:** cli.py (global option), all 5 scan commands, list_cmd.py output format
- **Channels affected:** none
- **Downtime required:** No
- **Rollback plan:** Revert to v0.2.0

---

## Implementation Plan

| # | TDD Cycle | Description |
|---|-----------|-------------|
| 1 | `--root` on CLI group | Add `--root` option to Click group, pass via context |
| 2 | Commands use root from context | All scan commands read root from `ctx.obj` instead of `Path.cwd()` |
| 3 | `af list` spacing | Change tab to fixed-width space alignment |
| 4 | Tests | Update existing tests, add `--root` tests |
| 5 | Version | Bump to 0.2.1 |

---

## Testing / Verification

- Test `af list --root <path>` scans the specified directory
- Test `af read --root <path> <ACID>` reads from specified directory
- Test `af list` output uses spaces not tabs
- All existing tests pass
- Dual code review (Codex + Gemini) per FXA-2100-SOP, both >= 9/10

---

## Approval

- [x] Reviewed by: Frank
- [x] Approved on: 2026-03-17

---

## Execution Log

| Date | Action | Result |
|------|--------|--------|
| | | |

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-17 | Initial version | Claude Code |
| 2026-03-20 | Migrated to Document Format Contract: fixed H1, normalized metadata prefix, added Applies to/Last updated/Last reviewed | af CLI |
