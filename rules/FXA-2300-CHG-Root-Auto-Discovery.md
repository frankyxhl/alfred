# CHG-2300: Root Auto Discovery

**Applies to:** FXA project
**Last updated:** 2026-06-11
**Last reviewed:** 2026-06-11
**Status:** In Progress
**Date:** 2026-06-11
**Requested by:** Frank Xu (session review finding 2026-06-10; follow-up batch 2026-06-11)
**Priority:** Medium
**Change Type:** Normal
**Targets:** src/fx_alfred/context.py; src/fx_alfred/cli.py; tests/test_root_discovery.py

---

## What

When `--root` is not given, `get_root()` now walks up from the working directory and uses the nearest ancestor (including cwd itself) whose `rules/` subdirectory contains at least one Alfred-pattern document (`FILENAME_PATTERN` match); if no such ancestor exists, it falls back to cwd exactly as today. Explicit `--root` always wins, unchanged.

Surface: one new pure helper `discover_root(start: Path) -> Path` in `context.py` + the one-line fallback change in `get_root`; `--root` help text and the CLI epilog's Layer System line document the new default.


## Why

`get_root`'s silent cwd fallback means running `af` from any subdirectory of a project sees zero PRJ documents with no hint why — the root cause of every command in CLAUDE.md, the session SOPs, and daily muscle memory carrying `--root /Users/frank/Projects/alfred` long-form. Flagged in the 2026-06-10 review as the highest-leverage ergonomic papercut. The validity check (≥1 pattern-matching doc inside `rules/`) prevents false positives from unrelated directories that merely contain a `rules/` folder.


## Out of Scope

- Changing explicit `--root` semantics or any layer ordering (PKG/USR resolution untouched).
- A `.alfred-root` marker file or config-based root pinning (no evidence of need).
- `.git`-based discovery (a repo without Alfred docs has no meaningful PRJ root; `rules/`+pattern is the Alfred-native marker).
- Removing `--root` from documented commands (explicit form keeps working everywhere; docs can shorten organically later).


## Behavior Compatibility

- From a project root (cwd contains valid `rules/`): discovered root == cwd — byte-identical behavior.
- From outside any project: no ancestor qualifies → cwd fallback — byte-identical behavior.
- From a project SUBDIRECTORY: previously zero PRJ docs (silent); now the project's docs resolve — the intended fix.
- Nested roots: nearest qualifying ancestor wins (a sub-project shadows its parent), deterministic.
- All existing tests run either with explicit `--root` or chdir'ed to a fixture root → unaffected (proof: suite must stay green unmodified).


## Acceptance Criteria

- A1: `discover_root` unit-tested: cwd-is-root; subdir→root; nested-root nearest-wins; no-marker→start fallback; `rules/` without pattern docs is not a root (walk continues).
- A2: CLI: `af list` invoked from a project subdirectory lists the project's PRJ documents; explicit `--root` still wins over discovery.
- A3: Full suite green with zero modifications to existing tests (compatibility proof).
- A4: `--root` help text + CLI epilog document the discovery default.
- A5: Full gates: pytest, ruff check, ruff format --check, pyright, `af validate`.


## Implementation Plan

1. **RED:** new `tests/test_root_discovery.py` (unit cases A1 + CLI cases A2). Confirm failures.
2. **GREEN:** `discover_root` in context.py (pure; uses `core.document.FILENAME_PATTERN`); `get_root` fallback → `discover_root(Path.cwd())`; help/epilog text.
3. Verify A1–A5.
4. Trinity triad review (glm, deepseek, minimax), COR-1610, all ≥ 9.0; fix convergent findings.
5. PR per COR-1505.

---

## Change History

| Date       | Change                                                                                                     | By               |
|------------|------------------------------------------------------------------------------------------------------------|------------------|
| 2026-06-11 | Initial version — nearest-ancestor rules/ discovery for default root (2026-06-10 review ergonomic finding) | Claude (Fable 5) |
