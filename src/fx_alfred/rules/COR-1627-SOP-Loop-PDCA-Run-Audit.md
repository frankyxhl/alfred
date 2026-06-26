# SOP-1627: Loop PDCA Run Audit

**Applies to:** All projects using the COR document system
**Last updated:** 2026-06-21
**Last reviewed:** 2026-06-21
**Status:** Draft
**Related:** COR-1624, COR-1625, COR-1626, COR-1617, COR-1620, COR-1602, COR-1609
**Task tags:** []
**Autonomy:** L1 report-only
**Disposition:** inherit-only

---

## What Is It?

A report-only PDCA loop for auditing a completed or in-progress run and turning its evidence into actionable process feedback.

This SOP is not a delivery loop. It does not implement code, modify documents, open issues, deploy services, or execute remediations. It observes an already-recorded run, checks what happened against the intended plan and gates, and emits feedback that a human or later L2 workflow can choose to act on.

Default autonomy is **L1 report-only** per COR-1624. The audit itself stays L1: it may recommend changes, but any follow-up action starts a separate COR-1625 L2 workflow or normal project workflow with its own concrete draft, human gate, and validation.

While this SOP is `Draft`, task tags stay empty so `af plan --task` does not auto-compose it as an active runbook. Add discoverability tags only when the SOP is promoted to an approved active status.

---

## Why

Delivery loops produce valuable evidence: plans, review rounds, CI results, deployment checks, rejected paths, operator corrections, and mistakes. Without a dedicated audit loop, that evidence stays trapped in chat history, PR comments, or scattered logs, and the same process defects reappear.

PDCA gives the retrospective a stable shape:

- **Plan** — what was supposed to happen?
- **Do** — what actually happened?
- **Check** — where did reality diverge from the plan, gates, or expected outcome?
- **Act** — what should change next?

The key safety rule is that at L1, **Act means recommendation, not execution**. The loop creates a feedback package; it does not apply the package.

---

## When to Use

- After an L2 code-delivery run, release, deployment, incident response, or multi-agent workflow.
- After a run had review churn, CI churn, repeated bot comments, identity drift, deployment risk, or unclear handoff state.
- When a project wants evidence-backed amendments to SOPs, checklists, or loop gates.
- When evaluating whether an L1 loop is ready for L2 promotion, or whether an L2 loop is stable enough to consider future L3 envelope work.

## When NOT to Use

- For real-time bug diagnosis; use COR-1503.
- For the delivery run itself; use the target delivery SOP such as COR-1616 or a project-specific loop SOP.
- To execute fixes automatically. At L1, this SOP only reports. Mutating follow-up work routes separately through COR-1625 or the project's normal CHG/PRP flow.
- For unrecorded work where no evidence exists. First reconstruct the run record or state that the audit is evidence-limited.

---

## Inputs

Use the smallest evidence set that can answer the audit question. Typical sources:

- run plan, PRP, CHG, PLN, ADR, issue, or SOP that declared the intended process;
- command summaries, CI/check results, local validation, deployment health checks, and release records;
- PR comments, review threads, bot review summaries, and human approval/handoff messages;
- agent role records, session IDs, transcript paths, and raw reviewer outputs when available;
- audit directories, append-only logs, or activity-ledger rows;
- final outcome: shipped, handed off, rolled back, deferred, rejected, or abandoned.

Do not read or copy secrets. If the source evidence includes private config paths or secret-adjacent logs, record existence and redacted summaries only.

---

## Steps

1. **Declare scope and autonomy** — Name the audited run, source artifacts, target repo/project, time window, and `Autonomy: L1`. State what the audit will not touch and name the passive report sink.
2. **Gather evidence read-only** — Collect the inputs needed to reconstruct the run using read-scoped capabilities only, except for at most one narrowly scoped passive-sink writer. Prefer durable artifacts over memory. If using chat history, quote only the minimum relevant facts and preserve private boundaries.
3. **Plan: reconstruct intended behavior** — Extract the promised plan, active SOPs, acceptance gates, review thresholds, identity expectations, deployment expectations, and stop conditions.
4. **Do: reconstruct actual behavior** — Produce a concise timeline of actions, actors, tool calls, review rounds, commits, validations, deployments, and handoffs. Separate facts from interpretation.
5. **Check: compare plan to reality** — Identify deviations, missing gates, late reviews, repeated work, unclear ownership, identity drift, stale assumptions, excessive churn, and places where success criteria were ambiguous or too weak.
6. **Classify findings** — Use severity language appropriate to process feedback:
   - **Blocking process defect** — likely to cause wrong action, unsafe automation, bad release/deploy, or false readiness if repeated.
   - **Improvement** — reduces waste, review churn, ambiguity, or operator load.
   - **Observation** — useful fact with no immediate process change.
