# PRP-2262: COR-1613-Council-Review-Mechanism

**Applies to:** FXA project
**Last updated:** 2026-05-03
**Last reviewed:** 2026-05-03
**Status:** Approved
**Reviewed by:** GLM, Codex, Gemini, DeepSeek (round 1, 2026-05-03 — unanimous FIX); revising for round 2
**Target document:** COR-1613 (PKG layer, new SOP) — ACID family-fit justified in §1.0
**Inspired by:** mattpocock/skills (Round 0 of skills-absorption initiative)

---

## What Is It?

A new PKG-layer SOP that defines the **generic mechanism for any multi-reviewer negotiated decision** on a given target (PRP / CHG / code diff / design choice / release decision). The SOP is intentionally framework-agnostic: it does not assume any specific harness, provider set, or fixed number of reviewers. Reviewers may be humans, LLMs, or a mix.

Existing review SOPs (COR-1602 multi-model parallel review, COR-1608/1609/1610 scoring rubrics, COR-1611 calibration) are **not replaced**. COR-1613 sits one layer above them as the **decision-mechanism contract**: it specifies what voting/consensus rule is in force, what the threshold is, who is voting, and how the decision is recorded. Existing rubrics are referenced as the scoring source when the chosen mechanism is scoring-based.

---

## Problem

Alfred today has scoring rubrics (COR-1608/9/10) and a multi-model parallel review SOP (COR-1602), but does not have a generic, declared **decision mechanism** layer. In practice this causes:

