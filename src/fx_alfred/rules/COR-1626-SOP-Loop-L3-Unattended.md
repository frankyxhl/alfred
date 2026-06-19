# SOP-1626: Loop — L3 Unattended

**Applies to:** All projects using the COR document system
**Last updated:** 2026-06-19
**Last reviewed:** 2026-06-19
**Status:** Draft
**Related:** COR-1624 (Loop — L1 Report-Only), COR-1625 (Loop — L2 Assisted + Gated, the rung below), COR-1617 (Multi-Agent Workflow Loop — the loop mechanism), COR-1620 (Self-Pacing Loop Primitives — pacing), COR-1622 (Multi-Agent Loop Project Configuration — general loop config; the L3 safety envelope is declared in the loop's own config/registry, not in COR-1622's schema), COR-1600 / COR-1602 (review-loop / multi-model panel — the L2 human gate; *not used per-action at L3*, retained for ladder symmetry and for the scheduled audit review)
**Disposition:** inherit-only

---

## What Is It?

The top rung of the **Loop autonomy ladder** (see COR-1624 for the full ladder):

- **L1 — Report-Only** (COR-1624): observe and report; no side effects.
- **L2 — Assisted + Gated** (COR-1625): draft actions; a human approves each.
- **L3 — Unattended** (this SOP): the loop executes authority-bearing actions
  **autonomously** — no per-action human approval.

At L3 a human is on the loop only through **escalation** (woken on anomaly) and
**periodic audit review** (scheduled, not per-action). These two are the *only*
human roles at L3 — remove them and the loop is ungoverned automation, not L3. The
safety does not come from a human watching each action; it comes from the
**envelope** the loop runs inside.

> **This SOP ships as `Status: Draft` deliberately.** L3 is the dangerous rung.
> Treat every L3 deployment as exceptional and explicitly opt-in. New loops default
> to L1 (COR-1624) or L2 (COR-1625); a loop reaches L3 only by deliberate promotion
> against the preconditions below — never by default and never by drift.

**The L3 invariant — autonomous execution is permitted only inside a verified,
bounded, reversible, killable envelope.** A loop may act without a human gate **iff
all six** of these hold; missing any one means the loop is **not** L3 and must be
held at L2 (COR-1625):

1. **Automated verification** can catch the action's failure modes (pre- and post-checks).
2. **A full audit log** durably records every action, decision, and outcome.
3. **A kill-switch** can halt the loop immediately, mid-flight.
4. **Bounded blast radius** — rate limits and scope caps cap the damage a runaway
   loop can do before the kill-switch or escalation fires.
5. **Automated rollback** — every action class has **automated** rollback (Step 7
   rolls back on post-verify failure). Manual-only reversibility is not enough — an
   action class without automated rollback stays L2.
6. **An escalation path** wakes a human on any anomaly.

This SOP governs only **what an L3 loop may and may not do**. The loop *mechanism*
is COR-1617 / COR-1620; the envelope *parameters* (rate caps, kill-switch wiring,
rollback, escalation) are declared in the loop's own config/registry entry — the
same place `Autonomy: L3` is recorded (per COR-1624 Step 1). COR-1622 covers
general multi-agent loop configuration and does **not** define L3 envelope keys.

## Why

Some loops are high-volume and low-ambiguity enough that a per-action human gate
(L2) is pure latency — and an over-frequent gate makes the human an inattentive
rubber stamp, which is its own failure mode. L3 removes the gate, but **replaces
it with machine verification + bounded blast radius + automated rollback**, so the
safety comes from the envelope rather than from a person watching.

Automation amplifies judgment, including bad judgment, at machine speed. L3 is
therefore only safe where the envelope can **catch and undo** a bad action
automatically and a human can **stop and inspect** the whole loop at will. Where
that envelope cannot be built, the correct level is L2, not L3.

---

## When to Use

- A loop promoted from L2 (COR-1625) whose gate has been approving
  essentially-unmodified drafts long enough to be a rubber stamp.
- An action class with **automated rollback**, bounded and automatically verifiable, at a
  volume where a human gate is impractical.
- A deployment where **all six envelope preconditions** demonstrably hold.

## When NOT to Use

- **Any** envelope precondition is missing — no kill-switch, no rollback, unbounded
  blast radius, or no automated verification. Hold at L2 (COR-1625).
