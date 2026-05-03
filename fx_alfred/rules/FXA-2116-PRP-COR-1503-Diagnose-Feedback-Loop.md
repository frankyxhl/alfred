# PRP-2116: COR-1503-Diagnose-Feedback-Loop

**Applies to:** FXA project
**Last updated:** 2026-05-03
**Last reviewed:** 2026-05-03
**Status:** Approved
**Reviewed by:** Codex 8.8 FIX / Gemini 9.0 PASS / DeepSeek 6.8 FIX (R1); Codex 9.4 PASS / Gemini 9.5 PASS / DeepSeek 7.7 FIX (R2); revising for round 3
**Target document:** COR-1503 (PKG layer, new SOP) — ACID family-fit justified in §1.0
**Inspired by:** mattpocock/skills `engineering/diagnose` (Round 1 of skills-absorption initiative; Round 0 shipped COR-1613)

---

## What Is It?

A new PKG-layer SOP that defines a **disciplined diagnosis loop** for hard bugs and performance regressions. The loop is six phases: (1) build a fast deterministic feedback loop, (2) reproduce the user-reported symptom against that loop, (3) generate 3–5 ranked falsifiable hypotheses, (4) instrument one variable at a time to discriminate among them, (5) apply the fix, and (6) hand off to COR-1500 for the regression test scaffold.

The central claim — taken from the upstream skill and preserved in the SOP — is that **Phase 1 is the entire skill**. A 2-second deterministic pass/fail signal turns debugging into mechanical bisection; the absence of one turns debugging into staring. The SOP therefore ranks ten construction methods for the loop and treats the loop itself as a product to iterate on (faster, sharper, more deterministic).

The SOP is intentionally framework-agnostic per the universality contract first established in COR-1613. It names no harness, no provider, no agent, and no fixed reviewer count — it is invoked the same way any other Alfred SOP is invoked: the operator (human or LLM) declares COR-1503 active per COR-1402 before starting diagnosis.

---

## Problem

Alfred today has **COR-1500 TDD** for adding new features and **COR-1613 Council Review** for negotiating decisions about a target — but it has no SOP for the most common engineering activity that sits between them: **diagnosing an existing bug whose cause is unknown**. Concrete pains observed in recent sessions:

1. **No discipline around the feedback loop.** Engineers (human and LLM) routinely jump from "a bug was reported" straight to "let me read the code and guess the cause", skipping the construction of a deterministic, fast pass/fail signal. Without that signal, hypothesis-testing degrades into pattern-matching against memory.
2. **Single-hypothesis anchoring.** The first plausible cause that surfaces gets investigated to exhaustion before any alternative is generated, even when the alternative would have been ruled out in two minutes.
3. **Hypotheses are not falsifiable.** "Maybe the cache is stale" is a vibe, not a hypothesis — there is no stated prediction that would be wrong if it isn't the cache. Such statements consume time without narrowing the search.
4. **Multi-variable instrumentation.** Several probes get added in one round; when the symptom changes, the operator cannot attribute the change to a specific variable, and the next round repeats the confusion.
5. **Performance regressions get logged instead of measured.** Logs answer "did it run?" not "how long?". The diagnosis path for performance is structurally different from correctness and currently undocumented.
6. **No regression test by default.** Once the symptom disappears the work is declared done; the bug ships back six weeks later because nothing was added to the suite.

**Steelman of "do not ship — minimal alternative".** The strongest case for not shipping COR-1503 as a full SOP is **one sentence in COR-1500 §RED** ("if the cause is unknown, construct a deterministic repro signal before writing the assertion") **plus a sibling REF document** listing the ten feedback-loop construction methods. This delivers ~80% of the value at ~2% of the procedural footprint and avoids creating a new SOP. This stronger version of the steelman was raised in round-1 review (DeepSeek). It is rejected for three reasons: (a) the discipline is not just *constructing* a loop but *iterating on it as a product*, *generating ranked falsifiable hypotheses*, *one-variable-per-round instrumentation*, and *mandatory regression hand-off* — none of those have a natural home in a one-sentence COR-1500 hint; (b) phase enforcement (per §1.5 below) requires named gates that a hint cannot enforce; (c) a sibling REF document captures the methods but not the operator discipline that turns methods into reliable fixes. The minimal-alternative cost saving is real but bought at the cost of leaving the actual skill (the discipline, not the methods) undocumented. **The atomic SOP is justified only if the phase-enforcement gates in §1.5 ship with it** — without them, the steelman wins.

---

## Proposed Solution

### 1.0 ACID family-fit and routing

