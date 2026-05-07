# CHG-2275: FXA-2102 Promote README Check To Numbered Step

**Applies to:** FXA project
**Last updated:** 2026-05-07
**Last reviewed:** 2026-05-07
**Status:** Proposed
**Date:** 2026-05-07
**Requested by:** —
**Priority:** Medium
**Change Type:** Normal

---

## What

Promote the README check in `FXA-2102 Release To PyPI` from a Prerequisites bullet to a numbered, fully-described Step (new Step 2). Renumber the remaining steps 3-7 accordingly. Update the Prerequisites bullet to point at the new Step 2 for clarity.


## Why

During this session's release work for v1.12.0 and v1.13.0, the README update was silently skipped twice. The operator had to remind the agent ("pls don't forget to update README as well") during v1.12.0 and again ask "we have a release gate SOP for this?" during v1.13.0. Root cause: the check sat in Prerequisites and was never referenced in the Steps section, so a top-down read of the SOP missed it.

Promoting the check to a numbered Step makes it impossible to skip when working through the SOP linearly, and adds a concrete verification command (`git diff main -- README.md`) so the operator can confirm the change actually landed.


## Impact Analysis

**Files changed**

- `rules/FXA-2102-SOP-Release-To-PyPI.md` — single file; insert new Step 2; renumber Steps 3-7; tweak Prerequisites bullet to reference Step 2; add Change History row.

**Behavioural impact**

- Future release runs follow an explicit README step instead of relying on the operator to remember the Prerequisites bullet.
- Existing release work (v1.13.0 already shipped) is unaffected — this is an SOP wording change, not a code change.

**Out of scope** (explicitly deferred per operator decision)

- Versioning guidance (patch vs minor vs major) — not added.
- Branch policy clarification (release commits via feature-branch PR vs direct push) — not added.
- `gh auth status` identity gate as a Prerequisite — not added.
- Step 7 wording about "related CHG" — not clarified.

These four items were considered and explicitly de-scoped.


## Implementation Plan

1. Edit the Prerequisites bullet from `README up to date (FXA-2136 Update README SOP)` to `README updated per Step 2 below (FXA-2136 Update README SOP)`.
2. Insert new Step 2 between current Step 1 (Verify readiness) and current Step 2 (Create GitHub Release):
   - Title: "Update README per FXA-2136 (skip only when the release contains zero user-facing changes)"
   - Body: short bulleted list — bump NEW-in line, add new commands, confirm Quick Start, update Key SOPs table if applicable, commit before tagging, verification command.
3. Renumber the original Steps 2-6 to 3-7. (Specifically: "Create GitHub Release" → 3; "Wait for CI" → 4; "Verify CI passed" → 5; "Verify on PyPI" → 6; "Update CHG document" → 7.)
4. Add Change History row dated 2026-05-07 referencing FXA-2275.
5. Run `af validate --root .` to confirm no structural issues.
6. Commit + push + open PR; tag-style review (Codex bot only — no Trinity since change is below the trivial threshold per operator decision).


---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-07 | Initial version | — |
