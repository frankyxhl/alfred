# SOP-2318: Backfill Tags Across The Corpus

**Applies to:** FXA project (and any PRJ/USR document corpus with a Status field)
**Last updated:** 2026-06-29
**Last reviewed:** 2026-06-29
**Status:** Active
**Tags:** document, maintain

---

## What Is It?

A repeatable, AI-assisted loop for keeping the document corpus **completely and
correctly tagged**: scan for documents that are missing tags or carry
out-of-vocabulary tags, read each candidate to understand its purpose, propose
1–3 controlled-vocabulary tags with rationale, get human confirmation, write the
tags, and re-validate.

It is the *batch* complement to the two single-document tag SOPs:

- [[FXA-2315]] — the vocabulary and how to tag **one** document.
- [[FXA-2317]] — how to **add a new tag** to the allowed set on request.
- **This SOP (FXA-2318)** — how to **find and fill gaps** across the **whole**
  corpus.


## Why

Correct backfilling cannot be done purely mechanically: choosing the right tag
requires reading each document's purpose (`routing` for a router, `scoring` for
a review rubric, `loop` for an autonomous loop, …). Left to ad-hoc effort,
coverage drifts — new documents ship untagged and `af list --tag` silently
misses them. This SOP turns backfill into a deterministic, confirmable loop an
AI agent can drive, so the corpus stays filterable without a human curating
every entry.


## When to Use

- After a batch of documents is created or imported and needs tags.
- Periodically, to close coverage gaps (untagged SOPs, out-of-vocabulary tags).
- When `af validate` reports out-of-vocabulary tag instances or untagged SOPs
  and you want them reconciled against the controlled vocabulary.


## When NOT to Use

- **Single-document tagging** — just use [[FXA-2315]] §Steps directly.
- **Registering a brand-new personal/workflow tag** (e.g. `todo`, or USR-layer
  domain terms like machine/network names) — that is [[FXA-2317]]; do **not**
  rewrite those documents to force-fit the system vocabulary. Out-of-vocabulary
  tags on **personal USR documents** are usually intentional and should be
  registered with `af tag vocab add`, not backfilled.
- **PKG / COR documents** — read-only; tag changes go through a PR per
  [[FXA-2315]]. Propose the edit, never land it outside review.


## Steps

1. **Find candidates** using the `af validate` checks as the candidate-finders:
   ```bash
   # untagged SOP documents (missing the Tags: field) — SOP type only
   af validate --root <project-root> --warn-untagged-sops
   # out-of-vocabulary tags on ANY document type
   af validate --root <project-root> --tag-warnings detail
   ```
   Build a working list of `(document, gap-type)` pairs. Note the asymmetry: the
   out-of-vocabulary check is corpus-wide, but untagged-detection currently covers
   **SOP documents only** — there is no built-in untagged finder for PRP/CHG/REF/
   etc. (a known tooling gap; extend this SOP if one is added). An empty result
   from both finders means the covered surface is fully tagged — stop here.

2. **Triage each candidate by layer / intent** before proposing anything:
   - *Untagged PRJ/USR document* → propose tags (Step 3).
   - *Out-of-vocabulary tag on a **personal** USR document* → this is an
     [[FXA-2317]] case, not a backfill. Route to `af tag vocab add <tag>` (register
     the personal term) rather than re-tagging. Record it and move on.
   - *Out-of-vocabulary tag on a **PRJ/COR** document* → the tag is genuinely
     wrong; propose a correct controlled-vocabulary replacement (Step 3).

3. **Read and propose.** For each document that needs tags, read its content and
   propose **1–3** tags from the controlled vocabulary in [[FXA-2315]] (favour one
   lifecycle tag + one or two domain tags), each with a one-line rationale tied to
   the document's purpose. Never invent a tag here — if no vocabulary tag fits,
   the vocabulary itself is the gap: stop and route to [[FXA-2317]] (system-tag PR).

4. **Confirm with the human.** Present the full proposal list (document → proposed
   tags + rationale) and wait for explicit approval. Do not write on assumption.
   The human may accept, amend, or reject per document.

5. **Write** the approved tags:
   ```bash
   # Untagged / under-tagged document — add the approved tags
   af tag add <PREFIX-ACID> <tag> [<tag> ...] --root <project-root>

   # REPLACING an out-of-vocabulary tag — remove the bad one, then add the fix
   af tag rm  <PREFIX-ACID> <bad-tag>  --root <project-root>
   af tag add <PREFIX-ACID> <good-tag> --root <project-root>
   ```
   `af tag add` only **appends** — it does not drop the existing value. For an
   out-of-vocabulary correction you must `af tag rm` the bad tag (otherwise Step 6
   keeps reporting the same warning). Alternatively, `af update --spec` sets the
   full `Tags:` value in one operation (replace, not merge). PKG/COR documents are
   read-only — prepare those as a PR per [[FXA-2315]], never a direct write.

6. **Re-confirm coverage.** Re-run the Step 1 finders; both must come back empty:
   ```bash
   af validate --root <project-root> --warn-untagged-sops --tag-warnings detail
   ```
   Gate on these finders, **not** on the plain `af validate` "0 issues" line — tag
   gaps are *warnings*, not issues, so that line stays green even on an untagged
   corpus. Personal USR tags you registered with `af tag vocab add` in Step 2 are
   now *in* the vocabulary and produce **no** warning; any out-of-vocabulary
   warning that remains is a genuine unhandled candidate — loop back to Step 2.


## Examples

```bash
# 1. Scan
af validate --root . --warn-untagged-sops --tag-warnings detail

# 3-5. After reading FXA-2400 (a hypothetical new PRJ router) and confirming:
af tag add FXA-2400 routing plan --root .
#   A PKG/COR doc (e.g. COR-1103) cannot be written directly — af tag add
#   refuses it as read-only; prepare those as a PR per FXA-2315.

# 6. Confirm coverage with the finders (not a plain validate)
af validate --root . --warn-untagged-sops --tag-warnings detail
```

---

## Change History

| Date       | Change                                                                | By          |
|------------|-----------------------------------------------------------------------|-------------|
| 2026-06-29 | Initial version — AI-assisted corpus-wide tag backfill loop (FXA-253) | Claude Code |
