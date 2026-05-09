# CHG-2279: Codify GitHub App PR-Review Bot Scope-Hint Technique In COR-1612 + COR-1615

**Applies to:** FXA project
**Last updated:** 2026-05-09
**Last reviewed:** 2026-05-09
**Status:** Proposed
**Date:** 2026-05-09
**Requested by:** Frank (via session 2026-05-09; tracked as alfred#118)
**Priority:** Low
**Change Type:** Normal
**Targets:** COR-1612, COR-1615

---

## What

Two PKG-SOP edits codifying the **PR-body scope-hint technique** for steering GitHub App PR-review bots (e.g. `chatgpt-codex-connector[bot]`) toward on-scope correctness findings and away from polish-class noise on long-running review iteration loops:

### 1. COR-1612 (Respond To PR Review Comments) — new top-level section

Add a new section after §Pitfalls (and before §Why bot reviewers catch what humans/panels miss) titled `## Scoping bot reviews via PR body (optional, GitHub App review bots only)`. The section:

- Describes the technique: when a PR is large enough to attract many rounds of GitHub App review bot iteration, an optional `## Scope hints for automated reviewers` section in the PR body can declare in-scope vs out-of-scope finding classes.
- Notes that this is **GitHub-platform-specific**, **bot-vendor-dependent**, and **optional** — the bot must read PR body context as a directive (verified empirically only for `chatgpt-codex-connector[bot]`; other GitHub App review bots untested).
- Notes that **non-GitHub reviewer-detector classes do not apply**: CI-side static analyzers don't read PR body; multi-model panel review reads the artifact directly, not the PR body. Per COR-1612 §Reviewer Detector Classes terminology (the SOP's own term is "GitHub App review bot" — the section title and prose use that exact term).
- Provides the recommended PR-body template inline (literal markdown, not a reference). The template is reproduced verbatim below in §Implementation-Template Block so reviewers of this CHG can evaluate it without chasing the alfred#118 issue body.
- States the "when most useful" heuristic (5+ rounds of GitHub App bot iteration where remaining items are tightening edge cases vs catching defects), the explicit non-substitution caveat (not a way to suppress real findings), and a "when NOT useful" note (skip if the installed bot already produces zero off-scope findings **AND** per-round finding volume is already acceptably low; or for PRs with fewer than 3 review rounds). The compound AND condition matters: the alfred evidence base itself comes from a bot already at zero off-scope pre-hints, where the value the technique added was per-round volume reduction (1.5 → 1.0); a heuristic of "skip if zero off-scope" alone would have wrongly excluded the very repo class that produced the evidence.
- Cites alfred#117 R11–R12 + alfred#119 R1–R5 as the **quantitative** evidence base (N=7 post-hint rounds, both rounds-counted and findings-counted). Alfred#120 is cited as **qualitative** evidence only — the technique was applied to PR #120 and operator-observed to behave consistently with #117/#119 expectations, but #120's review rounds are not folded into the N=7 quantitative count.

### 2. COR-1615 (GitHub App PR Review Bot Loop) — new bullet in §Operator Checklist

Add a single one-line bullet to the §Operator Checklist (true pointer; no re-explanation of caveats — those live in COR-1612):

> - For long iteration loops on the same PR, see COR-1612 §Scoping bot reviews via PR body for an optional, bot-vendor-dependent PR-body scope-hint technique.

The pointer is intentionally minimal: it names the destination section and flags the technique's "optional" + "bot-vendor-dependent" qualifiers but defers all recipe content, empirical caveats, and the when-most-useful heuristic to COR-1612. Adopters who want the full picture follow the link; operators skimming the checklist see only that the technique exists.

### Implementation-Template Block

The exact markdown to be embedded in the new COR-1612 section (verbatim PR-body template, for reviewer self-containment):

````markdown
## Scope hints for automated reviewers

**In-scope (please flag):**
- P0/P1 — security, fail-OPEN gates, correctness regressions, cross-doc contract violations.
- P2 — cross-doc / cross-recipe drift between sibling SOPs.
- Anything that would break a real adopter following the recipe verbatim.

**Out-of-scope (please skip or batch into a follow-up):**
- P3 cosmetic — naming preferences, footnote/header polish.
- Future-refactor suggestions.
- Minor wording inconsistencies that don't change the contract.
- "Could be more thorough" suggestions when the existing recipe meets its declared invariant.
````

The severity tags (P0/P1/P2/P3) match COR-1621 verbatim; "in-scope / out-of-scope" framing maps to COR-1612 §Reviewer Detector Classes "actionable vs polish" distinction. No new vocabulary is introduced.

---

## Why

