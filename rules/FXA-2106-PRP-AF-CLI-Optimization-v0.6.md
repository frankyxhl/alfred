# PRP-2106: AF CLI Optimization v0.6

**Applies to:** FXA project
**Last updated:** 2026-03-20
**Last reviewed:** 2026-03-19
**Status:** Implemented
**Related:** FXA-2107-CHG (prior refactoring)
**Reviewed by:** Codex (GPT-5.4), Gemini 3

---

## What Is It?

A batch of 6 targeted optimizations to the af CLI (fx-alfred v0.5.0 -> v0.6.0), covering internal code quality, UX improvements, and new commands. No breaking changes.

---

## Problem

1. Every command repeats the same `scan_documents` + `LayerValidationError` try/except boilerplate (6 occurrences across `list_cmd`, `status_cmd`, `read_cmd`, `create_cmd`, `update_cmd`, and `index_cmd`).
2. `cli.py` eagerly imports all 8 command modules on every invocation, even for `af --version`.
3. `af list` dumps all documents with no filtering -- users must visually scan the full list.
4. `af list` and `af status` output is human-only -- not consumable by scripts or pipelines.
5. No way to search document contents (only listing/reading by ID is possible).
6. Document structural validation only happens as a side effect during `af update` -- no dedicated health check.

---

## Scope

**In scope (v0.6):**
- CHG-1: Extract `scan_or_fail()` helper to eliminate 6x repeated try/except boilerplate
- CHG-2: Lazy command loading via Click LazyGroup -- import commands on demand
- CHG-3: `af list` filtering with `--type`, `--prefix`, `--source` options
- CHG-4: `--json` output flag for `list`, `status`, and `read` commands
- CHG-5: New `af search` command -- keyword search across document contents
- CHG-6: New `af validate` command -- structural health check for all documents

**Out of scope (v0.6):**
- `af edit` command (opens `$EDITOR`) -- deferred to future version
- Shell completion -- depends on all commands being finalized first
- Breaking changes to existing CLI interface

---

## Proposed Solution

### CHG-1: DRY scan boilerplate

Add `scan_or_fail(ctx) -> list[Document]` to a new `fx_alfred/commands/_helpers.py` module that wraps `scan_documents` with `LayerValidationError` -> `click.ClickException` conversion. Replace all 6 call sites. The helper lives in the commands layer (not `core/`) because it depends on `click`; the `core/` layer must remain framework-agnostic.

Current pattern (repeated in each command):

```python
try:
    docs = scan_documents(root)
except LayerValidationError as e:
    raise click.ClickException(str(e)) from e
```

Proposed helper in `fx_alfred/commands/_helpers.py`:

```python
# fx_alfred/commands/_helpers.py
import click
from fx_alfred.context import get_root
from fx_alfred.core.scanner import LayerValidationError, scan_documents

def scan_or_fail(ctx: click.Context) -> list:
    """Scan documents, converting LayerValidationError to ClickException."""
    root = get_root(ctx)
    try:
        return scan_documents(root)
    except LayerValidationError as e:
        raise click.ClickException(str(e)) from e
```

Optionally, a `find_or_fail(docs, identifier)` helper can also be extracted to wrap `find_document` with `DocumentNotFoundError`/`AmbiguousDocumentError` -> `ClickException` conversion (used in `read_cmd` and `update_cmd`).

Each command simplifies to:

```python
docs = scan_or_fail(ctx)
```

### CHG-2: Lazy command loading

Replace `click.Group` with a `LazyGroup` subclass in `cli.py`. Each command is registered as a string import path and only imported when invoked.

```python
class LazyGroup(click.Group):
    def __init__(self, *args, lazy_subcommands: dict[str, str] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._lazy_subcommands = lazy_subcommands or {}

    def list_commands(self, ctx: click.Context) -> list[str]:
        base = super().list_commands(ctx)
        lazy = sorted(self._lazy_subcommands.keys())
        return base + lazy

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        if cmd_name in self._lazy_subcommands:
            return self._load_lazy(cmd_name)
        return super().get_command(ctx, cmd_name)

    def _load_lazy(self, cmd_name: str) -> click.Command:
        import importlib
        module_path, attr = self._lazy_subcommands[cmd_name].rsplit(":", 1)
        mod = importlib.import_module(module_path)
        return getattr(mod, attr)
```

No explicit command caching is needed — Python's `importlib.import_module` caches modules in `sys.modules`, so repeated `get_command` calls for the same command will not re-execute module-level code.

All existing `cli.add_command(...)` calls (lines 23-30) must be removed. The `@root_option` and `@click.version_option` decorators remain unchanged on the `cli` function.

Registration in `cli.py`:

