# SOP-1602: Workflow — Multi Model Parallel Review

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-19
**Last reviewed:** 2026-03-19

---

## What Is It?

A collaboration pattern where multiple Reviewers independently analyze the same input in parallel, and the Leader synthesizes their findings. There is no Worker role — the artifact under review already exists (a plan, design, CHG document, code, etc.).

Also known as: Second Opinion, Multi-Model Review.

---

## Roles

| Role | Responsibility | Count |
|------|---------------|-------|
| **Leader** | Provides the artifact, dispatches reviewers, synthesizes findings, makes final decision | 1 |
| **Reviewer** | Independently analyzes the artifact, provides feedback and recommendations | 2+ |

No Worker role. The artifact is produced before this SOP is invoked.

---

## Sequence Diagram

```
Leader      Reviewer A    Reviewer B
  │             │             │
  │──artifact──▶│             │
  │──artifact────────────────▶│
  │             │             │        ← parallel review
  │◀──findings──│             │
  │◀──findings────────────────│
  │                           │
  │  synthesize               │
  │                           │
  │──revised───▶│             │        ← iteration (default: on)
  │──revised────────────────▶│
  │◀──OK────────│             │
  │◀──OK──────────────────────│
  │                           │
  │  ✓ accepted               │
  │             │             │
```

---

## Steps

1. **Leader identifies artifact** — the document, plan, code, or design to be reviewed
2. **Leader dispatches Reviewers** — all Reviewers receive the same artifact in parallel
3. **Reviewers analyze independently** — each produces findings, risks, and recommendations
4. **Leader collects all reviews** — waits for all Reviewers to complete
5. **Leader synthesizes** — identifies consensus, conflicts, and unique insights
6. **Leader revises artifact** — incorporates feedback (Leader is also the author in this pattern)
7. **If iteration is on** — Leader sends revised artifact back to Reviewers for re-review (repeat from step 3)
8. **If all Reviewers approve or Leader accepts** — done

---

## Iteration Mode

**Default: on** — Leader revises based on feedback and resubmits to Reviewers until approved or max rounds reached.

**To disable** (single-pass mode): set `iterate: false` when invoking the SOP.

```
/team plan --sop 1602 --no-iterate "review this plan"
```

When off: Reviewers analyze once, Leader synthesizes and decides. No re-review round.

| Setting | Behavior |
|---------|----------|
| `iterate: true` (default) | Review → Leader revise → Re-review → ... until approved |
| `iterate: false` | Review → Leader synthesize → done (single pass) |

**Max rounds:** 3 (default, lower than 1600/1601 since Leader is doing the revision). Configurable.

---

## Termination Criteria

- All Reviewers approve the (revised) artifact
- Or: Leader accepts the synthesis (with justification)
- Or: maximum iteration count reached (default: 3 rounds), Leader makes final call

---

## Review Scoring

**Pass threshold: >= 9/10.** Scores below 9 require revision.

Reviewers must provide a decision matrix with per-dimension scores:

| Dimension | Score (1-10) | Deductions |
|-----------|-------------|------------|
| Correctness | | e.g., logic error in step 3 |
| Completeness | | e.g., missing edge case handling |
| Clarity | | e.g., ambiguous variable naming |
| Consistency | | e.g., inconsistent with existing patterns |
| **Overall** | | **>= 9 = PASS, < 9 = FIX** |

- **PASS** (>= 9): no revision needed, approved
- **FIX** (< 9): Leader revises artifact based on deduction reasons

---

## When to Use

- Reviewing plans, designs, CHG documents before implementation
- Getting diverse perspectives on a decision
- Validating an approach before committing resources
- When the artifact already exists and needs evaluation, not creation

---

## When NOT to Use

- When the artifact needs to be created from scratch (use COR-1600 or COR-1601)
- When only one opinion is needed (just ask one model directly)
- Trivial decisions where parallel review adds latency without value

---

## Example

```
Task: Review FXA-2107-CHG (Code Quality Refactoring)
Leader: Claude Code
Reviewers: Codex (GPT-5.4), Gemini 3
Criteria: Both reviewers agree on implementation plan

Round 1 (iterate: false, single-pass):
  Claude sends CHG + source files to Codex and Gemini (parallel)
  Codex: "Item 4 not recommended — violates ISP. Expand item 1 scope."
  Gemini: "Item 4 needs caution. Suggest bottom-up order."
  Claude synthesizes: both reject item 4, consensus on expanding item 1
  Claude revises CHG → done
```

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-19 | Initial version, with sequence diagram (D4), iteration mode (D3), review scoring (D9), Workflow prefix (D5) | Claude Code |
