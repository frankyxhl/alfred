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

Concrete recipient persona: a collaborator's AI coding agent (Claude/ChatGPT/other) that should follow this team's SOPs for one engagement — today the operator would have to hand-copy dozens of files or ask the collaborator to install and configure the CLI plus obtain the private USR/PRJ trees. There is no way to hand over the *complete, layer-merged* runbook as one artifact: pasteable into an AI context, vendorable into another repo as a single reference file, or attached to an onboarding message. The bundled `INIT.md` bootstrap is CLI-dependent ("Run `af read COR-0001`") and useless to a no-install reader.

Measured corpus at proposal time: default scope (Active SOP + REF across three layers) = 118 documents, ~130k words — large but within modern agent context budgets, and filterable far smaller.


## Decisions (resolved from R1 Open Questions, panel-reviewed)

| # | Question | Decision | Rationale (R1 panel) |
|---|----------|----------|----------------------|
| D1 | Default scope | **Active SOP + REF** | Unanimous: REFs (e.g. COR-0002) are referenced BY SOPs — excluding them breaks the self-contained promise; everything-Active drags 57 PRPs + 101 CHGs of history into a hand-off artifact. |
| D2 | `--stamp` provenance line | **Deferred to follow-up CHG** | Unanimous: determinism is load-bearing (vendoring, golden tests, clean diffs); v1 ships strictly deterministic. |
| D3 | Command name | **`export`** | Unanimous: one-way semantics, no collision with the PKG "bundled docs" notion; `pack`/`bundle` evoke archives. |
| D4 | Draft-status documents | **`--status STATUS` single-value filter in v1, default `Active`** | 2:1 (deepseek wanted at least `--include-draft`; minimax generalized to `--status`; both reject pure deferral — "where is my Draft doc?" is the first mid-authoring question). One option, same metadata read as the default gate. |


## Scope

**In scope**

- New command `af export`, registered in `cli.py` `lazy_subcommands`, implemented in `commands/export_cmd.py`.
- **Selection surface**: optional positional `IDS...` (resolved like `af plan`: `PREFIX-ACID` or bare ACID), plus single-value filters `--type`, `--prefix`, `--source`, `--tag` (exact `af list` semantics), plus `--status` (D4, default `Active`), plus `--all`.
- **Routing-detection helper extraction** — the "is routing + Active" check currently inline in `guide_cmd.py` moves to a shared helper (new `core/` surface — this PRP explicitly adds it) so guide and export cannot drift. `guide_cmd.py` is refactored onto it; the existing `tests/test_guide_cmd.py` routing coverage must pass unmodified.
- `--list` **dry-run flag**: prints the export set (one `ID  TYPE  LAYER  STATUS  TITLE` line per doc, plus the summary) and writes **no document content** — the operator can audit exactly what would be shared before generating the artifact.
- Output structure, behaviors, and risk surface as specified below.
- Tests: CLI behaviors for every Specified Behavior below + determinism golden + guide-refactor regression; docs-drift guards force README/CLAUDE.md command-list updates automatically.

**Out of scope**

