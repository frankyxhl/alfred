# CHG-2291: COR-1622 Test-Writer-Worker-Agent Schema Row

**Applies to:** FXA project
**Last updated:** 2026-05-17
**Last reviewed:** 2026-05-17
**Status:** Approved
**Related:** PRP-1507 (Two-Worker TDD Dispatch — design source), GitHub issue #175, CHG-2287 / CHG-2288 / CHG-2289 / CHG-2290 (the four amendments that consume this schema row), GitHub issue #176 (CHG-E — alfred's PRJ-layer opt-in via FXA-2276, depends on this CHG merging)
**Date:** 2026-05-17
**Requested by:** @frankyxhl
**Priority:** Medium
**Change Type:** Normal
**Targets:** src/fx_alfred/rules/COR-1622-REF-Multi-Agent-Loop-Project-Configuration.md §Worker dispatch (COR-1619)

---

## What

Append a new optional `<test-writer-worker-agent>` row to the §Worker dispatch (COR-1619) parameter table in `src/fx_alfred/rules/COR-1622-REF-Multi-Agent-Loop-Project-Configuration.md`. The row uses the same five-column shape as every other row in the table (`Key | Type | Required | Default | Description`) and defaults to the same value as `<worker-agent>` so non-adopters see zero behaviour change. Content is verbatim from PRP-1507 §Proposed Solution lines 162–164.

The row enables three downstream amendments: CHG-A's Phase 1 sub-section gates on it; CHG-B's implementer reading constraint gates on it (transitively via the Phase 1 sub-section); CHG-C1's §Two-Worker TDD Dispatch contract gates on it (transitively via COR-1500); CHG-C2's `P` node tests it directly. Without this row, the four amendments either reference an undefined parameter (lints flag) or have no operative effect (no project can opt in).

## Why

The parameter is the single switch that turns the two-worker split ON for an adopter. PRP-1507 §Decisions item 3 chose opt-in default (split OFF for non-adopters), achieved by defaulting the parameter to the same value as `<worker-agent>` — when equal, COR-1500's Phase 1 sub-section's "OFF" branch triggers and Mandatory Rule #3 alone applies. Setting the parameter to a distinct value (different model OR same model with different `:instance` suffix per the row's note) turns the split ON for that project.

The verbose name `<test-writer-worker-agent>` was deliberately chosen (PRP-1507 §Decisions item 4) over shorter alternatives (`<test-worker-agent>`, `<red-worker-agent>`) for semantic precision — the slot is specifically a *writer* of tests at RED, not a generic test-related worker. The MUST-level note about `:instance` suffix verification (added in R3.5 from MiniMax R2 P2 advisory) prevents adopters from naively setting `<test-writer-worker-agent> = glm:writer` and `<worker-agent> = glm:impl` without checking whether their dispatch backend actually gives the two suffixes distinct contexts.

## Out of Scope

- Editing the §Worked Example table in COR-1622 — that table illustrates trinity's instantiation only; trinity's PRJ REF (TRN-1209) decides whether to set the new parameter and is amended separately if trinity adopts. Alfred's instantiation (FXA-2276) is in its own PRJ-layer file.
- Setting alfred's value for the new parameter — lands as CHG-E (separate PR per PRP-1507 §Implementation Plan, tracked in issue #176; this CHG only adds the schema row, not any project's value).
- Changing existing parameter rows (`<worker-agent>`, `<worker-min-loc>`, others) — separate surfaces; not in PRP-1507 §Implementation Plan.
- Modifying §Guard Rails or §Placeholder Convention — the new parameter is gated by the COR-1500 / COR-1619 amendments; no new guard rail is required at the schema layer beyond what those SOPs already declare.
- Renaming the parameter to a shorter form — PRP-1507 §Decisions item 4 resolved this; re-opening requires a follow-up PRP per the §Decisions re-evaluation-trigger contract (≥ 3 adopters report the name as a usability barrier).

## Impact Analysis