- The action is irreversible **or** lacks automated rollback — keep a human in the
  loop (L2), regardless of volume (this is envelope precondition #5 failing).
- The loop's judgment is still unproven — stay at L1/L2 until it is.

## Steps

1. **Declare the level + the envelope.** Record `Autonomy: L3`, reference this SOP
   (COR-1626), and declare the concrete envelope (which kill-switch, what
   rate/scope caps, what rollback, what escalation path) in the loop's own
   config/registry entry, the same place `Autonomy: L3` is recorded (per COR-1624
   Step 1) — this declaration is the auditable envelope record the conformance
   drills check against. (COR-1622 is general loop config; it has no L3 envelope keys.)
2. **Enablement gate (once, human-approved).** A human owner runs the envelope
   audit (below), confirms **all six** invariant conditions exist and are wired,
   then **records an explicit approval** promoting the loop to L3. A loop never
   self-declares L3 — enablement is a human decision, exactly as L1→L2 promotion is
   (COR-1624: "Never auto-promote"). If any precondition fails, the loop cannot be
   enabled — it stays L2 (COR-1625).
3. **Trigger.** The loop wakes on its schedule/event (pacing per COR-1620).
4. **Gather + classify (read-scoped).** As at L1/L2.
5. **Pre-verify.** Check the action's preconditions automatically. If they do not
   hold, **abort and escalate** — do not act on a stale or unexpected world.
6. **Execute inside the bounded envelope.** Perform the action under the declared
   rate limits and scope caps. Never exceed them, even to "catch up."
7. **Post-verify.** Confirm the action had the intended effect. **On failure,
   auto-rollback and escalate** — never leave a half-applied change in place.
8. **Audit.** Record the action, its verification results, and any rollback to a
   durable, human-reviewable log (an L1-style passive sink, per COR-1624).
9. **Continuous safety.** Honor the kill-switch immediately. On anomaly — a rising
   verification-failure rate, drift, or a tripped cap — **auto-demote**: the loop
   **stops executing autonomously and parks fail-closed, taking no further action
   until a human gates it.** "Demote to L2/L1" means *wait for a human*; it never
   means keep acting on its own under a lower label.
10. **Periodic human review.** A human reviews the audit log on a **schedule**.
    L3 is unattended *per action*, never *unaudited*.

### The envelope — six hard requirements

| # | Requirement | Verified by |
|---|---|---|
| 1 | Automated pre/post **verification** of each action | the post-verify drill (Step 7) |
| 2 | Durable, complete **audit log** | audit-completeness check |
| 3 | Immediate **kill-switch** | the kill-switch drill |
| 4 | **Bounded blast radius** (rate + scope caps) | caps present and enforced |
| 5 | **Reversibility / auto-rollback** | the rollback drill |
| 6 | **Escalation** path that wakes a human | the demotion/escalation test |

All six are required. An L3 loop missing any one is misclassified — hold it at L2.

---

## Guard Rails

- **No L3 without the full envelope.** All six preconditions, no exceptions. A loop
  missing any one is not L3 — **halt it, or retrofit the missing envelope piece plus
  a human gate and run it as L2 (COR-1625).** A bot found executing autonomously
  outside its envelope must be stopped, not left running at a "ceiling" no one enforces.
- **Never self-promote to L3.** Enablement is a recorded human-owner decision (Step
  2). A loop that flips itself to `Autonomy: L3` by passing its own checks violates
  the ladder's inherited "Never auto-promote" rule (COR-1624).
- **The kill-switch is non-negotiable** and must halt the loop mid-flight, not just
  prevent the next iteration.
- **Bounded blast radius always.** Rate limits and scope caps must cap total damage
  before the kill-switch or escalation can fire — an L3 loop is never unbounded.
- **Fail-closed.** A verification failure or anomaly means **stop and escalate**,
  never "proceed anyway."
- **Auto-demote on anomaly = stop and park.** When verification degrades or a cap
  trips, the loop stops acting autonomously and waits fail-closed for a human at the
  gate — it must never keep executing under a lower label without a human present.
- **Unattended is not unaudited.** The scheduled human audit-log review is part of
  the contract, not optional.
- **Draft status is a gate, not a formality.** While this SOP is `Draft`, an L3
  promotion is an exceptional, deliberate decision; default loops to L1/L2.

### Conformance — how to verify a loop really is L3 (and safe)

- **Envelope audit.** Prove all six preconditions exist and are wired — not just
  documented. Each row of the envelope table has a passing drill.
- **Kill-switch drill.** Trigger it; confirm the loop halts immediately, mid-action.
- **Rollback drill.** Force a post-verify failure; confirm automated rollback leaves
  no half-applied change.
- **Blast-radius check.** Confirm rate/scope caps are enforced (the loop cannot
  exceed them under load), not merely configured.
- **Audit completeness.** Every action in a sampled window appears in the log with
  its verification result.
- **Demotion test.** Inject an anomaly; confirm the loop auto-demotes/escalates
  rather than continuing.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-06-19 | Initial version (Status: Draft) — L3 rung of the Loop autonomy ladder; autonomous execution permitted only inside a six-precondition verified/bounded/reversible/killable envelope; ships Draft so L3 stays exceptional and opt-in | — |
| 2026-06-19 | COR-1602 review fixes (Codex 8.7 + DeepSeek 8.8, convergent): add a recorded human-owner enablement gate (no self-promotion to L3); "demote to L2/L1" = stop-and-park-fail-closed-until-a-human-gates, never keep acting; add the non-conformance remediation verb (halt or retrofit-gate-and-run-as-L2); "irreversible AND" → "irreversible OR lacks rollback"; note escalation + scheduled review are the sole human roles; add COR-1600/1602 to Related: for ladder symmetry | — |
| 2026-06-19 | PR-bot (chatgpt-codex) review fix: stop claiming the L3 envelope is declared "per COR-1622" — COR-1622's schema has no envelope keys, making the enablement record non-auditable. The envelope is now declared in the loop's own config/registry (same place `Autonomy: L3` lives, per COR-1624 Step 1); COR-1622 clarified as general loop config only (3 spots: invariant, Step 1, Related:) | — |
| 2026-06-19 | PR-bot (chatgpt-codex) review fix (follow-on): tighten envelope precondition #5 from "reversible OR automated rollback" to "automated rollback required" — manual-only reversibility now stays L2, matching Step 7, the rollback drill, and the When-NOT clause (closes the weak-checklist gap) | — |
| 2026-06-19 | Proactive consistency sweep: When-to-Use entry criterion "reversible/bounded" → "automated rollback, bounded" to match the tightened precondition #5 | — |
