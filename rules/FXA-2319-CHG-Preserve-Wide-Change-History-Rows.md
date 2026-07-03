# CHG-2319: Preserve Wide Change History Rows

**Applies to:** FXA project
**Last updated:** 2026-07-03
**Last reviewed:** 2026-07-02
**Status:** Completed
**Date:** 2026-07-02
**Requested by:** @frankyxhl via GitHub issue #260
**Priority:** High
**Change Type:** Normal
**Targets:** src/fx_alfred/core/parser.py, src/fx_alfred/commands/fmt_cmd.py, src/fx_alfred/commands/update_cmd.py, src/fx_alfred/commands/tag_cmd.py, tests/test_parser.py, tests/test_fmt_cmd.py, tests/test_update_cmd.py, tests/test_tag_cmd.py
**Closes:** #260

---

## What

Preserve all cells in Change History table rows when Alfred parses and re-renders documents. `af fmt --write`, `af update --history`, and other render paths must not truncate rows that contain columns beyond the canonical Date / Change / By set.


## Why

GitHub issue #260 reports silent data loss: a Change History table with a fourth `PR` column keeps the header but loses row data such as `#123` after `af fmt --write`. The current `HistoryRow` model stores only `date`, `change`, and `by`, while formatter alignment marks rows dirty and forces `render_document` to regenerate rows from those three fields.


## Impact Analysis

- **Systems affected:** document parser history-row model, Change History table alignment in `af fmt`, document render paths used by `af update`, and regression tests.
- **Behavior preserved:** canonical 3-column Change History tables continue to render exactly as before.
- **Behavior fixed:** wider and ragged Change History rows preserve every parsed cell through formatting and update append operations.
- **Existing data limitation:** documents already processed by the buggy `af fmt --write` path may have permanently lost extra-column cell data. This CHG prevents future loss; it cannot reconstruct cells that are no longer present in the file.
- **Append path:** `af update --history` continues to append canonical 3-column rows, while existing wider rows remain intact because rendering uses each row's complete cell list.
- **Tag path:** `af tag add` / `af tag rm` call `render_document` after metadata changes; they must continue to preserve wide Change History rows because they do not dirty history rows.
- **Validation path:** `af validate` continues to require Date, Change, and By header columns. Extra Change History columns remain allowed and must not be treated as invalid.
- **Generated index:** `af index` remains canonical 3-column generated output and is out of scope except for normal index regeneration after this CHG is created or rolled back.
- **Rollback plan:** revert the parser/formatter/test changes and this CHG, then run `af index` to remove the FXA-2319 row from `FXA-0000` if rolling back the CHG document. Documents written by the fixed formatter remain valid Markdown under the old parser, but old-code re-renders would reintroduce the original 3-column truncation behavior.


## Acceptance Criteria

- A1: `parse_metadata` stores the complete list of cells for every Change History data row, including cells beyond Date / Change / By.
- A2: `render_document` preserves a dirty 4-column Change History row without dropping the fourth cell.
- A3: `af fmt --write` preserves a table with header `Date | Change | By | PR` and row cell `#123`, allowing only intended alignment whitespace changes.
- A4: `af fmt --write` preserves ragged rows by padding missing trailing cells without truncating wider rows.
- A5: `af update --history` appends a canonical 3-column row to a wider table; a subsequent `af fmt --write` still preserves every pre-existing extra cell and pads the appended row with empty trailing cells.
- A6: `af tag add` on a document with a wider Change History table preserves all existing history cells.
- A7: Existing canonical 3-column Change History formatting remains stable after an end-to-end `af fmt --write` pass that dirties/aligned rows.
- A8: Escaped pipes in extra columns, such as a fourth-column cell containing `Fix \| pipe`, survive parse, render, and `af fmt --write`.
- A9: Post-implementation `af fmt --check --root /Users/frank/Projects/alfred` does not introduce any new unrelated formatting churn beyond the pre-implementation baseline.


## Implementation Plan

1. Add RED tests:
   - `tests/test_parser.py::test_parse_metadata_history_row_retains_all_cells`
   - `tests/test_parser.py::test_render_document_dirty_wide_history_row_preserves_extra_cells`
   - `tests/test_fmt_cmd.py::test_fmt_write_preserves_wide_history_table_cells`
   - `tests/test_fmt_cmd.py::test_fmt_write_preserves_ragged_history_table_cells`
   - `tests/test_fmt_cmd.py::test_fmt_write_preserves_update_appended_row_in_wide_table`
   - `tests/test_update_cmd.py::test_update_history_append_preserves_existing_wide_rows`
   - `tests/test_tag_cmd.py::test_tag_add_preserves_existing_wide_history_rows`
   - `tests/test_fmt_cmd.py::test_fmt_write_preserves_canonical_three_column_history_table`
   - `tests/test_fmt_cmd.py::test_fmt_write_preserves_escaped_pipe_in_extra_history_cell`
