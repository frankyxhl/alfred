# PRP-2105: AF Rename Command

**Applies to:** FXA project
**Last updated:** 2026-03-19
**Last reviewed:** 2026-03-19
**Status:** Rejected
**Related:** D13 (FXA-2108), FXA-2104 (af update)
**Rejected reason:** `af update --title` already fully covers rename. Real issue is discoverability (README missing af update docs). Codex scored 5/10, recommended improving documentation instead. Leader concurred.

---

## What Is It?

A new `af rename` CLI command as a dedicated, user-friendly shortcut for renaming documents. While `af update --title` already supports rename, `af rename` provides a simpler interface for the most common rename operation.

---

## Problem

1. **`af update --title` exists but is verbose** — renaming is common enough to warrant its own command: `af rename COR-1600 "New Title"` vs `af update COR-1600 --title "New Title" -y`
2. **During this session**, we renamed 5 COR files manually via `mv` + manual H1 edits — a dedicated command would have saved significant effort
3. **Batch rename not supported** — renaming multiple documents (e.g., adding "Workflow" prefix to all 16xx SOPs) required repetitive manual work

---

## Proposed Solution

### Command signature

```bash
af rename <IDENTIFIER> <NEW_TITLE> [options]
```

`<IDENTIFIER>`: same lookup as `af read` / `af update` (PREFIX-ACID or ACID-only).
`<NEW_TITLE>`: the new title (positional argument — simpler UX than `--title` flag).

### Options

| Option | Description |
|--------|------------|
| `--history "description"` | Override auto-generated history entry |
| `--by "author"` | Author for history entry (default: `—`) |
| `--dry-run` | Preview the rename without writing |
| `-y` / `--yes` | Skip confirmation prompt |

### Behaviors

- Delegates to the same core rename logic as `af update --title` (extract shared function)
- Auto-generates a history entry: `"Renamed: <old title> → <new title>"` (unless `--history` overrides)
- Same validations: FILENAME_PATTERN, conflict check, PKG rejection, non-interactive check
- Same layer behavior as `af update`
- Auto-touches `Last updated` if field exists
- Auto-runs `af index` for PRJ layer only

### Implementation approach

Extract rename logic from `update_cmd.py` into a shared core function (e.g., `core/rename.py` or a function in `core/parser.py`). Both `af update --title` and `af rename` call this shared function. `af rename` adds:
1. Positional `<NEW_TITLE>` argument (simpler UX)
2. Auto-generated history entry

---

## Open Questions

1. **Thin wrapper vs shared function?** — Should rename logic be extracted to a core function that both commands use, or should `af rename` literally invoke `ctx.invoke(update_cmd)` internally?
2. **Batch rename?** — Should v1 support batch operations (e.g., `af rename --prefix COR --area 16 --add-prefix "Workflow"`)? Or defer?
3. **Is this command necessary at all?** — `af update --title` already works. Is the UX improvement worth the added command surface area?

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-19 | Initial version | Frank + Claude |
| 2026-03-19 | Rejected after COR-1602 review: Codex 5/10, Gemini 9.25/10. Leader sided with Codex — supplement README instead of new command | Frank + Claude |