**Family-fit justification.** The 15xx family is the **code-lifecycle family**. Current allocations: COR-1500 (TDD Workflow), COR-1501 (Create GitHub Issue), COR-1502 (Git Branch Naming). The family is "code-production discipline" and 1503 is the next free slot adjacent to 1500 — natural placement for a sibling SOP that produces the input COR-1500 consumes (a known-cause assertion). The earlier draft of this section incorrectly described 1501/1502 as unallocated; that error was caught in round 1 (Codex) and is corrected here. ACID 1503 stands; only the supporting prose needed correction.

Two alternatives were considered and rejected:

- **16xx (review family).** Rejected: diagnosis is not a review activity; the review of the resulting fix happens later under COR-1613.
- **New 17xx family for "investigation".** Rejected: no other investigation SOPs exist yet; creating a one-member family violates COR-1400 atomicity at the family level. Re-evaluate if a second investigation SOP appears.

**Routing.** This PRP commits to a follow-up CHG (`FXA-2118`) that updates COR-1103's intent router and OVERLAYS section to add COR-1503 under intents like "diagnose this", "debug this", "X is broken / throwing / failing", "performance regression". Without that CHG the SOP would be discoverable only by direct reference; the CHG is small (one OVERLAYS row, one decision-tree branch under the existing branch 2 "Something broken/failing/unexpected?") and is in scope for the same merge window as the SOP. **Note on ACID:** the previous draft proposed `FXA-2117`; that ACID is already reserved per CLAUDE.md "Active PRPs" for "AF Filter + Section Update". To avoid the ACID-collision class of bug recently fixed in PR #87, this PRP uses `FXA-2118`.

### 1.1 New PKG SOP — COR-1503-SOP-Diagnose-Feedback-Loop

A 5W1H SOP defining the six phases below. The body is normative; the prose summarises what each phase requires and forbids. **Phase enforcement gates are defined in §1.5 — phases without their evidence artefact recorded in the session log/PR body do not satisfy this SOP, regardless of operator self-report.**

**Phase 1 — Build a feedback loop.** The operator must construct a fast, deterministic, machine-runnable pass/fail signal for the bug *before* any hypothesis is tested. The SOP body lists the ten construction methods in ranked order (failing test → curl/HTTP probe → CLI fixture diff → headless browser → replayed trace → throwaway harness → property/fuzz → bisection harness → differential loop → HITL bash script as last resort) and instructs the operator to walk the list top-down, taking the first one that fits. The loop is then iterated on as a product: make it faster (target single-digit seconds), sharper (assert on the specific symptom, not "did not crash"), and more deterministic (pin time, seed RNG, isolate filesystem, freeze network).

For non-deterministic bugs, the goal is a **higher reproduction rate**, not a clean repro. The operator must establish the current rate (run the trigger N≥20 times; rate = failures/N), then loop / parallelise / narrow timing windows / inject sleeps until the rate reaches **at least 30% over ≥20 trials**. Below that floor, hypothesis-testing is unreliable; the operator must keep raising the rate before proceeding to Phase 3.

**Phase 1 escape hatch (anti-abuse rules).** If after honest effort no loop can be built, the operator may escape only when **all three** conditions are met: (i) **at least three** of the ten construction methods were attempted, with the attempt artefact (commands run, files created, output captured) recorded in the session log; (ii) the operator records a **structural-incompatibility justification** for each rejected method (e.g., "method 4 headless browser N/A — target is a CLI tool with no rendered UI"; not "tried it, was hard"); (iii) the operator explicitly stops and asks for the missing artefact (environment access, captured trace, permission to add temporary instrumentation). Proceeding to Phase 3 without satisfying all three is forbidden. The escape hatch exists for genuinely-impossible cases (production-only repros, lost test environments) and must not become the path of least resistance.

**Phase 2 — Reproduce.** Run the loop. Confirm the failure mode matches the user-reported symptom (not a different failure that happens to be nearby), confirm reproducibility across multiple runs (or at the elevated rate established in Phase 1), and capture the exact symptom signature so Phase 6 can verify the fix actually addresses it. Forbidden to advance until reproduction is confirmed.

**Phase 3 — Hypothesise.** Generate **3–5 ranked falsifiable hypotheses** before testing any one of them. Each must state a prediction in the form "if X is the cause, then changing Y will make the bug disappear / changing Z will make it worse". Vibes ("maybe the cache is stale") that do not yield a prediction are discarded or sharpened. The ranked list is **shown to the user before testing begins** as a cheap checkpoint — domain knowledge frequently re-ranks the list instantly. Default is mandatory consultation; the operator may opt out only by recording an explicit `consultation: skip` line in the Phase-3 hypothesis list with a reason (typical reasons: solo operator, AFK user with no second party, experimental sandbox where audit trail is the recorded skip). The skip itself is the audit trail; silent skipping is forbidden.

