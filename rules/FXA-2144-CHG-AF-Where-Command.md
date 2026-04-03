# CHG-2144: AF Where Command

**Applies to:** FXA project
**Last updated:** 2026-03-22
**Last reviewed:** 2026-03-22
**Status:** Completed
**Date:** 2026-03-22
**Requested by:** Frank
**Priority:** Medium
**Change Type:** Normal

---

## What

Add a new `af where IDENTIFIER` command that prints the absolute file path of any Alfred document to stdout.

```bash
af where FXA-2107
# → /Users/frank/.../rules/FXA-2107-CHG-Code-Quality-Refactoring.md

af where FXA-2107 --json
# → {"doc_id": "FXA-2107", "path": "/...", "source": "prj", "filename": "FXA-2107-CHG-....md"}
```


## Why

Users and agents often need to open, edit, or pass the raw file to other tools (editors, linters, scripts), but there is no way to find the file path from the document identifier. Currently the only option is to grep the filesystem manually.

`af where FXA-2107` is composable: `vi $(af where FXA-2107)`, `open $(af where FXA-2107)`.


## Impact Analysis

- **Systems affected:** `cli.py` (new lazy entry), new `where_cmd.py`
- **Breaking changes:** None — additive new command
- **Rollback plan:** Remove `where_cmd.py` and its `cli.py` entry


## Implementation Plan

1. Create `src/fx_alfred/commands/where_cmd.py`
   - `@click.command("where")`
   - Argument: `identifier` (required)
   - Option: `--json` (output JSON object)
   - Default: print absolute path to stdout (one line)
   - JSON schema: `{"doc_id": "PREFIX-ACID", "path": "...", "source": "prj|usr|pkg", "filename": "..."}`
   - Reuse `scan_or_fail` + `find_or_fail` from `_helpers.py`
2. Register in `cli.py` lazy_subcommands
3. Add tests in `tests/test_where_cmd.py`
   - `test_where_prints_path` — output contains the filename
   - `test_where_by_acid_only` — `af where 2107` works
   - `test_where_json_output` — JSON has correct keys and values
   - `test_where_unknown_id_fails` — exit nonzero on unknown ID
   - `test_where_pkg_layer` — works for PKG layer docs too


---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-22 | Initial version | — |
| 2026-03-22 | R3 review: Codex 9.24/10 PASS, Gemini 9.65/10 PASS. Merged. | Claude |
| 2026-03-22 | R3 PASS (Codex 9.24/10, Gemini 9.65/10). Merged and released in v1.1.0. | Claude Code |
