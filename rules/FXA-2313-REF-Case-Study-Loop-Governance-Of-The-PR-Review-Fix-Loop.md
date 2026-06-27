# REF-2313: Case Study Loop Governance Of The PR Review Fix Loop

**Applies to:** FXA project
**Last updated:** 2026-06-27
**Last reviewed:** 2026-06-20
**Status:** Active

---

## What Is It?

A worked, evidence-backed case study of a real autonomous loop: the PR-review-fix
loop run on alfred PR #227 (the PR that shipped the Loop autonomy ladder, COR-1624 /
COR-1625 / COR-1626). An AI agent polled the PR's review bot, fixed each finding,
pushed, replied, and repeated until the bot went quiet. That loop is itself a
loop-engineering loop — and when classified with the very ladder it was shipping, it
comes out **under-governed**. The framework catches the loop that built it. The
evidence source is PR #227 itself: GitHub's PR commit list preserves the branch
commits even though they are not reachable from `main` after the merge.

This document also serves as the **build spec** for a compliant implementation (§7):
the actual governed loop, if built, belongs in the Voyager automation factory, not in
this docs/SOP engine.

---

## The loop, as a loop

```
trigger (timer, ~4.5 min)
  → gather   : fetch new chatgpt-codex review comments on the PR head
  → classify : assess each finding, verify it against the live doc text
  → act      : edit the SOP + git commit + git push + reply to the thread
  → repeat   : until two consecutive checks find nothing new
```

The `act` step makes **authority-bearing writes** — it mutates a system of record
(the repo) and posts to GitHub. By COR-1624's passive-sink-vs-active-trigger line
that is **not L1**.


## Classifying it against the ladder

- **Not L1** — it writes to the repo and to GitHub.
- **Fails L2** — L2 requires *a prior, informed, per-action human approval*. This
  loop ran on a single **standing authorization** ("fix everything until thumbs-up").
  COR-1625's own conformance check fails exactly that: *"a single approval driving
  repeated actions is an L2 violation — stop or re-gate."*
- **Not a clean L3** — it executed autonomously, but without the full COR-1626
  envelope (see the audit below).

> **Verdict: under-governed.** Read one way it is an L2 loop running on a standing
> license (a COR-1625 violation); read the other way it is an L3 loop without a
> complete envelope. Same diagnosis from both directions.


## Envelope audit — the six L3 preconditions vs. what this loop had

| # | COR-1626 precondition | This loop | Evidence |
|---|---|---|---|
| 1 | Automated verification | ✅ strong | every fix ran `af validate` + parser/schema + `pytest` (20 passed); **the review bot itself was an independent external verifier** re-reviewing every push; plus a glm/minimax/deepseek panel on the larger changes |
| 2 | Durable audit log | ◐ partial | per-fix change-history rows + commit messages + thread replies — but no single machine-readable log; reconstructing the run needed git + the PR API |
| 3 | Kill-switch | ✅ | the human typing "stop" / "merge" halts it immediately |
| 4 | Bounded blast radius | ❌ | **no cap** — it ran 13 rounds and would have continued; each round force-pushed to a real branch |
| 5 | Automated rollback | ◐ partial | `git revert` was available and tests gated each push, but there was **no automated revert-on-failure** |
| 6 | Escalation path | ✅ | it reported to the human each round and proactively raised a convergence concern at round ~8 |
| — | Recorded enablement | ❌ | an informal standing nod, not a recorded, human-approved envelope (COR-1626 Step 2) |

**Score: 3 ✅, 2 ◐, 1 ❌, no recorded enablement.** Not a clean L3; no per-action
gate, so not a valid L2 either.

**The honest nuance:** in practice the run was *safer than its score* — because the
bot was an independent verifier and the blast radius was contained to one PR branch
(never `main`). But "safe because of the surrounding context" is precisely what the
ladder warns against: an L3 loop is supposed to be safe **by construction** (the
envelope), not by luck. Take away the external bot or point it at `main` and the
missing preconditions bite.


## The empirical run (real data)

13 PR-branch commits over **~2h18m** (10:02 → 12:20), then **3 clean checks** to
declare convergence. **13 distinct bot findings**, every one fixed and replied to.
The commit links below point at PR #227's archived commit list, not at `main`
history; this is intentional because #227 landed as a single-parent
squash/rebase-style commit, while these per-round branch commits are evidence for
the loop, not release-line milestones.

