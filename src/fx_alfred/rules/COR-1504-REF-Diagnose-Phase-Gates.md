# REF-1504: Diagnose Phase Gates

**Applies to:** All projects using the COR document system
**Last updated:** 2026-05-03
**Last reviewed:** 2026-05-03
**Status:** Active
**Depends on:** COR-1503 (Diagnose Feedback Loop)
**Authored from:** FXA-2265 PRP (companion REF to COR-1503, extracted from §1.5 per round-3 review)
**Disposition:** inherit-only

---

## What Is It?

The detailed evidence-artefact specification for each phase gate in COR-1503 §Phase Enforcement Gates. This REF is the authoritative layout of what evidence closes a phase; COR-1503 carries a one-line-per-phase summary and links here. Operators should consult this REF when recording artefacts to close a phase; reviewers should consult this REF when verifying a diagnosis record.

---

## Phase Gate Table

| Phase | Minimum evidence artefact | Notes |
|---|---|---|
| 1 | **Loop command path** (a shell command, test invocation, script file, or HTTP request). **For non-deterministic bugs:** the measured rate (`X/N trials → P% rate`), with N≥20 trials and rate ≥30%. **Escape-hatch use:** the three items in COR-1503 §Phase 1 anti-abuse rules (≥3 methods attempted with command/output artefacts, structural-incompatibility justification per rejected method, explicit ask for missing artefact). | The loop command must be machine-executable. For deterministic bugs, a reviewer or CI system rerunning the command from the log must produce the same pass/fail. For non-deterministic bugs, rerunning the loop N≥20 trials must produce a rate ≥30% — single-run parity is not required by definition. For escape-hatch invocation, all three conjunctive conditions must be present; two of three is insufficient. |
| 2 | **Captured failure signature** (error message verbatim, wrong-output diff, or timing number in the `(metric, value, unit, baseline_comparison)` format). **AND** run count confirming reproducibility (≥2 runs for deterministic bugs; measured rate from Phase 1 for non-deterministic). | The failure signature must match the user-reported symptom. A "different failure that happens to be nearby" does not satisfy this gate — the operator must document the match. |
| 3 | **The 3–5 ranked hypotheses written down**, each stating a prediction in the form "if X is the cause, then changing Y will make the bug disappear / changing Z will make it worse". **AND** consultation outcome: user response (verbatim or paraphrased re-ranking), or an explicit `consultation: skip` line with reason. | "Vibes" without predictions do not count as hypotheses. A hypothesis list of 1 or 2 items does not satisfy the gate (single-hypothesis anchoring is the failure mode this gate prevents). `consultation: skip` without a reason is invalid — the reason is the audit trail. |
| 4 | **Probe→hypothesis mapping** (which probe tests which hypothesis from Phase 3) **AND** the result of each round: one variable changed, what happened. **Perf branch:** the baseline measurement artefact — one of (a) timing harness with N≥10 runs and reported median + p95 in seconds/ms, (b) profiler invocation with the captured profile saved to disk and path recorded, (c) EXPLAIN / query-plan capture saved to disk and path recorded. | Multi-variable "log everything" does not satisfy this gate — each probe must be attributable to a specific Phase-3 hypothesis. The perf-branch artefact must be present before any instrumentation; "it feels slow" is not a baseline. |
| 5 | **The fix diff** (commit hash or PR diff link). | Two or more unrelated changes bundled in the same fix commit violate COR-1503 §Phase 5. The fix must be the smallest change addressing the confirmed cause. |
| 6 | **The regression test path AND result** (passing). **OR** the explicit "seam absence acknowledged" line with reviewer identity (see COR-1503 §Phase 6 for the required format). | The test must exercise the Phase-1 repro at the correct seam. A shallow test that gives false confidence (testing a different surface, not the actual failure path) does not satisfy this gate. Seam-absence escape without reviewer acknowledgement is invalid. |

---

## Revision Clause

The numeric calibrations in rows 1 (≥30% rate over ≥20 trials) and 4 (N≥10 runs for timing harness) are **v1 defaults**, chosen as conservative working values rather than from a published study. After COR-1503 has been invoked in 5 real diagnoses, revisit these numbers — either tighten from empirical data or relax if they prove unnecessarily conservative. This REF carries the same revision clause as COR-1503 §Numeric calibrations note.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-03 | Initial version per FXA-2265 PRP. Extracted from COR-1503 §1.5 in round-3 review to resolve atomicity stress. | Frank Xu |