**Phase 4 — Instrument.** Each probe maps to a specific prediction from Phase 3. **One variable changes per round.** Tool preference: debugger / REPL inspection where the environment supports it (one breakpoint beats ten logs), then targeted logs at boundaries that discriminate hypotheses. Never "log everything and grep". Every debug log carries a unique tag prefix (e.g. `[DEBUG-a4f2]`) so cleanup at the end is a single grep — untagged logs survive and rot.

**Phase 4 — performance branch.** For performance regressions, logs are usually wrong; the operator establishes a **baseline measurement artefact** before instrumenting. The artefact is one of: (a) a recorded timing harness with N≥10 runs and reported median + p95 in seconds/ms; (b) a profiler invocation with the captured profile saved to disk and the path recorded; (c) a query-plan capture (EXPLAIN output) for database regressions, saved to disk. The operator records the chosen artefact type and the baseline number / file path in the session log before any instrumentation. Bisection then proceeds against this fixed baseline. "It feels slow" or "it's slower than before" is not a baseline; without an artefact, Phase 4 perf branch has not started.

**Phase 5 — Fix.** Apply the smallest change that addresses the confirmed cause. Forbidden to bundle in unrelated cleanups; those go to a separate change. If the diagnosis revealed an architectural smell (no good test seam, hidden coupling, tangled call chain), record the finding for Phase 6 hand-off but do not act on it inside the fix.

**Phase 6 — Regression-test.** Hand off to COR-1500 for the test scaffold: turn the Phase-1/Phase-2 repro into a failing test at the correct seam (RED), then confirm the Phase-5 fix makes it pass (GREEN), then refactor (REFACTOR). If no correct seam exists, that is itself the finding — and the **absence-of-seam escape requires explicit reviewer acknowledgement in the PR body** before merge ("seam absence acknowledged: <reviewer> confirmed that <reason: no public boundary / external dependency only / etc.> makes a regression test infeasible at this revision"). Without that acknowledgement, the absence claim is a default-skip and the SOP gate has not closed. Required before declaring done: original repro no longer reproduces, regression test passes (or absence-of-seam acknowledgement above), all `[DEBUG-...]` instrumentation removed, throwaway prototypes deleted, and the hypothesis that turned out correct stated in the commit/PR message so the next debugger learns. The fix PR then enters the normal review path — see §1.3.

### 1.2 Relationship to COR-1500

COR-1503 is the **prelude** to TDD when the bug is already known. COR-1500 assumes the operator knows what assertion to write; COR-1503 produces that knowledge. The hand-off is explicit: Phase 6 invokes COR-1500's RED→GREEN→REFACTOR cycle for the regression test, with the Phase 1 repro as the RED assertion source. The two SOPs do not overlap in scope: COR-1500 covers feature TDD where the failure mode is specified by acceptance criteria; COR-1503 covers diagnosis where the failure mode must first be characterised against a live system.

### 1.3 Relationship to COR-1613

When the Phase-5 fix produces a code change, the resulting PR enters **Council Review (COR-1613)** like any other code change. The operator declares a Review Unit per COR-1613 §Step 1 with mechanism defaulting to Decision Matrix (COR-1602/1608). COR-1503 ends at the moment a fix is committed; COR-1613 begins for the PR that lands it. The two SOPs are sequential: a Council Review of a half-diagnosed fix is **forbidden** because the Review Unit cannot record a falsified hypothesis it never saw. To make this prohibition enforceable rather than aspirational, this PRP commits to a parallel companion CHG (`FXA-2119`) that adds the prohibition to COR-1613 §When NOT to Use, shipping in the same merge window.

### 1.4 Universality contract

The SOP body must NOT contain any of the following tokens (this is a greppable blocklist; the SOP review checklist runs `grep -nE` against the SOP file before merge):

```
Claude Code | trinity | Codex | Gemini | DeepSeek | GLM | Anthropic | OpenAI |
ChatGPT | Copilot | bugfixer | coder | refactorer | code-reviewer | translator
```

In addition, the SOP body must NOT mention:

- Any specific harness or runtime (e.g., "in Claude Code", "in Cursor")
- Any fixed number of reviewers
- Any specific human role names beyond abstract roles (operator, reviewer, dispatcher)

