# SOP-1208: Session Startup Sanity Check

**Applies to:** All projects using the COR document system
**Last updated:** 2026-05-07
**Last reviewed:** 2026-05-07
**Status:** Active
**Related:** COR-1201 (Discussion Tracking — auto-incremented at startup), COR-1103 (Workflow Routing — runs after this SOP), COR-1402 (Declare Active Process — declares this SOP as the first action), COR-1200 (Session Retrospective — the paired session-end SOP)
**Inspired by:** Anthropic Engineering — *"Effective harnesses for long-running agents"* (2025-11-26), Principle #6 ("Ritualized Session Startup") + Principle #1 ("Specialized Initialization Phase"). Round 5 of the skills-absorption initiative.
**Disposition:** inherit-only

---

## What Is It?

A ~1-minute discipline executed at the start of every active session, **before** declaring an active SOP per COR-1402 or routing per COR-1103. The agent recovers working-tree state, verifies the codebase is in a known-good shape, and surfaces any anomaly that should change the operator's plan before a single token is spent on the planned task.

The check is cheap because each step is bounded:

- `pwd` + `git status` + `git log -5` ≈ 5 seconds
- Project smoke test (declared in CLAUDE.md — typically `pytest -q`, `ruff check`, or `af validate`) ≈ 30 seconds
- Reading today's Discussion Tracker per COR-1201 ≈ 30 seconds

Total ≤ 90 seconds. The cost of skipping it — building on a broken base, redoing what a prior session already shipped, or stacking edits on top of someone's uncommitted work — is hours.

## Why

Long-running agent work spans many sessions; each session resumes without short-term memory. Three failure modes recur and this SOP eliminates all three:

1. **Stale-state work.** The agent resumes where it *thinks* it left off, but a prior session shipped (or reverted) changes this agent does not know about. Result: redundant work, or worse, conflicting overlap that surfaces at commit time.
2. **Broken-base work.** The agent assumes the tree is healthy, but a previous failed merge or partial revert left tests red. Symptoms only surface late, costing a full diagnose loop (COR-1503) when an earlier 30-second check would have caught it.
3. **Uncommitted-overlay work.** Uncommitted changes from a prior session are still in the working tree. The agent edits files without knowing they are mid-edit and produces a chaotic diff that is hard to review or revert.

The startup ritual is also Anthropic's empirical finding: *"Established consistent debugging and orientation steps before productive work"* — they ship it as a top-tier principle for harnesses, not an optional polish.

## When to Use

- The first action of every active session, before COR-1402 declaration
- When resuming after a break ≥ 1 day, regardless of whether a session was technically left open
- When switching `--root` between projects within a single session — re-run for the new root, since state recovery is per-project
- After any external action that may have changed the working tree (CI run, another agent, manual edit, machine handoff)

## When NOT to Use

- Pure reading sessions with no planned code changes and no planned commits
- Sub-agents launched by a parent agent that has already completed the check
- Continuations where state was preserved < 5 minutes ago and no external action could have changed the tree

## Steps

1. **Orient.** Run `pwd`. Confirm the cwd matches the project root the operator intends. If the operator did not specify a project, ask before proceeding rather than guessing from `cd` history.

2. **Snapshot the working tree.** Run `git status --short --branch` (the `--branch` flag is required — plain `--short` omits branch info, defeating the third bullet below) and `git log --oneline -5`. Read both. Note three things:
   - Uncommitted files (staged + working tree) — what was left mid-edit
   - Most recent commits — what was just shipped, which determines what the next task can assume
   - Current branch — main? a feature branch? matches operator's intent?

3. **Run the project's smoke test.** Each project declares its smoke command in CLAUDE.md. Examples: a Python library may use `pytest -q`, a docs-only project may use `af validate`, a TS project may use `tsc --noEmit`. If CLAUDE.md does not declare one, ask the operator what the smoke is — do not invent one. Record the result (pass / fail / not-applicable) before continuing.

4. **Load the session tracker.** Per COR-1201, read today's Discussion Tracker. The tracker preserves cross-session context the agent's prompt does not — items the operator wanted carried forward, decisions made, blockers surfaced. Without this read, step 5's anomaly framing misses half the relevant context.

5. **Surface anomalies before declaring.** State each anomaly explicitly and stop until the operator acknowledges or directs action. Examples:
   - *"Uncommitted changes in `X.py` from a prior session — include in this work, revert, or leave alone?"*
   - *"Smoke test failing on `test_Y` — diagnose first via COR-1503, or accept and continue?"*
   - *"Currently on branch `feature-z`, expected `main` — confirm?"*
   - *"Tracker mentions an in-flight CHG-1234 expecting completion today — proceed with that, or override?"*

   The agent does NOT proceed past this step until anomalies are resolved or explicitly accepted. Resolution is recorded in the active session's Discussion Tracker entry per COR-1201.

6. **Declare the active process.** Only after anomalies are resolved or accepted, declare the next SOP per COR-1402 (typically COR-1103 routing leading to a task-specific SOP). The declaration line should briefly note the sanity-check outcome: *"Tree clean, tests green, no tracker blockers — declaring COR-1103."*

---

## Change History

| Date | Change | By |
|---|---|---|
| 2026-05-07 | Initial SOP, Round 5 of the skills-absorption initiative. Absorbed from Anthropic Engineering's *"Effective harnesses for long-running agents"* (Principles #1 + #6). Alfred-specific adaptations: smoke test is project-defined via CLAUDE.md rather than hardcoded; integration with COR-1201 (Discussion Tracking) for session-state recovery; explicit anomaly-surfacing step 5 with "stop until acknowledged" rule. | Claude Code (Opus 4.7) |
