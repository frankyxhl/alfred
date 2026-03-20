# CLAUDE.md — fx-alfred (af CLI)

## Project

- **Package:** fx-alfred v0.9.1
- **Language:** Python 3.10+, Click 8.0+
- **Entry point:** `af = fx_alfred.cli:cli`
- **Source:** `src/fx_alfred/`
- **Tests:** `tests/` (238 tests, pytest)

## Commands

```
af list [--type TYPE] [--prefix PREFIX] [--source SOURCE] [--json]
af read IDENTIFIER [--json]
af create TYPE --prefix PREFIX --acid ACID|--area AREA --title TITLE [--layer] [--subdir]
af update IDENTIFIER [--status] [--field KEY VALUE] [--history] [--title] [--dry-run]
af search PATTERN
af validate
af status [--json]
af index
af guide [--root]                                                        # workflow routing (PKG → USR → PRJ)
af changelog
```

## Architecture

```
src/fx_alfred/
├── cli.py              # LazyGroup entry point (zero eager imports)
├── lazy.py             # LazyGroup class (importlib on demand)
├── context.py          # --root option, get_root()
├── commands/
│   ├── _helpers.py     # scan_or_fail(), find_or_fail()
│   ├── list_cmd.py     # list + filtering + --json
│   ├── read_cmd.py     # read + --json
│   ├── create_cmd.py   # create from template
│   ├── update_cmd.py   # metadata/history/rename updates
│   ├── search_cmd.py   # content search
│   ├── validate_cmd.py # structural health check
│   ├── status_cmd.py   # summary counts + --json
│   ├── index_cmd.py    # regenerate document index
│   ├── guide_cmd.py    # workflow routing (layered PKG→USR→PRJ)
│   └── changelog_cmd.py
├── core/
│   ├── document.py     # Document dataclass, FILENAME_PATTERN
│   ├── parser.py       # parse_metadata(), render_document(), H1_PATTERN
│   ├── scanner.py      # scan_documents(), find_document(), layer validation
│   └── source.py       # Source type, SOURCE_LABELS, SOURCE_ORDER
├── rules/              # PKG layer (bundled COR-* documents, read-only)
└── templates/          # Document templates for af create
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
  FXA   -2106 -PRP -AF-CLI-Optimization-v0.6.md
```

## Essential Commands

```bash
# Dev
.venv/bin/pytest -v --tb=short        # run tests
.venv/bin/ruff check .                 # lint
.venv/bin/ruff format --check .        # format check
.venv/bin/pyright src/                 # typecheck
make check                             # all of the above

# Install (editable)
make install

# Alfred ops (project documents)
af list --root /Users/frank/Projects/alfred/alfred_ops
af read FXA-2106 --root /Users/frank/Projects/alfred/alfred_ops
```

## Key Design Patterns

- **scan_or_fail(ctx)** / **find_or_fail(docs, id)** — all commands use these helpers from `_helpers.py`, never raw try/except
- **LazyGroup** — cli.py imports zero command modules at startup; all loaded on demand via `importlib`
- **core/ is framework-agnostic** — no Click imports in `core/`; Click dependency lives in `commands/`
- **Atomic writes** — `update_cmd` uses tempfile + os.replace for safe file updates

## Active PRPs (Draft)

| ACID | Title | Dependency |
|------|-------|-----------|
| FXA-2117 | AF Filter + Section Update | FXA-2116 (done) |
| ALF-2202 | Team Skill Session Management | None |
| ALF-2203 | Multi-CHG Implementation Workflow | None |
| ALF-2204 | Team Agent Health Monitoring | ALF-2202 |

## Workflow

- **Session start:** `af guide --root /Users/frank/Projects/alfred/alfred_ops`
- **Routing:** COR-1103 (PKG) → ALF-2207 (USR) → FXA-2125 (PRJ)
- All code changes go through `/team` dispatch (GLM = Worker, Codex/Gemini = Reviewer)
- TDD mandatory: COR-1500 (Red-Green-Refactor)
- Code review: COR-1602 (both >= 9/10 to pass)
- Release: FXA-2102 SOP (GitHub Actions → PyPI)
- Documents: always `af create`, never manual files
