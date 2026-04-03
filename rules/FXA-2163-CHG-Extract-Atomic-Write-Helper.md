# CHG-2163: Extract Atomic Write Helper

**Applies to:** FXA project
**Last updated:** 2026-03-30
**Last reviewed:** 2026-03-30
**Status:** Approved
**Date:** 2026-03-30
**Requested by:** Evolve-CLI (FXA-2149)
**Priority:** Medium
**Change Type:** Standard

---

## What

Extract the duplicated atomic file-write pattern into a shared `atomic_write()` helper in `_helpers.py`, replacing identical inline implementations in `fmt_cmd.py` and `update_cmd.py`.

## Why

The same 8-line safety-critical pattern (tempfile + os.fdopen + os.replace + cleanup) is duplicated in two command modules. Duplicating safety patterns risks divergent behavior. Approved via PRP FXA-2162 (Codex 9.3, Gemini 10.0).

## Impact Analysis

- **Systems affected:** `commands/_helpers.py`, `commands/fmt_cmd.py`, `commands/update_cmd.py`
- **Rollback plan:** Revert the 3-file commit; both call sites have identical original patterns

## Implementation Plan

1. Add `atomic_write(path: Path, content: str) -> None` to `_helpers.py` with `os`/`tempfile` imports
2. Replace `fmt_cmd.py:397-409` with `atomic_write(file_path, new_content)`
3. Replace `update_cmd.py:399-410` with `atomic_write(file_path, new_content)`
4. Add 3 unit tests to `tests/test_helpers.py`
5. Verify all 389 tests pass + ruff clean

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-30 | Initial version per PRP FXA-2162 | Frank + Claude |
