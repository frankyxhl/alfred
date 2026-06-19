# SOP-1624: Loop — L1 Report-Only

**Applies to:** All projects using the COR document system
**Last updated:** 2026-06-19
**Last reviewed:** 2026-06-19
**Status:** Active
**Related:** COR-1617 (Multi-Agent Workflow Loop — the loop mechanism this level governs), COR-1620 (Self-Pacing Loop Primitives — how an L1 loop is paced), COR-1600 / COR-1602 (general review gates an L2 loop's human-approval step uses)
**Disposition:** inherit-only

---

## What Is It?

The lowest rung of the **Loop autonomy ladder** — the classification of how much
a running agent loop is allowed to do on its own:

- **L1 — Report-Only** (this SOP): the loop observes and reports; no authority-bearing side effects.
- **L2 — Assisted + Gated** (COR-1625): the loop drafts actions; a human approves each risky one.
- **L3 — Unattended** (COR-1626, *Draft*): the loop executes autonomously under strong verification.

> A loop only ever sits at one rung. Start at L1; a loop earns **L2** by a recorded
> promotion once its judgment is proven (COR-1625), and **L3** only by a recorded
> human-owner decision against COR-1626's envelope — which ships `Draft`, so treat
> L3 as exceptional and opt-in. A loop that needs to act is not "held at L1"; it is
> promoted to the rung whose gate it can satisfy.

**The L1 invariant — passive reporting only; no authority-bearing side effects.**
An L1 loop may read any source and write its findings to a **passive report sink**
(a log, a feed, a draft artifact a human reads) — writing to that sink is the one
mutation it is allowed. It must never perform an action that changes a system of
record or hands work to anything that will act on it — no writes to source state,
no send that hands work to a system or another agent, no deletes, no opening/merging
of PRs, no enqueuing of actions for pickup. (A *notification delivered to a human to
read* — a page, an alert, an email — is a passive report sink, not a forbidden send;
see [Notifying a human is L1](#passive-sink-vs-active-trigger). The forbidden "send"
is one that asks a *machine* to act or hands off work.) Recording an observation is
permitted; *acting on it* is not. The single test that separates the two is in
[Passive sink vs active trigger](#passive-sink-vs-active-trigger).

This SOP governs only **what an L1 loop may and may not do**. The loop *mechanism*
— scheduling, pacing, multi-agent wiring — is COR-1617 and COR-1620.

## Why

Most loops should start here. A loop's judgment is unproven on day one, and
automation amplifies judgment — a correct call and a wrong call are both executed
at machine speed. Report-Only is the safe way to let a loop *prove its
observations are right* before it is ever granted the power to act. An L1 loop
that has been correct long enough earns promotion to L2; one that is noisy or
wrong is cheap to ignore, because it changed nothing.

It also makes every automation's autonomy **legible**: instead of "is this bot
safe?", the question becomes "what level is it?" — and L1 is, by construction,
safe to run unattended.

---

## When to Use

- A new loop whose judgment has not yet been validated in production.
- Any monitor, watcher, scanner, or **draft-generator** whose job is to *surface*
  a signal (errors, drift, stale branches, a missing changelog entry) — not to apply it.
- A loop whose actions are not yet reversible, auditable, or cheap to undo — keep
  it L1 until those guarantees exist, then promote to L2 (COR-1625).
- Any loop, during its first runs, before a human has read its output enough to trust it.

## When NOT to Use

- The loop already needs to *change* a system of record (apply, fix, send, delete,
  merge) without a human in between — that is L2 (COR-1625) at minimum; do not
  smuggle the write into an L1 loop.
- A one-off manual analysis with no recurring trigger — that is not a loop; just
  run the analysis.
- The action is fully trusted, reversible, audited, and kill-switched — that may
  qualify for L3 (COR-1626); L1 would only add latency.

## Steps

1. **Declare the level.** Record `Autonomy: L1` as a metadata field on the owning
   automation's SOP/registry doc — the same place its trigger/schedule lives — and
   reference this SOP (COR-1624). A bot with no SOP doc records the level in its
   config/registry entry. The declared tag is the contract a reviewer holds it to.
2. **Trigger.** The loop wakes on its schedule/event (pacing per COR-1620). No
   human-in-the-loop is required to *start* an L1 loop — it is safe by construction.
3. **Gather (read-only by capability).** Collect inputs using **read-scoped
   capabilities only** — tokens/credentials that *cannot* mutate state. Judge by
   capability, not by HTTP verb: a `POST` search endpoint that only returns data
   is fine; any call that *can* change state is not — even if this run happens not
   to. If the loop holds a credential able to mutate **inputs or any system of
   record**, scope it down or it is not L1. (The one exception — a narrow
   append-only writer for the report sink — is introduced in Step 5.)
4. **Classify.** Turn raw inputs into a verdict/pattern/draft (on-track vs
   off-track, matched vs clear, drafted text). Analysis only — still side-effect-free.
5. **Emit to a passive report sink.** Write the result to a sink a human or higher
   loop *reads* — a log table, a Markdown verdict, a notification feed, a draft
   artifact. Confirm the sink is passive (see below); a sink that something drains
   and acts on is not L1. **Scope the sink-write capability narrowly too:** the
   credential that writes the sink must reach *only* that passive surface (append
   to a drafts/log/notification store), never a system of record — an L1 loop must
   not hold a token that can write production state even to "report" with it.
6. **Stop.** The loop ends. It does **not** queue an action, open a PR, send a
   message that asks a machine to act / hands off work, delete anything, or hand a
   payload to anything that will execute. (Paging or notifying a *human* to read is
   fine — that is the passive sink, not a hand-off.) Acting on the report is a
   separate, human-initiated step (or a promotion to L2).
7. **(Promotion check.)** Track the loop's hit rate. When its reports have been
   correct and acted-on by a human across enough runs to trust — set a concrete
   threshold per project (e.g. ≥ N consecutive runs at 100% human-accepted) —
   propose promotion to **L2 (COR-1625)**. Never skip straight to **L3 (COR-1626)** —
   promotion is one rung at a time. Set a minimum *total* run count too, so a 2-for-2
   loop is not promoted prematurely.

### Passive sink vs active trigger

The one line that decides L1 vs L2: **does the loop's output get *read by a human*,
or *consumed by a machine that then acts*?**

| The loop's output goes to… | Side effect? | Level |
|---|---|---|
| A log / feed / dashboard a human reads | No — passive recording | **L1** |
| A **draft artifact** (e.g. a drafted changelog entry) a human later reviews and publishes | No — the human is the one who acts | **L1** |
| A queue / branch / PR that another automation drains and executes | Yes — it triggers work | **L2+** |
| A system of record directly (deletes a branch, posts a comment, sends a message) | Yes — it acts | **L2+** |

So a bot that **auto-drafts** a changelog entry for a human to review is **L1**;
the moment it *commits or publishes* that entry itself, it is L2+.

Two clarifications this line implies:

- **Notifying a human is L1; triggering a machine is L2+.** A monitor that *pages
  or alerts a human* (Prometheus-style) is still passive reporting — the human
  decides. The same signal wired to fire an *auto-remediation machine action* is
  L2+. The receiver of the output (human vs. executing machine), not the urgency,
  sets the level.
- **L1 governs machine autonomy, not human discipline.** The invariant constrains
  what the *loop* may do. A human who rubber-stamps a draft without reading it is a
  human-process failure, not an L1 violation — the loop stayed within L1 by leaving
  the decision to a human at all.

---

## Guard Rails

- **No authority-bearing writes, ever.** An L1 loop that mutates a system of record
  — even "just" deleting a merged branch, even "just" enqueuing a suggestion for
  auto-pickup — is not L1. Reclassify it as L2 (COR-1625) and add the human gate.
- **A passive sink is not a side effect; a consumed sink is.** Logging or drafting
  for a human is L1. Writing to a queue/branch that something else acts on is L2.
- **Read-scoped credentials, plus at most one narrow sink-writer.** Every
  capability an L1 loop holds must be read-scoped, with a single exception: a
  narrowly-scoped writer for its passive report sink (append-only to a drafts / log
  / notification surface). Any write capability that reaches a system of record,
  execution queue, send/delete path, or auto-remediation trigger fails L1. Enforce
  by the environment (scoped tokens) where possible, not just by discipline.
- **Never auto-promote.** A loop does not move L1 → L2 on its own; promotion is a
  human decision backed by the loop's track record (Step 7).

### Conformance — how to verify a loop really is L1

The L1 invariant is checkable, not aspirational:

- **Capability audit.** Enumerate every capability the loop *can* exercise. All
  must be read-scoped, except **at most one** narrowly-scoped passive-sink writer (append to
  the drafts / log / notification surface). Any other write capability — to a
  system of record, execution queue, send/delete path, or auto-remediation trigger
  — fails L1, independent of whether this run used it.
- **No writes to systems of record.** A run must make **no change to any system of
  record or execution queue** — same branches, source files, PRs, and work queues
  before and after. Any mutation must be strictly isolated to the designated
  passive report sink. (Writing a draft to a drafts store or a row to a log table
  legitimately records the observation and is allowed; it is the *system of record*
  that must be byte-identical, not every external service.)
- **Sink-is-passive check.** Confirm nothing *consumes* the report sink as a work
  trigger. If writing the report causes downstream execution, the loop is acting —
  that is L2, not L1.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-06-19 | Initial version — L1 rung of the Loop autonomy ladder | — |
| 2026-06-19 | COR-1602 review fixes (round 1): restate invariant as "no authority-bearing side effects" (reconcile with passive sink); add `Related:` line + mark L2/L3 forthcoming; fold Conformance under Guard Rails; define where `Autonomy: L1` is declared; judge read-only by capability not HTTP verb; add passive-sink vs active-trigger table | — |
| 2026-06-19 | COR-1602 review fixes (round 2): name the passive-sink exception in the invariant headline; rewrite "byte-identical world" conformance as "no writes to systems of record" (passive external sinks like a drafts store / log table are allowed); scope the sink-write credential narrowly; add the notify-human (L1) vs trigger-machine (L2+) and "L1 governs machine autonomy, not human discipline" clarifications | — |
| 2026-06-19 | COR-1602 review fixes (round 3): reconcile credential language across Guard Rails + Capability audit with Step 5 — every capability read-scoped except one narrow append-only passive-sink writer; any write reaching a system of record / queue / send-delete / auto-remediation trigger fails L1 | — |
| 2026-06-19 | PR-bot (chatgpt-codex) review fixes: reconcile "no sends" with "paging a human is L1" — the forbidden send is one that hands work to a machine; a notification a human reads is the passive sink (invariant + Step 6); remove stale "L2/L3 forthcoming/reserved" language now that COR-1625 (Active) / COR-1626 (Draft) ship in the same change — in BOTH the "What Is It?" block and the Step 7 "(once COR-1626 is published)" conditional (second location caught by MiniMax re-review) | — |
| 2026-06-19 | COR-1602 panel PASS (Codex 9.4 / DeepSeek 9.4); final polish: Step 3 forward-references the Step 5 sink-writer exception; "at most one" sink-writer aligned across Guard Rails + audit (pure-observer loop with zero writers is valid); soften COR-1600/1602 `Related:` wording; Step 7 adds minimum-total-run-count + "(once COR-1626 is published)" | — |
