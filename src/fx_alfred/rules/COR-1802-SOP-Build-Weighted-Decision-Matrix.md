# SOP-1802: Build Weighted Decision Matrix

**Applies to:** All projects using the COR document system
**Last updated:** 2026-05-10
**Last reviewed:** 2026-05-10
**Status:** Active

---

## What Is It?

COR-1802 is a PKG-layer SOP that codifies how to design, calibrate, and validate a weighted scoring rubric for any decision domain. It provides an eight-step process — from defining the decision question through documenting calibrated thresholds — that produces a matrix with consistent quality: weights that sum to 100%, anchors expressed as observable behaviors rather than adjectives, and thresholds verified against known-correct cases before use.

---

## Why

The COR system already uses weighted decision matrices (COR-1800 §Evaluation Rubric, COR-1608–1610 review scoring, COR-1621 multi-reviewer triage) but the process for building one is implicit. This causes:

- Ad-hoc matrix construction with inconsistent quality — weights that don't sum to 100%, anchors that are adjectives rather than behaviors, thresholds set by intuition rather than calibration
- No shared vocabulary for critiquing a matrix: "the weights are wrong" is not actionable; "this dimension fails the isolation test" is

COR-1802 fills that gap: any agent or human follows it to produce a well-formed, calibrated matrix.

---

## When to Use

When an agent or human needs to build a new weighted decision matrix for any domain:

- Retrospective signal scoring (e.g., COR-1800 evolution candidate evaluation)
- Code, PRP, or CHG review rubrics (e.g., COR-1608–1610)
- PR triage and severity classification
- Session quality assessment
- Any multi-dimensional decision where no single factor is a definitive gate

---

## When NOT to Use

Do not build a weighted matrix when any of the following conditions apply:

| Condition | Reason |
|-----------|--------|
| A simple binary checklist already decides the outcome (e.g., "does the PR have a passing CI run?") | Matrices add no value when any single mandatory condition is the sole determinant |
| A single factor dominates so strongly (> 70% of outcomes) that no combination of other dimensions can reverse it | At that point, the dominant factor is a gate, not a dimension — model it as a gate + optional advisory dimensions |
| Fewer than 3 known calibration cases exist | A matrix without calibration is untested; calibration is the only validity check |

---

## Steps

### Step 1 — Define the decision

State the single question the matrix answers. Name the action set: binary (yes/no) or ordinal (create issue / log / discard). A matrix with > 3 action bands is a smell — split into two decisions.

### Step 2 — Enumerate dimensions (3–6)

For each candidate dimension, apply four tests before keeping it:

| Test | Pass condition |
|------|----------------|
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

### Step 4 — Write anchors

For each dimension, write three anchor descriptions at 0, 5, and 10:

- **Behaviors, not adjectives.** "First time seen in any context" not "low recurrence"
- **Anchors must be mutually exclusive** — a real case maps to exactly one anchor
- If 5 is hard to define, use 0 and 10 only and interpolate linearly

### Step 5 — Calibrate with known cases

Collect 3–5 cases where the correct action is already known. Cases come from historical decisions in the consuming SOP's domain, or from expert judgment when no relevant history exists. Score each on every dimension, compute composite, check action. A matrix is not valid until all calibration cases produce the correct action.

If a case produces the wrong action: identify the miscalibrated dimension and adjust. Re-run all cases after each adjustment.

**Termination rule:** if calibration fails after ≥3 adjustment cycles, return to Step 2. Persistent failure means the dimension set is MECE-incomplete, not that weights are slightly off.

### Step 6 — Set action thresholds

1. Pick the clearest "definitely action X" case → its composite is the floor of band X
2. Pick the clearest "definitely not action X" case → its composite is the ceiling of the band below X
3. The gap is the "uncertain" middle band — **strongly preferred**. A pure binary threshold (no middle band) is permitted only with explicit written justification. Note: COR-1608/1609/1610 use binary pass/fail (≥9.0) — intentional exceptions, not violations.

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

---

## Worked Example — COR-1610 Code Review Scoring

This section traces COR-1610's decision matrix through all 8 steps to illustrate how the SOP is applied in practice.

**COR-1610 question (Step 1):** "Should this code change be merged?" Action set: binary — PASS (merge) or FIX (block until resolved). One band boundary at 9.0 (justified explicitly per Step 6 note).

**Dimension enumeration (Step 2):** The COR-1610 authors considered every observable signal in a code review and applied the four tests:

| Candidate dimension | MECE | Indep. observability | Anchor-testable | Decision-relevant | Kept? |
|---------------------|------|---------------------|-----------------|-------------------|-------|
| Correctness | Yes | Yes — logic is observable without style context | Yes — wrong output vs. correct output on test case | Yes — wrong logic alone blocks merge | Yes |
| Test Coverage | Yes | Yes — coverage is measurable without reading logic | Yes — 0% new tests vs. full behavior coverage | Yes — untested behavior is a known defect vector | Yes |
| Code Style | Yes | Yes — linter is independent | Yes — fails lint vs. passes lint | Yes — style debt accumulates, so unclean style scores low | Yes |
| Security | Yes | Yes — injection risk is analyzable on its own | Yes — SQL injection present vs. parameterized queries | Yes — security flaw blocks merge regardless of other scores | Yes |
| Simplicity | Yes | Yes — over-engineering is visible without style context | Yes — 300-line function vs. 3-line idiom for same logic | Yes — over-abstraction causes future defects | Yes |
| "Author reputation" | No — not MECE with correctness | — | — | — | Discarded |