7. **Accept and recommend only** — Triage findings into accepted, rejected, and watch-only. For each accepted finding, propose the smallest next action and its target layer:
   - COR candidate;
   - USR/WUK amendment;
   - PRJ/OCO amendment;
   - target-project amendment;
   - GitHub issue/PR candidate recorded in the report, not opened or staged for machine pickup;
   - no action / keep watching.
8. **Record the audit report** — Write a passive report sink: external REF-style draft outside the tracked document corpus, append-only activity log, audit Markdown, or dashboard row. The sink must be read by a human and must not be drained by automation. If a PLN, REF, SOP, or other tracked system-of-record document/status change is wanted, route that mutation through a separate L2 workflow. The report must include evidence links, findings, recommendations, rejected suggestions, and residual risks.
9. **Stop at the boundary** — Do not execute the recommendations in the same L1 loop. If follow-up work is approved, start a new L2 gated action or normal project workflow with its own plan and validation.

---

## Output Shape

Use this shape unless the project has a stricter local template:

```markdown
## Scope

- Run:
- Time window:
- Target repo/project:
- Autonomy: L1 report-only
- Report sink:
- L1 conformance checks:
- Evidence sources:

## Plan

- Intended SOPs/gates:
- Expected outputs:
- Stop/handoff conditions:

## Do

- Timeline:
- Actors/tools:
- Validation/review/deploy results:

## Check

- Passed gates:
- Deviations:
- Waste/churn:
- Risk signals:

## Act Recommendations

- [Layer] Recommendation:
- Evidence:
- Suggested next workflow:
- Priority:
- Status: accepted / rejected / watch-only

## Residual Risk

- What remains unknown:
- What should be watched next:
```

---

## Guard Rails

- **L1 Act is recommendation-only.** Never apply a recommendation from this SOP without a separate L2 gate or project workflow.
- **No audit laundering.** Do not turn weak evidence into strong conclusions. Mark uncertainty explicitly.
- **No blame reports.** Audit the process, gates, artifacts, and automation boundaries. Avoid personal fault language unless identity/permission evidence is materially relevant.
- **Preserve privacy.** Redact secrets, private keys, tokens, env values, and private message content not needed for the finding.
- **Layer feedback correctly.** Do not push a local project preference into COR unless it generalizes across projects. Do not hide a generic protocol flaw inside OCO or WUK if the evidence shows it belongs in COR.
- **Separate evidence from action.** The report may recommend a CHG/PRP/SOP amendment, but the amendment is a separate workflow.
- **Keep the sink passive.** A report sink that another automation or agent consumes to execute work is not L1; route that design through COR-1625 or higher.

### Conformance — how to verify the loop stayed L1

- Every capability the loop can exercise is read-scoped, except at most one narrowly scoped passive-sink writer.
- The only write is to the named passive report sink, and the sink is not consumed by automation.
- No source files, issues, PRs, deployments, labels, branches, tracked status fields, or queues were changed by the audit loop itself.
- Recommendations name target layers and workflows rather than executing them.
- Every blocking finding cites evidence or is marked as hypothesis.

---

## Relationship to the Loop Ladder

- **COR-1624 / L1:** This SOP defaults here. It observes and reports.
- **COR-1625 / L2:** Use when a recommendation becomes a concrete draft action and a human approves it.
- **COR-1626 / L3:** A PDCA audit may review an L3 loop's audit log, but it does not itself justify L3 promotion. L3 still requires COR-1626's full six-precondition envelope and recorded human enablement.
- **COR-1620 / pacing:** If the audit is repeated or scheduled, use COR-1620 pacing primitives to avoid noisy or overly frequent retrospective churn.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-06-21 | R2 review PASS: Claude 9.2/10 and Codex 9.3/10; polish Step 2 to say "at most one" passive-sink writer | Moth |
| 2026-06-21 | COR-1602 review fixes: make L1 conformance capability-based, remove PLN closeout as a passive sink, require human-read/non-automated sink, add accepted/rejected/watch-only finding states, and clarify that execution starts a separate L2 workflow | Moth |
| 2026-06-21 | Initial draft — PDCA report-only run audit loop for evidence-backed process feedback | Moth |
