# PRP-2303: AF Export Single File Runbook

**Applies to:** FXA project
**Last updated:** 2026-06-12
**Last reviewed:** 2026-06-12
**Status:** Draft
**Date:** 2026-06-12
**Requested by:** Frank Xu (2026-06-12 session)

---

## What Is It?

A new `af export` command that flattens the layer-resolved document corpus (PKG + USR + PRJ) into **one self-contained plain-Markdown stream** — a "single-file runbook" a recipient can read with any AI agent (or eyes) **without installing fx-alfred**. The file opens with a no-CLI usage preamble and the routing documents, then carries every selected document verbatim under collision-safe delimiters.


## Problem

The SOPs' value is the text itself, but today there are only two consumption paths, both gated:

1. `pip install fx-alfred` + the user's `~/.alfred` + project `rules/` — full three-layer view, but requires installing and configuring a Python CLI the recipient may not want ("不希望装这些 Alfred 多余程序的人").
2. The mkdocs site — zero-install, but **PKG layer only** (COR docs), a website rather than a hand-off artifact, and never includes the user's USR/PRJ documents.

There is no way to hand a collaborator (human or AI) the *complete, layer-merged* runbook as one artifact: pasteable into an AI context, vendorable into another repo as a single reference file, or attached to an onboarding message. The bundled `INIT.md` bootstrap is CLI-dependent ("Run `af read COR-0001`") and useless to a no-install reader.

Measured corpus at proposal time: default scope (Active SOP + REF across three layers) = 118 documents, ~130k words — large but within modern agent context budgets, and filterable far smaller.


## Scope

**In scope**

- New command `af export`, registered in `cli.py` `lazy_subcommands`, implemented in `commands/export_cmd.py`.
- **Selection surface** mirrors `af list`: optional positional `IDS...` (same resolution as `af plan` — `PREFIX-ACID` or bare ACID), plus `--type`, `--prefix`, `--source`, `--tag` filters, plus `--all`.
- **Default scope** (no IDs, no filters): documents of type `SOP` and `REF` with `Status: Active`, across all three layers. `--all` lifts both the type and status restriction (everything the scanner sees). Explicit positional IDs bypass scope rules entirely (you asked for it, you get it, any type/status).
- **Ordering**: routing documents first (same detection as `af guide`: `Document role: routing` metadata or `SOP-Workflow-Routing` filename, Active only, one per layer in PKG→USR→PRJ order), then all remaining documents in scanner order (PKG by ACID → USR → PRJ).
- **Output structure** (stdout by default; `-o/--output FILE` writes atomically):

  ```
  ALFRED RUNBOOK — SINGLE-FILE EXPORT
  fx-alfred <version> · <N> documents (PKG <a> · USR <b> · PRJ <c>) · layers merged, routing first

  ═══════════════════════ HOW TO USE THIS FILE ═══════════════════════
  <fixed no-CLI preamble: you are reading the full runbook inline; start
   with the routing documents below to pick the SOP for your task; each
   document begins at a ═══ delimiter line carrying ID · TYPE · LAYER ·
   STATUS; document IDs referenced in text (e.g. "per COR-1402") are all
   findable in this same file via the Contents table.>

  ═══════════════════════ CONTENTS ═══════════════════════
  COR-1103  SOP  PKG  Active  Workflow Routing
  ... (one line per document, export order)

  ═══════════════════════ COR-1103 · SOP · PKG · Active ═══════════════════════
  <document content, verbatim bytes>

  ═══════════════════════ <next id> ... ═══════════════════════
  ...
  ```

- **Delimiters are plain text, not Markdown headings** — `═`-rule lines never collide with document content (docs own their `#` headings and ``` fences; a `#`-based wrapper would corrupt the heading hierarchy and fence-blind splitters).
- **Deterministic output**: same corpus + same selection → byte-identical bytes. No timestamp in the body (vendored exports must diff cleanly; tests can golden it). The version line uses the installed fx-alfred version.
- **Human summary to stderr** when writing to a file or pipe: `exported 118 documents (~130k words) — PKG 71 · USR 10 · PRJ 37`, so the operator sees the blast radius of what they are about to share.
- Empty selection (filters match nothing) → exit 1 with a clear error (mirrors `af plan` no-IDs behavior).
- Tests: CLI behaviors (default scope, --all, filters, positional IDs, ordering incl. routing-first, delimiter safety with fence-heavy docs, determinism, -o atomic write, stderr summary, empty-selection failure); docs-drift guards will force README/CLAUDE.md command-list updates automatically.

**Out of scope**

- Summarization, compression, or token budgeting of content (the export is verbatim; trimming is the selector's job).
- Redaction/secret-scanning of USR/PRJ content — the operator reviews what they share (stderr summary supports this); a future `--redact` could layer on.
- HTML/PDF/zip outputs; incremental/diff exports; auto-publishing.
- Import/round-trip (`af import`) — one-way export only.
- Changing INIT.md or the mkdocs pipeline.


## Proposed Solution

**Command shape**

```
af export [IDS...] [--type TYPE] [--prefix PREFIX] [--source SOURCE] [--tag TAG]
          [--all] [-o FILE] [--root DIR]
```

**Implementation sketch** (composes existing core; no new core surface expected)

1. `scan_or_fail(ctx)` → corpus (root auto-discovery applies, CHG-2300).
2. Selection: positional IDs via `find_or_fail` each; else filter pipeline reusing `list_cmd`'s filter semantics (type/prefix/source/tag), then the default `type ∈ {SOP, REF} ∧ Status == Active` gate unless `--all`/filters given. Status read via `parse_metadata` (same as guide_cmd).
3. Ordering: routing-doc detection reused from `guide_cmd` (extract the small "is_routing + Active" check into a shared helper in `core/` or `_helpers` so guide and export cannot drift); stable sort as specified.
4. Rendering: header line (version via `importlib.metadata`), fixed preamble constant, contents table, then per-doc `resolve_resource().read_text()` verbatim between delimiter lines. `emit_json` not involved — this is a text artifact; output via `click.echo`/file write with `atomic_write` for `-o`.
5. Guards already in place keep it honest: function-length ratchet (≤150), emit-through-helper rules don't apply (no JSON), docs-drift guard forces command documentation.

**Why one file rather than a directory/zip:** the unit of hand-off is "paste/attach/vendor one thing"; a directory reintroduces tooling. Verbatim-bytes + delimiters keeps the artifact greppable and AI-splittable without a parser.

**Estimated size:** command ~150–200 lines + ~250 lines of tests; one shared routing-detection helper extraction (~20 lines moved from guide_cmd).


## Open Questions

1. **Default scope** — proposed `Active SOP+REF`. Alternatives: SOP-only (REFs like COR-0002 Document Format Contract are referenced BY SOPs, so excluding them leaves dangling references — hence included); or everything-Active (drags 57 PRPs + 101 CHGs of historical record into a hand-off artifact — noise). Panel input welcome.
2. **Determinism vs provenance stamp** — proposed deterministic body (no date). A `--stamp` flag could add a generated-on line for one-off sends. Include `--stamp` in v1 or defer?
3. **Name** — `export` (proposed) vs `pack`/`bundle`. `export` matches industry convention and doesn't collide with the packaging notion of "bundled PKG docs".
4. **Draft-status PRJ docs** — default excludes them (Active-only). Teams mid-authoring might want `--status` as a filter later; defer unless panel sees v1 need.

---

## Change History

| Date       | Change                                                                  | By               |
|------------|-------------------------------------------------------------------------|------------------|
| 2026-06-12 | Initial draft — single-file runbook export for zero-install consumption | Claude (Fable 5) |