If a project's habits depend on such specifics, record those in a USR/PRJ-layer supplementary doc, not in the PKG SOP. **This blocklist is identical in shape to COR-1613 §Universality Contract; the additional explicit token list closes the "claimed but unenforced" gap raised in round-1 review.**

### 1.5 Phase enforcement gates

Each phase requires a minimum evidence artefact recorded in the session log or PR body before the operator may claim the phase complete. Without the artefact, the phase has not closed regardless of self-report.

The **detailed gate table** is extracted to a sibling reference document `COR-1504-REF-Diagnose-Phase-Gates.md` (companion CHG `FXA-2120` ships in the same merge window). The SOP body keeps a one-line summary per phase and links to the REF for the full evidence-artefact spec. This split keeps COR-1503 atomic ("define the diagnosis loop") while preserving the gate enforcement that the §Problem steelman requires. The summary:

| Phase | Gate (one-line; see COR-1504 REF for full artefact spec) |
|---|---|
| 1 | Loop command + measured non-determinism rate (escape hatch requires §1.1 triplet) |
| 2 | Captured failure signature + reproducibility/rate confirmation |
| 3 | Ranked hypotheses with predictions + consultation outcome (or `consultation: skip` line) |
| 4 | Probe→hypothesis mapping + per-round result; perf branch requires baseline `(metric, value, unit, baseline_comparison)` |
| 5 | Fix diff (commit hash or PR diff link) |
| 6 | Regression test path + passing result OR explicit "seam absence acknowledged" line with reviewer identity |

**Numeric calibrations note.** The Phase-1 non-determinism floor (≥30% over ≥20 trials) and Phase-4 perf-baseline run count (N≥10) are **v1 calibrations**, chosen as conservative working defaults rather than from a published study. They are flagged for revision after the SOP has been invoked in 5 real diagnoses; the COR-1504 REF carries the same revision clause.

These artefacts are not new bureaucracy — most operators record them informally already. The gate makes them required and named.

### 1.6 When NOT to Use

This SOP is the wrong tool for the following classes of work; use the named alternative instead:

- **One-line typo fixes, obvious null-checks, off-by-one in a clearly-tested function.** The bug is known by inspection in seconds; six phases is over-process. Fix directly and apply COR-1500 RED for the regression test in one step.
- **Style / lint / format-only fixes.** No diagnosis exists; no SOP needed.
- **Reverting a known-bad commit.** The "diagnosis" is the bisect result already in hand; skip to Phase 5.
- **Documentation fixes.** No code feedback loop applies.
- **Adding a feature whose test fails because the feature does not exist yet.** That's COR-1500 territory; the failing test was written by intent, not discovered.

The bright line is **"is the cause unknown?"** If yes → COR-1503. If no → direct fix + COR-1500 RED for the regression test.

### 2. Scope of this PRP

In scope:

- Drafting the new PKG SOP `COR-1503-SOP-Diagnose-Feedback-Loop.md` at `src/fx_alfred/rules/`
- Drafting the sibling PKG REF `COR-1504-REF-Diagnose-Phase-Gates.md` at `src/fx_alfred/rules/` (per §1.5; companion CHG `FXA-2120`)
- Defining the six phases with the prohibitions, hand-offs, linked gates (§1.5), and "When NOT to Use" (§1.6)
- Three companion CHGs (separate PRs, same merge window):
  - `FXA-2118-CHG-COR-1103-Add-Diagnose-Routing.md` — adds COR-1503 entry to COR-1103 OVERLAYS + decision tree under branch 2
  - `FXA-2119-CHG-COR-1613-Add-Half-Diagnosed-Fix-Prohibition.md` — adds "fix PR entering Council Review without a complete COR-1503 record" to COR-1613 §When NOT to Use (per §1.3)
  - `FXA-2120-CHG-COR-1504-REF-Diagnose-Phase-Gates.md` — creates the sibling reference document for the detailed gate table, linked from COR-1503 §1.5

Out of scope:

- Any modification to the bugfixer agent or any other agent definition (explicit user constraint — diagnosis is invoked the same way other SOPs are, by declaration per COR-1402)
- Tooling (`af diagnose`, harness scaffolders) — deferred; flag for future PRP if usage warrants
- Retroactive migration of past bugfix sessions to COR-1503 records
- Modifying COR-1500 (the relationship is one-way reference; COR-1500 needs no change)

---

## Open Questions

All resolved by user confirmation prior to round-2 dispatch. Round-1 and round-2 reviewer findings have been incorporated into the body above; no new OQs raised in either revision.

