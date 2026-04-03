# PRP-2162: Extract Atomic Write Helper

**Applies to:** FXA project
**Last updated:** 2026-03-30
**Last reviewed:** 2026-03-30
**Status:** Draft

---

## What Is It?

Extract the duplicated atomic file-write pattern (tempfile + os.fdopen + os.replace + cleanup) into a shared helper in `_helpers.py`.

---

## Problem

The atomic write pattern for safe file updates is duplicated verbatim in two command modules:
- `fmt_cmd.py:397-409` — write formatted document
- `update_cmd.py:399-410` — write updated document

Both implement the same 8-line pattern:
```python
fd, tmp_path_str = tempfile.mkstemp(dir=str(file_path.parent), suffix=".md.tmp")
try:
    with os.fdopen(fd, "w") as f:
        f.write(new_content)
    os.replace(tmp_path_str, str(file_path))
except Exception:
    try:
        os.unlink(tmp_path_str)
    except OSError:
        pass
    raise
```

Duplicating safety-critical patterns risks divergent behavior if one copy is updated without the other. A repo-wide search confirms `os.replace` appears in exactly these two files — no hidden instances exist.

## Proposed Solution

Add `atomic_write(path: Path, content: str) -> None` to `_helpers.py`. Replace both inline implementations with calls to the helper.

### Behavioral Contract

| Aspect | Specification |
|--------|--------------|
| Encoding | UTF-8 — `os.fdopen(fd, "w")` in Python text mode uses the locale encoding; on all supported platforms (macOS/Linux) the default is UTF-8. Both call sites write `.md` files that are UTF-8. No encoding parameter is exposed. |
| Newline | Platform-native (Python text mode default) — matches current behavior exactly |
| Temp file | Created in `path.parent` with suffix `.md.tmp`; cleaned up on failure |
| Success path | `os.replace(tmp, path)` — atomic on POSIX, best-effort on Windows |
| Failure path | `os.unlink(tmp)` on exception; re-raises the original exception |
| Target dir | Must exist (caller responsibility; matches current behavior — both call sites ensure parent exists before calling) |
| Return | `None` |
| Exceptions | Re-raises any exception from write/replace; silently handles `OSError` on cleanup `unlink` |

### Files Changed

1. `src/fx_alfred/commands/_helpers.py` — add `atomic_write()`, add `os` and `tempfile` imports
2. `src/fx_alfred/commands/fmt_cmd.py` — replace lines 397-409 with `atomic_write(file_path, new_content)`, remove `os`/`tempfile` imports if unused
3. `src/fx_alfred/commands/update_cmd.py` — replace lines 399-410 with `atomic_write(file_path, new_content)`, remove `os`/`tempfile` imports if unused

### Test Plan

**Unit tests** in `tests/test_helpers.py` (extend existing file):
- `test_atomic_write_success` — write content, verify target file matches
- `test_atomic_write_cleanup_on_failure` — mock `os.replace` to raise, verify temp file removed
- `test_atomic_write_preserves_existing` — verify original file unchanged on failure

**Call-site regression** (existing tests must continue passing):
- `tests/test_fmt_cmd.py` — all existing fmt tests pass unchanged (verifies fmt_cmd still writes correctly via the helper)
- `tests/test_update_cmd.py` — all existing update tests pass unchanged (verifies update_cmd still writes correctly via the helper)

### Non-Goals

- No changes to `core/` modules
- No changes to other command modules (only fmt_cmd and update_cmd contain the pattern)
- No addition of fsync, permission mode parameters, or encoding options
- No logging within `atomic_write` (matches current behavior — neither call site logs)

### Impact Boundary

- **No SOP, document, or process artifacts affected** — this is a pure code refactoring
- **No CLI interface changes** — backward compatible
- **No dependency changes** — uses only stdlib (`os`, `tempfile`)

### Risks and Trade-offs

| Risk | Mitigation |
|------|------------|
| `os.replace` non-atomic on NFS/some network filesystems | Not a concern — `fx_alfred` targets local development machines |
| `_helpers.py` gains I/O responsibility (currently Click-wrapping only) | Acceptable — the helper is Click-adjacent (used only by Click commands); a separate `_io.py` would be premature for a single function |
| Behavioral regression if helper diverges from original pattern | Test plan verifies equivalence; 389 existing tests cover both call sites |

### Rollback

Revert the 3-file commit. Both call sites have identical original patterns, so rollback is trivial.

## Open Questions

None.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-30 | Initial version | Frank + Claude |
| 2026-03-30 | R1: add behavioral contract, test plan, non-goals, risks, rollback per Codex+Gemini review | Frank + Claude |
| 2026-03-30 | R2: fix encoding spec, add call-site regression tests, add impact boundary, clean up per Codex review | Frank + Claude |
