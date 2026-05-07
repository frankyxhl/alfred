# PRP-2274: AF Star Command Bookmark Documents

**Applies to:** FXA project
**Last updated:** 2026-05-07
**Last reviewed:** 2026-05-07
**Status:** Draft

---

## What Is It?

Direct document bookmarking by ACID. Adds three top-level CLI commands:

- `af star <ID>` — bookmark a document by its identifier (e.g., `af star COR-1202`)
- `af unstar <ID>` — remove a bookmark
- `af starred` — list bookmarked documents

Bookmarks persist in the existing `~/.alfred/preferences.yaml` (introduced in v1.13.0 / FXA-2273) under a new top-level key `starred_docs: [...]`, alongside the existing `starred_tags`. Forward-compat already verified: `tests/test_tag_cmd.py::test_preferences_file_preserves_unknown_keys` proves the v1.13.0 layer survives unknown keys round-tripping through write.

The feature is **independent of `Tags:` metadata**. Any document that resolves through `af read <ID>` is starrable.

---

## Problem

`af tag star` (shipped in v1.13.0, FXA-2273) starred **tag values**, not documents. To bookmark a specific SOP a user routinely opens — say `COR-1202` (Compose Session Plan) — the user has to either:

- Find what `Tags:` field that doc has (it may have none), or
- Add `Tags:` metadata to the doc (mutates a shared PKG/PRJ doc — wrong layer for personal preferences).

Real coverage check (2026-05-07): only **5 of 238 documents in the repo** carry `**Tags:**` metadata. `COR-1202` is in the 233-doc majority that has none. So the v1.13.0 starred-tags feature has narrow utility today, and does not solve the natural "bookmark this specific doc" use case at all.

The user's mental model when they say "I want to star X" is almost always "remember the document X for me", not "remember a tag string". This PRP closes that gap.

## Scope

**In scope:**

- Three new top-level commands: `af star <ID>`, `af unstar <ID>`, `af starred`.
- New top-level key `starred_docs` in `~/.alfred/preferences.yaml`. Stored as a sorted list of canonical IDs (e.g., `COR-1202`, `FXA-2273`).
- `<ID>` accepts the same forms `af read` accepts: `PREFIX-ACID` (e.g., `COR-1202`) or ACID-only (e.g., `1202`). On ACID-only input, resolve via the same scanner-based lookup `af read` uses; raise `ClickException` with disambiguation hint when multiple prefixes match.
- Validate that the ID resolves to an existing document **at star time**. If not, exit non-zero with `"no document found: <ID>"`. (Stale entries that point at later-deleted docs are tolerated on read; see Risk Awareness below.)
- Idempotent `star`/`unstar` (matches v1.13.0 tag-star semantics).
- `af starred` output: one canonical ID per line (sorted), or JSON `{"schema_version": "1", "starred_docs": [...]}` with `--json`. When a starred ID no longer resolves, the text output marks it `(missing)`; JSON output adds `"missing": [...]` alongside `starred_docs`.
- Atomic writes via the same `_atomic_write` helper already in `core/preferences.py`.
- Tests: minimum 8 new (star/unstar idempotency, ACID-only resolution, multi-prefix disambiguation error, `af starred` empty/populated/JSON, missing-doc warning on list, atomic-write artefact check).
- README + CHANGELOG entries.

**Out of scope:**

- Cross-machine sync. `~/.alfred/preferences.yaml` stays local.
- Server-side preferences or any network call.
- Filtering `af list` by starred docs (since `af starred` directly lists them, no intersection logic needed). If a future user wants `af list --starred-docs --type SOP`, that's a separate PRP.
- Renaming or deprecating `af tag star/unstar/list` from v1.13.0 — both feature pairs coexist. `af star` is for documents; `af tag star` is for tag values. They share the same preferences file but different keys.
- Changes to PKG-bundled COR docs (read-only).
- Backfilling `Tags:` metadata across the doc base (separate workstream if ever desired).

