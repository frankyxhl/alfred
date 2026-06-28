# SOP-2315: Tag Documents For Filtering

**Applies to:** FXA project (and any PRJ/USR document with a Status field)
**Last updated:** 2026-06-28
**Last reviewed:** 2026-06-28
**Status:** Active
**Tags:** document, maintain

---

## What Is It?

Procedure for assigning the **`Tags:`** metadata field to documents so they
can be filtered with `af list --tag <tag>`. Tags are a flat, controlled
vocabulary drawn from two dimensions — lifecycle stage and functional domain.
Each document carries 1–3 tags.

`Tags:` is read by `Document.tags` and consumed by `af list --tag`
(case-insensitive exact match). It is **distinct from `Task tags:`**, which
feeds `af plan --task` SOP auto-composition — do not conflate the two.

**Controlled vocabulary** (extend only by amending this SOP):

| Dimension | Tags |
|-----------|------|
| Lifecycle | `routing` `plan` `session` `implement` `review` `ship` `maintain` |
| Domain | `document` `proposal` `change-request` `decision-record` `sop-authoring` `interaction` `tdd` `git` `issue` `diagnosis` `workflow` `pr` `loop` `scoring` `project` `evolution` |

PRJ/USR-only domain tags may also be used where they apply: `release`, `commit`.


## Why

Without a controlled vocabulary, tags drift into synonyms (`review` vs
`reviewing` vs `code-review`) and filtering breaks. A single source of truth
for the tag set — plus a fixed write procedure — keeps `af list --tag`
reliable and lets AI agents self-serve tag maintenance without a human
curating every entry.


## When to Use

- A new PRJ/USR SOP (or other document) is created and needs tags for discovery.
- An existing PRJ/USR document is missing `Tags:` or has stale tags.
- The user asks to "tag", "retag", or "make documents filterable".


## When NOT to Use

- **PKG / COR documents.** `af update` refuses them ("read-only"). COR tag
  changes edit `src/fx_alfred/rules/*.md` package source and **must go through
  a PR** (CHG flow). An AI agent may prepare the edit but must not land it
  outside a reviewed PR.
- Inventing a new tag not in the controlled vocabulary. Amend this SOP first
  (PR), then apply the new tag.
- The `Task tags:` field — that is governed by COR-1202 / `af plan --task`,
  not this SOP.


## Steps

1. **Pick tags** from the controlled vocabulary above — 1–3 per document,
   favouring one lifecycle tag + one or two domain tags. `routing` for routers,
   `scoring` for review rubrics, `loop` for autonomous loops, etc.

2. **PRJ / USR documents — apply via `af tag add`:**
   ```bash
   af tag add <PREFIX-ACID> routing plan --root <project-root>
   ```
   Comma-separated values and multiple positional args are both accepted.
   `af tag add` is idempotent (re-adding an existing tag is a no-op). Use
   `af tag rm <PREFIX-ACID> <tag>` to remove a tag; removing the last tag drops
   the `Tags:` field entirely.

   Alternatively, use `af update --spec` to set the full `Tags:` value in one
   operation (useful when bulk-setting tags from a YAML spec):
   ```bash
   printf 'metadata:\n  Tags: "%s"\n' "routing, plan" > /tmp/tags.yaml
   af update <PREFIX-ACID> --spec /tmp/tags.yaml --root <project-root> -y
   ```

3. **PKG / COR documents — PR only:** do **not** use `af update` (it refuses).
   Edit the `**Status:**` line's successor in `src/fx_alfred/rules/<COR-file>.md`
   to insert `**Tags:** <tags>`, then submit through the standard CHG/PR review
   loop. Never commit COR tag edits to a shared branch without review.

4. **Validate:** `af validate --root <project-root>` must report 0 issues. The
   Tags format check rejects empty or duplicate tags.

5. **Confirm filtering:** `af list --tag <tag> --root <project-root>` returns the
   document. (Use the project's `.venv/bin/af` when a stale global `af` shadows
   the live package layer.)


## Examples

- `COR-1103 Workflow Routing` → `routing, plan`
- `COR-1500 TDD Development Workflow` → `tdd, implement`
- `COR-1608 PRP Review Scoring` → `review, scoring, proposal`
- `FXA-2102 Release To PyPI` → `ship`
- `FXA-2148 Evolve SOP` → `evolution`


---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-06-28 | Initial version | — |
