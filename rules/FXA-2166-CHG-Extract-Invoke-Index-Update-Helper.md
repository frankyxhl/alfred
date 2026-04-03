# CHG-2166: Extract Invoke Index Update Helper

**Applies to:** FXA project
**Last updated:** 2026-04-01
**Last reviewed:** 2026-04-01
**Status:** Approved
**Date:** 2026-04-01
**Requested by:** Evolve-CLI (FXA-2164)
**Priority:** Medium
**Change Type:** Standard

---

## What

Extract the duplicated index update pattern into a shared `invoke_index_update(ctx)` helper, replacing identical inline implementations in `create_cmd.py` (x2) and `update_cmd.py` (x1).

Both call sites implement the same 5-line pattern:
```python
try:
    from fx_alfred.commands.index_cmd import index_cmd
    ctx.invoke(index_cmd)
except Exception as e:
    click.echo(f"Warning: Failed to update index: {e}", err=True)
```

## Why

Deduplication — three identical inline implementations create maintenance burden and divergence risk. Extracting to a shared helper ensures consistent behavior across all call sites.

## Steps

1. Add `invoke_index_update(ctx: click.Context) -> None` to `src/fx_alfred/commands/_helpers.py`
2. Replace 2 inline patterns in `src/fx_alfred/commands/create_cmd.py` with `invoke_index_update(ctx)`
3. Replace 1 inline pattern in `src/fx_alfred/commands/update_cmd.py` with `invoke_index_update(ctx)`
4. Add 3 unit tests to `tests/test_helpers.py` (success, failure, preserve-existing)
5. Verify all tests pass + ruff clean

See PRP FXA-2165 for full specification including behavioral contract and test plan.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-01 | Initial version (from PRP FXA-2165) | Frank + Claude |
| 2026-04-01 | CHG FXA-2179: Reconstructed from corrupted state using FXA-2165 as source | Claude Code |