- Summarization, compression, or token budgeting (export is verbatim; trimming is the selector's job).
- `--redact` content scrubbing — follow-up CHG once a redaction policy is designed; v1 mitigates via §Hand-off Risk below.
- `--stamp` (D2). HTML/PDF/zip outputs; incremental/diff exports; auto-publishing; `af import` round-trip.
- INIT.md and the mkdocs pipeline are not modified — the export's preamble **replaces INIT.md's role for no-install readers**; INIT.md keeps serving installed-CLI bootstrap.


## Proposed Solution

**Command shape**

```
af export [IDS...] [--type TYPE] [--prefix PREFIX] [--source SOURCE] [--tag TAG]
          [--status STATUS] [--all] [--list] [-o FILE] [--root DIR]
```

**Output structure** (stdout by default; `-o/--output FILE` writes the same text atomically):

```
ALFRED RUNBOOK — SINGLE-FILE EXPORT
fx-alfred <version> · <N> documents (PKG <a> · USR <b> · PRJ <c>) · layers merged, routing first · UTF-8

═══════════════════════ HOW TO USE THIS FILE ═══════════════════════
<fixed no-CLI preamble: you are reading the full runbook inline; start
 with the routing documents below to pick the SOP for your task; each
 document begins at a delimiter line carrying ID · TYPE · LAYER ·
 STATUS; every document ID referenced in text (e.g. "per COR-1402") is
 findable in this file via the Contents table.>

═══════════════════════ CONTENTS ═══════════════════════
COR-1103  SOP  PKG  Active  Workflow Routing
... (one line per document, export order, two-space-separated fields)

═══════════════════════ COR-1103 · SOP · PKG · Active ═══════════════════════
<document content, verbatim text>

═══════════════════════ <next id> ... ═══════════════════════
...
```

**Specified behaviors** (R1 panel hunt, all resolved — implementer guesses nothing):

1. **Selection algebra.** Positional IDs bypass ALL filters and scope rules ("you asked for it, you get it" — any type, any status), are de-duplicated keeping first occurrence, and may be freely combined with filters: filters constrain only the non-positional pool, and the result is the union (positional ∪ filtered), de-duplicated. `--all` lifts the default type∈{SOP,REF} and status gates; explicit `--type/--prefix/--source/--tag/--status` filters AND together and also apply under `--all`. Documents with no `Status:` metadata are excluded by the default/`--status` gate (only `--all` or positional IDs include them).
2. **Ordering.** Active routing documents first (PKG→USR→PRJ, at most one per layer, same detection as `af guide` via the shared helper); a layer with no routing doc is silently absent (no placeholder). All remaining documents follow in scanner order (PKG by ACID → USR → PRJ). A routing document — whether selected by scope or named positionally — appears exactly once, in the routing-first block.
3. **Contents table** lists every exported document exactly once, in export order, format `ID  TYPE  LAYER  STATUS  TITLE` (two-space separators, no column padding — deterministic and diff-friendly).
4. **Encoding.** Every document read uses `read_text(encoding="utf-8")` (CHG-2286 contract; PKG Traversable included). `-o` writes UTF-8 via `atomic_write`. The determinism guarantee is **text-level everywhere and byte-level for `-o`**; stdout bytes follow the terminal's stream encoding (platform norm). The header carries `· UTF-8` so recipients/tools know the artifact encoding. Python text-mode reading yields LF regardless of on-disk CRLF — stable across runs.
5. **Per-document failure policy.** A document that raises on read or `parse_metadata` (needed for Status/routing/tag checks) is **skipped with a `⚠ skipped <ID>: <reason>` stderr warning**; the export continues and exits 0 (guide_cmd's established pattern). The summary line reports `skipped N` when N > 0. `Document.tags`' error-swallowing (`[]` on malformed) is mirrored, not redefined; `--tag` filtering reads every candidate document (≈118 reads — acceptable, noted).
6. **`-o` semantics.** Existing file is silently and atomically replaced (`atomic_write`, tempfile + `os.replace`); `-o -` means stdout (Unix convention); `-o <existing-directory>` → `ClickException` exit 1; unwritable target → `atomic_write` cleans its temp file and the error surfaces as exit 1, original file untouched.
7. **Exit codes.** Empty selection → `click.UsageError` (exit 2 — *correcting R1's "exit 1 mirrors af plan" inaccuracy; `af plan` raises UsageError*) with guidance ("no documents matched; try --all, different filters, or positional IDs"). Write failure → exit 1. Per-doc skips → exit 0 (partial export is explicit in stderr). Success → exit 0.
8. **Version line** uses `importlib.metadata.version("fx-alfred")`; on `PackageNotFoundError` (odd dev environments) prints `unknown` — never crashes the export.
9. **Delimiter contract.** A document boundary is a line matching `^═{N,} <ID> · <TYPE> · <LAYER> · <STATUS> ═{N,}$` — the full field pattern, not bare `═` runs. A content line of pure `═` therefore cannot be mistaken for a boundary by pattern-matching consumers; probability of a content line matching the *full* pattern is negligible and accepted (documented in the preamble).
10. **Header counts** always show all three layers (`PRJ 0` shown, never omitted).
11. **Summary/warnings stream.** All human signals (summary, ⚠ lines) go to stderr in every mode; document text is the only stdout/file content. Word count is `len(text.split())` and explicitly approximate (`~` prefix; CJK undercount accepted and documented).

**Hand-off risk surface (v1 mitigations — R1 GLM B2 / minimax A8 / deepseek)**

USR/PRJ layers may contain private material (keys, names, internal processes). v1 ships three concrete mitigations, not just a volume counter:

- **`--list` dry-run** (in scope above): identity-level audit — IDs and titles of exactly what would ship, before anything is generated.
- **stderr warning line** whenever USR+PRJ count > 0: `⚠ includes USR/PRJ content — review for private material before sharing` appended to the summary.
- **`--source pkg` documented as the safe public-only export** (bundled COR docs only) in the command help; the `--help` epilog states the sharing-risk note explicitly.

`--redact` remains the deferred stronger control.

**Implementation sketch** (modular up front — CHG-2302's 150-line function ratchet is a hard cap):

1. `scan_or_fail(ctx)` → corpus (root auto-discovery, CHG-2300).
2. `_select_documents(...)` — selection algebra per behavior 1 (filters reuse `list_cmd` semantics).
3. `_order_documents(...)` — routing-first via the shared `core/` routing helper + scanner order.
4. `_render_header(...)`, `_render_contents(...)`, `_render_document(...)` — pure string builders; orchestrating `export_cmd()` stays well under the ratchet; no single function approaches 150 lines.
5. Output via `click.echo` (stdout) or `atomic_write` (`-o`); summary via stderr.

Estimated: `export_cmd.py` ~200–250 lines across 5–6 functions + shared routing helper (~20 lines moved to `core/`, `guide_cmd` refactored onto it) + ~300 lines of tests.

**Why one file rather than a directory/zip:** the unit of hand-off is "paste/attach/vendor one thing"; a directory reintroduces tooling. Verbatim text + a full-pattern delimiter keeps the artifact greppable and AI-splittable without a parser.


## Open Questions

None — all R1 questions resolved in §Decisions; all R1 behavior gaps resolved in §Specified behaviors.

---

## Change History

| Date       | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | By               |
|------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------|
| 2026-06-12 | Initial draft — single-file runbook export for zero-install consumption                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | Claude (Fable 5) |
| 2026-06-12 | R1 panel [glm 7.9 FIX, deepseek 8.9 FIX, minimax 8.3 FIX — unanimous FIX]. Revision: Open Questions → §Decisions (D1 SOP+REF unanimous; D2 defer --stamp unanimous; D3 export unanimous; D4 --status filter per deepseek+minimax 2:1 over deferral); §Specified behaviors added — 11 numbered contracts covering the panel's 20+ unstated-behavior hunt (selection algebra, dedupe, -o/-o -/directory/unwritable, exit codes incl. B5 correction to UsageError exit 2, encoding incl. Traversable utf-8 + stdout-vs-file determinism boundary, per-doc skip policy, delimiter full-pattern contract, version fallback, summary stream); risk section upgraded per GLM B2/minimax A8 (--list dry-run in v1, ⚠ USR/PRJ stderr warning, --source pkg safe path + help epilog note); B4 module split named up front; B6/A9 corrected — routing-helper extraction acknowledged as new core surface with guide_cmd refactor + test-green requirement in scope; A10 INIT.md replacement sentence added; recipient persona added to §Problem. | Claude (Fable 5) |
