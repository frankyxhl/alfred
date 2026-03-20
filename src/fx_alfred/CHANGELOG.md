# Changelog

## v0.11.0 (2026-03-20)

### Standardized SOP Section Structure (ALF-2210)
- **SOP template updated** — 5W1H pattern: What Is It?, Why, When to Use, When NOT to Use, Steps
- **`af validate` SOP section checking** — Validates required sections for SOP documents (USR/PRJ layers)
- **COR-1103 updated** — "How to Read an SOP" golden rule + SOP section compliance overlay
- **40 SOPs migrated** — All PKG, USR, PRJ SOPs now have Why, When to Use, When NOT to Use

### Stats
- 246 tests (8 new), all passing
- 86 documents validated, 0 issues

## v0.10.1 (2026-03-20)

### Docs
- **COR-1103** — Added golden rules for COR-1201, COR-1608~1611

## v0.10.0 (2026-03-20)

### Review Scoring Framework (ALF-2208)
- **COR-1608** — PRP Review Scoring rubric (6 weighted dimensions + OQ hard gate)
- **COR-1609** — CHG Review Scoring rubric (5 dimensions, fallback for PLN/ADR)
- **COR-1610** — Code Review Scoring rubric (5 dimensions)
- **COR-1611** — Shared Reviewer Calibration Guide (symmetric rules for all models)
- **COR-1602 updated** — Generic 4-dimension matrix replaced with artifact-specific rubric references
- **COR-1102 updated** — OQ hard gate + stale matrix reference fixed
- **COR-1103 updated** — Scoring rubric added to OVERLAYS

### Stats
- 238 tests, all passing
- 0 breaking changes

## v0.9.1 (2026-03-20)

### Docs
- **COR-1103** — Added USR/PRJ routing doc creation guide

## v0.9.0 (2026-03-20)

### Layered Workflow Routing (ALF-2206)
- **`af guide` enhanced** — Dynamically scans PKG → USR → PRJ for routing documents (`*-SOP-Workflow-Routing*.md`), filters by `Status: Active`, outputs full content per layer with separator headers
- **Quick-start moved** — Document naming, layer system, and create examples now in `af --help` epilog
- **Failure handling** — Graceful handling of missing layers, deprecated docs, malformed docs, and multiple active docs per layer

### Stats
- 238 tests (10 new), all passing
- 0 breaking changes

## v0.8.0 (2026-03-20)

### Workflow Routing (ALF-2205)
- **COR-1103 SOP** — New session-start routing SOP with intent-based router (ALWAYS → PRIMARY ROUTE → OVERLAYS) and golden rules. Replaces COR-1607.
- **COR-1607 deprecated** — Replaced by COR-1103 in the 11xx area
- **COR-1101 fix** — Corrected "use PLN" to "use PRP per COR-1102" in When NOT to Use section

### Stats
- 228 tests, all passing
- 0 breaking changes

## v0.7.0 (2026-03-20)

### Document Format Contract (FXA-2116)
- **COR-0002 Reference** — New document defining mandatory metadata format for all Alfred documents: required fields per type, allowed Status values, optional fields, H1 rules, section rules
- **COR-1607 SOP** — Workflow Routing SOP mapping work types to required SOP sequences
- **Template compliance** — All 7 `af create` templates now emit required fields (Applies to, Last updated, Last reviewed, Status) with correct defaults per type
- **`af validate` enhancements** — Per-type required field checks, Status value validation (rejects invalid values and annotations), ACID=0000 Index document H1 exemption
- **`af index` compliance** — Generated Index documents now include H1, metadata block, and Change History section per contract
- **PKG layer migration** — All 33 COR documents updated with Status field

### Stats
- 228 tests (49 new), all passing
- 0 breaking changes

## v0.6.0 (2026-03-19)

### Internal Improvements
- **DRY scan boilerplate (CHG-1)** — Extracted `scan_or_fail()` and `find_or_fail()` helpers to `commands/_helpers.py`, eliminating 6x repeated try/except blocks across command files
- **Lazy command loading (CHG-2)** — `LazyGroup` subclass loads command modules on demand via `importlib`, removing all eager imports from `cli.py`

### New Features
- **`af list` filtering (CHG-3)** — `--type`, `--prefix`, `--source` options with exact case-insensitive matching and AND logic
- **`--json` output (CHG-4)** — Machine-readable JSON output for `af list`, `af status`, and `af read` commands; combinable with filters
- **`af search` (CHG-5)** — Search document contents with case-insensitive substring matching, shows up to 3 matching lines with line numbers
- **`af validate` (CHG-6)** — Structural health check: validates H1 format, required metadata fields, Change History table, and COR/PKG layer invariant

### Stats
- 179 tests (45 new), all passing
- 0 breaking changes

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
