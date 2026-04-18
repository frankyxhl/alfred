# Changelog

## v1.6.0 (2026-04-18)

Major feature release: `af plan` gains auto-composition (`--task`), flat TODO (`--todo`), and graph output (`--graph`) with both terminal-friendly ASCII and GitHub/Obsidian-ready Mermaid. Three new SOP metadata fields (`Task tags`, `Workflow loops`, `Always included`) drive auto-composition and loop visualisation. New PKG SOP **COR-1202: Compose Session Plan** gives every user an ID-addressable entry point for the full session-workflow pattern.

### New

- **`af plan --task "<description>"`** — auto-compose the set of SOPs for a task from its one-sentence description using deterministic tag matching + always-included baseline. No LLM. Explicit positional IDs still work (union/normalise). Fail-closed on true dependency cycles; exits 2 with diagnostic on empty tag match. (FXA-2205 / PR #46)
- **`af plan --todo`** — emit a single continuously-numbered TODO list across all composed SOPs with `[SOP-ID]` provenance on every item, stable `{phase}.{step}` numbering, `⚠️ gate` markers, and `🔁 loop-start` / `🔁 back to N.M (max K)` loop markers. Mutually compatible with `--human` and `--json`. (FXA-2205 / PR #44)
- **`af plan --graph`** — emit a flowchart of the composed plan. Default `--graph-format=both` prints an ASCII box-and-arrow diagram (terminal-friendly, Unicode-width aware) followed by a fenced Mermaid block (GitHub / Obsidian / mermaid.live). `--graph-format=ascii` or `--graph-format=mermaid` pick one. JSON output adds `ascii_graph` + `graph_mermaid` keys. (FXA-2205 PR #45 / FXA-2206 PR #47)
- **`Workflow loops:` SOP metadata** — optional list of intra-SOP back-edges `[{id, from, to, max_iterations, condition}]`. Renders as dashed back-edges in Mermaid, `◄──┐ / ─────┘ max N` in ASCII, and `🔁 back to N.M (max K)` in TODO. `core/workflow.validate_loops()` enforces back-edge-only (`from > to`), positive `max_iterations`, and in-range step indices. (FXA-2205 / PR #43)
- **`Task tags:` SOP metadata** — optional list of keywords used by `--task` auto-matching. Free-form; advisory lint warning planned for singletons. Backfilled on COR-1500/1602/1608/1609/1610/1611 and FXA-2148/2149 as the pilot corpus. (FXA-2205 / PR #46, FXA-2206 / PR #47)
- **`Always included: true` SOP metadata** — optional boolean for SOPs that must be pulled into every `--task` composition (session baseline). Backfilled on COR-1103 (routing) and COR-1402 (declare-active-SOP). (FXA-2205 / PR #43)
- **`core/ascii_graph.py`** — new pure-stdlib ASCII box-and-arrow renderer with Unicode visual-width handling (CJK, emoji, variation selectors) and balanced-width-invariant test. (FXA-2206 / PR #47)
- **`core/phases.py`** — new shared `PhaseDict` / `StepDict` / `LoopDict` `TypedDict` contracts, formalising what was previously an implicit shape between `render_mermaid` and `_build_mermaid_phases`. `PhaseDict` uses `total=False` to keep legacy builders typecheckable. (FXA-2206 / PR #47)
- **COR-1202: Compose Session Plan SOP** — new PKG SOP giving every user a named, ID-addressable procedure for `af plan --task … --todo --graph`. Users can say "follow COR-1202" and get a complete session workflow plan. Includes 7 Steps, 3 worked Examples with expected output, and tag-gap recovery flow. (FXA-2207 / PR #48)
- **COR-1103 intent-router cross-reference** — routes "show me the plan" / "compose session plan" intents to COR-1202; disambiguates from the generic `af plan <SOP_IDs>` manual-checklist bullet. (FXA-2207 / PR #48)

### Fixed

- **Compose resolver**: `resolve_sops_from_task` now passes `workflow_edges` to `compose_order`, so Kahn's topological sort actually uses `Workflow input`/`Workflow output` metadata instead of always falling through to the layer+ASCII tiebreak. (FXA-2205 / PR #46)
- **Compose empty-match check**: now keyed on `tag_cands` + `positional_set`, not `candidates == always_set`; previously an always-included SOP that also had a matching `Task tags` entry would wrongly trigger exit 2. (FXA-2205 / PR #46, bot P2)
- **Compose positional IDs**: `--task` mode now accepts ACID-only IDs via `core.scanner.find_document` (normalised to PREFIX-ACID), matching the legacy `af plan <id>` semantics. (FXA-2205 / PR #46, bot P2)
- **ASCII renderer** inter-phase border off-by-one: `└─┬─┘` separator line previously rendered at `box_width + 1`. (FXA-2206 / PR #47)
- **ASCII renderer** `⚠️` visual width: `_visual_width` now treats `0x2600-0x27BF` (Misc Symbols + Dingbats) as 2 cells and `0xFE00-0xFE0F` (variation selectors) as 0. Gate step right borders now align. (FXA-2206 / PR #47)
- **`af plan --graph-format=mermaid`**: byte-identical to pre-v1.6 `af plan --graph` output, preserving backward-compat for scripted consumers. (FXA-2206 / PR #47)
- **`af plan`** no longer crashes on SOPs with malformed `Workflow loops` metadata; `parse_workflow_signature` and `parse_workflow_loops` now share the `MalformedDocumentError` warn-and-skip path with `parse_metadata`. (FXA-2205 / PR #44, bot P2)
- **`af plan --todo` marker composition**: gate / loop-start / loop-back markers are now independently composable rather than mutually exclusive. A step that is both a gate and a loop endpoint no longer silently loses its loop annotation. JSON `loop_marker ∈ {null, "loop-start", "loop-back"}` (gate is its own `gate: bool` field). (FXA-2205 / PR #44)
- **`af plan --json` contract**: `workflow_provides` for untyped phases is `[]` (list), not `""` (string); restores type stability. (FXA-2205 / PR #44)

### Improvements

- `Composed from:` header in the flat-TODO and default views now shows provenance markers `(always)` / `(auto)` / `(explicit)` next to every SOP ID. JSON output adds a `composed_from: {always, auto, explicit}` key when `--task` is used.
- Deterministic composition order: Kahn's topological sort with `(layer: PKG→USR→PRJ, then SOP-ID ASCII)` tiebreak guarantees same task + same corpus → same output bytes.
- `af plan` documentation in COR-1103 routing now explicitly distinguishes manual `af plan <SOP_IDs>` (targeted checklist) from the new COR-1202 auto-compose path (full session plan).

### Stats

- 660 tests (80+ new since v1.5.0), all passing
- `core/ascii_graph.py`, `core/compose.py`, `core/mermaid.py`, `core/phases.py` all new modules; 95%+ coverage on each
- 0 new runtime dependencies (still `click` + `pyyaml`)
- 0 breaking changes

### Install / Upgrade

```bash
pip install fx-alfred==1.6.0      # install specific version
pipx install fx-alfred             # first install
pipx upgrade fx-alfred             # upgrade existing
```

## v1.1.0 (2026-03-22)

### New

- `af where IDENTIFIER [--json]` — Print the absolute filesystem path of any document. Composable with shell tools: `vi $(af where FXA-2107)`. JSON output includes `doc_id`, `path`, `source`, `filename`. (FXA-2144)
- `af fmt [DOC_IDS...] [--write] [--check]` — Format documents to canonical style: normalize metadata order, whitespace, and table alignment. `--check` exits 1 if any changes needed (CI-friendly). (FXA-2140)
- `af create --spec FILE` — Spec-driven document creation: pass a YAML/JSON file for batch metadata and section content. (FXA-2143)
- `af update --spec FILE` — Spec-driven batch updates: update metadata fields and section content from a spec file. (FXA-2143)

### Improvements

- `af validate` — Schema-driven validation via new `core/schema.py`: DocType/DocRole enums, per-type `ALLOWED_STATUSES`, `REQUIRED_METADATA`, and `REQUIRED_SECTIONS`. Catches status violations and missing SOP sections precisely.
- `core/normalize.py` — Extracted `slugify()`, `sort_metadata()`, `normalize_date()`, `strip_trailing_whitespace()` as reusable utilities.
- COR-1103 — Golden Rules updated: added COR-1606 (select workflow before multi-agent work), clarified COR-1500 as TDD overlay, added standalone PLN route (branch 4, branches renumbered to 8). Sequence diagram simplified to linear flow.

### Stats

- 374 tests (108 new), all passing
- 0 breaking changes

## v1.0.6 (2026-03-22)

### New

- COR-1004 — New PKG SOP: Create Routing Document. Standardizes language (COR-1401), required sections (PRJ/USR), and decision tree format (ASCII + Mermaid) for all routing documents.

### Improvements

- COR-1103 — Clarified `af plan` ALWAYS rule: per-response decision (not just session-start). Before every response, decide if task needs a checklist; if task has clear steps or spans multiple SOPs, run `af plan <SOP_IDs>` before proceeding.
- COR-1103 — Reduced "Creating Routing Documents" section to a pointer to COR-1004.
- COR-0002 — Added `## Language` section referencing COR-1401 (all documents must be written in English).
- COR-1102, COR-1600–1605 — Updated `/team` references to `/trinity` (skill rename).

### Fixes

- `__init__.py` — Removed stale `__version__ = "0.5.0"` (version is read from package metadata).

## v1.0.5 (2026-03-22)

### Improvements

- `af setup` — All options now say "every time you are about to do a task" (not just session start)
- `af guide` — Tip updated: "Run this before EVERY task to route correctly"
- `ruff format` — Applied to list_cmd, read_cmd, status_cmd (previously uncommitted)

## v1.0.4 (2026-03-21)

### Improvements

- FXA-2102 Release SOP — Added `ruff format --check` to prerequisites
- `plan_cmd.py` — Applied ruff format

## v1.0.3 (2026-03-21)

### Improvements

- COR-1103 — Added workflow sequence diagram (session lifecycle visualization)
- COR-1103 — Added `af plan` to ALWAYS section (session-start checklist)
- COR-1103 — New overlay: "New SOP/doc created → review via COR-1600"
- CLAUDE.md updated to v1.0.2

## v1.0.2 (2026-03-21)

### Improvements

- Renamed to **Alfred — Agent Runbook** (replaces "Alfred Document System")

## v1.0.1 (2026-03-21)

### Improvements

- `af setup` — New standalone command for agent configuration prompts (replaces `af plan --init`)
- `af guide` tip updated to reference `af setup`

## v1.0.0 (2026-03-21)

### First Stable Release

Alfred v1.0.0 marks the completion of the core document management and AI agent workflow system.

### Highlights

- **11 CLI commands** — list, read, create, update, search, validate, status, index, guide, plan, changelog
- **Three-Layer Model** — PKG (bundled COR SOPs) → USR (personal preferences) → PRJ (project-specific)
- **`af guide`** — Dynamic three-layer workflow routing with intent-based decision tree
- **`af plan`** — LLM-optimized workflow checklists from SOPs (3 modes: default, --human, --init)
- **`af validate`** — Metadata format, per-type Status values, SOP section structure checking
- **Review Scoring Framework** — COR-1608/1609/1610 rubrics + COR-1611 calibration guide
- **40+ SOPs standardized** — 5W1H pattern (What, Why, When, When NOT, How)
- **README** — Logo, Mermaid diagrams, complete documentation

### Stats

- 262 tests, all passing
- 86+ documents, 0 validation issues
- 10 new COR SOPs (COR-0002, 1103, 1608-1611, plus updates)

### Install

```bash
pip install fx-alfred==1.0.0
pipx install fx-alfred
pipx upgrade fx-alfred
```

## v0.12.0 (2026-03-21)

### New Command: `af plan` (FXA-2134)
- **`af plan SOP_ID [...]`** — LLM-optimized workflow checklist with phases, hard stops, and RULES
- **`af plan --human`** — Human-readable format
- **`af plan --init`** — Suggested prompts for agent configuration
- **`extract_section()`** — New parser utility for section extraction
- **`af guide`** — Appends `af plan --init` tip

### Stats
- 262 tests (10 new), all passing

## v0.11.1 (2026-03-21)

### Bugfix
- **`af validate`** — Fixed SOP section detection to use exact heading match (`^## Section\s*$`). Prevents false passes on prefix headings like `## Why This Matters`.
- 6 new false-positive regression tests (252 total)

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
