# CHG-2330: Project SOP Registry

**Applies to:** FXA project
**Last updated:** 2026-09-02
**Last reviewed:** 2026-09-02
**Status:** Approved
**Date:** 2026-09-02
**Requested by:** Frank Xu (via pfc, machine-wide SOP card catalog)
**Priority:** Medium (risk: Low — additive read-path side table; scan core untouched)
**Change Type:** Normal

---

## What

A USER-level, auto-maintained **Project SOP Registry**: one markdown table row
per `(PRJ prefix, project root)` seen by `af`, so `af read USR-9000` shows the
whole machine's project SOP map — which projects carry Alfred documents, where
they live, how big their SOP corpus is, and when they were last touched.

1. **Registry document** — `~/.alfred/USR-9000-REF-Project-SOP-Registry.md`,
   a normal USR-layer REF doc (so it appears in every scan and is readable via
   the ordinary `af read`). ACID 9000 is a fixed, well-known slot: the registry
   must be addressable without discovery, and sequential auto-numbering
   (highest+1) will not organically reach 9000. The file holds a header block
   plus one table row per entry:

   ```
   | PRJ | Root | Docs | Last Seen |
   |-----|------|------|-----------|
   | FXA | /Users/frank/Projects/alfred | 128 | 2026-09-02 |
   ```

2. **UPSERT trigger on read paths** — `af guide`, `af list`, `af read`,
   `af status`: right after the shared scan, if the PRJ layer contributed at
   least one document, each `(prefix, root)` pair is upserted: absent → append;
   present → update doc count / last-seen date. Idempotent — when nothing
   changed (same day, same count) the file is not rewritten. The trigger
   **never blocks or fails the primary command**: any registry read/write
   problem is a one-line stderr warning, nothing else. Out-of-project cwd
   (0 PRJ docs) → no-op, no file created.

3. **Row key = (prefix, resolved root)** — roots are canonicalized with
   `Path.resolve()` (same normalization as FXA-2314) so symlinks don't fork
   rows. A repo with multiple prefixes (e.g. PFC + NRV side by side in one
   `rules/`) yields one row per prefix, each with its per-prefix doc count.
   Rows sort by `(root, prefix)` for stable diffs.

4. **`af register [--root]`** — explicit, immediate upsert for the current
   (or given) project. Unlike the background trigger, failures here ARE loud
   (ClickException): registering is the command's whole job. Registering a
   directory with zero Alfred PRJ documents is an error (the catalog tracks
   projects that actually carry SOP docs).

5. **`af projects [--json] [--prune]`** — list registry entries (text table /
   JSON array via `emit_json`); `--prune` drops entries whose root directory
   no longer exists (e.g. archived repos) and reports what was removed.

6. **Preserved hand rows** — `load` parses any table-shaped row; rows that
   don't belong to a currently-scanned project survive regeneration (only
   `--prune` or an upsert on the same key removes them). The document is
   regenerated from a fixed template on write, so header prose churn between
   versions cannot corrupt entries.


## Why

Alfred documents are spread across per-repo `rules/` trees and FXA-2314
subproject dirs under `~/.alfred/`; nothing today answers "what projects on
this machine carry SOPs, and where?" without a manual find. Frank asked for a
machine-wide SOP card catalog (owner request, relayed via pfc): agents hop
between citizen repos and Frank wants one `af read` to show the whole map.
Hanging the maintenance off the four hot read commands means the catalog keeps
itself current with zero new habits — every `af guide` at session start in any
project refreshes that project's row.


## Impact Analysis

- **Systems affected:**
  - **New** `src/fx_alfred/core/registry.py` — pure registry logic (no Click):
    `RegistryEntry` dataclass, `parse/render/load/save` (atomic write via
    tempfile + `os.replace`, mirroring `_helpers.atomic_write`), `upsert`
    returning a `changed` flag for no-op detection.
  - **New** `src/fx_alfred/commands/register_cmd.py`, `projects_cmd.py`.
  - `src/fx_alfred/commands/_helpers.py` — `touch_project_registry(ctx, docs)`
    wrapper (get_root + counts + upsert, all exceptions → stderr warning).
  - `guide_cmd.py`, `list_cmd.py`, `read_cmd.py`, `status_cmd.py` — one call
    after `scan_or_fail`. JSON output stays pure: the trigger is silent on
    success, warns on stderr only.
  - `cli.py` — `register`, `projects` lazy subcommands; `CLAUDE.md` command
    list + module inventory (docs-drift guards).
- **Concurrency:** read-modify-write races between simultaneous `af` processes
  resolve last-writer-wins per whole file; atomic replace prevents corruption.
  Acceptable for a catalog (worst case: a concurrent row update is delayed to
  the next invocation).
- **Scan interaction:** the registry doc itself is USR-layer (`USR-9000`),
  never PRJ, so it can never collide with project prefixes and never feeds its
  own counts. FXA-2314 mapped subprojects register under their external root
  (the mapping key), counting the redirected PRJ docs.
- **Rollback plan:** revert the commit; the registry file is inert data an
  older `af` simply lists as a normal USR REF doc (delete it at will).


## Implementation Plan

TDD per COR-1500.

1. **RED** — `tests/test_registry.py` (parse/render/upsert/idempotency/
   resolve-canonicalization/save-failure), `tests/test_register_cmd.py`,
   `tests/test_projects_cmd.py`, plus one auto-trigger test in each of
   `test_guide_cmd.py`, `test_list_cmd.py`, `test_read_cmd.py`,
   `test_status_cmd.py` (creates row on first visit; no-op outside projects;
   warning not fatal on registry failure; `--json` output unpolluted).
2. **GREEN** — core module, commands, `_helpers` wrapper, four call sites,
   `cli.py` registration.
3. **Verify** — full `pytest` + `ruff check` + `ruff format`; manual smoke:
   `af register` + `af projects` + `af read USR-9000` against the real home.
4. CLAUDE.md inventory updates; PR to `frankyxhl/alfred`.


## Acceptance Criteria

- [ ] `af list/read/guide/status` inside a project appends `(prefix, root,
      count, today)` rows to `~/.alfred/USR-9000-REF-Project-SOP-Registry.md`
- [ ] Repeat invocations the same day with unchanged counts rewrite nothing
      (idempotent; mtime-stable)
- [ ] Registry write failure never fails the primary command (stderr warning,
      exit 0, output identical to pre-change on success paths)
- [ ] Zero PRJ docs (cwd outside any project) → registry untouched, not even
      created
- [ ] Symlinked roots collapse to the resolved path (one row, no duplicates)
- [ ] `af register` upserts immediately, errors loudly on write failure and on
      zero-doc roots
- [ ] `af projects` lists entries; `--json` emits a clean array via
      `emit_json`; `--prune` removes dead roots and reports them
- [ ] `af read USR-9000` renders the full machine map (it is a normal USR doc)
- [ ] Existing rows for other projects survive an upsert (no wipe-on-write)
- [ ] `pytest -q` and `ruff check`/`ruff format` clean

---

## Change History

| Date       | Change                                                                                                                                                             | By     |
|------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|
| 2026-09-02 | Initial version — design pre-settled with owner (machine-wide SOP card catalog, relayed via pfc); Status straight to Approved per FXA-2100 owner-request fast path | alfred |
