# SOP-1503: Diagnose Feedback Loop

**Applies to:** All projects using the COR document system
**Last updated:** 2026-05-03
**Last reviewed:** 2026-05-03
**Status:** Active
**Depends on:** COR-1402 (Declare Active Process), COR-1500 (TDD Development Workflow)
**Related:** COR-1613 (Council Review), COR-1504-REF-Diagnose-Phase-Gates
**Authored from:** FXA-2265 PRP (unanimous 3-of-3 PASS, R3)

---

## What Is It?

A disciplined diagnosis loop for hard bugs and performance regressions. Six phases: (1) build a fast deterministic feedback loop, (2) reproduce the user-reported symptom against that loop, (3) generate 3–5 ranked falsifiable hypotheses, (4) instrument one variable at a time to discriminate among them, (5) apply the fix, and (6) hand off to COR-1500 for the regression test scaffold.

The central claim is that **Phase 1 is the entire skill**. A 2-second deterministic pass/fail signal turns debugging into mechanical bisection; the absence of one turns debugging into staring.

This SOP is intentionally framework-agnostic per the universality contract in §Universality Contract. It names no harness, no provider, no agent, and no fixed reviewer count — it is invoked the same way any other Alfred SOP is invoked: the operator (human or LLM) declares COR-1503 active per COR-1402 before starting diagnosis.

---

## Why

Alfred today has COR-1500 TDD for adding new features and COR-1613 Council Review for reviewing their outputs — but no SOP for diagnosing an existing bug whose cause is unknown. Without a named discipline, operators (human and LLM) jump from "a bug was reported" straight to guessing causes, skip feedback-loop construction, anchor on the first plausible hypothesis, and declare success when the symptom disappears without a regression test. This SOP gives the most common engineering activity a name and a reproducible shape.

---

## When to Use

- An existing bug, crash, or performance regression is reported and its cause is unknown
- An operator needs to diagnose "broken / throwing / failing / slower than before"
- The bug is reproducible (or at least non-deterministically observable) by the operator

## When NOT to Use

- **One-line typo fixes, obvious null-checks, off-by-one in a clearly-tested function.** The cause is known by inspection. Fix directly and apply COR-1500 RED for the regression test.
- **Style / lint / format-only fixes.** No diagnosis exists; no SOP needed.
- **Reverting a known-bad commit.** The diagnosis was the bisect; skip to Phase 5.
- **Documentation fixes.** No code feedback loop applies.
- **Adding a feature whose test fails because the feature does not exist yet.** COR-1500 territory; the failing test was written by intent, not discovered.

The bright line is **"is the cause unknown?"** If yes → COR-1503. If no → direct fix + COR-1500 RED for the regression test.

---

## How

### Phase 1 — Build a feedback loop

Construct a fast, deterministic, machine-runnable pass/fail signal for the bug **before** any hypothesis is tested. Walk the ten construction methods top-down, taking the first one that fits:

1. **Failing test** at whatever seam reaches the bug — unit, integration, e2e.
2. **Curl / HTTP script** against a running dev server.
3. **CLI invocation** with fixture input, diff stdout against a known-good snapshot.
4. **Headless browser script** — drive the UI via an automated browser, assert on DOM/console/network.
5. **Replay a captured trace.** Save a real network request / payload / event log to disk; replay through the code path in isolation.
6. **Throwaway harness.** Spin up a minimal subset of the system (one service, mocked deps) that exercises the bug code path with a single function call.
7. **Property / fuzz loop.** If the bug is "sometimes wrong output", run random inputs and look for the failure mode.
8. **Bisection harness.** If the bug appeared between two known states (commit, dataset, version), automate "boot at state X, check, repeat" so `git bisect run` can consume it.
9. **Differential loop.** Run the same input through old-version vs new-version (or two configs) and diff outputs.
10. **HITL bash script.** Last resort. If a human must click, drive them with a structured loop script so the loop is still structured.