Five dimensions pass all four tests.

**Weight assignment (Step 3):**

Forced ranking from most to least critical: Correctness = Test Coverage > Simplicity > Code Style = Security. Authors assigned:

| Dimension | Weight | Isolation test result |
|-----------|--------|-----------------------|
| Correctness | 25% | Moving correctness 0→10 (all others at 5) shifts composite from 5.0 to 7.5 — meaningful, feels right |
| Test Coverage | 25% | Same delta — confirms equal standing with correctness |
| Simplicity | 20% | Shifts composite 5.0→6.0 — appropriate third-tier influence |
| Code Style | 15% | Shifts composite 5.0→5.75 — advisory-level influence |
| Security | 15% | Same as Code Style numerically, but any security issue would score near 0, making this effectively a gate in practice |

No weight exceeds 40%, no weight falls below 10%. All weights sum to 100%.

**Anchor writing (Step 4, example — Correctness):**

| Score | Anchor behavior |
|-------|----------------|
| 0 | Logic produces incorrect output on at least one known input; or existing passing tests now fail |
| 5 | Logic handles the primary path correctly but has at least one unhandled edge case identified by the reviewer |
| 10 | Logic correct on all paths; handles edge cases; no regressions; reviewer cannot construct a failing scenario |

**Calibration (Step 5 — three real-world scenarios):**

*Case A — Trivial whitespace fix (correct action: PASS)*

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Correctness | 10 | Whitespace change cannot break logic |
| Test Coverage | 10 | No new behavior; no new tests needed |
| Code Style | 10 | Cleanup — improves style |
| Security | 10 | No security surface touched |
| Simplicity | 10 | Reduces lines |

Composite: 10.0 → PASS. Calibration: correct.

*Case B — Major refactor with no tests (correct action: FIX)*

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Correctness | 6 | Refactor looks plausible but no tests confirm behavior |
| Test Coverage | 0 | No tests for any changed behavior |
| Code Style | 8 | Clean, consistent |
| Security | 9 | No obvious security issues |
| Simplicity | 8 | Simplified internal structure |

Composite: 0.25×6 + 0.25×0 + 0.15×8 + 0.15×9 + 0.20×8 = 1.5 + 0 + 1.2 + 1.35 + 1.6 = **5.65 → FIX**. Calibration: correct.

*Case C — Security patch with comprehensive tests (correct action: PASS)*

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Correctness | 9 | Patch addresses the CVE; one minor edge case documented but low-risk |
| Test Coverage | 10 | New tests cover all attack vectors |
| Code Style | 8 | Minor inconsistency in variable naming |
| Security | 10 | Injection vector fully closed |
| Simplicity | 9 | Minimal change for maximum effect |

Composite: 0.25×9 + 0.25×10 + 0.15×8 + 0.15×10 + 0.20×9 = 2.25 + 2.5 + 1.2 + 1.5 + 1.8 = **9.25 → PASS**. Calibration: correct.

**Threshold (Step 6):** Case A (10.0) is the clearest PASS; Case B (5.65) is the clearest FIX. The ≥9.0 threshold is set between them. Binary threshold is explicitly justified: code review decisions require a deterministic merge gate — human negotiation of a "maybe" band would slow delivery without improving quality, and advisory findings are already captured in reviewer comments rather than the score.

**Validation (Step 7):** All three calibration cases cover the two bands (FIX, PASS). Case C (9.25) is a boundary case within ±0.5 of the 9.0 cutoff. Case B is initially counterintuitive (a clean-looking refactor fails) — exactly the edge case type Step 7 requires.

**Documentation (Step 8):** COR-1610 documents: scoring rubric table (Steps 3–4), action thresholds (≥9.0 PASS / <9.0 FIX), and the six scoring rules which encode calibration constraints. Calibration examples are implicit in the rules but would benefit from an explicit §Calibration Examples section — a future CHG target.

---

## Guard Rails

- Never skip calibration (Step 5). A matrix with no known-correct cases is untestable.
- Never use a pure binary threshold (Step 6) without written justification.
- Never use adjectives as anchors (Step 4). Anchors must be observable behaviors.
- Never let weights drift from 100% after an adjustment cycle.
- Never add a dimension with weight < 10%.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-10 | Initial version per CHG FXA-2281 (issue #135). ACID disambiguation verified: COR-1802 resolves to this file; CLD-1802 resolves to `~/.claude/rules/CLD-1802-CHG-Atomicity-Surface-Definition-+-Signal-Grep-Scope.md`. | Claude Sonnet 4.6 |
