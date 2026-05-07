# PRP-2273: AF Tag Star Command And List Filter

**Applies to:** FXA project
**Last updated:** 2026-05-07
**Last reviewed:** 2026-05-07
**Status:** Rejected

---

## What Is It?

A user-preference layer for marking commonly-used `Tags:` values as **starred**, plus a complementary `--starred` flag on `af list` that filters documents whose `Tags:` includes any starred tag. Starred tags are stored in a new per-user file `~/.alfred/preferences.yaml`, kept out of git and out of the document layer. Concretely:

- `af tag star <name>` — add `<name>` to the user's starred list (idempotent)
- `af tag unstar <name>` — remove `<name>` from the starred list (idempotent)
- `af tag list` — show the user's starred tags (one per line, or JSON with `--json`)
- `af list --starred` — filter docs whose `Tags:` metadata contains *any* starred tag

The feature does not modify any document — `Tags:` metadata is read-only as far as this feature is concerned. Only the user's `preferences.yaml` is mutated.

---

## Problem

`af list --tag <name>` exists today, but the user has to remember the exact tag string and pass it explicitly every time. For a small set of tags they retrieve frequently (e.g., `release`, `review`, `pr-review`, `bdd`), this is friction. There is no per-user preference layer to express *"these are the tags I care about most often"*.

Embedding "starred" semantics in document `Tags:` metadata is the wrong place — it's a personal preference, not a property of the document, and would pollute shared docs across users.

## Scope

**In scope:**