## Proposed Solution

### Architecture

| Component | Path | Purpose |
|---|---|---|
| Preferences I/O extension | `src/fx_alfred/core/preferences.py` (extend) | Add `add_starred_doc / remove_starred_doc / get_starred_docs`. **Note: doc-ID canonicalisation is uppercase-prefix (e.g., `COR-1202`), NOT lowercase like the tag helpers.** Reuse the same `load_preferences / _atomic_write / PreferencesError` infrastructure. Also update the `_HEADER_COMMENT` literal in this file from `"Managed by \`af tag star\`"` to `"Managed by \`af tag star\` and \`af star\`"`. |
| Star command module | `src/fx_alfred/commands/star_cmd.py` (new) | Three Click commands (`star_cmd`, `unstar_cmd`, `starred_cmd`) exported from a single module. Each declares `@root_option` (matching `list_cmd.py`'s pattern, NOT `tag_cmd.py` — `tag` doesn't need scanner access, but `star` does because it must resolve `<ID>`). Use `scan_or_fail(ctx)` + `find_or_fail(docs, identifier)` from `commands/_helpers.py` for ID resolution; `find_or_fail` already handles both not-found and ambiguous-match cases — no wrapping needed. |
| CLI registration | `src/fx_alfred/cli.py` | Add three LazyGroup entries: `"star": "fx_alfred.commands.star_cmd:star_cmd"`, `"unstar": "fx_alfred.commands.star_cmd:unstar_cmd"`, `"starred": "fx_alfred.commands.star_cmd:starred_cmd"`. |

Top-level commands are registered as **separate** Click commands (not a `star` subgroup) because the user wants `af star COR-1202`, not `af star add COR-1202`. This matches the conversation's stated UX target.

### Preferences file evolution

After v1.14.0 the file looks like:

```yaml
# Managed by `af tag star` and `af star`; safe to edit by hand.
starred_docs:
  - COR-1103
  - COR-1202
  - FXA-2273
starred_tags:
  - release
  - review
```

Both keys are independently optional. Missing key → empty list. Forward-compat is already proven for unknown keys; this PRP just adds one well-known key.

### ID resolution