Across alfred PR #117 (COR-1617 cluster promotion, 12 codex bot review rounds), PR #119 (FXA-2277 schema refinements), and PR #120 (FXA-2276 invocation shorthand — qualitative only; not folded into quantitative count below), an experimental `## Scope hints for automated reviewers` section in the PR body produced a measurable **drop in finding volume** from `chatgpt-codex-connector[bot]` while keeping the off-scope finding count at zero across all rounds (the bot on this repo was already P1/P2-focused pre-hints; the hints did not *redistribute* findings, they *reduced* the per-round count):

| PR | Rounds | Avg findings/round | Off-scope class findings |
|---|---|---|---|
| #117 R1–R10 (pre-hints) | 10 | 1.5 | 0 (bot already P1/P2-focused) |
| #117 R11–R12 (post-hints) | 2 | 1.0 | 0 |
| #119 R1–R5 (with hints from start) | 5 | 1.0 | 0 |

Total: **across 7 post-hint rounds (PR #117 + PR #119), per-round finding volume dropped from 1.5 → 1.0 (a one-third reduction); off-scope class count was 0 in both pre- and post-hint conditions, so the shift is in volume, not in distribution.** The volume drop is small in absolute terms (N=7); the more useful claim is the consistent-zero off-scope count across all 7 hint-applied rounds, suggesting the technique at minimum *does not provoke* off-scope findings.

The technique is currently documented only in those three PR bodies as an inline experiment. Without codification, future PR authors will:

1. Re-derive the format from scratch (or skip it entirely on PRs that would benefit).
2. Mis-apply it to non-GitHub-App reviewer classes (e.g. attempting to use PR-body hints on CI static analyzers, which can't read the PR body) and conclude the technique "doesn't work."
3. Treat it as a way to suppress findings rather than as a directive about *which* to defer.

Codifying in COR-1612 (the universal PR-comment-response SOP) and pointing at it from COR-1615 (the bot-trigger-loop SOP) covers the two natural touchpoints — the recipe lives where it's used; the loop SOP gets a one-line pointer so operators see it during long iterations.

---

## Impact Analysis

**Files changed**

- `src/fx_alfred/rules/COR-1612-SOP-Respond-To-PR-Review-Comments.md` — add new `## Scoping bot reviews via PR body (optional, GitHub App review bots only)` section between §Pitfalls and §Why bot reviewers catch what humans/panels miss; one new row in §Change History.
- `src/fx_alfred/rules/COR-1615-SOP-GitHub-App-PR-Review-Bot-Loop.md` — add one bullet to §Operator Checklist; one new row in §Change History.
- `rules/FXA-2279-CHG-Codify-GitHub-App-PR-Review-Bot-Scope-Hint-Technique-In-COR-1612-+-COR-1615.md` (this CHG) — flipped to `Status: Approved` post-merge.

**Behavioural impact**

- Operators iterating on a PR through a GitHub App review bot get an explicit, tested recipe for scoping bot reviews via the PR body — without re-deriving from scratch.
- `chatgpt-codex-connector[bot]` (the only GitHub App PR-review bot installed on this repo today, per FXA-2276's `<bot-actors>`) sees a documented PR-body convention; behavior on other GitHub App review bots is left explicitly empirical-confirm-required.
- COR-1612 §Reviewer Detector Classes already distinguishes GitHub App review bots from CI-side static analyzers + multi-model panels; the new section reinforces that distinction by stating the technique applies *only* to the first class.
- No PKG SOP semantic change. No CLI / behavior change. No COR-1617 / COR-1620 / COR-1621 / COR-1622 change.

**Out of scope** (explicitly deferred)

- Empirical study of whether other GitHub App review bots (CodeRabbit, Greptile, GitHub Copilot Reviewer, Sourcery) honor PR-body scope hints. Document only the `chatgpt-codex-connector[bot]` behavior; other GitHub App review bots noted as "project-dependent and untested" — adopters confirm in their own projects.
- Bot-vendor-specific configuration formats (CodeRabbit YAML, Copilot rules, etc.). Out of scope; this CHG covers PR-body-text directives only.
- Non-GitHub reviewer-detector classes (CI-side static analyzers, multi-model panel review tooling). The technique does not apply, and the new COR-1612 section says so explicitly.
- Any change to alfred's `<bot-actors>` list in FXA-2276 — the codex connector remains the sole installed bot; no new bot is being adopted by this CHG.
- Promotion of the technique into a separate dedicated SOP (e.g. COR-1623 or similar). The technique is one-section-shaped; a dedicated SOP would be premature until evidence accumulates that the recipe varies materially across bots / projects.

**Rollback plan**

- Revert the merge commit on COR-1612 + COR-1615 + this CHG (single-PR change).
- Set this CHG to `Status: Rolled Back` per COR-0002 allowed CHG status values; keep the document as historical record.
- No data migration / no behavior unwinding required (docs-only change).

---

## Implementation Plan

1. Edit `src/fx_alfred/rules/COR-1612-SOP-Respond-To-PR-Review-Comments.md`: insert the new `## Scoping bot reviews via PR body (optional, GitHub App review bots only)` section between §Pitfalls and §Why bot reviewers catch what humans/panels miss. Section body per the spec in alfred#118 issue body, with the recommended template inline as a fenced markdown block. Add change-history row.
2. Edit `src/fx_alfred/rules/COR-1615-SOP-GitHub-App-PR-Review-Bot-Loop.md`: append one bullet to §Operator Checklist pointing at COR-1612 §Scoping bot reviews via PR body. Add change-history row.
3. Run `af validate --root .` to confirm no structural issues.
4. Open PR; eat-our-own-dogfood — add a `## Scope hints for automated reviewers` section to *this* PR's body and observe `chatgpt-codex-connector[bot]`'s behavior across rounds (per alfred#118 acceptance criterion 6).
5. Iterate per COR-1612 §Step 6 + COR-1615 §Steps 1-12 until the bot is satisfied.
6. Post-merge: flip this CHG to `Status: Approved`; close alfred#118.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-09 | Initial version — drafted from alfred#118 issue body. | Claude Opus 4.7 |
| 2026-05-09 | R3: trinity fast-review R2 panel — glm PASS 9.6, deepseek FIX 7.9. Fixes folded: (i) glm A3 / deepseek A1 (stale finding pre-edit, but cross-verified): completed terminology sweep — `reviewers` → `review bots` in §Impact Analysis Files-changed quoted title and §Implementation Plan step 1 quoted title (replace_all). (ii) deepseek A2 (legitimate, R2-introduced): "when NOT useful" heuristic narrowed to compound AND condition (zero off-scope AND acceptably-low per-round volume); explanatory clause added so the heuristic does not exclude the very repo class that produced the evidence base. (iii) deepseek A3 (terminology): §Impact Analysis Behavioural-impact bullet 2 + Out-of-scope bullets 1 and 2 — `reviewers` → `review bots` for class-noun consistency; line 101 reworded to "Bot-vendor-specific configuration formats" (better English than "review bot-specific"). | Claude Opus 4.7 |
| 2026-05-09 | R2: trinity panel R1 findings folded — (a) glm A1 + codex A1 (convergent): PR #120 evidence-base inconsistency. §What item 1 last bullet now distinguishes #117/#119 as quantitative (N=7) from #120 as qualitative-only; §Why prose updated to match. (b) codex A3 + deepseek A4 (convergent): COR-1615 bullet over-length vs "one-line pointer" claim. §What item 2 bullet rewritten to a true one-liner; explicit note that recipe + caveats live in COR-1612, the bullet only flags existence. (c) codex A2 + deepseek A5 (convergent): "GitHub App reviewers" → "GitHub App review bots" (matches COR-1612 §Reviewer Detector Classes terminology) in section title and prose. (d) deepseek A2 (singleton, fair): template-by-reference made the CHG not self-contained for review. Added §Implementation-Template Block reproducing the exact PR-body template inline. (e) deepseek A1 (singleton, fair): "shift in finding distribution" claim was unsupported (data shows volume drop only; off-scope count was 0 in both pre- and post-hint conditions). §Why rewritten to claim "shift in volume" and "consistent-zero off-scope count" instead. (f) gemini B1 (P1, divergent — 1/4 dissent): proposed inverting placement (recipe in COR-1615, pointer in COR-1612). NOT adopted: codex A3 explicitly says "fix bullet not placement"; deepseek explicitly calls 2-SOP touchpoint design "architecturally sound"; 3/4 reviewers side with current placement. Per COR-1621 panel-rule, blockers without convergence are acknowledged but do not force a rewrite. The deeper rationale: COR-1612's §Reviewer Detector Classes already establishes the universal-overlay framing; placing GitHub-App-bot-specific recipes inside §Reviewer Detector Classes' parent SOP is consistent with that framing, with COR-1615 providing the bot-loop-specific entry point via the new pointer bullet. (g) glm A2 + codex A4 (singleton, P2/P3): minor metadata + severity-vocab cleanups deferred — `Targets` field is project-convention (FXA-2277, FXA-2278 both use it without `af validate` failure); severity vocab in §Why already aligned with COR-1621 in R2's volume-vs-distribution rewrite. | Claude Opus 4.7 |