1. **Implicit mechanism selection** — every review tacitly uses Decision-Matrix-style scoring (COR-1602's "2+ reviewers, COR-1608/9/10 rubrics, ≥ 9.0 PASS"), but no SOP names this as one *choice* among others, and there is no vocabulary for selecting alternatives (majority vote, veto, consensus, lazy consensus, etc.) when the situation calls for them.
2. **Reviewer set is implicit** — the operative reviewer set is assumed in conversation but not declared per-review. After the fact, a review record cannot tell us which seats were called.
3. **Threshold is implicit** — "≥ 9.0" is folklore inherited from COR-1608; not stated per review, not changeable per target risk level.
4. **Tight coupling to one harness/provider set** — current practice is hard to apply outside the default execution environment (e.g., a 3-person human review of a release, or a different multi-LLM panel). The mechanism vocabulary should be portable.
5. **No vocabulary for high-stakes decisions** — irreversible actions (delete PKG doc, release tag, schema change) should be able to require a stronger mechanism (veto / consensus). Today everything uses the same default.

**Steelman of "do not ship":** The cheapest fix for pains 1–3 is a one-paragraph "Decision Mechanism" addition to COR-1602 that names the implicit Decision Matrix as the current default. This was raised in round 1 review (DeepSeek, 2026-05-03) and is a real alternative. Rejected here because pains 4–5 require a *vocabulary* (more than one named mechanism), which a single paragraph cannot express — but the rejection is acknowledged, and the SOP body must justify the heavier scaffold against this baseline.

---

## Proposed Solution

### 1.0 ACID family-fit and routing

**Family-fit justification.** The 16xx family currently splits into:
- 1600/1601 — review *workflow loops* (who initiates, who arbitrates)
- 1602/1603/1604/1605 — review *workflow patterns* (parallel / pipeline / etc.)
- 1606 — *workflow selection* (decision tree picking among 1600–1605)
- 1608/1609/1610 — scoring *rubrics*
- 1611 — reviewer *calibration*
- 1612 — post-review *response* to PR comments

COR-1613 is a *meta-mechanism layer*: it declares **which decision rule** is being applied to whatever workflow pattern was selected. It is conceptually adjacent to COR-1606 (which selects workflows) but operates on the orthogonal axis (selecting decision rules). Two valid placement options were considered:

- **Option A (chosen): COR-1613.** Slot at end of the 16xx family on the basis that decision-mechanism selection is the natural pair to workflow selection (1606), and keeping the entire review topic in 16xx aids discoverability. Numerically last in family.
- **Option B (rejected): COR-1620 or new 19xx family.** Cleaner taxonomic separation but fragments the review topic across two ACID ranges and increases routing-tree depth in COR-1103.

**Routing.** This PRP commits to a follow-up CHG (`FXA-2263`) that updates COR-1103's intent router and OVERLAYS section to insert COR-1613. Without that update, the SOP would be discoverable only by direct reference and would be effectively orphaned. The CHG is small (one-line in the OVERLAYS table; one branch in the decision tree) and is in-scope for the same merge window as the SOP itself, even though authored as a separate PR.

### 1.1 New PKG SOP — COR-1613-SOP-Council-Review

A 5W1H SOP defining a **Review Unit** contract, a 6-step workflow, and a library of decision mechanisms.

**Review Unit (must be declared before review starts):**

```yaml
# Required
review_id:    <unique ID — free-form, e.g. "release-v1.9.0" or "FXA-2262-eval">
target:       <what is being reviewed — file path / PR # / decision question>
mechanism:    <one of the mechanisms in §1.2 below>
rubric:       <scoring rule when mechanism is scoring-based; reference an existing
              rubric ID (e.g. "COR-1608") OR inline a custom one. Set to "n/a"
              for non-scoring mechanisms (Simple Majority, Lazy Consensus, etc.)>
threshold:    <pass condition; if omitted, applies the mechanism's default>
reviewers:    <list of reviewer identities; humans, LLMs, or mixed; any N≥1>

# Required for specific mechanisms (see §1.2 mechanism table)
window:               <ISO-8601 duration; required for Lazy Consensus>
inner_mechanism:      <one of §1.2 mechanisms; required for Random Sample/Sortition>
veto_seats:           <subset of reviewers with veto power; required for Veto>
weights:              <map reviewer→weight; required for Weighted Vote>
max_rounds:           <int; required for Delphi>
variance_threshold:   <float; required for Delphi>

# Optional with explicit defaults
quorum:                  <min N responders; default = len(reviewers) (all must respond)>
abstention_rule:         <abstain_as_no | abstain_excluded | abstain_blocks; default = abstain_excluded>
tie_break:               <re_review | dictator:<name> | reject; default = re_review>
deadline:                <ISO-8601 timestamp; default = none (sync review assumed)>
disagreement_threshold:  <numeric or "any"; below which step-5 reconciliation is required;
                         default = "any" (any disagreement triggers reconciliation)>
blind:                   <true | false; default = true; lifts after Step 4 aggregation>
```

**Default scoring scale (single source of truth).** When `rubric` references one of COR-1608/1609/1610 (which use 0–10), thresholds are quoted on the **rubric's native 0–10 scale** — no conversion is applied. The Council SOP itself does not impose a competing scale. Inline custom rubrics declare their own scale in `rubric.scale:`. This eliminates the 100-pt vs 10-pt ambiguity flagged in round 1.

### 1.2 Mechanism library

Reorganized into **Core (4)** and **Advanced (10)** to address the COR-1400 atomicity stress flagged in round 1. The SOP body presents Core inline; Advanced moves to an appendix table with a one-line "use only when" disclaimer per mechanism. All 14 remain available; the inline/appendix split is a readability concession, not a reduction in scope.

**Core mechanisms (inline in SOP body):**

| # | Mechanism | When to use | Default threshold (uses rubric's native scale) |
|---|---|---|---|
| 1 | Decision Matrix | Multi-dimensional weighted scoring (PRP/CHG/code review) | weighted avg ≥ rubric's PASS line. **No additional per-dimension floor by default** — to add one, the Review Unit must explicitly set `threshold.min_per_dim: <value>`. (Removes the silent tightening flagged in round 1.) |
| 2 | Simple Majority | Binary / enum choice | > 50% of responders in favor (denominator = responders, modulo `abstention_rule`) |
| 4 | Consensus | Direction-setting in high-trust group | 100% of responders in favor; any objection blocks. Tie-break inapplicable. |
| 5 | Veto | Irreversible / high-risk (delete PKG doc, release tag, schema change) | All responders ≥ rubric PASS (or unconditional approve for non-scoring) AND no `veto_seats:` reviewer objects. The legacy "P5" alias is dropped — it implied a fixed 5-seat panel, conflicting with the universality contract. |

**Advanced mechanisms (appendix):**

| # | Mechanism | When to use | Default threshold |
|---|---|---|---|
| 3 | Supermajority | Medium-risk decisions where simple majority feels weak | declared at call time as `threshold.fraction: 2/3` (or 3/4); in favor count uses `abstention_rule`'s denominator |
| 6 | Weighted Vote | Reviewer weights differ (domain expert 2×, etc.) | Σ(weight × in-favor) / Σ(weight × responders) ≥ `threshold.fraction` (default 0.5) |
| 7 | Quadratic Voting | Multi-option ranking with preference intensity | √(votes) sum highest wins. **Pitfall:** susceptible to collusion (Gibbard-Satterthwaite) — see §1.4 voting-theory caveats. |
| 8 | Approval Voting | Pick ≥1 acceptable option from many | option with most approvals wins; ties → `tie_break`. |
| 9 | Ranked Choice / IRV | Multi-option needs single winner | iteratively eliminate lowest until majority. **Pitfall:** non-monotonic (ranking a candidate higher can hurt them). |
| 10 | Borda Count | Aggregate ranked preferences | rank-weighted sum highest wins. **Pitfall:** vulnerable to clone candidates (Condorcet). |
| 11 | Delphi | High uncertainty; need convergence forecast | rounds of anonymous estimates revealed in aggregate; stop when σ² < `variance_threshold` or rounds ≥ `max_rounds`. Final value = mean of last round. |
| 12 | Lazy Consensus | Low-risk routine changes (dep bump, doc typo) | no objection raised before `window` elapses = pass. `quorum: 0` is permitted (truly lazy). |
| 13 | Dictator / Single Reviewer | Emergency hotfix, micro-change, solo project | `reviewers:` list contains exactly one identity; that reviewer's verdict is final. |
| 14 | Random Sample / Sortition | Reviewer pool too large for full poll | randomly draw N from `reviewers:`, then apply `inner_mechanism` to the sample. Sortition is a **selection wrapper**, not a decision rule — `inner_mechanism` is required. |

### 1.3 Six-step workflow (How)

1. **Declare Review Unit** — fill all required fields in §1.1 (including mechanism-specific required fields per §1.2). Mechanism, rubric, threshold, and reviewers are **frozen** after declaration. Other fields (deadline extension, adding a reviewer who was unreachable) may be amended only with written annotation in the Review Unit log line.
2. **Convene** — distribute target + rubric to reviewers (sync or async per `deadline`). For LLM reviewers, COR-1611 calibration applies; for human reviewers, equivalent calibration is the caller's responsibility.
3. **Independent Evaluation** — when `blind: true` (default), reviewers do not see each other's outputs before submitting (prevents groupthink). Exception: Delphi explicitly iterates with shared aggregates (anonymized). Blind constraint lifts after Step 4 aggregation, allowing Step-5 reconciliation discussions.
4. **Aggregate** — compute outcome per declared mechanism, applying `quorum` and `abstention_rule`. If quorum fails, the result is `inconclusive`, not `reject`.
5. **Adjudicate** — `pass` / `re-review` / `reject`. If any pairwise disagreement exceeds `disagreement_threshold` (default: any disagreement triggers), the dispatcher must record a one-line reconciliation note (which reviewer, what point, what was decided) before declaring the final outcome. Tie-breaks resolved per `tie_break:` field.
6. **Record** — durable record requirements:
   - **Document outputs** (PRP / CHG / ADR / CTX) → produced via `af create`; the Review Unit `review_id:` appears in the output's "Reviewed by" field.
   - **Reject decisions** → recorded in target document's Change History with mechanism + reviewers + reason.
   - **Irreversible operations** → recorded in affected document's Change History.
   - **All other PASS decisions** → at minimum, a one-line entry appended to the target's Change History (or, if target has no Change History, to the PR description / commit body): `<date> | Council review (mechanism=X, reviewers=N, threshold=Y) → PASS | <dispatcher>`. This addresses the round-1 "lost decision context" gap (DeepSeek, GLM) without requiring a new archival store.

### 1.4 Voting-theory caveats (informational, in SOP body)

The SOP body must briefly note (≤ 5 lines) that mechanisms 7/8/9/10 are subject to known impossibility and manipulability results (Arrow, Gibbard-Satterthwaite, Condorcet). Alfred constrains the outcome space to `{PASS, FIX, REJECT}` for most reviews, which sidesteps most paradoxes — but for genuine multi-option choices (e.g., "which architecture?"), reviewers should prefer Approval or Decision Matrix over Borda/IRV unless they understand the trade-offs.

### 2. Relationship to existing SOPs

- **COR-1103 (Workflow Routing)** — **must be updated** in companion CHG `FXA-2263` to add Council-Review entry to OVERLAYS and to the intent router decision tree (e.g., "any task that produces a decision needing > 1 reviewer → consult COR-1613"). This is no longer optional; without it, COR-1613 is orphaned (round-1 finding, Gemini).
- **COR-1400 (Atomic SOP Principle)** — explicitly addressed: COR-1613 is one SOP because it has one purpose ("declare a decision mechanism"); the mechanism library is reference material under that single purpose, presented as a Core+Advanced split (precedent: COR-1606's quick-reference table). If reviewers reject this defense, fall-back is to split into COR-1613 (procedure) + COR-1614-REF (mechanism library).
- **COR-1402 (Declare Active Process)** — Council-Review is itself an active SOP that must be declared when in use.
- **COR-1602 (Multi-Model Parallel Review)** — becomes an *instance* of Council-Review where mechanism = Decision Matrix and reviewers = a parallel-dispatched panel (LLM, human, or mixed). COR-1602 contributes the Leader-synthesis + iteration plumbing; COR-1613 contributes the mechanism declaration. **The two are layered, not redundant.** A follow-up CHG (`FXA-2264`) will add a one-paragraph cross-reference to COR-1602 noting this; that CHG is the only sanctioned modification to COR-1602.
- **COR-1606 (Workflow Selection)** — orthogonal axis: COR-1606 picks a *workflow pattern* (1600–1605); COR-1613 picks a *decision rule* applied to that pattern. The SOP body must include a one-paragraph "How to read this alongside COR-1606" callout to prevent routing collision (round-1 finding, Gemini).
- **COR-1608/1609/1610 (Scoring Rubrics)** — referenced by Review Units that pick mechanism = Decision Matrix. Unchanged; no modifications proposed.
- **COR-1611 (Reviewer Calibration)** — applies to **any reviewer** using the COR-1608/9/10 rubrics under a Decision Matrix mechanism, not exclusively LLMs. (Round-1 correction from Codex.) Cross-reference in COR-1613 will state this scope explicitly.
- **COR-1612 (Respond To PR Review Comments)** — covers the *post-decision response* lane for PR-context reviews; complements COR-1613's *during-decision* mechanism layer. One-line cross-reference added in §2 of the SOP body.
- **COR-1600/1601 (Direct / Leader-Mediated Review Loops)** — cover *who routes the review*; orthogonal to mechanism choice. COR-1600's "Lead Reviewer tie-break" is itself an instance of Council's `tie_break: dictator:<lead_reviewer>` setting; the SOP body acknowledges this without modifying COR-1600.

### 3. Universality contract

The SOP body **must not** mention:
- Any specific harness or runtime (e.g., Claude Code)
- Any specific LLM provider or trinity panel composition
- Any fixed number of reviewers
- Any specific human role names

If any of those appear, they belong in a USR/PRJ-layer supplementary doc, not in the PKG SOP. **Enforcement:** the SOP review checklist will include a grep for forbidden tokens; future `af validate` enhancement (out of scope here) may codify this.

### 4. Scope of this PRP

In scope:
- Drafting the new PKG SOP `COR-1613-SOP-Council-Review.md`
- Specifying its file path: `src/fx_alfred/rules/COR-1613-SOP-Council-Review.md`
- Defining the Review Unit schema and the 14-mechanism library (Core + Advanced)
- Defining the 6-step workflow

Companion CHGs (separate PRs, same merge window):
- `FXA-2263-CHG-COR-1103-Add-Council-Review-Routing.md` — updates COR-1103 OVERLAYS + decision tree
- `FXA-2264-CHG-COR-1602-Add-Council-Cross-Reference.md` — one-paragraph cross-reference in COR-1602 §Relationship

Out of scope:
- `af council` tooling (deferred; flagged for future PRP if usage warrants)
- `af validate` enforcement of the universality contract grep (deferred)
- Migrating past reviews to declare retroactive Review Units (past records unchanged)
- Splitting into COR-1613 + COR-1614-REF (held as fall-back if round-2 review rejects the Core+Advanced split)

---

## Open Questions

All resolved by user confirmation prior to round-1 review. Round-1 reviewer findings have been incorporated into the body above; no new OQs raised.

1. **Self-review of this PRP** — RESOLVED: 4-LLM parallel Decision Matrix (COR-1608 rubric) for both round 1 (complete; unanimous FIX) and round 2 (this revision). From FXA-2263 onward, all reviews declare a Review Unit per COR-1613.
2. **Default threshold values** — RESOLVED: defer to rubric's native scale (no 100-pt conversion); each Review Unit may override via its `threshold:` field.
3. **Mechanism count (14)** — RESOLVED: keep 14, split into Core (4 inline) + Advanced (10 appendix) for atomicity.
4. **Where does the Review Unit live during the session?** — RESOLVED: conversation context only by default; promoted to a written one-liner in the target's Change History per Step 6.
5. **`af` tooling for Council mechanics** — RESOLVED: out of scope for this PRP.

---

## Change History

| Date       | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | By                     |
|------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------|
| 2026-05-03 | Initial version                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Claude Code            |
| 2026-05-03 | Drafted as Round 0 of mattpocock/skills absorption initiative; user confirmed 14-mechanism library, 100-pt default scale, no mandatory archival                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Claude Code            |
| 2026-05-03 | Round 1 review by GLM/Codex/Gemini/DeepSeek — unanimous FIX (mean 8.0/10, DeepSeek breach of <7.0 sub-floor on Risk Awareness). Revised: CJK→English, scoring scale ambiguity resolved, Review Unit schema expanded with quorum/abstention/tie_break/deadline/disagreement_threshold/blind/window/inner_mechanism/veto_seats/weights/max_rounds/variance_threshold, mechanism table reorganized into Core+Advanced for COR-1400 atomicity, dropped silent "no dim < 70" floor, ACID 1613 family-fit justified, COR-1606/1612 relationships added, COR-1611 scope corrected, voting-theory caveats added, two companion CHGs (FXA-2263 routing, FXA-2264 cross-ref) committed in scope, Step-6 traceability gap closed with mandatory one-line PASS log. | Claude Code            |
| 2026-05-03 | Round 2 review: GLM 9.12 PASS / Codex 9.41 PASS / Gemini 9.7 PASS / DeepSeek 7.9 FIX. Mean 9.03. 3-of-4 PASS. Chair (Frank Xu) cast deciding vote = PASS via Dictator/Single-Reviewer mechanism (COR-1613 mech #13 invoked as tie-break). DeepSeek's persistent dissent on mechanism count (14 may be overprovisioned) and steelman-strength is recorded as a known divergence; SOP body will carry an explicit OQ to revisit mechanism library after 90 days of usage data. Path C selected.                                                                                                                                                                                                                                                           | Frank Xu + Claude Code |