Iterate on the loop as a product:
- **Faster** (target single-digit seconds; cache setup, skip unrelated init, narrow test scope)
- **Sharper** (assert on the specific symptom, not "didn't crash")
- **More deterministic** (pin time, seed RNG, isolate filesystem, freeze network)

**Non-deterministic bugs.** The goal is a **higher reproduction rate**, not a clean repro. Establish the current rate (run the trigger N≥20 times; rate = failures/N), then loop / parallelise / narrow timing windows / inject sleeps until the rate reaches **at least 30% over ≥20 trials**. Below that floor, hypothesis-testing is unreliable; keep raising the rate before proceeding to Phase 3.

**Escape hatch (anti-abuse).** If after honest effort no loop can be built, proceed only when **all three** conditions are met: (i) at least **three** of the ten construction methods were attempted, with the attempt artefact (commands run, files created, output captured) recorded; (ii) a **structural-incompatibility justification** for each rejected method ("method 4 headless browser N/A — target is a CLI tool with no rendered UI", not "tried it, was hard"); (iii) the operator explicitly stops and asks for the missing artefact (environment access, captured trace, permission to add temporary instrumentation). Proceeding to Phase 2 without satisfying all three is forbidden.

Proceed to Phase 2 only when you have a loop you believe in. **If the escape hatch was invoked, the SOP stops at Phase 1.** The operator must communicate the missing artefact (environment access, captured trace, permission for instrumentation) to the requester and wait for it before re-entering. No further phases are reachable without a loop — the escape hatch is an exit, not a shortcut.

### Phase 2 — Reproduce

Run the loop. Confirm:

- The failure mode matches the **user-reported symptom** — not a different failure that happens to be nearby. Wrong bug = wrong fix.
- The failure is reproducible across multiple runs (or at the elevated rate established in Phase 1).
- The exact symptom signature is captured (error message verbatim, wrong-output diff, or timing number) so Phase 6 can verify the fix addresses it.

Forbidden to advance until reproduction is confirmed.

### Phase 3 — Hypothesise

Generate **3–5 ranked falsifiable hypotheses** before testing any one of them. Each must state a prediction:

> "If **X** is the cause, then **changing Y** will make the bug disappear / **changing Z** will make it worse."

Vibes ("maybe the cache is stale") that do not yield a prediction are discarded or sharpened.

**Show the ranked list to the user before testing.** Domain knowledge frequently re-ranks the list instantly — this is a cheap checkpoint with high payoff. The operator may opt out only by recording an explicit `consultation: skip` line in the hypothesis list with a reason (typical: solo operator, AFK user with no second party). The skip line itself is the audit trail; silent skipping is forbidden.

### Phase 4 — Instrument

Each probe maps to a **specific prediction from Phase 3**. One variable changes per round.

- Tool preference: debugger / REPL inspection where the environment supports it (one breakpoint beats ten logs), then targeted logs at boundaries that discriminate hypotheses.
- Never "log everything and grep".
- Every debug log carries a unique tag prefix (e.g. `[DEBUG-a4f2]`) so cleanup at the end is a single grep — untagged logs survive and rot.

**Performance branch.** For performance regressions, logs are usually wrong. Establish a baseline measurement artefact before instrumenting: (a) a recorded timing harness with N≥10 runs and reported median + p95 in seconds/ms; (b) a profiler invocation with the captured profile saved to disk and the path recorded; (c) a query-plan capture (EXPLAIN output) for database regressions, saved to disk. Record the chosen artefact type and the baseline number / file path before any instrumentation. "It feels slow" or "it's slower than before" is not a baseline; without an artefact, the perf branch has not started.

### Phase 5 — Fix

Apply the smallest change that addresses the confirmed cause. Forbidden to bundle in unrelated cleanups; those go to a separate change. If the diagnosis revealed an architectural smell (no good test seam, hidden coupling, tangled call chain), record the finding for Phase 6 but do not act on it inside the fix.

### Phase 6 — Regression-test

