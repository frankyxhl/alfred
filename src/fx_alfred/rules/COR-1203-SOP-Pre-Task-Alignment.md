# SOP-1203: Pre-Task Alignment

**Applies to:** All projects using the COR document system
**Last updated:** 2026-05-03
**Last reviewed:** 2026-05-03
**Status:** Active
**Depends on:** COR-1402 (Declare Active Process), COR-1403 (Interactive Question Principle)
**Related:** COR-1201 (Discussion Tracking), COR-1202 (Compose Session Plan), COR-1204 (CTX Format REF), COR-1613 (Council Review), COR-1503 (Diagnose Feedback Loop)
**Authored from:** FXA-2121 PRP (unanimous 3-of-3 PASS, R2)

---

## What Is It?

A structured Socratic interview conducted before task execution begins. The operator asks one question at a time, each with a recommended answer, challenging against the project glossary per COR-1204-REF, sharpening fuzzy terminology, stress-testing with concrete scenarios, and cross-referencing against existing code and documents. The interview stops when the plan is crisp or the user declines further questions.

This SOP covers the interview discipline only. Glossary maintenance lives in COR-1204-REF. ADR creation is an optional outcome gated by explicit criteria.

---

## Why

Without a pre-task alignment check, misalignment between what the user wants and what the operator builds surfaces mid-implementation — requiring rework that costs more than the interview. A misdirected PRP can consume two Council review rounds before the scope error is caught. A 7-question alignment interview is ~3 minutes. The cost asymmetry justifies the process.

---

## When to Use

- Any task producing a PRP, CHG, code change, or non-trivial document, **before** execution begins
- The operator declares COR-1203 active per COR-1402

## When NOT to Use

- Micro-changes (one-line typo, trivial version bump, rename a single variable)
- Already-aligned tasks (the user explicitly says "no alignment needed" or "we already agreed on this")
- Emergency hotfixes that would be harmed by delay
- Tasks where the user explicitly declines: "skip alignment" is a valid alignment outcome, recorded per Step 7

**Mandatory threshold.** COR-1203 is offered for PRPs and non-trivial code changes (>3 files or >50 lines), optional (declarable) for CHGs and trivial changes. Mandatory means the SOP is offered, not enforced — the user may always decline.

---

## Steps

### Step 1 — Declare active (COR-1402)

State a one-paragraph restatement of what the operator understands the task to be. This is the opening bid; the interview sharpens it.

### Step 2 — One question at a time, with a recommended answer

Walk down the design tree resolving dependencies between decisions one-by-one. Each question includes a recommended answer. Wait for user feedback before continuing.

Example: "I recommend ACID 1203 in the 12xx family, next to COR-1201 and COR-1202. Do you agree?"

### Step 3 — Challenge against the project glossary

For every term the user uses, check against existing CTX (glossary) documents per COR-1204-REF. If a term conflicts: "The glossary defines 'mechanism' as a voting rule applied to a Review Unit (per COR-1613). You seem to mean something broader — which is it?"

If no glossary exists, note it and continue. The interview still has value from Steps 1-2, 4-7.

### Step 4 — Sharpen fuzzy language

When the user uses vague or overloaded terms, propose a precise canonical term. "You said 'the alignment step' — do you mean during the interview, or after it concludes? I recommend we use 'in-interview' vs 'post-interview' as the distinction."

### Step 5 — Stress-test with concrete scenarios

Invent edge cases that force the user to be precise about boundaries. "If the user says 'grill me' but no CTX document exists — should I proceed with the interview, or abort?"

### Step 6 — Cross-reference with code (or current documents)

When the user states how something works, check whether the code or existing documents agree. For document-only tasks, cross-reference the current document state instead. Surface any contradiction.

### Step 7 — Stop when crisp or user-declined

Two stop conditions:
1. Both parties agree the plan is **crisp**: scope, output, terms, and open questions are all stated unambiguously.
2. The user explicitly **declines further questions** ("that's enough alignment, proceed").

Record the outcome immediately (append to the session discussion tracker per COR-1201, or inline in the task document):

```
alignment: <crisp | user-declined> | questions_asked: N | terms_resolved: N | offered_adr: N
```

---

## ADR Gating (optional interview outcome)

When the interview resolves a design decision, offer an ADR only when **at least 2 of 3** conditions are met, with a one-sentence justification per condition:

1. **Irreversible.** The cost of reversing this decision later is meaningful.
2. **Would surprise.** A future reader would not infer this decision from the code without context.
3. **Real trade-off.** The decision was the result of a genuine, non-obvious trade-off between alternatives.

Create ADRs via `af create adr` (COR-1100 flow) or as free-form narrative in `docs/adr/`.

---

## Relationship to COR-1403

COR-1403 defines the **how** of interactive questioning (present a recommended answer, wait for feedback, do not ask open-ended "is this okay?" questions). COR-1203 defines **when** (before task execution), **against what** (project glossary per COR-1204-REF), and **when to stop** (crisp or user-declined). COR-1403 is the principle; COR-1203 is the session-level procedure applying that principle.

---

## Universality Contract

This SOP must NOT contain any of the following tokens in its normative body text (the blocklist applies to everything between the `---` after frontmatter and `## Change History`; the blocklist definition itself and the Change History provenance rows are exempt):

```
Claude Code | trinity | Codex | Gemini | DeepSeek | GLM | Anthropic | OpenAI |
ChatGPT | Copilot | bugfixer | coder | refactorer | code-reviewer | translator
```

This SOP must NOT mention any specific harness, runtime, provider, model, panel composition, fixed reviewer count, agent name, or human role name beyond abstract roles (operator, user, dispatcher).

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-03 | Initial version per FXA-2121 PRP. Unanimous 3-of-3 PASS in round-2 panel review (Codex 9.2 / Gemini 9.0 / DeepSeek 9.1). | Frank Xu |
