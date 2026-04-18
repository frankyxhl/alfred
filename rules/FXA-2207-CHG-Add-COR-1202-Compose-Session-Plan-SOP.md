# CHG-2207: Add COR 1202 Compose Session Plan SOP

**Applies to:** FXA project
**Last updated:** 2026-04-18
**Last reviewed:** 2026-04-18
**Status:** Approved
**Date:** 2026-04-18
**Requested by:** Frank
**Priority:** Medium
**Change Type:** Normal
**Scheduled:** ASAP
**Related:** FXA-2205 (parent rollout), FXA-2206 (ASCII renderer follow-ups)

---

## What

Add a new PKG-layer SOP — **COR-1202: Compose Session Plan** — that ships with fx-alfred and gives every user a named, ID-addressable procedure for turning a one-sentence task description into a complete session workflow plan (ASCII graph + Mermaid + flat TODO), from session-start through task-completion.

The SOP is a thin but authoritative wrapper over the `af plan --task … --todo --graph` capability shipped in FXA-2205 (PRs #43–#46) and refined in FXA-2206 (PR #47). It codifies the canonical invocation, the when-to-use / when-not-to-use boundaries, the expected output shape, and the feedback loop for missing `Task tags`.

**Out of scope:** no new CLI flags, no behavior change in `af plan`, no new metadata fields. Pure documentation addition.


## Why

1. **Named entry point.** Today users have to remember the exact flag combination (`af plan --root . --task "…" --todo --graph`) and its UX nuances (composed SOPs list, ASCII vs Mermaid, tag coverage gaps). A stable COR-ID gives them one thing to reference: "follow COR-1202" and both humans and agents know exactly what to do.
2. **Matches Alfred's identity.** Alfred's core promise is "SOP as the system of record for how work happens." The `af plan --task` capability is now a first-class Alfred workflow; it deserves a SOP that documents its usage pattern, same as COR-1500 documents TDD or COR-1602 documents multi-model review.
3. **Closes a FXA-2205 gap.** FXA-2205's Success Criterion was "a single call produces a complete checklist." Users still need to **know** that call exists and how to invoke it — a SOP is where that lives.
4. **Drives tag coverage.** Step 4 of the SOP (review the `Composed from:` line) explicitly prompts users to flag missing SOPs, creating an organic feedback loop that keeps the `Task tags` corpus growing.


## Impact Analysis

- **Systems affected:**
  - `src/fx_alfred/rules/COR-1202-SOP-Compose-Session-Plan.md` — NEW PKG-layer SOP file (canonical path).
  - `src/fx_alfred/CHANGELOG.md` — record the new SOP + next release version bump.
  - `src/fx_alfred/rules/COR-1103-SOP-Workflow-Routing.md` — **required** small addition in the intent-router section cross-referencing COR-1202 for "show me the plan" / "compose session plan" intents. Required (not optional) because discoverability of the new SOP is the central value proposition of this CHG; without the routing breadcrumb, COR-1202 is effectively invisible to users who don't already know its ID.

- **NOT affected:**
  - No code files changed (no `src/fx_alfred/commands/`, no `src/fx_alfred/core/`).
  - No test files changed (the SOP has no executable surface beyond what `af plan` already exercises).
  - No other PKG SOP content.
  - `pyproject.toml`, dependencies, build configuration — untouched.

- **Channels affected:** none.

- **Downtime required:** No.

- **Backward compatibility:** Fully additive. No existing behavior changes. Users who don't know or use COR-1202 see zero difference.

- **Rollback plan:**
  - Revert the SOP file commit. `af validate` still passes. No data migration.
  - If COR-1103 cross-reference was added, that line is removed too.
  - Rollback verification: `af list --prefix COR --type SOP` shows COR-1202 gone; `af validate --root .` clean.


## Implementation Plan

### Phase 1 — CHG review

1. Leader dispatches Codex + Gemini (real CLI) to score this CHG against COR-1609 rubric. Both must score ≥ 9.0.
2. If either returns FIX, Leader revises and re-dispatches per COR-1602 round rules.
3. On double PASS, status → `In Progress`.

### Phase 2 — Write COR-1202 content

4. Create `src/fx_alfred/rules/COR-1202-SOP-Compose-Session-Plan.md`. The rules directory is part of the source tree, so authoring the file directly is fine (no `af create` ceremony for PKG — `af create` targets USR/PRJ).

5. **SOP body contract** (the final file must match this outline; exact prose can be tightened during implementation):

   - Metadata block: `Applies to`, `Last updated`, `Last reviewed`, `Status: Active`, `Related: COR-1103, COR-1402, COR-1200`.
   - `## What Is It?` — one-paragraph summary: procedure for turning a one-sentence task description into a complete workflow plan via `af plan --task … --todo --graph`.
   - `## Why` — the four bullets from the "Why" section of this CHG, distilled to one short paragraph.
   - `## When to Use` — start of non-trivial session; user says "follow COR-1202", "show me the plan", "compose the session plan", or similar; unsure which SOPs apply; before opening a long-running PR.
   - `## When NOT to Use` — single obvious SOP (no composition benefit); mid-session after plan is already running (don't re-plan unless scope changed). Note: the "too thin `Task tags` coverage" case is not a reason to avoid COR-1202 — run it anyway and use the Step-4 empty-match recovery flow (positional pin + deferred tag backfill).
   - `## Steps` — seven numbered steps:
     1. `af guide --root .` for routing. (Use `--root .` throughout; the SOP assumes the user's CWD is the project root.)
     2. Write the task in one sentence. Keep it concrete and tag-rich.
     3. Run `af plan --root . --task "<description>" --todo --graph`. Default `--graph-format=both` emits ASCII + Mermaid; use `--graph-format=ascii` or `--graph-format=mermaid` when a single format is wanted. Use `--json` when a programmatic consumer is downstream.
     4. Review the `Composed from:` header. Explain `(always)` / `(auto)` / `(explicit)` provenance markers. **If an expected SOP is missing**, the immediate in-session fix is to add it as a positional argument and re-run: `af plan --root . --task "<description>" MISSING-1234 --todo --graph`. The durable fix — backfilling the SOP's `Task tags` metadata so it auto-matches next time — is deferred to the session retrospective (COR-1200) to avoid mid-session context switching. Do not skip the gap silently; either pin it now or record it for retro.
     5. Copy the flat TODO into the session's working surface (issue / Discussion Tracker per COR-1201 / memory / PR body). The `{phase}.{step}` numbering is stable and greppable.
     6. Execute step by step. At each phase transition, the executor (the agent or human running the plan) declares the active SOP per COR-1402 and honours any `Workflow loops` `max N` bound rendered in the plan.
     7. At session end, compare completion against the plan. Unchecked items enter the retrospective (COR-1200) with a reason: either genuinely skipped (note why) or forgotten (process failure this SOP exists to prevent). `Task tags` gaps noted in Step 4 also go here.
   - `## Examples` — at least three canonical invocations, each with a short description of the scenario it demonstrates:
     1. **Standard auto-compose** — `af plan --root . --task "implement FXA-2208 PRP" --todo --graph`. Shows the common case: a tagged task description resolves to a full routing → TDD → review → scoring chain without any explicit SOP IDs.
     2. **Mixing tags with explicit pins** — `af plan --root . --task "implement feature" COR-1501 --todo --graph` (COR-1501 is "Create GitHub Issue" — a real existing SOP naturally paired with implement-feature work). Shows how positional SOP IDs combine with tag-matched ones (union, de-duplicated, normalised to PREFIX-ACID).
     3. **Empty-match recovery** — `af plan --root . --task "xyzzy unmatched" --todo --graph` exits 2 with a diagnostic; demonstrate the Step-4 workaround: `af plan --root . --task "xyzzy unmatched" COR-1500 --todo --graph` to proceed in-session, with `Task tags` backfill deferred to retrospective.
   - `## Change History` — initial entry referencing CHG-FXA-2207.

6. Run `af fmt COR-1202 --write --root .` to canonicalise. Verify metadata order matches COR-0002.

7. Add a CHANGELOG entry under the next unreleased version: `- Added COR-1202: Compose Session Plan SOP (CHG-2207).`

8. **Required** — update `src/fx_alfred/rules/COR-1103-SOP-Workflow-Routing.md`'s intent-router section with one bullet pointing "show me the plan" / "compose session plan" intents to COR-1202. Aligns with Impact Analysis §Systems affected — discoverability of the new SOP is the central value proposition of this CHG, so the routing breadcrumb is not optional. Keep the edit minimal (one bullet).

### Phase 3 — Content review

9. Leader dispatches Codex + Gemini (real CLI) against COR-1610 code-review rubric (SOP content ships in the PKG). Both must score ≥ 9.0. Emphasis on COR-0002 format compliance, prose clarity, and technical accuracy against `af plan --task` actual behaviour.

10. Fix-or-defer per COR-1602 round rules.

### Phase 4 — PR + NRV-2506 comment triage

11. Push branch, open PR titled `feat(FXA-2207): add COR-1202 Compose Session Plan SOP`.
12. Triage any `chatgpt-codex-connector[bot]` comments per NRV-2506.
13. On all-green + double PASS, notify Leader for merge.

### Phase 5 — Release

14. SOP ships to end users in the next fx-alfred PyPI release (per FXA-2102). No special handling — CHANGELOG entry is sufficient.

---

## Testing / Verification

- [ ] **Format compliance:** `af fmt COR-1202 --check --root .` reports clean.
- [ ] **Structural validation:** `af validate --root .` reports 0 issues including COR-1202.
- [ ] **Content accuracy:** the canonical invocation shown in Step 3 of the SOP body runs successfully against the current tree:

      ```bash
      af plan --root . --task "implement FXA-2117 PRP" --todo --graph
      ```

      Exit 0; output contains `Composed from:`, an ASCII box-and-arrow block, and a fenced Mermaid block.
- [ ] **Related-links integrity:** every `Related:` reference (COR-1103, COR-1402, COR-1200) resolves to an existing Active SOP via `af list --type SOP --prefix COR`.
- [ ] **Rollback verification:** `git revert` the SOP commit; confirm `af validate` still clean and `af list --prefix COR --type SOP` no longer shows COR-1202.

---

## Open Questions

All resolved (tracked here for Hard Gate closure):

1. **RESOLVED — Title is "Compose Session Plan".** Round-1 title was "Visualize Session Plan"; Gemini R1 review flagged that "Visualize" overpromises because the output is text (TODO + ASCII + Mermaid) rather than an interactive/graphical experience. Changed to "Compose" because it directly matches the underlying `--task` auto-composition semantics and keeps the name format-agnostic (doesn't bind the SOP to any single output format). Other alternatives considered and rejected: "Show Session Plan" (too passive), "Emit Session Plan As ASCII" (binds to one format), "Session Workflow Visualization" (same visualize-overpromise).
2. **RESOLVED — ACID is 1202.** Fits the 12xx Session-Management family (COR-1200 Retrospective, COR-1201 Discussion Tracking). Next free number.
3. **RESOLVED — Layer is PKG.** Ships with fx-alfred so every user gets it out of the box. USR-layer alternative rejected: this is general Alfred usage, not personal habit.
4. **RESOLVED — `af plan --task` is not changed.** This CHG is pure documentation. Any future flag change requires a separate CHG.

---

## Alternatives Considered

- **USR-layer SOP (`~/.alfred/` per user).** Rejected: general Alfred usage pattern, not personal habit. Shipping in the package is the natural home.
- **Fold into COR-1103 Workflow Routing.** Rejected: COR-1103 is the routing decision tree; adding a visualisation sub-SOP would dilute its focus. Cross-reference is better (required Step 8).
- **Make it a skill / slash command instead.** Rejected: skills live in the agent layer (Claude Code / similar), not in Alfred itself. Alfred users without those agents would miss it. A PKG SOP works for everyone.
- **New CLI subcommand `af session-plan`.** Rejected: introduces command-surface for zero new functionality (it's just `af plan --task … --todo --graph` preset). A SOP conveys the usage intent without command bloat.
- **Defer until more Task tags are backfilled.** Rejected: the SOP itself drives tag backfill (Step 4's feedback loop). Ship now, let usage surface the tagging gaps.

---

## Approval

- [ ] Reviewed by: Codex + Gemini (COR-1602 parallel, COR-1609 CHG rubric)
- [ ] Approved on: <YYYY-MM-DD when both reviewers PASS>

---

## Execution Log

| Date       | Action                                        | Result  |
|------------|-----------------------------------------------|---------|
| 2026-04-18 | CHG-2207 Proposed                             | Draft   |
| 2026-04-18 | R1 review: Codex 9.6 PASS / Gemini 9.8 PASS   | Revise  |
| 2026-04-18 | R1 fixes: title "Visualize" → "Compose"; 4 bullets not 3; CJK example removed (COR-0002 compliance); Step 8 COR-1103 xref promoted from optional to required; `--root .` unified; Examples section given 3 explicit scenarios; Step 4 revised to positional-pin immediate fix + tag backfill deferred to retro; Step 6 role clarified (executor honours loops, not user). | Ready   |
| 2026-04-18 | R2 review: Codex pending; Gemini 9.7 "FIX" (blocker: Step 8 text still said **Optional** despite Impact Analysis saying required — half-edit miss; plus advisory: `When NOT to Use` "too thin tag coverage" is unactionable, should point to empty-match recovery). | Revise  |
| 2026-04-18 | R2 fix applied: Step 8 now "Required" matching Impact Analysis; `When NOT to Use` refactored — "too thin coverage" removed, replaced with note pointing to Step-4 empty-match recovery flow. | Ready   |
| YYYY-MM-DD | R3 review (if needed)                         | —       |
| YYYY-MM-DD | SOP content written                           | —       |
| YYYY-MM-DD | Content review (Codex + Gemini)               | —       |
| YYYY-MM-DD | PR opened                                     | —       |
| YYYY-MM-DD | Merged                                        | —       |
| YYYY-MM-DD | Released in fx-alfred PyPI version            | —       |

---

## Post-Change Review

_To be filled in after merge + release:_

- Is COR-1202 actually being invoked by users? (qualitative check via session logs + user feedback)
- Has the Step-4 tag-gap feedback loop driven any `Task tags` additions?
- Any prose ambiguity surfaced during real usage?
- Any friction with the default `--graph-format=both` output?

---

## Change History

| Date       | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | By                |
|------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------|
| 2026-04-18 | Initial version | Claude (Opus 4.6) |
| 2026-04-18 | Round-1 review fixes (Codex 9.6 PASS + Gemini 9.8 PASS, both real CLI): title changed "Visualize Session Plan" → "Compose Session Plan" (Gemini: Visualize overpromises given text output); fixed Why bullet-count mismatch (3 → 4, Codex A1); removed CJK usage example per COR-0002 English-only rule (Codex A2); promoted COR-1103 cross-reference from optional to required for discoverability (Codex A3); unified `--root .` across all commands (Gemini A4); listed 3 explicit Examples scenarios — standard auto-compose / mixing tags with explicit pins / empty-match recovery (Gemini A5); clarified Step 6 role (executor honours loops, not user) (Gemini A6); revised Step 4 tag-gap remediation — immediate fix is positional pin `MISSING-1234`, durable fix (tag backfill) deferred to retrospective to avoid mid-session context switching (Gemini strategic insight). | Claude (Opus 4.6) |
| 2026-04-18 | R3 double PASS: Gemini 9.9 + Codex 9.9 (R2 post-fix re-read). All R1 advisories + R2 blocker + R3 stale-'optional' advisory resolved. Status: Proposed -> Approved. | Frank (Leader) |
