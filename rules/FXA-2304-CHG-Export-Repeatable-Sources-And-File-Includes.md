# CHG-2304: Export Repeatable Sources And File Includes

**Applies to:** FXA project
**Last updated:** 2026-06-12
**Last reviewed:** 2026-06-12
**Status:** In Progress
**Date:** 2026-06-12
**Requested by:** Frank Xu (first real use of af export, 2026-06-12)
**Priority:** Medium
**Change Type:** Normal
**Targets:** src/fx_alfred/commands/export_cmd.py; tests/test_export_cmd.py; rules/FXA-2303 (history row)

---

## What

Two v1.1 amendments to `af export` (PRP-2303), driven by its first real usage request — "export this project's PRJ SOPs plus the COR SOPs, with the README, as one shareable file":

1. **`--source` and `--type` become repeatable** (OR within the dimension, AND across dimensions — `--source pkg --source prj` selects both layers and excludes USR). PRP-2303 chose single-value filters "matching af list semantics" for v1; the very first real invocation needed the one combination single-value cannot express, and it is precisely the privacy-relevant one (share project + bundled docs WITHOUT the personal USR layer).
2. **`--include PATH` (repeatable)**: appends arbitrary project text files (e.g. `README.md`) after the documents, each under a distinct `FILE:` delimiter (`═══ FILE: <relpath> ═══`), listed in the Contents table (`<relpath>  FILE  -  -  <relpath>`), read UTF-8 relative to the export root (absolute paths allowed), skip-with-warning on read failure (same policy as documents), counted in the stderr summary (`+ N files`), and triggering the review-before-sharing warning (attached files are project content).


## Why

PRP-2303 R1 (minimax, Necessity): "necessity… not externally validated by an observed hand-off; a follow-up can record the first real use." This CHG is that record: the first real hand-off required (a) PKG+PRJ-without-USR in one deterministic artifact and (b) the project README riding along so the recipient gets context, not just procedures. Two-invocation concatenation works but produces two headers/Contents tables and loses the single-artifact guarantee.


## Out of Scope

- Whole-directory/tarball packaging (binary files, exclusion rules — different feature; `--include` covers the named-files need).
- Repeatable `--status`/`--prefix`/`--tag` (no observed need; string-valued dimensions).
- Globbing in `--include` (explicit paths only in v1.1).


## Acceptance Criteria

- A1: `af export --source pkg --source prj` selects both layers, excludes USR; repeated `--type` analogous; single-value usage byte-identical to v1.
- A2: `--include README.md` renders the file verbatim under `FILE:` delimiter, in Contents, in summary count, in CLI argument order; missing/unreadable include → ⚠ skip warning, export continues.
- A3: Includes trigger the review-before-sharing stderr warning.
- A4: Determinism preserved; existing 27 export tests pass unmodified except none require changes; full gates.


## Implementation Plan

1. `multiple=True` on `--source`/`--type`; gates become sets.
2. `--include` loading + rendering + contents + summary.
3. Tests (+6); delta panel review (triad) on the PR #201 increment; PRP-2303 history row.

---

## Change History

| Date       | Change                                                             | By               |
|------------|--------------------------------------------------------------------|------------------|
| 2026-06-12 | Initial version — first-real-use amendments to PRP-2303 v1 surface | Claude (Fable 5) |
