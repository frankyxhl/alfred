# CHG-2101: Add Multi-Layer Document Scanning

**Applies to:** FXA project
**Last updated:** 2026-03-17
**Last reviewed:** 2026-03-17
**Status:** Approved
**Date:** 2026-03-17
**Requested by:** Frank
**Priority:** Medium
**Change Type:** Normal
**Scheduled:** 2026-03-17
**Related:** FXA-2100-SOP (Leader Mediated Development), COR-1500-SOP (TDD Workflow)

---

## What

Add three-layer document scanning to fx-alfred CLI: PKG (bundled), USR (~/.alfred/), PRJ (rules/). Display source labels in `af list` output.

---

## Why

Currently `af list` only scans project-level directories. Users cannot see bundled COR documents or their own user-level custom documents. This makes the tool less useful across projects.

---

## Impact Analysis

- **Systems affected:** fx_alfred core (document.py, scanner.py), all 5 commands
- **Channels affected:** none
- **Downtime required:** No
- **Rollback plan:** Revert to v0.1.0

---

## Layer Contract

| Layer | Path | Allowed Prefixes | Writable |
|-------|------|-------------------|----------|
| PKG | pip installed `fx_alfred/rules/` | COR only | No |
| USR | `~/.alfred/` | Non-COR only | Yes |
| PRJ | `rules/` in cwd | Non-COR only | Yes |

### Invariants

- COR-* documents may ONLY exist in PKG layer
- COR-* found in USR or PRJ is a hard error with message listing the offending file and layer
- Duplicate ACID across any layers is a hard error (global uniqueness is an intentional CLI constraint)
- Any scan-based command (`list/read/status/create/index`) aborts if layer validation fails
- `af create` writes to PRJ `rules/` only, rejects COR prefix
- `af index` only indexes PRJ layer
- `af read` uses ACID lookup; global uniqueness guarantees no ambiguity
- INIT.md removed from PKG, replaced by `af guide` command

---

## Design Decisions

### ACID Collision: Error on duplicate
If the same ACID exists in multiple layers, `af` must raise an error listing the conflicting sources and layers. No silent shadowing or override.

### COR Enforcement
COR prefix is reserved for PKG layer. Hard error if COR-* found in USR or PRJ.

### `docs/` → `rules/` Migration: Not needed
v0.1.0 has no production users. No migration path required.

### Package Data: Explicit configuration
Configure pyproject.toml to bundle `rules/*.md` in both wheel and sdist distributions via hatchling.

### Resource Abstraction: `resolve_resource()`
Add `resolve_resource()` method to Document that returns a `read_text()`-compatible interface. Uses `Traversable` for PKG layer and `Path` for USR/PRJ. Commands consume this single API without path-type assumptions.

### `af index` Scope: PRJ only
`af index` only generates index for PRJ-level documents. PKG and USR documents are not written into project index files.

### `af guide` Content Source
Guide content is bundled as a markdown file in `fx_alfred/templates/guide.md` and loaded via `importlib.resources`, consistent with PKG layer pattern.

### Fail-Fast Behavior
All scan-based commands abort immediately if layer validation fails. No partial results.

---

## Implementation Plan

| # | TDD Cycle | Description |
|---|-----------|-------------|
| 1 | Document model | Add `source`, `base_path` fields and `resolve_resource()` method |
| 2 | Package data | Configure pyproject.toml to bundle `rules/*.md` in wheel + sdist |
| 3 | Scanner helper | `_scan_dir` using Traversable for PKG, Path for USR/PRJ |
| 4 | Scanner PKG | Scan bundled `fx_alfred/rules/` via `importlib.resources` Traversable |
| 5 | Scanner USR | Scan `~/.alfred/` |
| 6 | Scanner PRJ | Scan `rules/` only (no `.alfred/`) |
| 7 | Layer validation | COR in USR/PRJ = error, duplicate ACID = error |
| 8 | `af list` | Show PKG/USR/PRJ labels, tab-separated |
| 9 | `af read` | Use `doc.resolve_resource().read_text()` |
| 10 | `af create` | Write to `rules/`, reject COR prefix, check ACID collision |
| 11 | `af status` | Add "By source" counts |
| 12 | `af index` | Generate index for PRJ layer only |
| 13 | `af guide` | New command, replaces INIT.md, content from `templates/guide.md` |
| 14 | Docs update | Update README.md, remove INIT.md, fix `docs/` references in COR docs |
| 15 | Version | Bump to 0.2.0 |

---

## Testing / Verification

- All existing tests updated and passing
- New tests for each layer (PKG, USR, PRJ)
- Negative test: COR-* in USR → error with offending file and layer in message
- Negative test: COR-* in PRJ → error with offending file and layer in message
- Negative test: duplicate ACID across layers → error with both sources in message
- Test `resolve_resource()` works for PKG (Traversable) and USR/PRJ (Path)
- Test `af list` in empty project shows PKG documents
- Test `af read 1500` reads bundled COR-1500 from any directory
- Test installed wheel contains rules/*.md (wheel packaging check)
- Test sdist contains rules/*.md (sdist packaging check)
- Install-like CLI smoke test: `af list` and `af read` work from installed package
- Test `af guide` outputs onboarding content
- Test `af create` rejects COR prefix
- Test `af index` only indexes PRJ documents
- Command-level failure test: invalid layer state breaks a real command, not just scanner
- Dual code review (Codex + Gemini) per FXA-2100-SOP, both ≥ 9/10

---

## Approval

- [x] Reviewed by: Frank
- [x] Approved on: 2026-03-17

---

## Execution Log

| Date | Action | Result |
|------|--------|--------|
| 2026-03-17 | Task assigned to Droid (Coder) | In progress |

---

## Post-Change Review

- (to be filled after completion)

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-17 | Initial version | Claude Code |
| 2026-03-17 | Updated per Codex+Gemini plan review: added design decisions (ACID collision, package-data, centralized path, index scope), expanded TDD cycles | Claude Code |
| 2026-03-17 | Round 3-4 updates: Layer Contract, removed PRJ .alfred/, resolve_resource() API, fail-fast, af guide, Codex 10/10 details | Claude Code |
| 2026-03-20 | Migrated to Document Format Contract: fixed H1, normalized metadata prefix, added Applies to/Last updated/Last reviewed | af CLI |
