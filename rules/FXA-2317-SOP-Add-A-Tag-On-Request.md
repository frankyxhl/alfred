# SOP-2317: Add A Tag On Request

**Applies to:** FXA project (and any PRJ/USR document with a Status field)
**Last updated:** 2026-06-29
**Last reviewed:** 2026-06-29
**Status:** Active
**Tags:** document, maintain

---

## What Is It?

The repeatable runbook an agent follows when the user says *"add a tag"* (e.g.
*"按这个 SOP 帮我加个 tag `todo`"*). It routes the request to the correct layer —
a **personal/workflow tag** the user self-serves at the user layer, or a
**system semantic tag** that must go through a PR — then writes it and verifies.

This SOP is the *operational* companion to [[FXA-2315]] (the vocabulary +
document-tagging contract). FXA-2315 defines **what** the tags are and how to
put them on a document; this SOP defines **how to extend the allowed set** on
request and which path a given tag takes.


## Why

The allowed-tag vocabulary has two tiers:

- **System semantic tags** — the `CONTROLLED_TAGS` frozenset in
  `src/fx_alfred/core/schema.py`, mirrored in FXA-2315. Shared across all
  projects; changing them edits package source, so they go through a **PR**.
- **Personal/workflow tags** — words like `todo`, `wip`, `later` that matter to
  one user's workflow and do **not** belong in the shared vocabulary. These live
  in `~/.alfred/preferences.yaml` under `custom_tags` and are managed with
  `af tag vocab` — **no PR, no code change**.

Without a fixed decision rule, every "add a tag" request risks the wrong path:
a personal marker bloating the shared vocabulary, or a genuine semantic tag
hiding in one user's local config. This SOP makes the routing deterministic so
the user can just name a tag and trust the agent to place it correctly.


## When to Use

- The user asks to add / register / allow a new tag, by name.
- A tag the user wants triggers an out-of-vocabulary warning from
  `af tag add` or `af validate`, and they want it to stop warning.


## When NOT to Use

- **Applying an already-allowed tag to a document.** That is plain
  [[FXA-2315]] §Steps (`af tag add <DOC> <tag>`) — no vocabulary change needed.
- **Backfilling many documents with existing-vocabulary tags.** Use the
  AI-assisted backfill flow in [[FXA-2318]], not this one.
- **The `Task tags:` field** — governed by COR-1202 / `af plan --task`, never
  this SOP.


## Steps

1. **Classify the tag — personal or system?** Ask one question if unclear, but
   default by content:
   - *Personal/workflow marker* (state of work to **this** user: `todo`, `wip`,
     `later`, `urgent`, `blocked`) → **user layer** (Step 2).
   - *Semantic/domain tag* meaningful to **anyone** filtering the corpus, and
     intended to be shared / committed (a new lifecycle or domain dimension) →
     **system layer, via PR** (Step 3).

2. **Personal tag — user layer (no PR):**
   ```bash
   af tag vocab add <tag> [<tag> ...]   # writes ~/.alfred/preferences.yaml custom_tags
   af tag vocab ls                      # confirm it is registered
   ```
   `af tag vocab` is user-global — it takes **no `--root`**. After this,
   `af tag add` and `af validate` treat the tag as in-vocabulary (no warning),
   because the vocab check unions `CONTROLLED_TAGS` with the user's
   `custom_tags`. Remove with `af tag vocab rm <tag>`.

3. **System tag — package layer (PR required):** prepare, but do **not** land
   outside a reviewed PR:
   - Add the tag to `CONTROLLED_TAGS` in `src/fx_alfred/core/schema.py`.
   - Add it to the controlled-vocabulary table in [[FXA-2315]] (the drift test
     `tests/test_tag_vocab_drift.py` enforces the two stay in sync).
   - Run the suite + `af validate`, open a PR per the normal review flow.

4. **(Optional) Backfill the tag onto documents** that should carry it:
   ```bash
   af tag add <PREFIX-ACID> <tag> --root <project-root>
   ```
   PKG/COR documents are read-only — route those through a PR per [[FXA-2315]].

5. **Verify.** `af tag vocab ls` shows a personal tag; `af validate --root <root>`
   reports **0 issues** and does not flag the new tag; for a system tag, the
   drift test passes.

---

## Change History

| Date       | Change                                                        | By          |
|------------|---------------------------------------------------------------|-------------|
| 2026-06-29 | Initial version — operational runbook for FXA-256 custom_tags | Claude Code |
| 2026-06-29 | Update #253 backfill cross-ref to [[FXA-2318]]                | Claude Code |
