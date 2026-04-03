# PRP-2159: Replace Assert With ClickException

**Applies to:** FXA project
**Last updated:** 2026-03-30
**Last reviewed:** 2026-03-30
**Status:** Draft

---

## What Is It?

Replace two `assert` statements in `create_cmd.py` with explicit `click.ClickException` raises, ensuring runtime validation works even under Python's `-O` (optimized) mode.

- **Line 376** (spec-file mode): `assert final_acid is not None`
- **Line 449** (CLI-args mode): `assert acid is not None`

---

## Problem

`fx_alfred/src/fx_alfred/commands/create_cmd.py` uses `assert` for runtime validation at two locations:

1. **Line 376** (spec-file mode): `assert final_acid is not None` — guards that ACID was resolved from spec `acid` field or auto-assigned from spec `area` field.
2. **Line 449** (CLI-args mode): `assert acid is not None` — guards that ACID was provided via `--acid` or auto-assigned from `--area`.

Python's `-O` flag strips all `assert` statements, making these checks no-ops. If ACID resolution fails under `-O`, the code proceeds with `None`, leading to filenames like `FXA-None-SOP-...` or downstream `TypeError`.

**Evidence:** Source analysis during Evolve-CLI run FXA-2158 (2026-03-30).

## Proposed Solution

Replace each assert with a context-specific `click.ClickException`:

**Line 376** (spec-file mode):
```python
if final_acid is None:
    raise click.ClickException(
        "ACID resolution failed for spec-file mode "
        "(neither 'acid' nor 'area' resolved to a valid ACID)"
    )
```

**Line 449** (CLI-args mode):
```python
if acid is None:
    raise click.ClickException(
        "ACID resolution failed for CLI mode "
        "(neither --acid nor --area resolved to a valid ACID)"
    )
```

Distinct messages at each site enable debugging which code path triggered the error.

**Scope:** 2 lines changed in 1 file (`create_cmd.py`). No SOPs affected — this is an internal code quality fix.

## Risk Awareness

- **False positive risk:** None. Both guards sit after exhaustive checks that ensure ACID is non-None; the replacement preserves the same invariant with a user-facing error instead of an `AssertionError`.
- **Backward compatibility:** No CLI interface change. Normal-mode behavior identical (both `assert` and `if/raise` fail on `None`). Only `-O` mode gains protection.
- **Error message visibility:** `click.ClickException` prints to stderr and exits with code 1, matching existing error patterns in the same file.

## Open Questions

None. The fix is minimal and deterministic.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-30 | Initial version | — |
| 2026-03-30 | R1: Fix variable name (acid vs final_acid), add distinct error messages, add Risk Awareness section per Codex review (7.5 FIX) | Claude |
