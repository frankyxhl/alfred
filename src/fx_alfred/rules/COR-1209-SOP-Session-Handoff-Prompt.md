# SOP-1209: Session Handoff Prompt

**Applies to:** All projects using the COR document system
**Last updated:** 2026-07-04
**Last reviewed:** 2026-07-04
**Status:** Active
**Tags:** session
**Related:** COR-1208 (Session Startup Sanity Check — the receiving session's first action), COR-1200 (Session Retrospective — session-end reflection; a handoff is not a retrospective), COR-1202 (Compose Session Plan — the receiving session may re-plan from the handoff), COR-1402 (Declare Active Process — active SOPs must be named in the handoff), COR-1103 (Workflow Routing — the receiving session re-routes; the handoff names the routing entry point)
**Inspired by:** iterwheel/voyager session follow-up (PRs #230/#231, issue #227 handoff) — alfred issue #246
**Disposition:** inherit-only

---

## What Is It?

A discipline for producing a **copy-pasteable prompt** that transfers in-flight work to a new agent session — a fresh context window, a different runtime (Claude Code → Codex → droid), or a colleague's agent. The prompt is built from **freshly fetched state**, never from memory, and always names: the exact task, the active SOPs, the branch/PR state, the validation commands, and the explicit exclusions.

The output is one self-contained block of text. The receiving session should be able to start work after reading only that block plus running its own COR-1208 startup check — no archaeology through prior transcripts.

## Why

Ad-hoc handoff prompts fail in recurring ways, each observed in real sessions:

1. **Stale-memory state.** The prompt describes the branch/PR/issue as the writer *remembers* it, but a bot review landed, CI finished, or a PR merged since. The receiving session acts on fiction.
2. **Missing process context.** The prompt says *what* to do but not *under which SOPs* — the receiving session skips the review loop, pushes to the wrong branch, or opens a draft PR when the project requires ready-for-review.
3. **Scope bleed.** Adjacent issues/branches are in flight; without explicit do-not-touch exclusions the receiving session "helpfully" mixes them (the originating incident: issue #227 work almost absorbing #228).
4. **Vague continuation.** "Continue the work" forces the receiving session to reconstruct intent, burning context on archaeology and often reconstructing it wrong.
5. **Hidden identity/policy defaults.** GitHub write identity, PR draft policy, and merge authorization live in the operator's head or a config the new runtime does not load — public artifacts get created under the wrong account or policy.

## When to Use

- Work must continue in a **new session** (context exhausted, scheduled compaction, end of day with an in-flight task)
- Work moves to a **different runtime or model** that takes over session ownership (e.g. from one agent product to another) — a bounded one-deliverable dispatch to a worker CLI is a task brief instead (see When NOT to Use)
- A **long task splits** and a parallel session takes one lane
- The user explicitly asks for a handoff prompt

## When NOT to Use

- Session ends with **no in-flight work** — nothing to hand off; run COR-1200 (retrospective) if reflection is wanted
- The continuation happens in the **same session/context** — just keep working; a handoff prompt adds noise
- Delegating a **bounded subtask** to a worker agent — that is a task brief (see the project's worker-dispatch SOP, e.g. COR-1628), not a session handoff; a task brief scopes one deliverable, a handoff transfers session ownership
- As a substitute for durable state: anything that must survive **many** future sessions belongs in a document (rules/, tracker, issue body), not in a one-shot prompt

## Prerequisites

- Local checkout accessible (for fresh `git` state)
- GitHub CLI authenticated (for fresh issue/PR state) — if unavailable, the prompt must say its GitHub state is unverified
- The writer knows which SOPs are active (per COR-1402 declarations in the current session)

## Steps

1. **Confirm the target task and repository.** One sentence: what is being handed off, in which repo, and why the handoff is happening (context limit / runtime switch / task split). If more than one task is in flight, write one handoff per task — do not bundle.

2. **Fetch fresh local state — never quote from memory.**

   ```bash
   pwd
   git status --short --branch
   git log --oneline -5
   ```

   Record: current branch, ahead/behind counts, uncommitted files (and whether the receiving session may touch them), last commit SHA — and the current UTC timestamp (the template's "fetched" stamp; `date -u +%FT%TZ`).

3. **Fetch fresh GitHub state for every referenced artifact.**

   ```bash
   gh issue view <N> --json state,title
   gh pr view <N> --json state,mergeStateStatus,statusCheckRollup,reviewDecision
   ```

   Record: issue/PR numbers with their **current** states, CI status, unresolved review threads, and pending bot reviews. A handoff written between a push and its bot review must say so ("bot review on <SHA> still pending — wait for quiescence before merging").

4. **Name the active SOPs and overlays.** List every SOP the receiving session must operate under (routing entry point, review loop, TDD policy, worker-dispatch lanes), plus project overlays. Tell the receiving session to run the project router itself:

   ```bash
   af guide --root <project-root>
   ```

5. **State scope and exclusions explicitly.** Two lists:
   - **In scope:** the concrete next actions, in order, with their done-conditions.
   - **Do NOT touch:** adjacent issues, branches, files, or WIP owned by other sessions — each with one line of why. An exclusion the writer thinks is "obvious" is precisely the one to write down.

6. **List related files and validation commands.** The files the task actually touches (paths, not descriptions) and the exact commands that must pass before any commit/push (test suite, linter, type checker, `af validate`), copy-pasteable.

7. **State GitHub write identity and PR policy when any public write is possible.** Required account for public artifacts, draft vs ready-for-review policy, merge authorization (who may merge, and whether it is delegated), branch naming, and the review-loop expectations (which reviewers/bots must pass, quiescence rules).

8. **Assemble the prompt from the template below and hand it to the operator.** Do not paste it into the new session yourself unless asked — the operator may edit it first.

## Prompt Template

```text
## Handoff: <one-line task title>

**Repo:** <org/repo> at <absolute path> — branch `<branch>` (<ahead/behind>, last commit <SHA> "<subject>")
**Why this handoff:** <context limit | runtime switch | task split | operator request>

### Current state (fetched <UTC timestamp>)
- Issue #<N>: <state> — <title>
- PR #<N>: <state>, CI <status>, review <status>, unresolved threads: <n>
- Working tree: <clean | list uncommitted files + whether you may touch them>
- <any pending external event: bot review on <SHA>, CI run, deploy>
- Assumptions / unresolved blockers: <list, or "none">

### Process you must operate under
- Run the startup check (COR-1208) and `af guide --root <project-root>` first; declare your active SOP per COR-1402.
- Active SOPs for this task: <list, with one-line roles>
- Review loop: <reviewers/bots + pass thresholds + quiescence rules>

### Your task (in order)
1. <next concrete action + done-condition>
2. <...>

### Do NOT touch
- <issue/branch/file> — <why>

### Files
<paths>

### Validation before any commit
<exact commands>

### GitHub policy
- Public writes as <account>; verify with `gh auth status`.
- PRs: <draft|ready> by default; merge authorization: <who>.
```

## Anti-Patterns

| Anti-pattern | Why it fails | Instead |
|---|---|---|
| Memory-only summary | Branch/PR/issue state drifts the moment a bot or CI acts | Fetch with `git`/`gh` at write time; timestamp the fetch |
| Omitting branch or PR state | Receiving session works on main or re-opens shipped work | Always include Step 2 + Step 3 output |
| No do-not-touch list | Adjacent in-flight work gets absorbed or clobbered | Step 5 exclusions, each with a reason |
| Vague "continue where we left off" | Forces archaeology; intent gets reconstructed wrong | Ordered actions with done-conditions |
| Hidden PR/identity defaults | Wrong account or draft state on public artifacts | Step 7 policy block, always present when writes are possible |
| Bundling several tasks in one handoff | Receiving session interleaves them; scope bleed returns | One handoff per task |

## Relationship to the Session Lifecycle Family

- **COR-1208 (Startup Sanity Check)** is the *receiving* side: the new session still runs its own startup check — the handoff prompt tells it to, and never substitutes for it (state may have drifted between handoff and pickup).
- **COR-1200 (Session Retrospective)** is reflection on a *finished* session; a handoff transfers *unfinished* work. A session may end with both: a retrospective for what shipped, a handoff for what did not.
- **COR-1202 (Compose Session Plan)** may consume the handoff as input: the receiving session re-plans from the handoff's task list rather than inheriting the writer's plan blindly.

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-07-04 | Initial version (issue #246) | Claude Code |
