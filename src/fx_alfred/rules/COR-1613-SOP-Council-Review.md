# SOP-1613: Council Review

**Applies to:** All projects using the COR document system
**Last updated:** 2026-05-03
**Last reviewed:** 2026-05-03
**Status:** Active
**Depends on:** COR-1402 (Declare Active Process), COR-0002 (Document Format Contract)
**Related:** COR-1606 (Workflow Selection), COR-1602 (Multi-Model Parallel Review), COR-1600/1601 (Review Loops), COR-1608/1609/1610 (Scoring Rubrics), COR-1611 (Reviewer Calibration), COR-1612 (Respond To PR Review Comments)
**Authored from:** FXA-2113 PRP (3-of-4 reviewer PASS, chair-cast deciding vote via mechanism #13)

---

## What Is It?

The decision-mechanism contract for any multi-reviewer negotiated decision on a target (PRP / CHG / code diff / design choice / release decision / etc.). Council Review specifies **what voting/consensus rule is in force**, **what the threshold is**, **who is voting**, and **how the decision is recorded**, on top of whatever workflow pattern (COR-1600 through COR-1605) is already in use.

This SOP is intentionally framework-agnostic: it does not assume any specific harness, provider set, or fixed number of reviewers. Reviewers may be humans, LLMs, or a mix.

---

## Why

Without an explicit decision-mechanism layer, every multi-reviewer review tacitly inherits one rule (the implicit Decision-Matrix-style scoring under COR-1602 + COR-1608/9/10) and there is no vocabulary for selecting alternatives when the situation calls for them. This produces five failure modes:

1. Implicit mechanism selection — no SOP names the default as one *choice* among others
2. Implicit reviewer set — no record of which seats were called for a given review
3. Implicit threshold — "≥ 9.0 PASS" is folklore from COR-1608, not changeable per target risk
4. Tight coupling to one harness/provider set — current practice is hard to apply to a 3-person human review of a release, or a different multi-LLM panel
5. No vocabulary for high-stakes decisions — irreversible actions cannot demand a stronger rule (Veto / Consensus) than the default

Council Review fixes this by requiring every multi-reviewer review to **declare a Review Unit** before reviewers begin, naming the mechanism, threshold, reviewer set, and recording rule explicitly.

---

## When to Use

- Any task whose output is a decision that needs more than one reviewer
- Any review of a CHG / ADR / code PR / release / architectural choice with multi-party input
- Any decision whose reversibility, blast radius, or stakeholder count warrants a stronger rule than "two reviewers ≥ 9.0"

**Mandatory carve-out — PRP review.** PRP approval is governed by COR-1102, which mandates COR-1602 strict mode (both reviewers ≥ 9.0/10 on the COR-1608 rubric). Council Review applies to PRPs only as the *vocabulary* for declaring this gate explicitly: when the target is a PRP, the Review Unit's `mechanism:` MUST be `decision_matrix`, `rubric:` MUST be `COR-1608`, and `threshold:` MUST be `weighted_avg ≥ 9.0` for every reviewer (not the panel mean). Other mechanisms (Simple Majority, Lazy Consensus, etc.) are forbidden for PRP targets — they would bypass the COR-1102 gate.

## When NOT to Use

- Solo decisions on a single project with no other stakeholder (just decide and move on)
- Mid-task micro-choices that do not produce a durable artifact
- When an existing review SOP (COR-1600/1601/1602) already runs the review and the implicit Decision-Matrix mechanism is acceptable — in that case, declare the Review Unit inline (one block at the top of the review) rather than as a standalone artifact

---

## How

### Step 1 — Declare the Review Unit

Before reviewers begin, the dispatcher fills the following block (in conversation context, in the PR body, or in a session note — wherever the review is taking place):

```yaml
# Required (always)
review_id:    <unique ID — free-form, e.g. "release-v1.9.0" or "FXA-2113-eval">
target:       <what is being reviewed — file path / PR # / decision question>
mechanism:    <one of the mechanisms in §Mechanism Library below>
rubric:       <scoring rule when the mechanism is scoring-based; reference an existing
              rubric ID (e.g. "COR-1608") OR inline a custom one. Set to "n/a" for
              non-scoring mechanisms (Simple Majority, Lazy Consensus, etc.)>
threshold:    <pass condition; if omitted, applies the mechanism's default>
reviewers:    <list of reviewer identities; humans, LLMs, or mixed; any N≥1>

# Required only for specific mechanisms
window:               <ISO-8601 duration; required for Lazy Consensus>
inner_mechanism:      <one of the mechanisms below; required for Random Sample/Sortition>
veto_seats:           <subset of reviewers with veto power; required for Veto>
weights:              <map reviewer→weight; required for Weighted Vote>
max_rounds:           <int; required for Delphi>
variance_threshold:   <float; required for Delphi>

# Optional with explicit defaults
quorum:                  <min N responders; default = len(reviewers); a mechanism may override (e.g., Lazy Consensus permits 0)>
abstention_rule:         <abstain_as_no | abstain_excluded | abstain_blocks; default = abstain_excluded>
tie_break:               <re_review | dictator:<identity> | reject; default = re_review. <identity> must appear in `reviewers:`>
deadline:                <ISO-8601 timestamp; default = none (sync review assumed)>
disagreement_threshold:  <numeric or "any"; if pairwise disagreement exceeds this value, Step-5 reconciliation is required. Default = "any" (any non-zero disagreement triggers reconciliation)>
blind:                   <true | false; default = true; lifts after Step 4 aggregation>
```

**Frozen after declaration:** `mechanism`, `rubric`, `threshold`, `reviewers`. These cannot be changed after the review begins (prevents post-hoc rule-shopping). Other fields may be amended only with a written annotation in the Review Unit log line stating who amended what and why.

**Scoring scale.** When `rubric` references one of COR-1608/1609/1610 (which use 0–10), thresholds use the **rubric's native 0–10 scale** — no conversion is applied. Inline custom rubrics declare their own scale via `rubric.scale: <min>-<max>` (e.g., `0-100`, `1-5`).

### Step 2 — Convene

Distribute the target + rubric to all reviewers. For LLM reviewers, COR-1611 calibration applies; for human reviewers, equivalent calibration (shared briefing on what the rubric dimensions mean) is the dispatcher's responsibility.

### Step 3 — Independent Evaluation

When `blind: true` (default), reviewers do **not** see each other's outputs before submitting. This prevents groupthink and anchoring. Exception: Delphi explicitly iterates with shared anonymized aggregates between rounds. For async reviews with rolling submission, "submitted" means "the dispatcher has received the response"; the blind constraint lifts after Step 4 aggregation, allowing Step-5 reconciliation discussions.

### Step 4 — Aggregate

Compute the outcome per the declared mechanism. Apply `quorum` and `abstention_rule`. If quorum fails (insufficient responders), the result is **`inconclusive`** — neither pass nor reject. The dispatcher's only in-flight option is to extend the deadline (amend `deadline:` per the Step-1 amendment-annotation rule for non-frozen fields). **The current Review Unit's frozen fields (`mechanism`, `rubric`, `threshold`, `reviewers`) cannot be modified after declaration** — that would defeat the Step-1 freeze and re-introduce post-hoc rule-shopping for high-stakes mechanisms (Veto / Consensus). If a deadline extension is not viable or still does not reach quorum, abort the current Review Unit and start a brand-new one with whatever revised mechanism / reviewer set is appropriate, declared up front.

### Step 5 — Adjudicate

Outcome is one of `pass` / `re_review` / `reject`. If any pairwise disagreement among reviewers exceeds `disagreement_threshold` (default: any disagreement triggers), the dispatcher must record a one-line reconciliation note before declaring the final outcome:

```
Disagreement: <reviewer_a> rated X, <reviewer_b> rated Y on <dim>; resolved by <action>.
```

Tie-breaks are resolved per the `tie_break:` field.

### Step 6 — Record

Durable record requirements (in order of strength):

1. **Document outputs** — produced via `af create` for the supported types (`sop | adr | prp | ref | chg | pln | inc`). For PRP and CHG (the only types where COR-0002 lists `Reviewed by:` as an optional metadata field), the Review Unit `review_id:` appears in `Reviewed by:`. For other document types, the Review Unit `review_id:` is appended as the first line of the Change History entry recording the creation event instead.
2. **Reject decisions** → recorded in the target document's Change History with mechanism + reviewers + reason.
3. **Irreversible operations** (delete PKG doc, release tag, schema change) → recorded in the affected document's Change History.
4. **All other PASS decisions** → at minimum, append one line to the target's Change History (or, if the target has no Change History, to the PR description / commit body). Format:
   ```
   <date> | Council review (mechanism=X, reviewers=N, threshold=Y) → PASS | <dispatcher>
   ```

This minimum-line requirement closes the otherwise-invisible review trail without requiring a new archival store.

---

## Mechanism Library

Mechanisms are split into **Core** (4, presented inline) and **Advanced** (10, in the appendix). The split is a readability concession; all 14 are equally available — declare any by name in the Review Unit `mechanism:` field. The library size is itself an open question and will be revisited per §Open Questions §1.

### Core mechanisms

| # | Mechanism | When to use | Default threshold |
|---|---|---|---|
| 1 | Decision Matrix | Multi-dimensional weighted scoring (PRP/CHG/code review) | weighted average ≥ rubric's PASS line. **No per-dimension floor by default** — to add one, the Review Unit must explicitly set `threshold.min_per_dim: <value>`. |
| 2 | Simple Majority | Binary or enum choice | > 50% of responders in favor (denominator depends on `abstention_rule`) |
| 4 | Consensus | Direction-setting in high-trust group | 100% of responders in favor; any objection blocks. Tie-break inapplicable. |
| 5 | Veto | Irreversible / high-risk (delete PKG doc, release tag, schema change) | All responders ≥ rubric PASS (or, if `rubric: n/a`, all unconditionally approve) AND no `veto_seats:` reviewer objects. Example with `rubric: n/a` and `veto_seats: [security_lead]`: every responder must approve; if `security_lead` objects, the decision fails regardless of others. |

### Advanced mechanisms (appendix)

| # | Mechanism | When to use | Default threshold |
|---|---|---|---|
| 3 | Supermajority | Medium-risk decisions where simple majority feels weak | declared at call time as `threshold.fraction: 2/3` (or 3/4); in-favor count uses `abstention_rule`'s denominator |
| 6 | Weighted Vote | Reviewer weights differ (domain expert 2×, etc.) | Σ(weight × in-favor) / Σ(weight × responders) ≥ `threshold.fraction` (default 0.5) |
| 7 | Quadratic Voting | Multi-option ranking with preference intensity | √(votes) sum highest wins. **Pitfall:** susceptible to collusion (Gibbard-Satterthwaite). |
| 8 | Approval Voting | Pick ≥1 acceptable option from many | option with most approvals wins; ties resolved per `tie_break`. |
| 9 | Ranked Choice / IRV | Multi-option needs single winner | iteratively eliminate the lowest until majority. **Pitfall:** non-monotonic (ranking a candidate higher can hurt them). |
| 10 | Borda Count | Aggregate ranked preferences | rank-weighted sum highest wins. **Pitfall:** vulnerable to clone candidates. |
| 11 | Delphi | High uncertainty; need convergence forecast | rounds of anonymous estimates revealed in aggregate; stop when σ² < `variance_threshold` or rounds ≥ `max_rounds`. Final value = mean of last round. |
| 12 | Lazy Consensus | Low-risk routine changes (dep bump, doc typo) | no objection raised before `window` elapses = pass. `quorum: 0` is permitted (truly lazy). |
| 13 | Dictator / Single Reviewer | Emergency hotfix, micro-change, solo project, or chair-cast tie-break | `reviewers:` list contains exactly one identity; that reviewer's verdict is final. |
| 14 | Random Sample / Sortition | Reviewer pool too large for full poll | randomly draw N from `reviewers:`, then apply `inner_mechanism` to the sample. Sortition is a **selection wrapper**, not a decision rule — `inner_mechanism` is required. |

### Voting-theory caveats (for mechanisms 7/8/9/10)

These mechanisms are subject to known impossibility and manipulability results (Arrow, Gibbard-Satterthwaite, Condorcet). When the outcome space is constrained to a small set (e.g., `{PASS, FIX, REJECT}` for most reviews), the paradoxes are largely sidestepped. For genuine multi-option choices (e.g., "which architecture?"), prefer **Approval Voting** or **Decision Matrix** over Borda/IRV unless the dispatcher understands the trade-offs.

### Lightest-mechanism principle

Always pick the lightest mechanism that fits the decision's reversibility and blast radius. Reaching for Veto on every review labeled "important" is mechanism inflation — it imposes coordination cost without buying safety. The escalation ladder is roughly: Lazy Consensus → Simple Majority → Decision Matrix → Supermajority → Consensus → Veto.

---

## Relationship to Other SOPs

- **COR-1402 (Declare Active Process)** — Council Review is itself an active SOP that must be declared when in use.
- **COR-1606 (Workflow Selection)** — orthogonal axis: COR-1606 picks a *workflow pattern* (1600–1605) for *how reviewers are organized*; COR-1613 picks a *decision rule* applied to whatever pattern was selected. A review can use both: "COR-1602 parallel pattern with Council mechanism = Decision Matrix and reviewers = panel."
- **COR-1602 (Multi-Model Parallel Review)** — the most common instance of Council Review in current practice: mechanism = Decision Matrix, reviewers = a parallel-dispatched panel (LLM, human, or mixed). COR-1602 contributes the dispatch + Leader-synthesis plumbing; Council contributes the mechanism declaration.
- **COR-1600/1601 (Direct / Leader-Mediated Review Loops)** — describe *who routes the review*; the COR-1600 "Lead Reviewer tie-break" is itself an instance of the Council `tie_break: dictator:<lead_reviewer>` setting.
- **COR-1608/1609/1610 (Scoring Rubrics)** — referenced from a Review Unit's `rubric:` field when `mechanism = Decision Matrix`. Unchanged by this SOP.
- **COR-1611 (Reviewer Calibration)** — applies to **any reviewer** using one of the COR-1608/9/10 rubrics under a Decision Matrix mechanism (humans included), not exclusively LLMs.
- **COR-1612 (Respond To PR Review Comments)** — covers the *post-decision response* lane for PR-context reviews; complements Council's *during-decision* mechanism layer.

---

## Universality Contract

This SOP must not name:
- Any specific harness or runtime
- Any specific LLM provider, model name, or panel composition
- Any fixed number of reviewers
- Any specific human role names (other than abstract roles like "dispatcher", "reviewer", "lead reviewer")

If a project's habits depend on such specifics (e.g., "in this project, the default reviewer panel is a fixed 4-LLM set"), record those in a USR/PRJ-layer supplementary doc, not here.

---

## Open Questions

1. **Mechanism library size (deferred).** A round-2 reviewer of FXA-2113 raised that 14 mechanisms may be overprovisioned for current usage, where only Decision Matrix is in active use. The Core+Advanced split is a readability concession but does not retire the question. **Plan:** revisit this question 90 days after this SOP becomes Active (≈ 2026-08-01). If fewer than 6 mechanisms have been invoked at least once in real reviews by then, demote the unused mechanisms to a separate `COR-1614-REF-Decision-Mechanism-Library.md` and trim this SOP body to the Core. Until then, the full library is documented here.

2. **`af council` tooling.** No tooling exists today for declaring or aggregating Review Units — they live in conversation context, PR bodies, or session notes. If usage shows that manual declaration is error-prone, a future PRP may propose `af council declare/aggregate` commands. Out of scope for this SOP.

3. **Universality contract enforcement.** This SOP asks reviewers to verify the body does not name harnesses/providers/panels. A future small enhancement to `af validate` could grep for forbidden tokens. Out of scope here.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-03 | Initial version per FXA-2113 PRP. Round-1 review (4 reviewers) returned unanimous FIX (mean 8.0). Round-2 review returned 3-of-4 PASS (mean 9.03); one reviewer persistently raised mechanism-count and steelman-strength concerns. Chair cast the deciding vote PASS via mechanism #13 (Dictator/Single Reviewer) as tie-break. The dissent is captured as Open Question §1 with a 90-day revisit clause. | Frank Xu |
