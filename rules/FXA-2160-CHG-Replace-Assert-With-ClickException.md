# CHG-2160: Replace Assert With ClickException

**Applies to:** FXA project
**Last updated:** 2026-03-30
**Last reviewed:** 2026-03-30
**Status:** Proposed
**Date:** 2026-03-30
**Requested by:** —
**Priority:** Medium
**Change Type:** Normal

---

## What

Replace two `assert final_acid is not None` / `assert acid is not None` statements in `fx_alfred/src/fx_alfred/commands/create_cmd.py` (lines 376 and 449) with explicit `click.ClickException` raises.

## Why

Python's `-O` (optimized) flag strips all `assert` statements. Using `assert` for runtime validation means these checks silently disappear in optimized builds, allowing `None` to propagate and cause downstream crashes or incorrect filenames. `click.ClickException` is the correct pattern used elsewhere in the same file.

**Evidence:** Source analysis during Evolve-CLI run FXA-2158. Scored 9.85/10 under Evolve-CLI weights.

## Impact Analysis

- **Systems affected:** `fx_alfred` CLI — `af create` command only
- **Rollback plan:** Revert commit; re-add `assert` statements

## Implementation Plan

1. Write failing tests that verify `ClickException` is raised when ACID resolution returns `None`
2. Replace `assert final_acid is not None` (line 376) with `if final_acid is None: raise click.ClickException(...)`
3. Replace `assert acid is not None` (line 449) with `if acid is None: raise click.ClickException(...)`
4. Run pytest + ruff to verify

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-30 | Initial version | — |
