# CHG-2107: Code Quality Refactoring

**Applies to:** FXA project
**Last updated:** 2026-03-19
**Last reviewed:** 2026-03-19
**Status:** Completed
**Date:** 2026-03-18
**Requested by:** Frank
**Priority:** Low
**Change Type:** Normal
**Reviewed by:** Codex (GPT-5.4 xhigh), Gemini 3

---

## What

Three refactoring changes to fx-alfred source code, plus minor fixes, to reduce duplication, improve type accuracy, and strengthen domain boundaries.

1. Create `core/source.py` — consolidate source metadata (`Source` type, `SOURCE_LABELS`, `SOURCE_ORDER`, sort key)
2. Fix `Traversable` protocol — `iterdir()` return type to `Iterator`, remove `read_text()` from `Traversable`, keep `Resource` as separate protocol; delete `# type: ignore` on `scanner.py:120`
3. Refactor `find_document()` — move to core, change return-tuple API to raise domain exceptions (`DocumentNotFoundError`, `AmbiguousDocumentError`); CLI layer catches and converts to `ClickException`

Incidental fixes:
- Fix `scanner.py:85` comment ("Duplicate ACID" → "Duplicate prefix+ACID")
- Adjust verification criteria (see Testing section)

## Why

- `SOURCE_LABELS` duplicated in `list_cmd.py:6` and `status_cmd.py:8`; source order also duplicated in `status_cmd.py:32` and `scanner.py:134`
- `Traversable.iterdir()` return type `list[Traversable]` is inaccurate — `importlib.resources` returns `Iterator`; this forces a `# type: ignore` at `scanner.py:120`
- `_find_document()` returns `(doc, error_msg)` tuple — mixing domain logic with presentation; belongs in core with proper exception-based API
- Original item 4 (unify protocols) was rejected by both reviewers: `Traversable` (directory traversal) and `Resource` (text reading) are different capabilities — merging violates interface segregation principle

## Impact Analysis

- **Systems affected:** `fx_alfred.core.scanner`, `fx_alfred.core.document`, `fx_alfred.commands.list_cmd`, `fx_alfred.commands.status_cmd`, `fx_alfred.commands.read_cmd`
- **New file:** `fx_alfred.core.source`
- **Rollback plan:** Revert commits; no behavioral change, purely structural refactoring

## Implementation Plan

Order: bottom-up (core → commands)

### Step 1: Create `core/source.py`
- Define `Source = Literal["pkg", "usr", "prj"]`
- Move `SOURCE_LABELS: dict[Source, str]`
- Define `SOURCE_ORDER: tuple[Source, ...]` and `source_sort_key()`
- Update imports in `list_cmd.py`, `status_cmd.py`, `scanner.py`

### Step 2: Fix `Traversable` protocol in `scanner.py`
- Change `iterdir()` return type to `Iterator[Traversable]`
- Remove `read_text()` from `Traversable` (it belongs only on `Resource` in `document.py`)
- Delete `# type: ignore` on line 120
- Fix comment on line 85: "Duplicate ACID" → "Duplicate prefix+ACID"

### Step 3: Refactor `find_document()`
- Create `DocumentNotFoundError` and `AmbiguousDocumentError` exceptions in core
- Move `_find_document()` to `core/scanner.py` (or `core/document.py`), rename to `find_document()`, change signature to `find_document(docs: list[Document], identifier: str) -> Document`
- Update `read_cmd.py` to catch domain exceptions and convert to `ClickException`
- Preserve exact error messages and behavior for test compatibility

## Testing / Verification

- `pyright src/` must pass with 0 errors (current baseline: 0 errors)
- `pytest tests/` must pass (excluding `test_build.py` which has a pre-existing build-environment failure unrelated to this change)
- No behavioral changes — output of all commands remains identical
- Note: `make check` is not used as acceptance criteria because `ruff format` has a pre-existing failure

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-18 | Initial version | Frank + Claude |
| 2026-03-19 | Revised after Codex + Gemini review: dropped protocol unification (item 4), expanded source metadata scope, added exception-based API for find_document, fixed verification criteria | Frank + Claude |
| 2026-03-19 | Implementation completed. All 3 steps done + review fixes (SOURCE_ORDER in status_cmd, Source type on SOURCE_ORDER). pyright 0 errors, 83 tests pass. | Frank + Claude |