Hand off to COR-1500 for the test scaffold: turn the Phase-1/Phase-2 repro into a failing test at the correct seam (RED), then confirm the Phase-5 fix makes it pass (GREEN), then refactor (REFACTOR).

If no correct seam exists, that is itself the finding — and the **absence-of-seam escape requires explicit reviewer acknowledgement in the PR body** before merge:

> "seam absence acknowledged: <reviewer> confirmed that <reason> makes a regression test infeasible at this revision."

Required before declaring done:
- Original repro no longer reproduces
- Regression test passes (or absence-of-seam acknowledgement above)
- All `[DEBUG-...]` instrumentation removed; throwaway prototypes deleted
- The hypothesis that turned out correct stated in the commit/PR message

The fix PR then enters the normal review path — see §Relationship to COR-1613.

---

## Phase Enforcement Gates

Each phase requires a minimum evidence artefact before the operator may claim the phase complete. Without the artefact, the phase has not closed regardless of self-report.

The full artefact specification is in **COR-1504-REF-Diagnose-Phase-Gates**. For inline reference, the summary:

| Phase | Gate (one-line; see COR-1504 REF for full artefact spec) |
|---|---|
| 1 | Loop command + measured non-determinism rate (escape hatch requires triplet) |
| 2 | Captured failure signature + reproducibility/rate confirmation |
| 3 | Ranked hypotheses with predictions + consultation outcome (or `consultation: skip` line) |
| 4 | Probe→hypothesis mapping + per-round result; perf branch requires baseline `(metric, value, unit, baseline_comparison)` |
| 5 | Fix diff (commit hash or PR diff link) |
| 6 | Regression test path + passing result OR explicit "seam absence acknowledged" line with reviewer identity |

**Numeric calibrations note.** The Phase-1 non-determinism floor (≥30% over ≥20 trials) and Phase-4 perf-baseline run count (N≥10) are **v1 calibrations**, chosen as conservative working defaults rather than from a published study. They are flagged for revision after this SOP has been invoked in 5 real diagnoses; COR-1504 REF carries the same revision clause.

---

## Relationship to COR-1500

COR-1503 is the **prelude** to TDD when the bug is already known. COR-1500 assumes the operator knows what assertion to write; COR-1503 produces that knowledge. Phase 6 invokes COR-1500's RED→GREEN→REFACTOR cycle for the regression test, with the Phase-1 repro as the RED assertion source.

## Relationship to COR-1613

When the Phase-5 fix produces a code change, the resulting PR enters **Council Review (COR-1613)** like any other code change. The operator declares a Review Unit per COR-1613 §Step 1 with mechanism defaulting to Decision Matrix (COR-1602; rubric per the target type — COR-1608 for PRP, COR-1609 for CHG, COR-1610 for code per COR-1103). COR-1503 ends at the moment a fix is committed; COR-1613 begins for the PR that lands it. A Council Review of a half-diagnosed fix is **forbidden** (per COR-1613 §When NOT to Use).

---

## Universality Contract

This SOP must NOT contain any of the following tokens in its normative body text (the blocklist applies to everything between the `---` after frontmatter and `## Change History`; the blocklist definition itself and the Change History provenance rows are exempt from the matchup, since the blocklist names tokens to forbid and Change History records document authorship):

```
Claude Code | trinity | Codex | Gemini | DeepSeek | GLM | Anthropic | OpenAI |
ChatGPT | Copilot | bugfixer | coder | refactorer | code-reviewer | translator
```

This SOP must NOT mention any specific harness, runtime, provider, model, panel composition, fixed reviewer count, agent name, or human role name beyond abstract roles (operator, reviewer, dispatcher). If a project's habits depend on such specifics, record those in a USR/PRJ-layer supplementary doc.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-03 | Initial version per FXA-2265 PRP. Unanimous 3-of-3 PASS in round-3 panel review (Codex 9.7 / Gemini 9.5 / DeepSeek 9.2). | Frank Xu |
