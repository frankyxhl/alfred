# CHG-2327: COR-1615 Agent Execution Ladder

**Applies to:** FXA project
**Last updated:** 2026-08-16
**Last reviewed:** 2026-08-16
**Status:** Proposed
**Date:** 2026-08-16
**Requested by:** Frank Xu (session request: COR-1615 only followed when the operator manually reminds the agent, and the agent stops after one poll round instead of continuing the loop)
**Priority:** Medium
**Change Type:** Normal
**Targets:** src/fx_alfred/rules/COR-1615-SOP-GitHub-App-PR-Review-Bot-Loop.md, skills/alfred/alfred-contract.md, skills/alfred/claude/SKILL.md, skills/alfred/agents/AGENTS.md, skills/alfred/copilot/copilot-instructions.md

---

## What

Two portable fixes for the two observed COR-1615 failure modes, both layered so
every `af`-capable tool shares them (not only Claude Code):

1. **COR-1615 §Agent Execution (new section)** — translates the
   operator-centric "wait 3–5 minutes between polls" into an agent-executable
   capability ladder:
   - **Rung A** — harness has a wakeup/scheduler primitive: bind COR-1620
     (arm a wakeup after every push/trigger; prompt carries PR, headRefOid,
     re-entry step).
   - **Rung B** — harness can run shell: a bounded blocking wait script added
     to §Commands (poll inside one tool call; exit codes route to Step 8 /
     re-invoke / Step 1). Zero new code — inline in the SOP.
   - **Rung C** — neither: mandatory resumable handoff note (PR, headRefOid,
     pending request, re-entry step); silent turn-ending is a SOP violation.
   Plus a binding rule: an agent MUST NOT end its task while a review request
   for the current head is pending unless it satisfied A, B, or C.
   A second machine-readable back-edge (`poll-wait`, Step 8 → Step 6) makes
   the waiting loop parser-visible alongside the existing `restart-on-push`.

2. **skills/alfred contract trigger rule** — one new contract rule: after any
   `git push` to a branch with an open PR, or after creating a PR, the
   COR-1615 loop is active and the task must not be declared complete until
   its completion criteria are met (or a rung-C handoff is written). Synced
   into all three carriers per the FXA-2305 sentinel mechanism.

Out of scope (deliberately): renaming the SOP; new `af` subcommands;
harness-specific hooks (e.g. a Claude Code PostToolUse hook lives in the
operator's own config repo, not in fx-alfred); edits to COR-1620/1617.


## Why

Two failure modes observed across real PR sessions:

- **Activation** — COR-1615's trigger is a mid-task *event* (push / PR
  created), but SOP routing is pull-based at task start, so the doc is not in
  context at the moment it applies. The operator has been acting as a human
  reminder. The contract rule is the cross-tool "soft hook": it is loaded at
  session start by every carrier and fires on the event.
- **Persistence** — Step 6's "wait 3-5 minutes" is written for a human
  operator; an agent's turn ends and nothing re-invokes it, so it polls once
  and stops. The ladder gives every harness class an executable wait; the
  binding rule makes silent stopping a violation instead of a default.

COR-1620 was already designed for runtime substitution but COR-1615 never
bound to it; the `restart-on-push` back-edge (FXA-2324) made the push loop
parser-visible but gave the agent no mechanism to wait inside it.


## Impact Analysis

- **Systems affected:** one bundled PKG doc + the four skill-bundle files. No
  `af` code paths change; CLI behavior identical. `docs/` mirror regenerated.
- **Consumers:** all projects see the new section via `af read COR-1615`;
  tools with the skill bundle installed additionally get the event trigger.
  Machines with only `pip install fx-alfred` still get the full ladder
  (rung B is inline shell, zero dependencies).
- **Tests:** `tests/test_bundled_loop_declarations.py` pins loop signatures —
  the new `poll-wait` back-edge requires updating the COR-1615 pin (expected,
  guarded change). `tests/test_agent_skill_drift.py` forces carrier sync.
- **Rollback plan:** revert the commit; set this CHG to Rolled Back;
  regenerate `docs/` and `af index`.


## Implementation Plan

1. Edit COR-1615: metadata back-edge, §Agent Execution, §Commands wait
   script, Step 6 pointer, Operator Checklist line, Change History row.
2. Edit alfred-contract.md; sync sentinel regions in the three carriers.
3. Update loop-declaration pin for COR-1615; CHANGELOG Unreleased entry;
   regenerate `docs/` via `scripts/build_docs.py`.
4. Validate: full pytest, `af validate`, `af fmt --check` on touched docs,
   `af plan --graph COR-1615` visual check.
5. Trinity panel review (GLM + DeepSeek + MiniMax, all ≥ 9.0), then PR under
   the `ryosaeba1985` identity, closed out via the COR-1615 loop itself.

---

## Change History

| Date       | Change          | By          |
|------------|-----------------|-------------|
| 2026-08-16 | Initial version | Claude Code |