- `af star COR-1202` → resolve via `find_or_fail(docs, "COR-1202")`; store `f"{doc.prefix}-{doc.acid}"` (the `Document` dataclass already produces canonical uppercase-prefix output, so no separate `.upper()` call is needed).
- `af star cor-1202` (lowercase prefix) → **accepted on input**. The scanner `find_or_fail` is case-insensitive on prefix matching; storage is always canonical uppercase via `doc.prefix + "-" + doc.acid`. (See AC #2b below.)
- `af star 1202` (ACID-only) → `find_or_fail` resolves ACID-only and raises `AmbiguousDocumentError` when multiple prefixes match; `commands/_helpers.py` already surfaces this as a Click-friendly error.
- `af unstar <ID>` accepts the same input forms as `af star`. Resolution is **best-effort**: try `find_or_fail(docs, identifier)` first; if it succeeds, canonicalise to `f"{doc.prefix}-{doc.acid}"`. If `find_or_fail` raises (doc deleted, ACID-only with no current match), fall back to a literal-string match against `starred_docs` after normalising input via `identifier.strip().upper()`. This way: (a) `af unstar COR-1202` works whether or not the doc still exists; (b) `af unstar 1202` works when exactly one starred entry has ACID `1202`; (c) `af unstar 1202` reports "not starred: 1202" when no starred entry matches; (d) `af unstar 1202` reports an ambiguity error when multiple starred entries (e.g. `COR-1202` and `FXA-1202`) end with the same ACID — pick by full ID instead. Removing a stale bookmark must always succeed when the bookmark itself is unambiguously identified.
- All in-file comparisons against `starred_docs` are exact-string after the canonicalisation above.

`add_starred_doc` and `remove_starred_doc` accept a pre-canonicalised string from the command layer; they do not perform case mangling themselves (this avoids the asymmetry pitfall where a future caller might pass a `Document` object directly to the core function).

### Command behaviours

- `af star <ID>`: resolve `<ID>` (error on not-found / multi-match); load preferences; if canonical ID already in `starred_docs`, exit 0 with `"already starred: <ID>"`; else append, atomic-write, exit 0 with `"starred: <ID>"`.
- `af unstar <ID>`: canonicalise input only (no resolution required); load preferences; if not in list, exit 0 with `"not starred: <ID>"`; else remove, atomic-write, exit 0 with `"unstarred: <ID>"`.
- `af starred`: print starred IDs one per line (sorted). Each ID that no longer resolves to an existing doc is annotated ` (missing)`. `--json` emits `{"schema_version": "1", "starred_docs": [...], "missing": [...]}`. Exit 0 in both cases (missing entries are not errors — operator decides whether to clean up).

### Validation commands (FXA-2102 readiness gate)

```bash
.venv/bin/pytest -q                          # all tests pass, ≥8 new
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/pyright src/                       # 0 errors
.venv/bin/af validate --root .               # 0 issues
.venv/bin/af star --help                     # command registered
.venv/bin/af unstar --help                   # command registered
.venv/bin/af starred --help                  # command registered
.venv/bin/af star COR-1202 && .venv/bin/af starred  # functional smoke
```

### Acceptance Criteria

1. `af star COR-1202` creates/updates `~/.alfred/preferences.yaml` with `starred_docs` containing `COR-1202`; running it again exits 0 without duplicating.
2. `af star 1202` resolves `1202` to its single matching doc and stores the canonical `<PREFIX>-1202`. If no match, exit non-zero with `"no document found: 1202"`. If multiple prefixes match, exit non-zero with disambiguation hint.
2b. `af star cor-1202` (lowercase prefix) resolves and stores `COR-1202` — case-insensitive on input, canonical uppercase on storage.
3. `af unstar COR-1202` removes the entry; running it again on a now-clean list exits 0 with `"not starred: COR-1202"`. `af unstar 1202` also removes `COR-1202` when it is the unique starred entry with ACID `1202`.
3b. `af unstar 1202` returns an ambiguity error when both `COR-1202` and `FXA-1202` are starred — operator must use a full `PREFIX-ACID` to disambiguate.
4. `af unstar COR-1202` succeeds even when the underlying doc has been deleted from disk (operator-cleanup path) — best-effort resolution falls back to literal-string match against `starred_docs`.
5. `af starred` lists starred IDs sorted, one per line. Marks entries whose docs no longer resolve as `(missing)`. JSON form includes `"missing": [...]` alongside `"starred_docs"`.
6. **Forward-compat**: a hand-edited preferences file with unknown top-level keys (e.g., `future_key: keep-me`) survives a `star` round-trip with the unknown key intact. (Verified by `test_starred_ignores_unknown_top_level_keys`.)
7. Atomic writes leave no `.tmp` artefacts after sequential star+unstar+star.

> **Note**: previous versions of this PRP listed AC items asserting coexistence with `af tag star/unstar/list` and `af list --starred` (the FXA-2273 commands). Those features were deleted from main as part of this PR (see the Change History row dated 2026-05-07 for the scope pivot), so cross-feature acceptance criteria for them are obsolete and removed here.

## Risks / Failure Modes

| Risk | Mitigation |
|---|---|
| **Stale bookmark** — user stars `FXA-2107`, doc is later renamed/deleted | `af starred` annotates as `(missing)` (text) / lists in `"missing"` array (JSON). `af unstar` works on stale entries without resolving, so cleanup is one command. AC #4 + #5 cover this. |
| **Concurrent writes** — two terminals running `af star` simultaneously | Last-write-wins via `_atomic_write` (`tempfile.mkstemp` + `os.replace`). One write may be lost; documented limitation, acceptable for a single-user CLI. AC #8 covers no `.tmp` leftovers. |
| **Corrupted `preferences.yaml`** — invalid YAML from hand-edit or interrupted write | Existing v1.13.0 behaviour: `PreferencesError` → `ClickException` with path-bearing message. Already tested via `test_malformed_yaml_raises_click_exception`; will add equivalent for `af starred` per AC #5 propagation. |
| **File permission denied** — `~/.alfred/preferences.yaml` owned by root or chmod 0 | OS error propagates as `OSError` from `_atomic_write`; Click surfaces it as a `ClickException` via the standard exception chain. Documented behaviour, no special handling. |
| **Cross-feature interference** — v1.13.0 `af tag star` and v1.14.0 `af star` both touch the same file | Different top-level keys (`starred_tags` vs `starred_docs`); v1.13.0 forward-compat behaviour (preserves unknown keys, proven by `test_preferences_file_preserves_unknown_keys`) ensures coexistence. AC #6, #7, #9 cover this explicitly. |
| **Implementer copies tag-helper boilerplate verbatim** — would lowercase doc IDs by mistake | §Architecture explicitly notes "doc-ID canonicalisation is uppercase-prefix, NOT lowercase like the tag helpers". §ID resolution restates the canonicalisation rule and where it happens. |

## Open Questions

1. **`af starred` vs `af star list`?** Resolved: top-level `af starred` is more ergonomic and matches the conversation's stated UX. Three top-level commands accepted. Documented as decided.
2. **Show `(missing)` in plain text output?** Resolved: yes, show. Operator diagnostic clarity beats output minimalism. Documented as decided.
3. **Should `--json` always include `missing`, even when empty?** Resolved: yes, always present. Consistent shape for downstream tooling. Documented as decided.
4. **Case sensitivity for prefix?** Resolved: case-insensitive on input, canonical uppercase on storage. AC #2b covers this explicitly. No remaining open question.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-07 | Initial version | Claude Code |
| 2026-05-07 | Trinity fast-review round 1: GLM 9.08 PASS, DeepSeek 8.9 CONCERNS — gate not satisfied. Folded all 8 advisory items: explicit `--root` requirement on star_cmd; `_HEADER_COMMENT` update listed in Architecture; case-canonicalisation location made explicit (`doc.prefix + "-" + doc.acid` from Document dataclass); `find_or_fail` phrasing made definitive; doc-ID uppercase vs tag-value lowercase asymmetry called out to prevent copy-paste error; AC #2b added for case-insensitive prefix input; AC #9 added for cross-feature regression test; dedicated Risks section added; all 4 Open Questions resolved. | Claude Code |
| 2026-05-07 | Trinity fast-review round 2: GLM 9.48 PASS, DeepSeek 10.0 PASS — Decision Matrix gate satisfied (both ≥ 9.0, zero blocking). GLM caught a new advisory (`af unstar 1202` silent-failure when ACID-only doesn't match canonical-form storage); folded fix: best-effort resolution via `find_or_fail`, fallback to literal-string match for stale bookmarks, ambiguity error for multi-prefix ACID collisions. AC #3 + #3b updated. | Claude Code |
| 2026-05-07 | **Scope pivot**: per operator decision, `af tag star/unstar/list` and `af list --starred` (FXA-2273, never reached PyPI — v1.13.0 release PR #111 was closed unmerged) are deleted from main as part of this PR. v1.13.0 will ship a single coherent feature: `af star/unstar/starred`. AC #6, #7, #9 (cross-feature regression with the deleted commands) are obsolete and removed from acceptance. `core/preferences.py` infrastructure stays — `af star` reuses its atomic-write + `PreferencesError` layer. Implementation complete: 887 tests passing (+19 new for `af star`, −19 deleted from `af tag`), ruff/pyright/af validate clean. | Claude Code |
