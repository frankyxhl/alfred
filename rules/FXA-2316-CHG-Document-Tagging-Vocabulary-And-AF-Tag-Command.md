# CHG-2316: Document Tagging Vocabulary And AF Tag Command

**Applies to:** FXA project
**Last updated:** 2026-06-29
**Last reviewed:** 2026-06-28
**Status:** Completed
**Tags:** change-request
**Date:** 2026-06-28
**Requested by:** Frank Xu (@ryosaeba1985)
**Priority:** Medium
**Change Type:** Normal
**Related:** #247, FXA-2315

---

## What

Three coordinated changes that turn the latent `af list --tag` filter into a
usable tagging system:

1. **Data** — populate the `**Tags:**` metadata field on 79 SOPs (69 PKG/COR +
   10 PRJ/FXA) using a controlled vocabulary.
2. **Governance** — new SOP **FXA-2315** defining the controlled tag vocabulary
   and the add procedure (PRJ/USR via `af update --spec`; PKG/COR via PR).
3. **Tooling** — new **`af tag`** CLI subcommand: `af tag` lists every distinct
   tag with counts (alphabetical); `af tag <name>` lists all documents carrying
   that tag. Both support `--json` and `--root`.


## Why

`af list --tag` shipped but no document carried a `Tags:` field, so filtering
always returned empty. Without a controlled vocabulary, free-form tags drift
into synonyms and filtering breaks; without an enumeration command, users
cannot discover which tags exist. This change makes SOPs filterable by a stable
tag set and gives tag discovery a first-class command.


## Impact Analysis

- **Systems affected:** `fx_alfred` CLI (new `tag` command, LazyGroup entry);
  69 bundled PKG/COR documents gain a `Tags:` line; 10 PRJ SOPs + 1 new SOP;
  `CLAUDE.md` command list + module inventory.
- **Channels affected:** none.
- **Downtime required:** No.
- **Behavior change:** additive only — no existing command output changes;
  `af tag` is new; `Tags:` is an optional metadata field already supported by
  the parser, `af validate`, and canonical ordering.
- **Rollback plan:** revert the feature branch / PR commit. The `Tags:` lines
  and `af tag` command are self-contained; removing them restores prior
  behavior with no migration. FXA-2315 can be deprecated via COR-1301.


## Implementation Plan

1. Populate `**Tags:**` on 10 PRJ SOPs (direct insert after the `**Status:**`
   line — tags-only diff, no date/table churn) and 69 PKG/COR SOPs (edit
   `src/fx_alfred/rules/*.md`; `af update` refuses PKG by design).
2. Author FXA-2315 (controlled vocabulary + procedure); `af index`.
3. Implement `af tag` under TDD (COR-1500): `tests/test_tag_cmd.py` RED →
   `commands/tag_cmd.py` GREEN; register in `cli.py`; update `CLAUDE.md`
   (command list + module inventory) to satisfy `tests/test_docs_drift.py`.
4. Multi-model review (COR-1602) before merge; PR under `ryosaeba1985`.


## Testing / Verification

- `.venv/bin/pytest -q` → 1276 passed, 2 skipped (incl. 14 new `test_tag_cmd`).
- `.venv/bin/ruff check .` clean; `ruff format --check .` clean; `pyright src/`
  0 errors.
- `af validate --root .` → 0 issues (319 docs).
- `af tag` shows alphabetical tags+counts; `af tag review` → 21 docs;
  `af tag review --json` → valid JSON.
- Rollback verification: reverting the branch removes `af tag` and the `Tags:`
  lines; `af validate` stays green (Tags is optional).


## Approval

- [ ] Reviewed by: COR-1602 multi-model panel (GLM worker + Codex/Gemini reviewers)
- [ ] Approved on: YYYY-MM-DD


## Execution Log

| Date | Action | Result |
|------|--------|--------|
| 2026-06-28 | Tagged 79 SOPs; created FXA-2315; implemented `af tag` (TDD) | Suite green, validate 0 issues |
| 2026-06-28 | Filed issue #247 (blueprint-ready) | Done |


## Post-Change Review

- Pending merge. Follow-ups under consideration: optional `af validate`
  controlled-vocabulary warning for out-of-vocab tags; normalizing the 5
  legacy ad-hoc-tagged REF/CHG docs (FXA-2212/2237/2242/2243/2247) into the
  controlled vocabulary.


---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-06-28 | Initial version | — |
| 2026-06-29 | Shipped in v1.23.0 (af tag + tagging vocabulary, FXA-2315) | Claude Code |
