# PRP-2165: Extract Invoke Index Update Helper

**Applies to:** FXA project
**Last updated:** 2026-04-01
**Last reviewed:** 2026-04-01
**Status:** Draft

---

## What Is It It Extract the duplicated index-update pattern into a shared `invoke_index_update(ctx)` helper, replacing identical inline implementations in `create_cmd.py` (x2) and `update_cmd.py` (x1).

Both implement the same 5-line pattern:
```python
try:
    from fx_alfred.commands.index_cmd import index_cmd

    ctx.invoke(index_cmd)
except Exception as e:
    click.echo(f"Warning: Failed to update index: {e}", err=True)
```

## Proposed Solution

Add `invoke_index_update(ctx: click.Context) -> None` to `_helpers.py`. Replace 3 inline implementations with calls to `invoke_index_update(ctx)`).

**Files changed:**
1. `src/fx_alfred/commands/_helpers.py` — add `invoke_index_update()`
2. `src/fx_alfred/commands/create_cmd.py` — replace 2 inline patterns (lines 414-419, 492-497) with `invoke_index_update(ctx)`
3. `src/fx_alfred/commands/update_cmd.py` — replace inline pattern (line 410-415) with `invoke_index_update(ctx)`

### Behavioral Contract

| Aspect | Specification |
|--------|--------------|
| Encoding | UTF-8 — `os.fdopen(fd, "w")` in text mode; Python default encoding |
| Newline | Platform-native (Python text mode default — matches current behavior exactly |
| Target dir | Must exist (caller responsibility; matches current behavior) |
| Return | `None` |
| Exceptions | Re-raises any exception from write/replace; cleanup is `O OSError` on cleanup `unlink` — silently handles `O OSError` on cleanup `unlink` |

### Test Plan

Unit tests in `tests/test_helpers.py` (extend existing file):
- `test_invoke_index_update_success` — ctx.invoke(index_cmd) succeeds, verify index updated
 - `test_invoke_index_update_failure` — mock `ctx.invoke` to raise, verify index unchanged and temp file removed
 - `test_invoke_index_update_preserve_existing` — write file with initial content, mock `ctx.invoke` fails, verify original unchanged

 - Regression: existing 392 tests cover both call sites after extraction

### Non-Goals
- No changes to `core/` modules
  - No changes to other command modules (only `create_cmd` and `update_cmd` contain the pattern)
  - No addition of fsync, permission mode, or encoding options to `invoke_index_update` (matches current behavior — neither call site logs)

## Rollback
Revert the 3-file commit. Both call sites have identical original patterns, so rollback is trivial.

**No CLI interface changes.** Backward compatible.

**No dependency changes.** None

## Impact Boundary
- **No SOP, document/process artifacts affected** | pure code refactoring
 - **No CLI interface changes.** Backward compatible
- **No dependency changes.** None

## Open Questions

None.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-01 | Initial version | Frank + Claude |
