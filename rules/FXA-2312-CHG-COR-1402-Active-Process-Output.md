# CHG-2312: COR-1402 Active Process Output

**Applies to:** FXA project
**Last updated:** 2026-06-26
**Last reviewed:** 2026-06-26
**Status:** Completed
**Related:** COR-1202, COR-1402, FXA-2102

---

## What Is It?

Make COR-1402 declarations a generated, visible output of Alfred plans so agents can start every user-visible task with an active-process line instead of relying on memory.

---

## Why

`COR-1402` already requires active-process declaration, and `COR-1202` already composes it into task plans as an always-included SOP. The weak spot was execution ergonomics: plan output told the operator to declare the active process, but did not provide a copyable declaration per phase. That left agents to remember and format the declaration manually, which is easy to skip in chat.

---

## Scope

- Update `af plan` text output to include an `Active Process — COR-1402` section with one copyable declaration per phase.
- Add `active_process` to `--todo --json` output.
- Tighten `COR-1402` so every user-visible task emits an active-process line, including no-formal-SOP quick tasks.
- Tighten `COR-1202` so executing a composed plan means emitting the generated COR-1402 declaration at task start and phase transitions.
- Add task tags to `FXA-2102` so release tasks can be composed by `COR-1202`.
- Harden `COR-1402` so the active-process declaration must be the first line of every chat/conversational reply, not only plan-driven phases.
- Add an `af guide` closing reminder so the routing output itself nudges agents to open every reply with a COR-1402 line.
- Wire the project `CLAUDE.md` Workflow section to require the first-line declaration.
- Align bundled active-instruction surfaces that cited the old COR-1402 cadence (af plan's LLM RULES block, COR-1616 Step 1, COR-1202 execute step, the skill bundle, af setup, COR-1103 cheat-sheet and Golden Rules, INIT.md bootstrap) to the first-line/every-reply rule — all shipped active-instruction surfaces that teach the cadence — packaged rules (incl. INIT.md), CLI output, and the repo skill bundle — are covered; historical PRP/CHG records and review-packs are intentionally left as-is.

- Reconcile the first-line mandate with SOPs that mandate a different opening (COR-1208 sanity-check, COR-1207 unfamiliarity statement) via a generic exception in COR-1402, cross-referenced from those SOPs. A repo sweep confirms no other SOP currently mandates a competing reply-opening. The restating surfaces (skill bundle, `CLAUDE.md`, `af setup`/`af guide`/plan RULES, INIT.md) intentionally defer to COR-1402 as the authority for this exception rather than duplicating it — they say "first line of every reply, per COR-1402", and the exception lives in the canonical SOP they point to.

Out of scope:

- Enforcing declarations in external chat surfaces.
- Creating a new runtime hook or bot.
- Releasing a new package version.


## Acceptance Criteria

- [x] `af plan <SOP> --todo` prints an `Active Process — COR-1402` section before the flat TODO.
- [x] `af plan <SOP> --todo --json` includes a structured `active_process` list.
- [x] `COR-1402` covers every user-visible task, not only tasks with a task-specific SOP.
- [x] `COR-1202` tells executors to emit the generated declaration at task start and phase transitions.
- [x] `af plan --task "release fx-alfred to pypi"` can resolve `FXA-2102` via task tags.
- [x] `COR-1402` mandates the active-process line as the first line of every chat reply.
- [x] `af guide` text output ends with a COR-1402 active-process reminder.


## Validation

- `uv run pytest tests/test_plan_cmd.py -q`
- `uv run af validate --root /Users/frank/Projects/alfred-1402-active-process-output`

## Change History

| Date       | Change                                                                                                       | By          |
|------------|--------------------------------------------------------------------------------------------------------------|-------------|
| 2026-06-26 | Initial CHG for generated COR-1402 output                                                                    | Claude Code |
| 2026-06-26 | Extend scope: chat-surface first-line mandate + `af guide` reminder + CLAUDE.md wiring                       | Claude Code |
| 2026-06-26 | Extend scope: align af plan RULES block + COR-1616/COR-1202 + skill bundle + af setup to every-reply cadence | Claude Code |
| 2026-06-26 | Add COR-1103 cheat-sheet/Golden-Rules alignment + exhaustiveness note                                        | Claude Code |
| 2026-06-26 | Add INIT.md bootstrap to aligned-surfaces list (Codex finding)                                               | Claude Code |
| 2026-06-26 | Add startup/zoom-out reconciliation exception.                                                               | Claude Code |