- New CLI command group `af tag` with subcommands `star`, `unstar`, `list`.
- New flag `af list --starred`.
- New file format: `~/.alfred/preferences.yaml` with at least the key `starred_tags` (a list of strings). All tag names normalised to lowercase on write to match the existing `parse_tags()` lowercasing in `core/parser.py`.
- Atomic writes (tempfile + `os.replace`) for `preferences.yaml`, matching the pattern used by `update_cmd`.
- Read returns `[]` and never errors when the file is missing or empty.
- JSON output for `af tag list --json`.
- Tests: minimum 6 (star/unstar idempotency, list when empty, list when populated, `af list --starred` filter behaviour, missing file = empty starred set, atomic write doesn't leave `.tmp` artifacts).
- Help text and `af --help` discoverability for the new command group.

**Out of scope:**

- Cross-machine sync of starred tags. The `~/.alfred/preferences.yaml` file is local-only by design.
- Server-side preferences or any network call.
- Combinator changes to existing `--tag` flag (it stays case-insensitive exact-match against any single tag).
- `af tag suggest` or analytics ("which of my tags do I use most"). Pure manual star/unstar.
- Migrating existing `Tags:` metadata. No document is touched.
- Tags governance / canonicalisation. The user can star any string; if it doesn't match any doc's `Tags:`, `--starred` simply returns nothing.
- Any change to PKG (bundled COR docs). PKG layer is read-only.

## Proposed Solution

### Architecture

| Component | Path | Purpose |
|---|---|---|
| Preferences I/O | `src/fx_alfred/core/preferences.py` (new) | Atomic read/write of `~/.alfred/preferences.yaml`; framework-agnostic (no Click) |
| Tag command group | `src/fx_alfred/commands/tag_cmd.py` (new) | Click group with `star`, `unstar`, `list` subcommands |
| List filter | extend `src/fx_alfred/commands/list_cmd.py` | New `--starred` Click option; logic delegates to `core.preferences` |
| CLI registration | `src/fx_alfred/cli.py` | Add `"tag": "fx_alfred.commands.tag_cmd:tag_cmd"` to `lazy_subcommands` |

Logic stays in `core/preferences.py`; command modules stay thin (matches the existing `commands/` ↔ `core/` boundary and the LazyGroup convention).

### Preferences file schema (`~/.alfred/preferences.yaml`)

```yaml
# Created/managed by `af tag star`; safe to edit by hand.
starred_tags:
  - release
  - review
  - pr-review
```

Behaviour rules:

- File missing → treated as `{starred_tags: []}`. No error, no auto-create on read.
- `~/.alfred/` directory missing → created with `os.makedirs(..., exist_ok=True)` on first write (`af tag star`). Read paths never create the directory.
- File present but malformed YAML → `core/preferences.py` raises a custom `PreferencesError`; `commands/tag_cmd.py` and `commands/list_cmd.py` convert it to `click.ClickException` with a path-bearing message at the command boundary. `core/` stays Click-free.
- On `tag star <name>` write, the YAML output includes a header comment warning hand-editors that YAML may coerce certain bare strings (`yes`/`no`/`on`/`off`/numeric literals) — quote tag names that look like booleans or numbers.
- File present, valid YAML, missing `starred_tags` key → empty list, no error.
- File present, valid YAML, `starred_tags` not a list → `ClickException`.
- On write, only re-serialise the `starred_tags` key; preserve any other top-level keys the file may have (forward-compat with future preference keys).
- All tag names lowercased on `star`/`unstar` write; matches `parse_tags()` lowercasing on read in `core/parser.py`.

### Command behaviours

- `af tag star <name>` — lowercase + strip `<name>`; if empty/whitespace-only after normalisation, exit non-zero with `ClickException("tag name cannot be empty")`. Otherwise load preferences; if `<name>` already in `starred_tags`, exit 0 with `"already starred: <name>"`; else append, atomic-write, exit 0 with `"starred: <name>"`.
- `af tag unstar <name>` — same empty-string guard as `star`. Otherwise load preferences; if not in list, exit 0 with `"not starred: <name>"`; else remove, atomic-write, exit 0 with `"unstarred: <name>"`.
- `af tag list` — print starred tags one per line (sorted), or nothing when empty. `--json` emits `{"schema_version": "1", "starred_tags": [...]}`.
- `af list --starred` — filter docs to those whose `Document.tags` intersects with `starred_tags` (set intersection, case-insensitive — already lowercase on both sides). Composes with `--type`, `--prefix`, `--source`, `--tag` via the same AND logic as today. **When `starred_tags` is empty (no preferences file or nothing starred yet), `--starred` matches zero documents** — this is intentional ("star at least one tag first") rather than a bug; the command exits 0 with `"No documents found."` (or `[]` in JSON) just like any other empty filter result. `af tag list` returning empty is the diagnostic.

### Backward compatibility

- Existing `af list` behaviour unchanged when `--starred` is not passed.
- Existing `--tag` flag unchanged. `--tag` and `--starred` may be combined (AND).
- No document is modified; `af validate` results unchanged.
- No new dependency; `pyyaml` is already a project dependency.

### Validation commands (FXA-2102 readiness gate)

```bash
.venv/bin/pytest -q                          # all tests pass, ≥6 new
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/pyright src/                       # 0 errors
.venv/bin/af validate --root .               # 0 issues
.venv/bin/af tag --help                      # group registered, subcommands listed
.venv/bin/af list --help                     # --starred listed
```

### Acceptance Criteria

1. `af tag star release` creates `~/.alfred/preferences.yaml` with `starred_tags: [release]`; running it again exits 0 without duplicating.
2. `af tag unstar release` removes `release`; running it again on the now-empty list exits 0 ("not starred").
3. `af tag list` prints `release` after step 1; prints nothing (or `[]` in JSON) after step 2.
4. `af list --starred` returns only docs whose `Tags:` contains at least one starred tag (after `af tag star release`, returns docs tagged `release`).
5. Deleting the preferences file mid-session and running `af list --starred` returns the empty set with no error.
6. Concurrent writes (simulated in tests by writing twice in succession) leave no `.tmp` or partial files.
7. Existing `af list` (no `--starred`) output and `af list --tag <name>` output are semantically identical to v1.12.0 — same documents, same order, same labels (whitespace tolerance allowed for any incidental refactor of the print loop).

## Open Questions

1. **YAML vs JSON for the preferences file?** Proposed YAML for human-edit friendliness (matches `--spec` convention). Alternatively JSON (smaller, no YAML edge cases). Defaulting to YAML; flagged for review.
2. **`--starred` shortform `-s`?** No clash with existing flags. Defaulting to long-form only for safety; can add later.
3. **Should `af tag list` show all tags in use across docs (not just starred), with a star marker on starred ones?** That would unify `af tag list` and "list all tags discovered in PRJ docs". Defer — out of this PRP's scope, separate PRP if useful.
4. **AND vs OR for `--starred` + `--tag`?** AND keeps consistency with all other `af list` filters. Documented as AND in §Proposed Solution; flagged for confirmation.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-07 | Initial version | Claude Code |
| 2026-05-07 | Trinity fast-review (round 1): GLM 9.08 PASS, DeepSeek 9.30 PASS — 2/2 PASS, zero blocking. Folded convergent advisory (empty-string guard, empty-starred UX) and craft items (~/.alfred/ dir creation, `PreferencesError` at core boundary, AC #7 softened to semantic equivalence, YAML coercion warning). | Claude Code |
| 2026-05-07 | Implementation complete on branch `af-tag-star`. Validation: pytest 888 passing (+19 new), ruff/pyright clean, af validate 247 docs / 0 issues, `af tag --help` surfaces star/unstar/list, `af list --starred` works. Files: core/preferences.py + commands/tag_cmd.py (new); list_cmd.py + cli.py (modified). | Claude Code |
| 2026-05-07 | Trinity fast-review code review: GLM 9.13 PASS, DeepSeek 9.30 PASS — 2/2 PASS, zero blocking. Folded convergent advisory (`af list --starred` malformed-YAML test) and single-reviewer items (dedup-on-read in `get_starred_tags`, defensive `.strip().lower()` in `add_starred_tag`/`remove_starred_tag`, `--starred --json` test, `--starred --tag` combo test). Final: pytest 891 passing (+22 new). | Claude Code |
| 2026-05-07 | Superseded by FXA-2274 before reaching PyPI. v1.13.0 release pivoted: af tag star/unstar/list and af list --starred deleted from main; af star/unstar/starred ships instead. core/preferences.py infrastructure preserved and reused. | Claude Code |
