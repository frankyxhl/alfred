# SOP-1625: Loop — L2 Assisted + Gated

**Applies to:** All projects using the COR document system
**Last updated:** 2026-06-19
**Last reviewed:** 2026-06-19
**Status:** Active
**Related:** COR-1624 (Loop — L1 Report-Only, the rung below), COR-1626 (Loop — L3 Unattended, the rung above), COR-1617 (Multi-Agent Workflow Loop — the loop mechanism), COR-1620 (Self-Pacing Loop Primitives — pacing), COR-1600 / COR-1602 (review-loop / multi-model panel — the human-approval gate this level uses), COR-1608 / COR-1609 / COR-1610 (scoring rubrics when the gate is a review)
**Disposition:** inherit-only

---

## What Is It?

The middle rung of the **Loop autonomy ladder** (see COR-1624 for the full ladder):

- **L1 — Report-Only** (COR-1624): the loop observes and reports; no side effects.
- **L2 — Assisted + Gated** (this SOP): the loop drafts actions; a human approves each before it executes.
- **L3 — Unattended** (COR-1626): the loop executes autonomously inside a verified envelope.

An **L2 loop** does the gathering, judgment, drafting, and — *after approval* — the
execution. What it does **not** own is the *decision to act*: every authority-bearing
action is staged as a concrete draft and held at a **per-action human gate**.

**The L2 invariant — no authority-bearing action without a prior, informed,
per-action human approval.** The loop may read, classify, draft, and stage freely.
It may execute **only** the specific action a human has approved, **exactly as
approved** — it must never execute an unapproved action, a modified one, or a
batch the human did not see. The decision to mutate a system of record belongs to
the human at the gate; the loop does everything up to and after that decision.

This SOP governs only **what an L2 loop may and may not do**. The loop *mechanism*
— scheduling, pacing, multi-agent wiring — is COR-1617 and COR-1620. The *gate
itself* — how a human reviews and approves — reuses the existing review machinery
(COR-1600 / COR-1602, scored per COR-1608/1609/1610); L2 does not reinvent it.

## Why

L2 is where a loop earns leverage without surrendering control. L1 only reports —
a human still does all the work. L2 lets the loop do the work *right up to the
decision point*, collapsing the human's job to "review a concrete change and
approve or reject." It captures most of the automation value while keeping a human
accountable for every state change.

It is the right default for any loop whose actions are consequential but whose
judgment is good enough to produce a reviewable draft. Automation amplifies
judgment — at L2 the human gate is the amplifier's safety catch: a wrong draft is
caught at review and costs nothing, because nothing executed.

---

## When to Use

- A loop promoted from L1 (COR-1624) whose observations have proven correct and
  which now needs to *act* on them.
- Any loop whose actions are consequential or hard to reverse, but which can
  produce a **concrete, reviewable draft** (a diff, a payload, a PR, a command).
- Any setting where a human can give an **informed** approval — they see exactly
  what will happen — without the gate becoming an impractical bottleneck.

## When NOT to Use

- The action is pure observation/reporting — that is L1 (COR-1624); a gate only
  adds latency.
- The action class is reversible, bounded, audited, kill-switched, and verifiable
  automatically, and a per-action human gate is now pure latency (the human has
  become a rubber stamp) — that is L3 (COR-1626).
- The "approver" would be **another bot**, not a human — that is not L2. Autonomous
  machine execution belongs at L3 (COR-1626) **only inside its six-precondition
  envelope**; a bot rubber-stamping another bot's draft is neither an L2 gate nor a
  valid L3 envelope — put a human at the gate or stop the loop.

## Steps

1. **Declare the level.** Record `Autonomy: L2` and reference this SOP (COR-1625)
   on the owning automation's SOP/registry doc (or its config entry, per COR-1624
   Step 1). The tag is the contract a reviewer holds it to.
2. **Trigger.** The loop wakes on its schedule/event (pacing per COR-1620).
3. **Gather + classify (read-scoped).** Collect inputs with read-scoped
   capabilities and turn them into a verdict, exactly as at L1 (COR-1624 Steps 3–4).
