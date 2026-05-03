# PRP-2121: COR-1203-Pre-Task-Alignment

**Applies to:** FXA project
**Last updated:** 2026-05-03
**Last reviewed:** 2026-05-03
**Status:** Approved
**Related:** COR-1103 (routing — companion CHG FXA-2122), COR-1402 (declaration), COR-1403 (Interactive Question Principle), COR-1201/1202 (session-family siblings), COR-1204-REF (CTX format — companion REF in same merge window)
**Reviewed by:** Codex 8.3 FIX / Gemini 8.2 FIX / DeepSeek 7.7 FIX (Risk sub-floor 5.0) — round 1 (2026-05-03); revising for round 2
**Inspired by:** mattpocock/skills `productivity/grill-me` + `engineering/grill-with-docs` (Round 2 of skills-absorption initiative; Round 0 shipped COR-1613, Round 1 shipped COR-1503)

---

## What Is It?

Two products in a single proposal: (1) a new PKG-layer SOP **COR-1203-SOP-Pre-Task-Alignment** that defines a structured Socratic interview loop conducted before task execution begins; and (2) a companion PKG REF **COR-1204-REF-CTX-Format** defining the project glossary (CTX) document template, with a pilot glossary for the Alfred project itself.

The SOP is intentionally framework-agnostic per the universality contract established in COR-1613 and carried forward in COR-1503. It is invoked by declaration per COR-1402. The CTX REF provides the glossary template; the pilot instance is the first concrete glossary, placed in `fx_alfred/rules/`.

The SOP covers the Socratic interview discipline only — one question at a time, challenge against glossary, sharpen fuzzy language, scenario-stress-test, cross-reference with code. Glossary maintenance (create/update CTX documents) is a natural byproduct of a resolved interview but lives in a separate REF — the SOP references it but does not mandate it. ADR creation is an optional outcome gated by explicit criteria.

---

## Problem

Alfred today routes from COR-1103 intent detection straight into task execution with no structured step that asks "do we actually agree on what we are building?". Concrete pains:

