# PRP-2141: AF Fmt Command

**Applies to:** FXA project
**Last updated:** 2026-03-22
**Last reviewed:** 2026-03-22
**Status:** Implemented
**Related:** FXA-2140, COR-0002
**Reviewed by:** Codex (9.6/10), Gemini (10.0/10)

---

## What Is It?

A new `af fmt` command that automatically normalizes Alfred document formatting without changing semantic content. It fixes metadata key ordering, trailing whitespace, blank line counts, and Change History table alignment. Provides a `--check` mode for CI gates and a `--write` mode for in-place repair.

**Prerequisite:** FXA-2140 (core/schema.py + core/normalize.py) must be implemented first. `af fmt` depends on `schema.py` for canonical metadata field order.

---

## Problem

Documents drift from the format contract (COR-0002) over time through manual edits, agent writes, and incremental `af update` calls:

- Metadata fields appear in non-canonical order (e.g., `Status` before `Last updated`)
- Trailing whitespace accumulates in metadata and prose sections
- Blank lines before/after headings are inconsistent
- Change History table columns have uneven widths

Currently, `af validate` reports these issues but does not fix them. Fixing them manually is tedious and blocks commits. The parser already supports round-trip reads that preserve original formatting where unchanged — this makes a safe auto-fix command feasible via the `dirty` flag mechanism.

---

## Scope

**In scope (v1):**
- Metadata field ordering (canonical order per `DocType` from `schema.py`)
- Trailing whitespace on metadata lines only (not document body — see Safety section)
- Blank line normalization (single blank line between sections, two before H2)
- Change History table column width alignment
- `--check` mode: print diff, exit non-zero if any changes would be made (CI gate)
- `--write` mode: apply changes in-place
- Default (no flag): print diff to stdout, exit 0

