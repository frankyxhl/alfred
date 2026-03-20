# SOP-1605: Workflow — Sequential Pipeline

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-19
**Last reviewed:** 2026-03-19
**Status:** Active

---

## What Is It?

A collaboration pattern where Workers are chained in sequence — each Worker's output becomes the next Worker's input. The Leader defines the pipeline stages and monitors handoffs. An optional Reviewer validates the final output or individual stage outputs.

Also known as: Pipeline, Cascade, Stage-by-Stage Handoff.

---

## Roles

| Role | Responsibility | Count |
|------|---------------|-------|
| **Leader** | Defines pipeline stages, monitors handoffs, receives final result | 1 |
| **Worker** | Executes one stage, passes output to next stage | 2+ (ordered) |
| **Reviewer** | (Optional) Reviews final output or per-stage output | 0+ |

---

## Sequence Diagram

```
Leader      Worker A    Worker B    Worker C    Reviewer
  │            │           │           │           │
  │──stage1───▶│           │           │           │
  │◀──output A─│           │           │           │
  │                                                │
  │──stage2(A)────────────▶│           │           │
  │◀──output B────────────│           │           │
  │                                                │
  │──stage3(B)────────────────────────▶│           │
  │◀──output C────────────────────────│           │
  │                                                │
  │──review final─────────────────────────────────▶│
  │◀──8/10────────────────────────────────────────│
  │                                                │
  │──fix stage3───────────────────────▶│           │  ← iteration (default: on)
  │◀──output C'───────────────────────│           │
  │──re-review────────────────────────────────────▶│
  │◀──PASS────────────────────────────────────────│
  │                                                │
  │  ✓ pipeline complete                           │
  │            │           │           │           │
```

---

## Steps

1. **Leader defines pipeline** — ordered list of stages, each with input/output contract
2. **Leader assigns Workers** — one Worker per stage (or one Worker for multiple stages)
3. **Stage 1 Worker executes** — produces output
4. **Leader hands off** — passes Stage 1 output as input to Stage 2 Worker
5. **Repeat** — each stage receives the previous stage's output and produces its own
6. **Final output** — last stage's output is the deliverable
7. **(Optional) Reviewer reviews** — evaluates the final output (or per-stage checkpoints)
8. **If iteration is on and issues found** — Leader identifies which stage needs fixing, re-runs from that stage forward
9. **If approved** — pipeline complete

---

## Iteration Mode

**Default: on** — If review finds issues, Leader re-runs the pipeline from the failing stage onward (not from scratch).

**To disable** (single-pass mode): set `iterate: false` when invoking the SOP.

```
/team plan --sop 1605 --no-iterate "requirements → code → tests"
```

When off: Pipeline runs once start-to-finish, Reviewer scores, Leader receives as-is.

| Setting | Behavior |
|---------|----------|
| `iterate: true` (default) | Pipeline → Review → Re-run from failing stage → Review → ... until approved |
| `iterate: false` | Pipeline → Review → done (single pass) |

**Max rounds:** 3 (default). Configurable.

---

## Termination Criteria

- Reviewer approves the final output
- Or: Leader accepts (with justification)
- Or: maximum iteration count reached (default: 3 rounds), Leader makes final call

---

## Review Scoring

**Pass threshold: >= 9/10.** Scores below 9 require re-running from the failing stage.

Reviewers must provide a decision matrix with per-dimension scores:

| Dimension | Score (1-10) | Deductions |
|-----------|-------------|------------|
| Correctness | | e.g., test cases don't match requirements |
| Completeness | | e.g., missing stage output |
| Clarity | | e.g., ambiguous handoff contract |
| Consistency | | e.g., stage 2 output doesn't align with stage 1 |
| **Overall** | | **>= 9 = PASS, < 9 = FIX (specify failing stage)** |

- **PASS** (>= 9): pipeline output accepted
- **FIX** (< 9): identify failing stage; re-run from that stage forward

---

## When to Use

- Tasks with natural sequential dependencies (each stage needs the previous output)
- Multi-step transformations (requirements → design → code → tests)
- When different specialists handle different stages

---

## When NOT to Use

- Stages are independent and can run in parallel (use COR-1603 instead)
- Single-stage task (use COR-1600 or COR-1601)
- When backtracking to earlier stages is expected (consider COR-1601 for more flexibility)

---

## Example

```
Task: Build API endpoint from requirements
Leader: Claude Code
Workers: GLM:req (requirements analysis), GLM:impl (code implementation), GLM:test (test writing)
Reviewer: Codex
Criteria: Codex must score >= 9/10

Stage 1: GLM:req analyzes requirements → produces API spec
Stage 2: GLM:impl receives API spec → produces Python code
Stage 3: GLM:test receives code → produces pytest test suite

Review:
  Codex reviews final test suite + code: 8/10 (test coverage insufficient)
  Leader: re-run from Stage 3
  GLM:test adds more test cases → Codex re-reviews → 9/10 ✓
```

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-19 | Initial version, with sequence diagram (D4), iteration mode (D3), and review scoring (D9) | Claude Code |
