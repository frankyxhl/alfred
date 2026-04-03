# PRP-2104: AF Update Command

**Applies to:** FXA project
**Last updated:** 2026-03-19
**Last reviewed:** 2026-03-19
**Status:** Implemented
**Related:** D12 (FXA-2108 Session Retrospective)
**Reviewed by:** Codex (GPT-5.4), Gemini 3

---

## What Is It?

A new `af update` CLI command for structured metadata updates to existing documents. It modifies header fields, appends Change History entries, and optionally renames documents — without touching body content.

---

## Problem

1. **No update command** — `af` can `create`, `read`, `list`, `index`, but cannot update existing documents. Users must manually open and edit files.
2. **Inconsistency risk** — manual edits can forget to update date fields, miss Change History entries, or introduce formatting inconsistencies.
3. **No rename support** — changing a document title requires manually renaming the file, editing the H1 header, and re-running `af index`.

---

## Scope

**In scope (v1):**
- Metadata field updates (header fields between H1 and first `---`)
- Change History table append
- Document rename (title change → filename + H1 + index)
- PRJ and USR layer documents only

**Out of scope (v1):**
- Body content editing (future: `af edit` via system editor)
- PKG layer writes (always read-only, error if attempted)
- Arbitrary section append/insert

---

## Document Structure Contract

`af update` expects documents to follow this structure:

```markdown
# <TYP>-<ACID>: <Title>              ← H1 title line (line 1)

**Field:** value                       ← metadata block
**Another field:** value               ← (continues until first ---)

---                                    ← first horizontal rule ends metadata

<body content>                         ← not touched by af update

---

## Change History                      ← Change History section

| Date | Change | By |                 ← table header
|------|--------|----|
| YYYY-MM-DD | description | author |  ← rows
```

**Parsing rules:**
- **H1**: first line, format `# <TYP>-<ACID>: <Title>`
- **Metadata block**: lines between H1 and first `---`, matching either format:
  - `**Key:** value` (standard)
  - `- **Key:** value` (list-prefixed variant found in some existing documents)
- **Change History**: last table under `## Change History` heading
- Field matching: case-sensitive, exact match on key name

**Structural validation:** If the document does not match the expected structure (missing H1, missing first `---` separator, unrecognizable metadata format), `af update` must raise a clear error:
- Missing H1: `"Malformed document: first line is not a valid H1 header"`
- Missing `---` separator: `"Malformed document: missing metadata separator '---'"`
- No recognizable metadata fields: `"No metadata fields found in document"`

---

## Proposed Solution

### Command signature

```bash
af update <IDENTIFIER> [options]
```

`<IDENTIFIER>` follows the same lookup semantics as `af read`: supports `PREFIX-ACID` (e.g., `FXA-2107`) or ACID-only (e.g., `2107`). Uses `find_document()` from core.

### Options

| Option | Description |
|--------|------------|
| `--title "New Title"` | Rename: update filename, H1, and auto-run index (PRJ only) |
| `--history "description"` | Append row to Change History table (date=today, By=`--by` or `—`) |
| `--by "author"` | Author name for history entry (default: `—`) |
| `--status "value"` | Update Status field (only if field already exists in document) |
| `--field "key" "value"` | Update any metadata field (only if field already exists) |
| `--dry-run` | Preview changes without writing to disk |
| `-y` / `--yes` | Skip interactive confirmation for destructive operations (rename) |

### Removed from original PRP
- `--date`: removed. Only `Last updated` is implicitly touched (see below).

### Behaviors

**Execution order (transaction semantics):**
When multiple options are provided, `af update` follows this order:
1. **Validate all** — check all options are valid before writing anything (field exists, title is safe, no conflicts)
2. **Apply metadata updates** — `--field`, `--status`
3. **Apply history append** — `--history`
4. **Apply rename** — `--title` (last, because it changes the filename)
5. **Auto-touch `Last updated`** — only if the field exists in the document
6. **Write** — atomic write (temp file → rename)
7. **Post-write** — auto-run `af index` if PRJ layer and rename occurred

If validation fails at step 1, no changes are written. If write fails at step 6, the original file is preserved.