4. **Draft the action — do not execute.** Produce a **concrete, reviewable
   artifact**: the exact diff, payload, command, or PR body that *would* run. The
   draft is the unit of approval; a vague intent ("fix the lint errors") is not a
   draftable action — the specific change is.
5. **Stage and present to the human gate.** Route the draft to a human for an
   **informed** decision — they see the concrete change itself, not a summary of
   it. Use COR-1600 / COR-1602 (scored per COR-1608/1609/1610) when the gate is a
   review. The gate is **fail-closed**: no response, timeout, or ambiguity = no action.
6. **On approval, execute exactly the approved action.** Same payload, same scope.
   First re-confirm the draft still applies — the world may have changed since
   approval; if it no longer applies cleanly, **re-draft and re-gate** (Step 4), do
   not force it. Never widen, batch, or "improve" the approved action.
7. **Record to the audit trail.** Log the executed action, the approver, the
   approved payload, and the result. One approval, one execution — recorded.
8. **Stop / loop.** One approval authorizes one action, never a standing license to
   keep acting.
9. **(Promotion check.)** Propose promotion to **L3 (COR-1626)** only when: the
   action class is reversible/bounded, automated verification can catch its failure
   modes, an audit log + kill-switch exist, and the human gate has been approving
   essentially-unmodified drafts long enough that the gate is now a rubber stamp —
   which is precisely the signal it is safe to replace with the L3 envelope.

### Gate semantics

- **Per-action, not per-batch.** One approval covers one staged action. Approving a
  batch requires the human to have seen every item in it.
- **Informed gate.** The approval surface must show the concrete change (the diff /
  payload), not a paraphrase. An uninformed click is not an L2 approval.
- **Human, not machine.** The approver is a person. A bot that "approves" another
  bot's draft is not an L2 gate (see [When NOT to Use](#when-not-to-use)).
- **Single-use + fresh.** An approval is consumed by one execution and expires if
  the underlying state drifts **or after a bounded freshness window**; stale or
  aged approvals are re-gated, not reused.

---

## Guard Rails

- **Never execute an unapproved action.** No action is "obvious enough" to skip the
  gate. If it executed without a recorded human approval, the loop is acting as L3 —
  reclassify or stop it.
- **Never widen, modify, or batch an approved action.** Approval is for the exact
  staged payload. A bigger/cleverer action than the one approved is unapproved.
- **The gate is a human.** Machine self-approval is L3 (COR-1626), not L2.
- **Approval is single-use.** N approvals authorize at most N executions — never a
  standing license.
- **Stale approval ⇒ re-gate.** If the world changed and the approved change no
  longer applies cleanly, re-draft and re-approve.
- **Fail-closed.** Timeout, ambiguity, or error at the gate means **do not act**.
- **The draft must not act.** Staging the draft (a PR, a branch, a queued payload)
  must not itself fire execution or downstream automation before approval. If
  creating the draft trips hooks that act, the draft is an active trigger and you
  are already past the gate — that is the L1 passive-sink vs active-trigger failure
  (COR-1624), now at L2.

### Conformance — how to verify a loop really is L2

- **Gate-before-mutation trace.** Every authority-bearing call is immediately
  preceded by a recorded human approval that references the exact payload executed.
  A mutation with no matching prior approval fails L2.
- **Payload equivalence.** Diff the executed payload against the approved one; they
  must match. Any widening/modification fails L2.
- **No standing license.** Over any window, executions ≤ approvals, one-to-one. A
  single approval driving repeated actions fails L2 (that is L3).
- **Informed-gate check.** Confirm the approval surface presented the concrete
  change, not a summary — an uninformed gate is not an L2 gate.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-06-19 | Initial version — L2 rung of the Loop autonomy ladder (drafts actions; per-action informed human gate before execution; reuses COR-1600/1602 as the gate) | — |
| 2026-06-19 | COR-1602 review polish (Codex 9.3 + DeepSeek 9.4, both PASS): add "the draft must not act" guard rail (a PR/branch that trips automation hooks pre-approval is an active trigger past the gate); approval expiry keys on a freshness window as well as state drift; tighten the machine-self-approval wording to point at the L3 envelope | — |
