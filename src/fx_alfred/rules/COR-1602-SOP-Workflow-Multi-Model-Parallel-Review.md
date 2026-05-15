# SOP-1602: Workflow — Multi Model Parallel Review

**Applies to:** All projects using the COR document system
**Last updated:** 2026-05-15
**Last reviewed:** 2026-05-15
**Status:** Active
**Related:** COR-1612 (Respond To PR Review Comments), COR-1613 (Council Review), COR-1615 (GitHub App PR Review Bot Loop)
**Workflow loops:** [{id: review-retry, from: 7, to: 3, max_iterations: 3, condition: "iteration is on and not all reviewers approve"}]
**Task tags:** [review, code-review, plan-review, multi-model, prp-review, implement]

---

## What Is It?

A collaboration pattern where multiple Reviewers independently analyze the same input in parallel, and the Leader synthesizes their findings. There is no Worker role — the artifact under review already exists (a plan, design, CHG document, code, etc.).

Also known as: Second Opinion, Multi-Model Review.

---

## Why

Leverages diverse model perspectives to catch blind spots, reduce bias, and produce higher-confidence decisions on existing artifacts before committing to implementation.

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

   **Reference:** COR-1705 through COR-1709 (Code Review Checklists) for domain-specific review items. Consult the relevant SOP based on the artifact's surface: COR-1706 (structural checks), COR-1707 (cross-cutting concerns), COR-1708 (domain-specific checks), COR-1709 (AI-assisted code + quick reference). Read COR-1705 (REF — Classification System) once for the G/A/H and P0/P1/P2 taxonomy used by all checklist SOPs.

2. **Leader dispatches Reviewers** — all Reviewers receive the same artifact in parallel

   **Dispatch context:** When dispatching Reviewers, include instructions for accessing project artifacts. Since all projects using this workflow have `af` installed, include:
   - `af read <ACID>` — read a document by ID
   - `af list` — list all documents

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
/trinity codex "review this plan" gemini "review this plan"  # parallel dispatch, single pass
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
- For PR-context artifacts, GitHub-side review channels are an independent readiness gate: before declaring merge-ready, run the COR-1615 pre-merge sweep and route any non-bookkeeping GitHub App review bot, code-review app, or human GitHub review-thread findings through COR-1612.
- In-conversation panel PASS is necessary where this SOP is the selected review workflow, but it is not sufficient when unresolved or unreplied GitHub-side review threads exist. The PR is not done until each non-bookkeeping GitHub-side thread is resolved, outdated, or has an author reply addressing it per COR-1612.
- If the repository has no GitHub App review bot installed, the bot-specific portion of the sweep is empty; human and code-review-app GitHub threads still count. This PR-readiness gate is satisfied only when the COR-1615 sweep finds zero non-bookkeeping GitHub-side review threads, or every such thread is resolved, outdated, or author-addressed.

---

## Review Scoring

**Pass threshold: >= 9.0/10.** Scores below 9.0 require revision.

Before scoring, select the appropriate rubric based on artifact type:
- PRP (Proposal) → COR-1608
- CHG (Change Request) → COR-1609
- Code → COR-1610
- Other (PLN, ADR, design, etc.) → use COR-1609 (CHG rubric) as fallback

All reviewers must follow COR-1611 (Reviewer Calibration Guide).

Score = weighted average of the rubric's dimensions, rounded to one decimal.
- **PASS** (>= 9.0): approved
- **FIX** (< 9.0): Leader revises based on deduction reasons

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

## Relationship to COR-1613 (Council Review)

COR-1602 specifies the *workflow pattern* for parallel-dispatch reviews (how reviewers are convened, how the Leader synthesizes outputs, how iteration loops work). COR-1613 specifies the *decision rule* applied to whatever pattern is in use. The two are layered, not redundant: a typical multi-reviewer review under COR-1602 declares a Council Review Unit (per COR-1613) with `mechanism: decision_matrix` and `rubric: COR-1608/1609/1610` as the default.

Reviewers may declare a different mechanism (Veto, Consensus, etc.) when the target's risk profile warrants it. **When the declared Council mechanism is anything other than `decision_matrix`, COR-1602's Leader-override termination paths are suspended** — specifically, "Leader accepts" approval and "max rounds ... Leader makes final call" cannot override the declared mechanism's outcome. A Veto-objected target cannot be approved by Leader override; a Consensus-blocked target cannot be approved by Leader override. The Leader's role in non-Decision-Matrix mode is reduced to dispatch + synthesis + recording the mechanism-determined outcome. This preserves the Step-1 freeze guarantee in COR-1613.

The GitHub-side pre-merge sweep above is not a Council decision mechanism and does not alter a declared Review Unit's frozen mechanism, threshold, or reviewer set. It is a PR-readiness precondition that runs after or alongside the mechanism result, because GitHub App review bots and inline review threads are detector surfaces outside the in-conversation panel.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-19 | Initial version, with sequence diagram (D4), iteration mode (D3), review scoring (D9), Workflow prefix (D5) | Claude Code |
| 2026-03-20 | Added Why section per FXA-2223 | Claude Code |
| 2026-04-01 | CHG FXA-2183: Add dispatch context with af read/af list usage to dispatch steps | Claude Code |
| 2026-05-03 | FXA-2264: add "Relationship to COR-1613 (Council Review)" subsection clarifying COR-1602 as workflow-pattern layered with Council's mechanism contract. | Frank Xu |
| 2026-05-15 | FXA-2285: add GitHub-side pre-merge review-thread gate; panel PASS is necessary but not sufficient when unresolved GitHub PR threads exist. | Codex |
| 2026-05-15 | FXA-2285 R2: clarify no-bot repos still must clear human and code-review-app GitHub threads before merge-ready. | Codex |
