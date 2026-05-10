# CHG-2281: Add COR-1802 Build Weighted Decision Matrix SOP

**Applies to:** FXA project (alfred — `frankyxhl/alfred`)
**Last updated:** 2026-05-10
**Last reviewed:** 2026-05-10
**Status:** Approved
**Date:** 2026-05-10
**Requested by:** Frank Xu (session 2026-05-10, issue #135)
**Priority:** P2 — foundational (before next matrix is designed from scratch)
**Change Type:** Normal
**Targets:** PKG layer (`src/fx_alfred/rules/`), `COR-1800`

---

## What

Add `COR-1802-SOP-Build-Weighted-Decision-Matrix.md` — a PKG-layer SOP that codifies how to design, calibrate, and validate a weighted scoring rubric for any decision domain (retrospective findings, code review, evolution candidates, PR triage, etc.).

Also add a one-line forward-reference to COR-1802 in `COR-1800-REF-Evolution-Philosophy.md` §Evaluation Rubric (not a compliance claim — COR-1800 pre-dates COR-1802).

No CLI changes. No new schema fields.

## Why

The COR system already uses weighted decision matrices (COR-1800 §Evaluation Rubric, COR-1608–1610 review scoring, COR-1200 §Scoring per issue #134) but the process for *building* one is implicit. This causes:

- Ad-hoc matrix construction with inconsistent quality (weights that don't sum to 100%, anchors that are adjectives rather than behaviors, thresholds set by intuition rather than calibration)
- No shared vocabulary for critiquing a matrix ("the weights are wrong" is not actionable; "this dimension fails the isolation test" is)

COR-1802 fills the gap: any agent or human follows it to produce a well-formed, calibrated matrix.

## Surfaces

| File | Action |
|------|--------|
| `src/fx_alfred/rules/COR-1802-SOP-Build-Weighted-Decision-Matrix.md` | **Create** — new PKG-layer SOP |
| `src/fx_alfred/rules/COR-1800-REF-Evolution-Philosophy.md` | **Edit** — add one-line forward-reference to COR-1802 in §Evaluation Rubric (not a compliance claim; COR-1800 pre-dates COR-1802 and lacks required anchors/calibration sections) |

**Out of scope in this CHG:** `COR-1200-SOP-Session-Retrospective.md` also receives a "built per COR-1802" back-reference, but COR-1200 §Scoring does not yet exist — that edit is deferred to the issue #134 implementer, who adds it as part of creating §Scoring.

## Impact Analysis

- **Systems affected:** PKG layer documentation. No code changes. No CLI behavior change.
- **ACID collision note:** COR-1802 shares the `1802` ACID with `CLD-1802` (in `~/.claude/rules/`). `af read 1802` becomes ambiguous; `af read COR-1802` and `af read CLD-1802` each resolve correctly with prefix qualification. Must verify post-creation.
- **Rollback plan:** `git revert` the commit that adds COR-1802 and the COR-1800 edit.

## Implementation Plan

1. `af create SOP --prefix COR --acid 1802 --title "Build Weighted Decision Matrix"` — scaffold metadata
2. Write document sections:
   - §What Is It, §Why, §When to Use, §When NOT to Use (≥3 disqualifying conditions)
   - §Steps 1–8 (see §SOP Draft below for content)
   - §Worked Example — trace COR-1610 (Code Review Scoring, already existing) through all 8 steps
   - §Guard Rails
3. Edit `COR-1800` §Evaluation Rubric intro: add "built per COR-1802" reference line
4. `af validate --root /Users/frank/Projects/alfred` — must pass
5. Verify `af read COR-1802` and `af read CLD-1802` each resolve to their respective docs
6. Push branch `fxa-135-cor-1802-weighted-decision-matrix`, open PR with `Closes #135`
7. Trinity fast-review (glm + deepseek ≥ 9.0); iterate on findings

## SOP Draft (Step Content)

The eight steps below are the authoritative content for §Steps in the new SOP:

### Step 1 — Define the decision

State the single question the matrix answers. Name the action set: binary (yes/no) or ordinal (create issue / log / discard). A matrix with > 3 action bands is a smell — split into two decisions.

### Step 2 — Enumerate dimensions (3–6)

For each candidate dimension, apply four tests before keeping it:

| Test | Pass condition |
|------|---------------|
| **MECE** | No two dimensions measure the same signal; together they capture everything that matters |
| **Independent observability** | You can score dimension A without knowing the score of dimension B |
| **Anchor-testability** | You can write distinct concrete behaviors for 0, 5, and 10 |
| **Decision-relevance** | Removing this dimension would change the outcome in ≥1 known case |

Discard any dimension that fails any test. If you have > 6 passing dimensions, the decision is probably two decisions — split it.

### Step 3 — Assign weights

1. Rank dimensions by importance (forced ranking — no ties)
2. Assign weights top-down; all must sum to 100%
3. Apply the **isolation test**: *"If all other dimensions score 5, does moving THIS dimension from 0 → 10 change the composite outcome in a way that feels right?"*
4. Warning: weight > 40% → consider as a gate condition instead
5. Warning: weight < 10% → drop or merge
6. **Equal weights after forced ranking are permitted** when two adjacent-ranked dimensions are genuinely indistinguishable in importance — the ranking still records the tiebreaker for edge cases even when weights are the same.

### Step 4 — Write anchors

For each dimension, write three anchor descriptions at 0, 5, and 10:
- **Behaviors, not adjectives.** "First time seen in any context" not "low recurrence"
- **Anchors must be mutually exclusive** — a real case maps to exactly one anchor
- If writing a 5 anchor is genuinely difficult, return to Step 2 — consider dropping or splitting the dimension rather than omitting the midpoint anchor

### Step 5 — Calibrate with known cases

Collect 3–5 cases where the correct action is already known. Cases come from historical decisions in the consuming SOP's domain, or from expert judgment when no relevant history exists. Score each on every dimension, compute composite, check action. A matrix is not valid until all calibration cases produce the correct action.

If a case produces the wrong action: identify the miscalibrated dimension and adjust. Re-run all cases after each adjustment.

**Termination rule:** if calibration fails after ≥3 adjustment cycles, return to Step 2. Persistent failure means the dimension set is MECE-incomplete, not that weights are slightly off.

### Step 6 — Set action thresholds

Use boundary cases — the weakest acceptable and the strongest unacceptable — not the clearest extremes:

1. Pick the **weakest case that still clearly deserves action X** → its composite is the upper evidence bound for the threshold (threshold must be ≤ this composite)
2. Pick the **strongest case that clearly does NOT deserve action X** → its composite is the lower evidence bound (threshold must be > this composite)
3. Set the threshold in the gap between those two composites. That gap is the **"uncertain" middle band** — strongly preferred. A pure binary threshold (no middle band) is permitted only with explicit written justification. Note: COR-1608/1609/1610 use binary pass/fail (≥9.0) — intentional exceptions, not violations.

### Step 7 — Validate

Run at least:
- ≥1 case in each action band
- ≥1 case at each threshold boundary (within ±0.5 of cutoff)
- ≥1 initially-counterintuitive edge case

### Step 8 — Document

Use the COR-1800 table format. Required consuming-document sections:
- **Scoring rubric** table (Steps 3–4 output)
- **Action thresholds** table (Step 6 output)
- **Calibration examples** section with ≥3 worked cases (Step 5 output)

### When NOT to Use

Do not build a weighted matrix when any of the following conditions apply:

| Condition | Reason |
|-----------|--------|
| A simple binary checklist already decides the outcome (e.g., "does the PR have a passing CI run?") | Matrices add no value when any single mandatory condition is the sole determinant |
| A single factor dominates so strongly (> 70% of outcomes) that no combination of other dimensions can reverse it | At that point, the dominant factor is a gate, not a dimension — model it as a gate + optional advisory dimensions |
| Fewer than 3 known calibration cases exist | A matrix without calibration is untested; calibration is the only validity check |

### Guard Rails

- Never skip calibration (Step 5). A matrix with no known-correct cases is untestable.
- Never use a pure binary threshold (Step 6) without written justification.
- Never use adjectives as anchors (Step 4).
- Never let weights drift from 100% after an adjustment.
- Never add a dimension with weight < 10%.

## Acceptance Criteria

- [ ] `COR-1802` exists with correct metadata (Type: SOP, Status: Active)
- [ ] Eight numbered steps present; each with ≥1 concrete sub-rule
- [ ] MECE, independent observability, anchor-testability, decision-relevance named explicitly
- [ ] Isolation test, dominant-weight warning (>40%), drop-threshold (<10%) stated
- [ ] Anchor rules: behavior descriptions required; 0/5/10 anchors required
- [ ] Calibration: minimum 3 known cases required
- [ ] Threshold: middle "uncertain" band required (pure binary forbidden without justification)
- [ ] "When NOT to Use" covers ≥3 disqualifying conditions
- [ ] ≥1 worked example using COR-1610 (or other real existing COR matrix)
- [ ] COR-1800 adds one-line forward-reference to COR-1802 (not a compliance claim)
- [ ] `af validate --root /Users/frank/Projects/alfred` passes
- [ ] `af read COR-1802` and `af read CLD-1802` each resolve correctly
- [ ] Trinity fast-review (glm + deepseek) both ≥ 9.0

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-10 | Initial version | Claude Sonnet 4.6 |
| 2026-05-10 | R2: fix GLM B1 — add §When NOT to Use to SOP Draft (3 conditions from issue body); fix convergent COR-1200 advisory — add Out of Scope note scoping COR-1200 back-reference to #134 implementer; fix A1 — add calibration sourcing guidance to Step 5; fix A2 — clarify COR-1200 §Scoring phrasing in §Why | Claude Sonnet 4.6 |
