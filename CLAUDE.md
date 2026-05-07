# CLAUDE.md — Alfred: Agent Runbook (af CLI)

## Project

- **Package:** fx-alfred v1.8.0
- **Description:** Alfred — Agent Runbook: workflow routing, SOP checklists, and document management
- **Language:** Python 3.10+, Click 8.0+
- **Entry point:** `af = fx_alfred.cli:cli`
- **Source:** `src/fx_alfred/`
- **Tests:** `tests/` (pytest)

## Commands

```
af guide [--root DIR] [--json]              # workflow routing (PKG → USR → PRJ)
af plan SOP_ID [...] [--root DIR] [--json]  # LLM-optimized workflow checklist from SOPs
af plan --human SOP_ID [...]                # human-readable checklist
af setup                                    # suggested prompts for agent config
af list [--type TYPE] [--prefix PREFIX] [--source SOURCE] [--tag TAG] [--json]
af read IDENTIFIER [--json]                 # read by PREFIX-ACID or ACID only
af create [TYPE] --prefix PREFIX --acid ACID|--area AREA --title TITLE [--layer project|user] [--subdir] [--spec FILE] [--dry-run]
af update IDENTIFIER [--status] [--field KEY VALUE] [--history TEXT] [--by TEXT] [--title TEXT] [--dry-run] [-y] [--spec FILE]
af where IDENTIFIER [--json]               # print absolute file path of a document
af fmt [DOC_IDS...] [--write] [--check]     # format documents to canonical style
af search PATTERN [--json]                  # case-insensitive content search
af validate [--root DIR] [--json]           # structural correctness checks
af status [--json]                          # document counts by source/type/prefix
af index                                    # regenerate PRJ layer index
af changelog                                # show version changelog
```

## Architecture

```
src/fx_alfred/
├── cli.py              # LazyGroup entry point (zero eager imports)
├── lazy.py             # LazyGroup class (importlib on demand)
├── context.py          # --root option, get_root()
├── commands/
│   ├── _helpers.py     # scan_or_fail(), find_or_fail()
│   ├── guide_cmd.py    # workflow routing (layered PKG→USR→PRJ)
│   ├── plan_cmd.py     # workflow checklist from SOPs
│   ├── setup_cmd.py    # agent configuration prompts
│   ├── list_cmd.py     # list + filtering + --json
│   ├── read_cmd.py     # read + --json
│   ├── create_cmd.py   # create from template or spec
│   ├── update_cmd.py   # metadata/history/rename updates; --spec FILE
│   ├── fmt_cmd.py      # format to canonical style (metadata order, whitespace, table align)
│   ├── where_cmd.py    # find absolute file path of a document (--json)
│   ├── search_cmd.py   # content search
│   ├── validate_cmd.py # metadata + status + SOP section validation
│   ├── status_cmd.py   # summary counts + --json
│   ├── index_cmd.py    # regenerate document index (COR-0002 compliant)
│   └── changelog_cmd.py
├── core/
│   ├── document.py     # Document dataclass, FILENAME_PATTERN
│   ├── parser.py       # parse_metadata(), render_document(), extract_section()
│   ├── scanner.py      # scan_documents(), find_document(), layer validation
│   ├── schema.py       # DocType/DocRole enums, ALLOWED_STATUSES, REQUIRED_METADATA/SECTIONS
│   ├── normalize.py    # slugify(), sort_metadata(), normalize_date(), strip_trailing_whitespace()
│   └── source.py       # Source type, SOURCE_LABELS, SOURCE_ORDER
├── rules/              # PKG layer (bundled COR-* documents, read-only)
└── templates/          # Document templates for af create (5W1H SOP template)
```

## Three-Layer Document Model

| Layer | Location | Source | Writable |
|-------|----------|--------|----------|
| PKG | Bundled in package (`rules/`) | `pkg` | No |
| USR | `~/.alfred/` (recursive) | `usr` | Yes |
| PRJ | `./rules/` in project root | `prj` | Yes |