| # | Time | Commit | Finding fixed | Category |
|---|------|--------|---------------|----------|
| 1 | 10:02 | [`c6f7216326a84367ebc8e1100f4823cb68c9cfde`](https://github.com/frankyxhl/alfred/pull/227/commits/c6f7216326a84367ebc8e1100f4823cb68c9cfde) | (L1 shipped) | — |
| 2 | 10:35 | [`c965906394464ca33272f089d8a609e1739c3d97`](https://github.com/frankyxhl/alfred/pull/227/commits/c965906394464ca33272f089d8a609e1739c3d97) | (L2+L3 shipped) | — |
| 3 | 11:04 | [`9b1e54a6816a7756075f4569d205af7a5f35e451`](https://github.com/frankyxhl/alfred/pull/227/commits/9b1e54a6816a7756075f4569d205af7a5f35e451) | draft-must-not-act (field-test) | refinement |
| 4 | 11:24 | [`005cf66b123f843d07d170172f70bfe8a994c481`](https://github.com/frankyxhl/alfred/pull/227/commits/005cf66b123f843d07d170172f70bfe8a994c481) | no-sends vs page-a-human · stale rungs · L3-relabel | consistency · stale · loophole |
| 5 | 11:37 | [`f4c1b20b12de0d595c51d460d59881d3c116f611`](https://github.com/frankyxhl/alfred/pull/227/commits/f4c1b20b12de0d595c51d460d59881d3c116f611) | envelope "per COR-1622" overclaim | wrong reference |
| 6 | 11:43 | [`88c49f645757fd285df6e9fad9efbff4092fa149`](https://github.com/frankyxhl/alfred/pull/227/commits/88c49f645757fd285df6e9fad9efbff4092fa149) | index missing (Draft) marker | hygiene |
| 7 | 11:49 | [`173256e45c7ce1ebdda5c5fe352662280174b7ac`](https://github.com/frankyxhl/alfred/pull/227/commits/173256e45c7ce1ebdda5c5fe352662280174b7ac) | capability rule still listed bare "send" | consistency (sibling of #4) |
| 8 | 11:55 | [`6628c583a2b6e6ccf84bf9d97032dd5a07af554f`](https://github.com/frankyxhl/alfred/pull/227/commits/6628c583a2b6e6ccf84bf9d97032dd5a07af554f) | standing-approval mislabelled L3 · weak rollback precondition | loophole · weak-precondition |
| 9 | 11:57 | [`ad040bf8bf7ad4decb0c7e50a4d171df5d979324`](https://github.com/frankyxhl/alfred/pull/227/commits/ad040bf8bf7ad4decb0c7e50a4d171df5d979324) | proactive sweep (machine-self-approval, reversible/bounded) | pre-emptive |
| 10 | 12:04 | [`76ea6af6eea0533becf98e31cc40e67d48a3881e`](https://github.com/frankyxhl/alfred/pull/227/commits/76ea6af6eea0533becf98e31cc40e67d48a3881e) | envelope table row 5 · L2 When-NOT partial list | partial-enumeration |
| 11 | 12:08 | [`49c51aa68e351234959e48491754a0ca377941f8`](https://github.com/frankyxhl/alfred/pull/227/commits/49c51aa68e351234959e48491754a0ca377941f8) | Step 9 promotion check omitted escalation | partial-enumeration |
| 12 | 12:15 | [`d438bb30f94ad21f553b30a01403c392ffd7e050`](https://github.com/frankyxhl/alfred/pull/227/commits/d438bb30f94ad21f553b30a01403c392ffd7e050) | pre-verify abort not audited | **substantive workflow gap** |
| 13 | 12:20 | [`060bffcc63ccda5a0d11204dd05c7b539afc9c63`](https://github.com/frankyxhl/alfred/pull/227/commits/060bffcc63ccda5a0d11204dd05c7b539afc9c63) | audit-completeness drill didn't sample failure paths | follow-on (sibling of #12) |

### The dominant dynamic: each fix exposes a sibling

The single biggest pattern — **most findings were consequences of an earlier fix.**
The same concept lived in many places, and fixing one left the others inconsistent:

- the **human-notification carve-out** had to be applied in ~4 spots (invariant,
  Step 6, guard rail, capability audit) — findings #4 and #7;
- the **six-precondition envelope** was re-listed in ~6 spots (When-NOT ×2, promotion
  check, table, invariant, entry criteria) — findings #8, #10, #11;
- the **audit-on-failure-path** rule touched the step, the cross-cutting audit step,
  and the conformance drill — findings #12, #13.

This converged only after a **structural** fix: stop re-enumerating, point every site
at a single source of truth (COR-1626's six preconditions). Whack-a-mole on individual
sites would not have terminated.

### Finding taxonomy

- **Cross-doc consistency / sibling-exposure:** ~7 (the dominant class)
- **Governance loopholes** (relabel-as-L3, standing-license): 2
- **Hygiene / stale text:** 2
- **Wrong/weak reference:** 1
- **Substantive workflow gap:** 1 (pre-verify aborts skipping the audit — a real
  ordering bug, not a wording nit)

### Two-layer verification

Findings came from two independent layers: the **chatgpt-codex PR bot** (the 13 above,
caught in-flight) and a **glm/minimax/deepseek COR-1602 panel** that scored the larger
changes ≥9.0 and caught issues the single bot missed (e.g. MiniMax found a residual
stale conditional DeepSeek passed). Diversity of reviewers mattered.


## The lesson

Loop engineering eats its own tail: the act of *writing* the autonomy ladder was
governed by a loop the ladder *classifies as under-governed*. That is not an
embarrassment — it is the framework working. The loop shipped good output **because of
the surrounding context** (an external verifier, a contained blast radius, an attentive
human), not because it had an envelope. The ladder's whole point is to make that
distinction legible and to say: if you want this to run unattended and safely, **build
the envelope**.


## The compliant redesign (the build spec)

Two compliant shapes. The implementation — a real `pr-review-fix` bot — belongs in
**Voyager** (the automation/bot factory), alongside its existing GitHub-App bots; this
SOP engine only defines and classifies it.

### Option A — a clean L2 loop (human-gated)
Each round, present the batch of drafted fixes to the human; push only on approval.
Simplest path to compliance; slower. Essentially what we did, minus the standing
license — make the per-round approval explicit and single-use.

### Option B — a clean L3 loop (unattended, governed by an envelope)
Complete the six preconditions so it runs unattended **safely by construction**:

| Precondition | Concrete implementation |
|---|---|
| Bounded blast radius | hard cap: ≤ N rounds (e.g. 8) and ≤ M fixes/round; on exceed → stop + escalate |
| Automated rollback | if `af validate` / tests fail after a fix, **auto-revert that commit, do not push** |
| Durable audit log | append-only JSONL per round: `{round, commit, finding_id, category, verdict, tests}` |
| Recorded enablement | a config entry `Autonomy: L3` + the declared envelope, human-approved once (COR-1626 Step 2) |
| Verification | `af validate` + `pytest` per fix; optionally keep an external review bot |
| Escalation | on non-convergence (N rounds) or repeated test failures → wake the human; never loop silently |
| Kill-switch | a flag/file the human can set to halt mid-round |

Only branches, never `main`; never auto-merge (the merge stays a human L2 gate).


## Honest limits

This is **one** loop, **one** review bot, **one** session — an *illustrative* case, not
a statistical claim. The numbers (13 findings, 13 rounds, ~2h18m, 3 clean checks to
converge) describe this run, not "PR-review loops in general." Its value is the worked
classification and the convergence dynamic, both concrete and reproducible from the
cited commits. If the governed Option-B loop runs on future PRs and logs each run, this
becomes the first row of a dataset rather than an anecdote.

---

## Change History

| Date       | Change                                                                                                                                                | By   |
|------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|------|
| 2026-06-27 | Renumbered from FXA-2307 to FXA-2313 after main claimed 2307; replaced unreachable short SHA citations with full PR #227 commit links.                | Moth |
| 2026-06-20 | Initial version — case study of the PR #227 review-fix loop classified against the COR-1624/1625/1626 ladder; build spec for a Voyager implementation | —    |