```python
@click.group(cls=LazyGroup, lazy_subcommands={
    "changelog": "fx_alfred.commands.changelog_cmd:changelog_cmd",
    "create":    "fx_alfred.commands.create_cmd:create_cmd",
    "guide":     "fx_alfred.commands.guide_cmd:guide_cmd",
    "index":     "fx_alfred.commands.index_cmd:index_cmd",
    "list":      "fx_alfred.commands.list_cmd:list_cmd",
    "read":      "fx_alfred.commands.read_cmd:read_cmd",
    "status":    "fx_alfred.commands.status_cmd:status_cmd",
    "update":    "fx_alfred.commands.update_cmd:update_cmd",
    "search":    "fx_alfred.commands.search_cmd:search_cmd",
    "validate":  "fx_alfred.commands.validate_cmd:validate_cmd",
})
```

### CHG-3: List filtering

Add options to `af list`:

```bash
af list [--type TYPE] [--prefix PREFIX] [--source SOURCE] [--root DIR]
```

| Option | Description |
|--------|------------|
| `--type SOP` | Filter by document type code (e.g. SOP, PRP, CHG, ADR) |
| `--prefix FXA` | Filter by project prefix (e.g. FXA, COR, NRV) |
| `--source prj` | Filter by layer: `pkg`, `usr`, or `prj` |

All filters are combinable (AND logic). Exact case-insensitive match for `--type`, `--prefix`, and `--source`. Example:

```bash
af list --type PRP --prefix FXA    # All FXA proposals
af list --source pkg               # All bundled PKG documents
af list --type sop                 # Matches SOP (case-insensitive exact match)
af list --type SO                  # Does NOT match SOP (not an exact match)
```

### CHG-4: JSON output

Add `--json` flag to `list`, `status`, and `read`:

```bash
af list --json
af status --json
af read IDENTIFIER --json
```

| Option | Description |
|--------|------------|
| `--json` | Output machine-readable JSON instead of human table |

Behaviors:
- `af list --json` outputs a JSON array of document objects, each with keys: `prefix`, `acid`, `type_code`, `title`, `source`, `directory` (the directory name as stored in `Document.directory`, e.g. `"rules"` — not a full path).
- `af status --json` outputs a JSON object with keys: `total`, `by_source`, `by_type`, `by_prefix`.
- `af read IDENTIFIER --json` outputs the document as a JSON object with keys: `prefix`, `acid`, `type_code`, `title`, `source`, `content`. This enables pipeline/automation use cases.
- `--json` is combinable with CHG-3 filters (e.g. `af list --type SOP --json`).
- No external dependencies (uses stdlib `json` module).

### CHG-5: af search command

```bash
af search PATTERN [--root DIR]
```

| Option | Description |
|--------|------------|
| `PATTERN` | Required argument: case-insensitive substring to search for |
| `--root DIR` | Project root override |

Behaviors:
- Searches document contents (via `resolve_resource().read_text()`) for PATTERN.
- Case-insensitive substring match.
- Each match shows the document ID, source label, and up to 3 matching lines. Each line is prefixed with its line number.
- If no matches: prints "No matches found." and exits 0.
- If a document cannot be read (e.g. permission error): skip it silently and continue.

### CHG-6: af validate command

```bash
af validate [--root DIR]
```

| Option | Description |
|--------|------------|
| `--root DIR` | Project root override |

Checks all documents for:
- H1 must match pattern `^# [A-Z]{3}-\d{4}: .+$` (already defined as `H1_PATTERN` in `parser.py`). Additionally, the type_code and ACID in the H1 must match the filename's type_code and ACID.
- Required metadata fields present (`Applies to`, `Last updated`, `Last reviewed`).
- Change History table structure valid (has Date, Change, By columns).
- COR-* documents only in PKG layer (already checked by scanner, but reported here too).

Behaviors:
- Reports issues per document, grouped by document ID.
- Summary line at end: "N documents checked, M issues found."
- Exit code 0 if clean, exit code 1 if any issues found.
- Report-only: no auto-fixing in v0.6.

---

## Implementation Order

CHGs are ordered by dependency:

1. **CHG-1** (DRY) -- pure refactor, makes subsequent work cleaner
2. **CHG-2** (Lazy) -- pure performance, no behavior change
3. **CHG-3** (List filter) -- most impactful UX improvement
4. **CHG-4** (JSON) -- builds on list/status infrastructure
5. **CHG-5** (Search) -- new command, independent
6. **CHG-6** (Validate) -- new command, independent

After all CHGs are implemented, update `pyproject.toml` version to 0.6.0 and add a CHANGELOG entry.

---

## Open Questions

1. Should `af search` support regex or just substring match for v0.6?
2. Should `af validate` auto-fix simple issues (like H1 mismatch) or only report?
3. Should `af list --json` include the resolved file path in each document object?
4. Should `af validate` report or skip documents that fail to parse (`MalformedDocumentError`)?

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-19 | Initial version -- full PRP content | GLM |
| 2026-03-19 | Round 1 revision -- address Codex and Gemini review feedback | GLM |
| 2026-03-19 | Round 2 micro-fix -- clarify LazyGroup caching and directory field semantics | Claude Code |
| 2026-03-19 | COR-1602 approved: Codex 9.25, Gemini 9.8 (Round 3) | Claude Code |
| 2026-03-20 | All 6 CHGs implemented and reviewed. Version bumped to 0.6.0. | Claude Code |