## Document Filename Format

```
<PREFIX>-<ACID>-<TYP>-<Title-With-Hyphens>.md
  FXA   -2134 -PRP -AF-Plan-Command-Workflow-Checklist.md
```

## Essential Commands

```bash
# Dev
.venv/bin/pytest -v --tb=short        # run tests
.venv/bin/ruff check .                 # lint
.venv/bin/ruff format --check .        # format check

# Install (editable)
pip install -e .

# Alfred ops (project documents — in top-level rules/)
af guide --root /Users/frank/Projects/alfred
af validate --root /Users/frank/Projects/alfred
af list --root /Users/frank/Projects/alfred
```

## Key Design Patterns

- **scan_or_fail(ctx)** / **find_or_fail(docs, id)** — all commands use these helpers from `_helpers.py`
- **LazyGroup** — cli.py imports zero command modules at startup; all loaded on demand via `importlib`
- **core/ is framework-agnostic** — no Click imports in `core/`; Click dependency lives in `commands/`
- **Atomic writes** — `update_cmd` uses tempfile + os.replace for safe file updates
- **extract_section(body, heading)** — reusable section extraction in `parser.py`

## Key COR SOPs (PKG layer)

| SOP | Purpose |
|-----|---------|
| COR-1103 | Workflow Routing — intent-based router + golden rules |
| COR-0002 | Document Format Contract — metadata rules, status values |
| COR-1102 | Create Proposal (PRP lifecycle) |
| COR-1101 | Submit Change Request (CHG) |
| COR-1500 | TDD Development Workflow |
| COR-1602 | Multi-Model Parallel Review |
| COR-1608/1609/1610 | Review Scoring (PRP/CHG/Code rubrics) |
| COR-1611 | Reviewer Calibration Guide |
| COR-1613 | Council Review — decision-mechanism contract for multi-reviewer negotiation |
| COR-1503 | Diagnose Feedback Loop — 6-phase bug/perf diagnosis with enforcement gates |

## Active PRPs (Draft)

| ACID | Title | Dependency |
|------|-------|-----------|
| FXA-2117 | AF Filter + Section Update | FXA-2116 (done) |
| ALF-2203 | Multi-CHG Implementation Workflow | None |

## Workflow

- **Session start:** Run COR-1208 (Session Startup Sanity Check — `pwd`, `git status`/`log`, smoke test, load tracker, surface anomalies) before anything else. Then `af guide --root /Users/frank/Projects/alfred/fx_alfred`. Smoke for this project: `.venv/bin/pytest -v --tb=short` and `af validate --root /Users/frank/Projects/alfred/fx_alfred`.
- **Before every task:** Declare active SOP per COR-1402 before starting work (or flag if none exist)
- **Workflow checklist:** `af plan <SOP_IDs>` (LLM-optimized, follow each phase)
- **First time:** `af setup` (suggested prompts for agent config)
- **Workflow branches:** SOPs can declare `Workflow branches:` metadata to express branching task flows (e.g., "do EITHER A or B"). `af plan --graph` renders these as ASCII/Mermaid branch diagrams. Branch targets use step indices; sub-steps use `{phase}.{step}{letter}` notation (e.g., `3.1a`).
- **Routing:** COR-1103 (PKG) → ALF-2207 (USR) → FXA-2125 (PRJ)
- All code changes go through `/trinity` dispatch (GLM = Worker, Codex/Gemini = Reviewer)
- TDD mandatory: COR-1500 (Red-Green-Refactor)
- Code review: COR-1602 + COR-1608/1609/1610 rubrics + COR-1611 calibration (both >= 9.0 to pass)
- Release: FXA-2102 SOP + FXA-2136 README check (GitHub Actions → PyPI)
- Documents: always `af create`, never manual files
- Documents live in top-level `rules/` (PRJ layer)