**Field updates (`--status`, `--field`):**
- Only update fields that already exist in the metadata block
- If field not found → error: `"Field 'Status' not found in document"`
- `Last updated` field is auto-touched to today on any successful update (only if it exists; `Date` fields are NOT touched — they represent creation/event dates, not modification times)

**History append (`--history`):**
- Locate `## Change History` section and its table
- Append row: `| {today} | {description} | {by} |`
- Pipe characters (`|`) in description or by values are escaped as `\|`
- If Change History section not found → error with suggestion to add it manually

**Rename (`--title`):**
- Requires interactive confirmation unless `-y` is passed
- Validates new title: no path separators (`/`, `\`), not empty, no leading/trailing whitespace, generates a filename matching `FILENAME_PATTERN` regex (`^[A-Z]{3}-\d{4}-[A-Z]{3}-.+\.md$`)
- In non-interactive environments (no TTY) without `-y`: error instead of hanging on confirmation prompt
- Checks target path does not already exist (conflict → error)
- Updates: filename (via rename), H1 line, `Document.title`
- Auto-runs `af index` only for PRJ layer documents (mirrors `create_cmd` behavior: index failure produces warning, does not roll back the rename)
- Uses atomic write: write to temp file → rename (prevents partial writes)

**Dry run (`--dry-run`):**
- Shows diff of what would change (old → new for each modified line)
- For rename: shows old filename → new filename
- Does not write to disk, does not run `af index`

### Layer behavior

| Layer | Readable | Writable | Notes |
|-------|----------|----------|-------|
| PKG | Yes (for lookup) | **No** | Error: `"Cannot update PKG layer documents. They are read-only."` |
| USR | Yes | Yes | Resolve via `~/.alfred/` path |
| PRJ | Yes | Yes | Resolve via `base_path` on Document |

### Error handling

| Scenario | Behavior |
|----------|----------|
| Document not found | `DocumentNotFoundError` → `ClickException` |
| Ambiguous identifier | `AmbiguousDocumentError` → `ClickException` |
| PKG layer document | Error: read-only |
| Field not found | Error: field does not exist |
| Rename target exists | Error: target path already exists |
| Change History missing | Error: section not found |
| No options provided | Error: nothing to update |
| Malformed H1 | Error: first line is not a valid H1 header |
| Missing `---` separator | Error: missing metadata separator |
| No metadata fields found | Error: no recognizable metadata |
| Pipe in history text | Auto-escaped as `\|` |
| Non-interactive + no `-y` + rename | Error: cannot confirm in non-interactive mode |

---

## Implementation Plan

1. **Core**: add `parse_metadata(content: str)` utility — extract H1, metadata fields, body, Change History table; raise on malformed structure
2. **Core**: add `render_document(parsed)` — reconstruct document preserving original body, whitespace, and `---` separators
3. **Command**: `update_cmd.py` — Click command with all options, registered in `cli.py` via `cli.add_command(update_cmd)`
4. **Tests**: comprehensive coverage:
   - PRJ layer: field update, history append, rename, dry-run
   - USR layer: field update, history append
   - PKG layer: rejection
   - Error cases: field not found, malformed document, rename conflict, ambiguous ID, no options, non-interactive rename
   - Multi-option: `--title` + `--history` + `--field` combined
   - Metadata format variants: `**Key:** value` and `- **Key:** value`

---

## Open Questions (resolved)

| Q | Decision | Rationale |
|---|----------|-----------|
| 1. Content editing | v1 metadata only | Body editing is complex; defer to future `af edit` |
| 2. PKG writes | Always read-only | `importlib.resources` returns non-writable paths; explicit error |
| 3. Undo/backup | Rely on git | Backup files pollute workspace; atomic writes prevent corruption |
| 4. Validation | Validate filename + check target exists | Both FILENAME_PATTERN and filesystem conflict check |

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-19 | Initial version | Frank + Claude |
| 2026-03-19 | Round 1 revision: narrowed scope to PRJ/USR only, added parsing contract, removed --date, added --dry-run/-y, fixed field update semantics, added error handling matrix | Frank + Claude |
| 2026-03-19 | Round 2 revision: fixed Date auto-touch (only Last updated), added list-prefixed metadata support, structural validation errors, transaction semantics, pipe escaping, non-interactive handling, expanded test matrix | Frank + Claude |