1. **Performance regressions in the same SOP?** RESOLVED: yes, single SOP. Phase 4 has an explicit "performance branch" with its own minimum baseline artefact (§1.5).
2. **Phase 3 user consultation mandatory?** RESOLVED: yes, mandatory by default. Opt-out requires an explicit `consultation: skip` line with reason recorded in the Phase-3 hypothesis list. Solo-LLM operators record the skip themselves; the audit trail is the line, not silence.
3. **Phase 6 regression test optional for env-only fixes?** RESOLVED: never fully optional. CI assertion, dependency-pin lockfile entry, or documented manual verification step all count as the regression check.
4. **What counts as "honest effort" in Phase 1's escape hatch?** RESOLVED: at least three of the ten construction methods attempted with artefact recorded, structural-incompatibility justification per rejected method, and an explicit ask for the missing artefact (§1.1 Phase 1 escape hatch).
5. **Recursive application for regressions of recent fixes?** RESOLVED: yes, recursive. Re-enter Phase 1 of a new COR-1503 invocation; the prior falsified hypothesis is recorded as a falsified prior in the new Phase 3.

---

## Change History

| Date       | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | By           |
|------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|
| 2026-05-03 | Initial version                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | —            |
| 2026-05-03 | Drafted PRP body as Round 1 of mattpocock/skills absorption initiative; GLM as worker per user constraint (no bugfixer agent modification); 6-phase SOP with explicit hand-offs to COR-1500 (regression test) and COR-1613 (fix PR review); universality contract mirrors COR-1613 §1.4                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | GLM (worker) |
| 2026-05-03 | Round-1 review: Codex 8.8 FIX, Gemini 9.0 PASS (thin), DeepSeek 6.8 FIX (Risk Awareness 4.0 sub-floor breach). Mean 8.2. Revised: §1.0 corrected false 1501/1502-unallocated claim; companion CHG ACID changed FXA-2117 → FXA-2118 (collision with reserved AF Filter PRP per CLAUDE.md, mirrors PR #87 fix); §1.1 Phase 3 aligned with OQ2 (consultation: skip line required for opt-out, no silent skipping); §1.1 Phase 1 surfaces OQ4 (≥3 methods + structural-incompatibility justification + explicit ask) into the prose; §1.1 Phase 4 perf branch defines minimum baseline artefact (timing harness OR profiler OR query plan, with N≥10 / saved path); §1.1 Phase 6 absence-of-seam escape requires explicit reviewer acknowledgement; §1.1 Phase 1 quantifies non-determinism floor (≥30% rate over ≥20 trials); §1.4 universality contract adds explicit greppable token blocklist; §1.5 Phase enforcement gates table added (DeepSeek's primary required fix); §1.6 "When NOT to Use" added for trivial bugs / lint / docs / known-bad-revert (Gemini Risk + DeepSeek steelman); §Problem steelman rewritten to engage strongest version (DeepSeek) — minimal alternative is COR-1500 §RED hint + sibling REF, rejected only because §1.5 enforcement gates need a named SOP; §1.3 softens "forbidden" → "should not" since COR-1613 doesn't encode the prohibition. | Frank Xu     |
| 2026-05-03 | Round-2 review: Codex 9.4 PASS, Gemini 9.5 PASS, DeepSeek 7.7 FIX (Risk 7.5, sub-floor lifted). DeepSeek N1 (atomicity drift from §1.5+§1.6 growth), N3 (backslide on §1.3 softening), N2 + C3 (row-2 timing-number ambiguity, number provenance). Revised: §1.3 restored "forbidden" with parallel companion CHG FXA-2119 committing to COR-1613 §When NOT to Use prohibition; §1.5 detailed gate table extracted to sibling REF COR-1504 (FXA-2120), one-line summary kept in SOP body; §1.5 row 2 timing signature tightened to `(metric, value, unit, baseline_comparison)`; numeric calibrations (30% / N≥20 / N≥10) annotated as v1 with 5-invocation revision clause. Companion CHG count grew from 1 to 3 (FXA-2118 routing + FXA-2119 COR-1613 prohibition + FXA-2120 gate REF).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | Frank Xu     |
| 2026-05-03 | Round 3 panel review: Codex 9.7 PASS / Gemini 9.5 PASS / DeepSeek 9.2 PASS. Mean 9.47. Unanimous 3-of-3 PASS — first unanimous Council Review in Alfred history. DeepSeek crossed 9.0 threshold for the first time after 3 rounds (R1 6.8 → R2 7.7 → R3 9.2). All 4 R2 concerns resolved, no new issues. Proceeding to implementation.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | Frank Xu     |
