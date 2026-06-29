# SOP-1003: Tag Document

**Applies to:** All projects using the COR document system
**Last updated:** 2026-06-29
**Last reviewed:** 2026-06-29
**Status:** Active
**Tags:** document, maintain
**Disposition:** optional-overlay

---

## What Is It?

The standard process for assigning **tags** to documents so they can be filtered
with `af list --tag <tag>`. Tags are a flat, controlled vocabulary written to the
`Tags:` metadata field (1–3 per document, distinct from `Task tags:`). This SOP
defines the **mechanism and process** that work in every project.

The *enforced* allowed set is the built-in `CONTROLLED_TAGS` (in package source
`core/schema.py`) unioned with each user's personal `custom_tags` — the CLI does
not read any SOP to determine it. A project records its recommended vocabulary and
conventions in a PRJ-layer SOP that overlays this one (declared with
`**Overlays:** COR-1003`); for the FXA project that overlay is FXA-2315, kept in
sync with `CONTROLLED_TAGS` by a drift test.

It has three sub-flows, each with a dedicated tool:

- **Tag a document** — put existing-vocabulary tags on one document (`af tag add`).
- **Extend the vocabulary** — register a new allowed tag (`af tag vocab add` for a
  personal tag; a PR for a shared/system tag).
- **Backfill the corpus** — find and fill gaps across many documents.

---

## Why

Without a controlled vocabulary and a fixed write process, tags drift into
synonyms (`review` / `reviewing` / `code-review`) and filtering silently breaks.
A single source of truth for the tag set, plus the `af tag` commands as the write
path, keeps `af list --tag` reliable and lets agents self-serve tag maintenance
without a human curating every entry.

---

## When to Use

- A new document is created and needs tags for discovery.
- An existing document is missing `Tags:` or carries stale/wrong tags.
- The user asks to "tag", "retag", or "make documents filterable", or to add a
  new tag to the allowed set.

---

## When NOT to Use

- **PKG / COR documents.** `af tag add`/`af update` refuse them ("read-only").
  Their tag changes edit package source and **must go through a PR**. An agent may
  prepare the edit but must not land it outside review.
- **The `Task tags:` field** — that drives plan composition (`af plan --task`),
  not document filtering; it is governed separately.
- **Inventing a tag not in the vocabulary** — first extend the vocabulary (Step 2),
  then apply it.

---

## Steps

1. **Tag a document (existing vocabulary).** Pick 1–3 tags from the allowed set —
   the built-in `CONTROLLED_TAGS` plus any registered personal `custom_tags` —
   favouring one lifecycle tag + one or two domain tags. The project's PRJ overlay
   SOP documents the recommended vocabulary (the CLI enforces `CONTROLLED_TAGS`,
   not the SOP text). Then write:
   ```bash
   af tag add  <PREFIX-ACID> <tag> [<tag> ...] --root <project-root>
   af tag rm   <PREFIX-ACID> <tag>             --root <project-root>   # remove (replace = rm then add)
   af tag ls                                                            # list tags already IN USE, with counts
   af tag show <tag>                                                    # documents carrying a tag
   ```
   `af tag add` is idempotent and only **appends**; to fix a wrong tag, `af tag rm`
   it (or set the full value with `af update --spec`).

2. **Extend the vocabulary** when no existing tag fits:
   - *Personal / workflow tag* (meaningful to one user: `todo`, `wip`, …) →
     `af tag vocab add <tag>`. This registers it in the user's
     `~/.alfred/preferences.yaml` `custom_tags`, which the vocabulary check unions
     with the system set — no PR, no warning afterward. `af tag vocab ls` lists the
     user's custom tags.
   - *Shared / system tag* (meaningful to anyone filtering the corpus) → add it to
     `CONTROLLED_TAGS` in package source (`core/schema.py`) **and** the project's
     overlay SOP, then submit a **PR**. The CLI enforces the built-in set, so a tag
     only listed in the SOP still warns until it is in `CONTROLLED_TAGS`.

3. **Backfill the corpus.** To close coverage gaps across many documents, scan for
   candidates, read each, propose tags, confirm, write, and re-scan:
   ```bash
   af validate --root <project-root> --warn-untagged-sops --tag-warnings detail
   ```
   Gate completion on the finders coming back empty — tag gaps are *warnings*, not
   issues, so a plain `af validate` "0 issues" line does not prove coverage.

4. **Verify.** `af validate --root <project-root>` reports 0 issues; `af list --tag
   <tag> --root <project-root>` returns the document; and for a newly registered
   personal tag, `af tag add`/`af validate` no longer warn about it.

---

## Examples

- A new router SOP → `routing, plan`
- A TDD workflow SOP → `tdd, implement`
- A release SOP → `release, ship`
- Registering a personal marker: `af tag vocab add todo` → `todo` stops warning.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-06-29 | Initial version — COR-level tagging mechanism + process | Claude Code |