1. **Misalignment discovered mid-implementation.** The operator and the user agree on a surface-level description but disagree on scope, boundaries, or expected output. The disagreement surfaces only when the deliverable is presented, requiring rework. (Example from Round 0: the PRP's initial scope bundled Council Review with bugfixer-agent wiring — the user rejected the agent wiring only after the PRP was drafted.)

2. **No project glossary.** Agents explain terms on every invocation because there is no shared lexicon. "Review Unit", "mechanism", "gate", "artefact" have no canonical definition. This inflates every prompt by 10-30 words of re-explanation per ambiguous term.

3. **Domain terms drift session-to-session.** "Fix" means different things in COR-1503 (smallest change eliminating the symptom) vs COR-1613 (response to a reviewer deduction). Without a shared glossary, operators must re-calibrate each time.

4. **Misalignment wastes more effort than the interview costs.** A misdirected PRP consumes two Council review rounds before the scope error is caught (~4 human review cycles). A 7-question pre-alignment interview is ~3 minutes. The cost asymmetry is large.

5. **Existing alignment tools are partial.** COR-1402 (Declare Active Process) flags current SOP but does not check agreement. COR-1403 (Interactive Question Principle) defines the one-question-at-a-time pattern but is a *principle*, not a session-level procedure with glossary cross-reference or stop conditions. COR-1202 (Compose Session Plan) assumes terms are already sharp — it composes based on what the operator *thinks* the task is. No existing SOP closes the "do we agree?" loop before execution begins.

**Steelman of "do not ship".** There are two strong versions. *Strong version 1:* COR-1402 + COR-1403 + COR-1202 collectively cover pre-task alignment. COR-1402 forces an explicit SOP declaration, COR-1403 defines the one-question pattern, and COR-1202 composes the plan. Adding COR-1203 as a dedicated alignment SOP is renaming, not adding. *Strong version 2:* "if the cause is unknown" (COR-1503 line) is the right alignment trigger — alignment matters for diagnosis because the operator is investigating an unknown; for known-cause changes (PRPs, CHGs), the SOP already defines the output shape, so alignment is implicit in following the SOP. Rejected for three reasons: (a) COR-1403 is a principle, not a procedure — it tells you *how* to ask a question but not *when* to stop, *what* to challenge against, or *how* to record the outcome; (b) known-cause changes still suffer misalignment (the Round-0 ACID-range error happened on a PRP, not a diagnosis); (c) a named SOP creates a decision point in COR-1103's routing, which COR-1403 alone cannot do — the router needs a concrete SOP to reference. **The SOP is justified only if it adds procedure (stop conditions, glossary challenge, one-line record) that the existing principle does not.** Without those three, the steelman wins.

---

## Proposed Solution

### 1.0 ACID family-fit and routing

**Family-fit justification.** The 12xx family is the **session-management family**. Current allocations: COR-1200 (Session Retrospective), COR-1201 (Discussion Tracking), COR-1202 (Compose Session Plan). COR-1203 is the next free slot (1203 and 1204 unallocated; verified via `af list COR` and COR-0000 index). Pre-task alignment is a session-management activity — it happens at the start of a session, before task execution. It is the natural sibling of COR-1201 (which asks "what came up?") and COR-1202 (which asks "what is the plan?"): COR-1203 asks "do we agree on the plan's terms?".

Two alternatives were considered and rejected:
- **16xx (review family).** Rejected: alignment is pre-execution, not post-hoc evaluation.
- **New 11xx family.** Rejected: creating a one-member family violates COR-1400. Re-evaluate if a second alignment SOP appears.

**Routing.** This PRP commits to companion CHG `FXA-2122` that updates COR-1103. Insertion point: after COR-1201 (load tracker) and before task-specific routing. COR-1203 is mandatory for PRPs and non-trivial code changes (>3 files or >50 lines), optional (declarable) for CHGs and trivial changes. Mandatory also implies: the user may decline the interview by saying "skip alignment" — that is itself the alignment outcome, recorded as `user-declined` per Step 7.

### 1.1 New PKG SOP — COR-1203-SOP-Pre-Task-Alignment

**When to use.** Any task producing a PRP, CHG, code change, or non-trivial document, **before** execution begins. The operator declares COR-1203 active per COR-1402.

**When NOT to use.**
- Micro-changes (one-line typo, trivial version bump, rename a single variable)
- Already-aligned tasks (user explicitly says "no alignment needed")
- Emergency hotfixes harmed by delay
- Tasks where the user explicitly declines: "skip alignment" is a valid outcome, recorded as `user-declined`

**Interview loop (7 steps):**

1. **Declare active (COR-1402).** State a one-paragraph restatement of what the operator understands the task to be.

2. **One question at a time, with a recommended answer.** Walk down the design tree resolving dependencies. Wait for feedback after each question. Example: "I recommend ACID 1203 in the 12xx family. Do you agree?"

3. **Challenge against the project glossary.** For every term the user uses, check against existing CTX (glossary) documents per COR-1204-REF. If the user's term conflicts: "The glossary defines 'mechanism' as X. You seem to mean Y — which is it?"

4. **Sharpen fuzzy language.** Propose precise canonical terms for vague/overloaded words. "You said 'alignment step' — do you mean within the interview, or after it concludes?"

5. **Stress-test with concrete scenarios.** Invent edge cases that force precision about boundaries. "If the user says 'grill me' but no CTX exists, should the interview proceed or abort?"

6. **Cross-reference with code.** When the user states how something works, check the code/current documents agree. Surface contradictions.

7. **Stop when crisp or user-declined.** Two stop conditions: (a) both parties agree the plan is crisp (scope, output, terms, OQs stated unambiguously), or (b) the user explicitly declines further questions. Record: `alignment: <crisp | user-declined> | questions_asked: N | terms_resolved: N | offered_adr: N`.

**Relationship to COR-1403.** COR-1403 (Interactive Question Principle) defines *how* to ask a question — present a recommended answer, wait for feedback, do not ask "is this okay?"-style open-ended questions. COR-1203 is the session-level procedure that applies that pattern: it adds *when* (before task execution), *against what* (project glossary), and *when to stop* (crisp or user-declined). COR-1203 references COR-1403's question format; COR-1403 remains the principle SOP.

**Relationship to CTX (COR-1204-REF).** Steps 3 and 4 reference the project glossary. When no glossary exists (a new project), these steps are no-ops — the operator notes "no CTX found" and continues. The interview still has value from Steps 1-2, 5-7. Glossary creation is the natural next step after the first successful alignment interview, but is a separate operation (write a markdown file following COR-1204-REF format).

### 1.2 Companion PKG REF — COR-1204-REF-CTX-Format

Defines the project glossary (CTX) document template. A CTX document is a simple term/definition table:

```
| Term | Definition | Source | Updated |
|------|------------|--------|----------|
| SOP  | ...        | COR-0002 | YYYY-MM-DD |
```

- **Term:** the canonical name (capitalised if domain-specific, lowercase if generic)
- **Definition:** one or two sentences; precise but concise
- **Source:** the SOP/REF/PRP ACID that first defined the term, or "session" if resolved in-conversation
- **Updated:** ISO date of last change

A CTX document may live in any layer — `rules/` for PRJ-layer glossaries, or the project root as `CONTEXT.md` for single-context projects. COR-1204-REF is the format specification; individual CTX instances are project-maintained documents.

**Pilot instance.** The first CTX instance is the Alfred project glossary at `fx_alfred/rules/FXA-2123-CTX-Alfred-Glossary.md` (companion document, same merge window). It covers ~15 core Alfred terms (SOP, PRP, CHG, ADR, REF, ACID, PKG/USR/PRJ, Review Unit, mechanism, gate, operator, dispatcher, universality contract, phase, evidence artefact).

**Constraints (from user).** This is a PRJ-layer pilot + PKG format REF. No changes to `src/fx_alfred/core/schema.py`. No `af create ctx` command. No `DocType.CTX` enum value. After 90 days and at least 3 CTX instances in real use, a future PRP may propose PKG promotion. Filename convention for PRJ-layer CTX documents: `FXA-XXXX-CTX-<topic>.md`. Within existing `FILENAME_PATTERN`, the 3-letter code CTX parses correctly — no tooling changes needed.

### 1.3 ADR gating (optional interview outcome)

When the interview resolves a design decision, the operator offers an ADR only when **at least 2 of 3** conditions are met, with a one-sentence justification per condition:

1. **Irreversible.** The cost of reversing the decision later is meaningful (not just "revert the commit").
2. **Would surprise.** A future reader would not infer this decision from the code without context.
3. **Real trade-off.** The decision was the result of a genuine, non-obvious trade-off between alternatives.

"0 of 3" or "1 of 3" → skip ADR. ADRs are created via `af create adr` (existing COR-1100 flow) or as free-form narrative in `docs/adr/`. The interview record in Step 7 logs `offered_adr: N` — 0 is a valid outcome.

### 1.4 Universality contract

(Same blocklist as COR-1503 §1.4 and COR-1613 §Universality Contract — exempting the blocklist definition and Change History from the grep.)

### 2. Relationship to existing SOPs

- **COR-1403 (Interactive Question Principle)** — COR-1203 references COR-1403's question format (recommended answer, wait for feedback) and is the session-level procedure applying that principle. COR-1403 defines *how*; COR-1203 defines *when* and *against what* and *when to stop*.
- **COR-1103 (Workflow Routing)** — updated in companion CHG FXA-2122.
- **COR-1402 (Declare Active Process)** — COR-1203 is declared via COR-1402 when in use.
- **COR-1201 (Discussion Tracking)** — no D items created during interview. Unresolvable points deferred to COR-1201.
- **COR-1202 (Compose Session Plan)** — COR-1203 is a prelude that sharpens terms before COR-1202 composes.
- **COR-1613 (Council Review)** — alignment is upstream of review: align on what to build, build it, review the result.
- **COR-1503 (Diagnose Feedback Loop)** — COR-1203 applies before diagnosis: align on the symptom, diagnostic depth, and expected output before entering Phase 1.
- **COR-0002 (Document Format Contract)** — no changes proposed. CTX documents use base REF metadata format.

---

## Scope

**In scope:**
- Drafting `COR-1203-SOP-Pre-Task-Alignment.md` at `src/fx_alfred/rules/`
- Drafting `COR-1204-REF-CTX-Format.md` at `src/fx_alfred/rules/`
- Drafting pilot CTX instance `FXA-2123-CTX-Alfred-Glossary.md` at `fx_alfred/rules/`
- Updating COR-0000 PKG index with COR-1203 and COR-1204; updating FXA-0000 PRJ index with FXA-2123
- Companion CHG `FXA-2122` — adds COR-1203 to COR-1103 routing

**Out of scope:**
- `src/fx_alfred/core/schema.py` changes (DocType.CTX, new enums — deferred, minimum 90 days)
- `af create ctx` or `af read --type ctx` tooling
- Agent modifications
- Creating `docs/adr/` directory
- Modifying existing SOPs beyond the companion CHG

---

## Open Questions

All resolved by user confirmation on 2026-05-03 prior to round-2 dispatch. Round-1 reviewer findings incorporated.

1. **Should the interview be mandatory or opt-in?** RESOLVED: mandatory for PRPs and non-trivial code changes (>3 files / >50 lines); optional for CHGs and trivial changes. The user may also say "skip alignment" — that is itself the alignment, recorded as `user-declined` in the Step 7 log line. Mandatory means the SOP is offered, not enforced — the offer itself is the alignment check.

2. **Should the interview be time-boxed?** RESOLVED: no hard time limit. After N questions (default 7), the operator proposes summarising; the user may accept or continue. The stop condition is crispness or user decline, not a timer.

3. **Should CTX be PRJ-layer pilot or immediately promoted to PKG?** RESOLVED: PRJ-layer pilot for 90 days per user constraint. After ≥3 CTX instances in real use + a retrospective, a future PRP evaluates promotion. The companion COR-1204-REF defines the format at PKG layer so the template is discoverable; individual CTX instances are PRJ-layer documents.

4. **Where do ADRs live?** RESOLVED: `af create adr` (COR-1100 flow) for structured, reviewable ADRs in `rules/`; `docs/adr/` for free-form narrative. Both coexist; the operator chooses based on significance. The 2-of-3 gate in §1.3 determines *whether* to create one, not *where*.

5. **Should the interview produce a written artefact beyond the one-line record?** RESOLVED: the one-line `alignment:` record in the session log is sufficient. No separate document. The record is machine-readable: `alignment: <crisp | user-declined> | questions_asked: N | terms_resolved: N | offered_adr: N`.

---

## Change History

| Date       | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | By           |
|------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|
| 2026-05-03 | Initial version | — |
| 2026-05-03 | Drafted PRP body as Round 2 of mattpocock/skills absorption initiative; GLM as worker per user constraint (no agent modification); two-product proposal (COR-1203 SOP + CTX pilot); 10-step interview loop; CTX constrained to PRJ-layer pilot with 90-day promotion horizon; universality contract mirrors COR-1613/COR-1503 blocklist; companion CHG FXA-2122 for COR-1103 routing. | GLM (worker) |
| 2026-05-03 | Round-1 review: Codex 8.3 FIX / Gemini 8.2 FIX / DeepSeek 7.7 FIX (Risk 5.0 sub-floor). Mean 8.07. Revised: OQs resolved per user confirmation; 10-step loop compressed to 7 (glossary-maintenance and ADR-creation steps extracted to COR-1204-REF / §1.3 as optional outcomes, not SOP steps); COR-1403 relationship explicitly added (§1.1); CTX promoted from "pilot doc only" to companion PKG REF COR-1204 + PRJ-layer pilot instance FXA-2123; strongest steelman (COR-1402+1403+1202 collectively cover alignment) engaged in §Problem; grill fatigue addressed via mandatory/optional distinction + user-decline-as-alignment; ADR gate hardened to "at least 2 of 3 conditions with one-sentence justification per condition"; `## Scope` promoted to H2; COR-0000 index update added to in-scope. | Frank Xu |
| 2026-05-03 | Round 2 panel review: Gemini 9.0 PASS / Codex 9.2 PASS / DeepSeek 9.1 PASS — unanimous 3-of-3 PASS (first PRP to pass in round 2 without round 3). Mean 9.1. DeepSeek Risk Awareness improved from 5.0 to 8.0. All R1 blockers resolved. Proceeding to implementation. | Frank Xu |
