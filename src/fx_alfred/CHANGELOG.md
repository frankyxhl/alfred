# Changelog

## v0.5.0 (2026-03-19)

### New Commands
- **`af update`** — Structured metadata updates to existing documents
  - Field updates (`--status`, `--field`): modify existing metadata fields
  - Change History append (`--history`, `--by`): add entries with pipe escaping
  - Document rename (`--title`): changes filename + H1 + auto-indexes
  - Dry run (`--dry-run`): preview changes without writing
  - Atomic writes via temp file for safety
  - PRJ and USR layers only; PKG is read-only
- **`af changelog`** — View this changelog

### New Core Module
- **`core/parser.py`** — Document metadata parser and renderer
  - Supports both `**Key:** value` and `- **Key:** value` metadata formats
  - Round-trip fidelity: preserves formatting of unmodified fields
  - Strict H1 validation against `# <TYP>-<ACID>: <Title>` format

### Code Quality Refactoring
- **`core/source.py`** — Consolidated `Source` type, `SOURCE_LABELS`, `SOURCE_ORDER`, `source_sort_key()`
- **`core/scanner.py`** — Fixed `Traversable` protocol (`iterdir()` returns `Iterator`), removed `read_text()` from `Traversable`
- **`find_document()`** — Moved to core with exception-based API (`DocumentNotFoundError`, `AmbiguousDocumentError`)
- Removed 4 `# type: ignore` comments

### New SOPs (bundled in PKG layer)
- **COR-1102** — Create Proposal (PRP lifecycle)
- **COR-1201** — Discussion Tracking (D item protocol)
- **COR-1602** — Workflow: Multi Model Parallel Review
- **COR-1603** — Workflow: Parallel Module Implementation
- **COR-1604** — Workflow: Competitive Parallel Exploration
- **COR-1605** — Workflow: Sequential Pipeline
- **COR-1606** — Workflow: Selection (decision tree)

### Updated SOPs
- **COR-1200** — Added Step 0 (close D items before retrospective)
- **COR-1600** — Added sequence diagram, iteration mode, review scoring (>=9), Lead Reviewer rule
- **COR-1601** — Added sequence diagram, iteration mode, review scoring

### Documentation
- **README.md** — Added `af update` usage examples and documentation

## v0.4.3 (2026-03-17)

- Added COR-1403/1404/1405 interactive question SOPs
- Improved COR-1200 session retrospective

## v0.4.2 (2026-03-17)

- Test isolation improvements
- `--layer`/`--subdir` support for `af create`
- Docs migration to 3-layer model

## v0.4.0 (2026-03-16)

- `af create` command improvements

## v0.3.4 (2026-03-15)

- `af read` supports PREFIX-ACID format (e.g., `COR-1000`)