**Out of scope (v1):**
- Semantic content changes (status values, section content, titles)
- Adding missing required sections (that is `af validate`'s job)
- H1 slug normalization or filename rename (slug repair requires separate design)
- Format changes to COR-0002 itself
- USR or PKG layer documents (PRJ layer only by default)

---

## Proposed Solution

### Command signature

```bash
af fmt [DOC_ID ...] [--write] [--check] [--root ROOT]
```

### Options

| Option | Description |
|--------|-------------|
| `DOC_ID ...` | One or more document IDs (e.g. `FXA-2140`). If omitted, formats all documents in PRJ layer. |
| `--write` | Apply changes in-place. Without this flag, output diff to stdout only. |
| `--check` | Report what would change and exit non-zero if any changes needed. For CI. Cannot combine with `--write`. |
| `--root ROOT` | Project root (same as other commands). |

### Document discovery (when no DOC_ID given)

When `DOC_ID` is omitted, fmt scans the PRJ layer using the scanner, filtered to documents where `source == Source.PRJ`. This is the same mechanism used by `af validate` and `af list`. PKG and USR layers are excluded.

### Parser integration — dirty flag mechanism

`af fmt` modifies documents through the existing parser round-trip, not by string replacement. The workflow for each document:

1. Parse document into `ParsedDocument` (with `MetadataField` objects, `body`, `history_rows`, etc.)
2. For each `MetadataField` that needs reordering: set `field.dirty = True` and update `field.value` if needed
3. For blank line normalization and table alignment: modify `blank_after_h1`, `blank_after_metadata`, and `history_rows` directly
4. Call `render_document()` — dirty fields are re-rendered, unmodified fields preserve their `raw_line`
5. Compare rendered output to original; if identical, document is already formatted

This ensures only modified fields are rewritten, preserving all other formatting.

### Safety specification for whitespace normalization

**Metadata section only:** trailing whitespace is stripped from `MetadataField.value` strings before marking dirty. Body content is **not** touched.

**Body content is excluded from all whitespace normalization** because (fence-aware rule):
- Blank-line normalization at section boundaries must be fence-aware: lines inside fenced code blocks (between ` ``` ` delimiters) are never treated as section headings, even if they start with `##`. The normalizer tracks fence state and skips all normalization inside fenced blocks.

Additionally:
- Code blocks (indented or fenced) use whitespace semantically
- Nested lists depend on indentation
- Blockquotes use leading `>` which may have trailing spaces

The only body modification in v1 is blank line normalization at section boundaries (between `##` headings), which is safe because headings are detected by line-start pattern, not by indentation.

### Idempotence requirement

Running `af fmt --write` twice on the same document must produce identical output. This is tested explicitly (see Testing section).

### Behaviors

**Default (no flag):**
```
$ af fmt FXA-2140
--- FXA-2140 (before)
+++ FXA-2140 (after)
@@ -3,4 +3,4 @@
-**Status:** Draft
-**Last updated:** 2026-03-22
+**Last updated:** 2026-03-22
+**Status:** Draft
1 document(s) would be changed.
```

**`--check` (for CI/pre-commit):**
```
$ af fmt --check
FXA-2140: metadata order
FXA-2133: trailing whitespace (3 lines)
2 document(s) need formatting. Run `af fmt --write` to fix.
Exit code: 1
```

**`--write`:**
```
$ af fmt --write FXA-2140
FXA-2140: fixed metadata order
1 document(s) updated.
```

**No changes needed:**
```
$ af fmt --check FXA-2141
All documents already formatted.
Exit code: 0
```

### Error handling

- Document not found: print error, skip, continue with remaining
- Parser error (malformed document): print error, skip, do not write
- `--check` and `--write` together: exit with usage error immediately
- Explicit `DOC_ID` points to a PKG-layer document: print warning (`"FXA-0000 is in the read-only PKG layer, skipping."`), skip, continue

---

## Open Questions

_All resolved._

1. ~~Should `af fmt` without arguments default to PRJ layer only, or all three layers?~~
   **Resolved:** PRJ layer only by default. PKG is read-only and would fail; USR is personal and potentially risky to bulk-format.

2. ~~Should blank line normalization be configurable?~~
   **Resolved:** Fixed rule per COR-0002. No configuration.

3. ~~Should `af fmt --write` update the `Last updated` metadata field?~~
   **Resolved:** No. Formatting is not a semantic change.

---

## Implementation Plan

0. **Prerequisite:** Confirm FXA-2140 (`core/schema.py`, `core/normalize.py`) is implemented and merged
1. Add formatters to `core/normalize.py` (from FXA-2140): `order_metadata()`, `strip_trailing_whitespace_from_metadata()`, `normalize_blank_lines()`, `align_table_columns()`
2. Add `commands/fmt_cmd.py` with `fmt_cmd` Click group
3. Register `fmt` in `cli.py` lazy subcommands
4. Implement document discovery (PRJ-layer scan via scanner when no DOC_ID)
5. Implement parser round-trip: parse → mark dirty fields → render → diff
6. Add `--check` logic (diff output, exit code 1 if changes needed)
7. Add `--write` logic (in-place write via parser round-trip)
8. Add unit tests:
   - Each normalizer function in isolation
   - Default/check/write modes
   - No-op case (already formatted document)
   - **Idempotence test: run --write twice, assert identical output**
   - Code blocks preserved (whitespace inside fenced blocks unchanged)
   - Discovery with no DOC_ID (finds all PRJ docs)

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-22 | Initial version | Frank + Claude Code |
| 2026-03-22 | Round 1 revision: remove H1 slug from scope/problem, add FXA-2140 as explicit prerequisite, add parser dirty-flag mechanism section, add body whitespace safety specification, add document discovery specification, add idempotence requirement | Frank + Claude Code |
| 2026-03-22 | Round 2 approved (Codex 9.6, Gemini 10.0). Advisory: add fence-aware rule to safety spec, PKG-layer skip warning to error handling | Frank + Claude Code |
| 2026-03-22 | Round 3 approved (Codex 9.27, Gemini 9.9). Fixes: rendered-output truth as change detector; id() identity comparison for metadata reorder; false-positive elimination for duplicate keys and aligned tables. Status → Implemented | — |