- **Systems affected:** `src/fx_alfred/rules/COR-1622-REF-Multi-Agent-Loop-Project-Configuration.md` only (one new row appended to one table; the §Worked Example table is not modified in this CHG).
- **Behavioural impact:** All existing adopters (trinity and any other project that instantiates COR-1622) see zero behaviour change — the new row is optional (Required = no) and defaults to the same value as `<worker-agent>`. The Phase 1 sub-section's "OFF when equal or unset" branch applies until an adopter explicitly opts in by setting a distinct value.
- **Compatibility:** Backwards-compatible. Every existing PRJ REF that does not declare the new key gets the default automatically (equal to `<worker-agent>`), which matches today's single-worker behaviour. No existing parameter row's column shape, type, default, or description changes.
- **Risk surface:** Very low. The schema-row column order matches the existing table verbatim (Codex caught a column-order mismatch in PRP-1507 R3 P1 — fixed in the panel-approved R6 text used here). The row's MUST-level `:instance` verification note is the only normative content beyond declaring the key.
- **Rollback plan:** Revert this commit. The row vanishes; CHG-A/B/C1/C2's references to `<test-writer-worker-agent>` become dangling, so the bundle PR revert covers all five CHGs together.

## Acceptance Criteria

- A1: `src/fx_alfred/rules/COR-1622-REF-Multi-Agent-Loop-Project-Configuration.md` §Worker dispatch (COR-1619) parameter table contains a new row keyed `<test-writer-worker-agent>` appended after the existing `<worker-min-loc>` row.
- A2: The new row's column shape matches the existing rows verbatim: `Key | Type | Required | Default | Description` in that order. (Codex bot R3 P1 caught an earlier column-order bug in the PRP draft; verify against the live table in the file at the time of the edit, not against any cached snapshot of the schema.)
- A3: The row content matches PRP-1507 §Proposed Solution lines 162–164 verbatim:
  - Type: `string`
  - Required: `no`
  - Default: `same value as <worker-agent>`
  - Description: the full sentence including the MUST-level `:instance` verification note.
- A4: No existing row in any table in COR-1622 is modified. (Schema rows for `<repo>`, `<repo-owner>`, `<repo-trusted-reactor-list>`, `<gh-write-identity>`, `<pr-push-remote>`, consent-gate rows, review-panel rows, the other §Worker dispatch row `<worker-agent>` and `<worker-min-loc>`, R-count cap rows, resilience rows, bot-polling row, and loop-primitives rows — all unchanged.)
- A5: §Worked Example, §Guard Rails, and §Placeholder Convention are unchanged.
- A6: `Last updated` and `Last reviewed` in COR-1622 frontmatter are updated to 2026-05-17.
- A7: A Change History row dated 2026-05-17 referencing CHG-D (FXA-2291) and PRP-1507 is appended.
- A8: `af validate --root /Users/frank/Projects/alfred` reports 0 issues after the edit.
- A9: This CHG document (`rules/FXA-2291-CHG-COR-1622-Test-Writer-Worker-Agent-Schema-Row.md`) exists, has `Status: Proposed` on creation and is moved to `Status: Completed` in the merge commit.

## Implementation Plan

1. Open `src/fx_alfred/rules/COR-1622-REF-Multi-Agent-Loop-Project-Configuration.md`.
2. Locate the §Worker dispatch (COR-1619) parameter table.
3. Append a new table row after the existing `<worker-min-loc>` row with the verbatim content from PRP-1507 §Proposed Solution lines 162–164.
4. Update `Last updated` and `Last reviewed` to 2026-05-17.
5. Append a Change History row dated 2026-05-17 referencing CHG-D (FXA-2291) and PRP-1507.
6. Run `af validate --root /Users/frank/Projects/alfred`; expect 0 issues.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-17 | Initial version — drafted as CHG-D of PRP-1507 §Implementation Plan, bundled with CHG-A/B/C1/C2 in PR closing issue #175 | Claude Opus 4.7 |
| 2026-05-17 | R1 plan-review panel (alfred triad, gemini substituted for minimax which hit usage limit): glm 9.97, deepseek 10.0, gemini 10.0 — PASS, blocking == []. No advisories on this CHG specifically. Status moved Proposed → Approved. | Claude Opus 4.7 |