2. Extend `HistoryRow` with `cells: list[str] = field(default_factory=list)` and an `effective_cells` property returning `cells if cells else [date, change, by]`, so parsed rows retain the complete cell list while preserving existing `date`, `change`, `by`, `raw_line`, and `dirty` compatibility fields.
3. Define the cell fallback rule explicitly: when `HistoryRow.cells` is empty, all render and alignment paths MUST use `row.effective_cells`. This keeps existing construction sites such as `af update --history` safe until they are updated to pass cells directly.
4. Define the dirty-row semantic change explicitly: `dirty=True` means "render from the full effective cell list"; `date`, `change`, and `by` remain compatibility aliases for the first three cells.
5. Define the table column-count rule for `normalize_table_alignment`: use `num_cols = max(len(header_cells), max(len(row.effective_cells) for row in rows))`; pad header and short rows with empty trailing cells; never slice a row below its original effective cell count. If a row has more cells than the header, preserve the extra cells by extending the formatted table with empty header cells after the existing header cells, e.g. `| Date | Change | By |  |` for a canonical 3-column header and a 4-column row.
6. Update `parse_metadata` to populate `HistoryRow.cells` for parsed rows, including escaped-pipe behavior already covered by the existing split rule. `cells` stores stripped cell text using the same semantics as existing `date`, `change`, and `by`; escaped pipe text remains escaped.
7. Update `render_document` and `normalize_table_alignment` to read and write full effective row cells whenever rows are dirty or aligned.
8. Keep `update_cmd.py`'s history append construction unchanged (`HistoryRow(date=..., change=..., by=...)`). The new `HistoryRow.effective_cells` fallback provides `[date, change, by]`, and `normalize_table_alignment` pads the appended row when the table has more columns.
9. Update `HistoryRow` comments/docstring to describe `cells`, effective-cell fallback, and dirty rendering from full cells.
10. Confirm `validate_cmd.py` needs no code change because it already validates required header columns without rejecting extra columns.
11. Verify with targeted tests, full pytest, ruff, pyright, and `af validate --root /Users/frank/Projects/alfred`.


## Testing / Verification

- RED: the nine new tests above fail before implementation and demonstrate the #260 truncation path.
- GREEN targeted: `.venv/bin/pytest tests/test_parser.py tests/test_fmt_cmd.py tests/test_update_cmd.py tests/test_tag_cmd.py -q`
- Churn baseline: before and after implementation, run `af fmt --check --root /Users/frank/Projects/alfred`; any changed count must be explained by this CHG or fixed before handoff.
- Full suite: `.venv/bin/pytest -v --tb=short`
- Lint: `.venv/bin/ruff check .`
- Format check: `.venv/bin/ruff format --check .`
- Type check: `.venv/bin/pyright src/`
- Document validation: `af validate --root /Users/frank/Projects/alfred`


## Approval

- [x] COR-1602 / COR-1609 plan review cleared as far as available providers allowed: DeepSeek PASS and MiniMax PASS after revisions; GLM timed out on three consecutive attempts and was treated as unavailable under the FXA-2276 provider-failure path.
- [x] Operator authorized proceeding on 2026-07-03 with a Codex subagent implementation in place of the unavailable GLM worker/reviewer lane.
- [x] Status changed to Approved before GREEN implementation begins.


## Execution Log

| Date | Action | Result |
|------|--------|--------|
| 2026-07-02 | Created CHG and ran R1 plan review. | DeepSeek PASS 9.3; MiniMax FIX 7.8; GLM timed out; revised CHG before implementation. |
| 2026-07-02 | Ran R2 plan review. | DeepSeek FIX 8.1; MiniMax FIX 8.7; GLM timed out; revised column-count, fallback, append-format, tag, validation, and canonical dirty-row coverage. |
| 2026-07-02 | Ran R3 plan review. | DeepSeek PASS 9.2; MiniMax FIX 8.5; GLM timed out for the third time; revised update append path, effective-cells API, ragged-header output, rollback, and index scope. |
| 2026-07-03 | Ran post-R3 two-provider confirmation after GLM retry exhaustion. | DeepSeek PASS 9.3; MiniMax FIX 8.2 due header-extension example; revised example and added escaped-pipe/churn criteria. |
| 2026-07-03 | Operator approved provider-outage exception. | Proceed with Codex subagent implementation; keep GLM outage documented for review. |
| 2026-07-03 | Implemented parser and formatter preservation path. | `HistoryRow.cells` and `effective_cells` now keep full Change History rows; dirty rendering and formatter alignment use complete row cells. |
| 2026-07-03 | Added regression coverage. | Parser, formatter, update, and tag tests cover wide, ragged, canonical, escaped-pipe, append, and idempotent format-check cases. |
| 2026-07-03 | Ran advisory implementation review. | DeepSeek PASS 9.5 and MiniMax PASS with non-blocking advisories; added idempotent update-format assertion after review. |
| 2026-07-03 | Verified implementation. | Targeted pytest 176 passed; full pytest 1383 passed, 2 skipped; ruff check passed; ruff format check passed; pyright src passed. |
| 2026-07-03 | Checked project document baseline. | FXA-2319 fmt and validate pass; project-wide validate retains unrelated FXA-2271 warning and FXA-2315 issue; project-wide fmt check reports pre-existing corpus formatting noise outside #260 scope. |


## Post-Change Review

- Did the fix preserve wide Change History row cells across `af fmt --write` and `af update --history`?
- Did canonical 3-column documents remain stable?
- Any follow-up needed for already-corrupted documents that lost extra-column cells before this fix?

---

## Change History

| Date       | Change                                                                                                                                                        | By    |
|------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|-------|
| 2026-07-02 | Initial version                                                                                                                                               | —     |
| 2026-07-02 | R1 plan-review revisions: added acceptance criteria, verification, approval, execution log, limitations, and full-cell dirty semantics                        | Codex |
| 2026-07-02 | R2 plan-review revisions: defined column-count and fallback rules; added append-format, tag, validate, canonical dirty-row, and escaped-cell coverage         | Codex |
| 2026-07-02 | R3 plan-review revisions: pinned update append behavior, effective-cells property, ragged-header output, rollback/index handling, and stripped-cell semantics | Codex |
| 2026-07-03 | Post-R3 confirmation revisions: clarified canonical header extension and added escaped-pipe and churn acceptance criteria                                     | Codex |
| 2026-07-03 | Approved provider-outage exception and authorized Codex subagent implementation                                                                               | Codex |
| 2026-07-03 | Completed #260 implementation, review, and verification                                                                                                       | Codex |
