# SOP-1628: Sandboxed Worker CLI Dispatch

**Applies to:** All projects adopting COR-1617/COR-1619 whose `<worker-agent>` is an external one-shot CLI running in a sandbox (reference implementation: `codex exec`)
**Last updated:** 2026-07-03
**Last reviewed:** 2026-07-03
**Status:** Active
**Tags:** workflow
**Related:** COR-1619 (worker dispatch contract — this SOP specializes its WORKER leaves), COR-1622 (parameter schema — `<worker-agent>`, `<worker-min-loc>`, `<test-writer-worker-agent>`), COR-1500 (TDD protocol the task brief enforces), COR-1507 (two-worker TDD split), COR-1629 (loop-config starter template)
**Disposition:** optional-overlay

---

## What Is It?

The dispatch contract for implementation workers that run as **external one-shot CLI processes inside a sandbox** — no network, no session UI, one prompt in, one working tree + report out. The orchestrator drives the CLI directly from its own shell (no intermediary subagent), then independently verifies the result before anything touches git history.

This specializes COR-1619's Worker Dispatch Contract for the sandboxed-CLI case. COR-1619 decides *whether* to dispatch; this SOP defines *how* when the worker is a sandboxed CLI.

## Why

Validated on two dispatches (alfred #282 two-line fix, alfred #283 parser design work): both first-try correct, TDD-compliant with RED evidence, zero scope violations; the #283 diff scored 9.5/9.5/9.1 in triad review. Orchestrator-side token cost was roughly ⅕–⅓ of direct implementation.

Every observed failure was in the **orchestration layer**, not implementation quality — and each is mechanical to prevent (see §Failure Modes). Without this SOP each adopter rediscovers them one burned timeout at a time.

## When to Use

- COR-1619's decision tree routed to a WORKER leaf, and `<worker-agent>` is a sandboxed CLI
- The task is fully specifiable up front: named files, acceptance criteria, local verification commands
- The change exceeds `<worker-min-loc>` or carries a design decision worth an isolated implementer

## When NOT to Use

- COR-1619's orchestrator-direct leaves (O1–O4), e.g. trivial edits or generator re-runs — cheaper done directly
- Tasks that require network, git history mutation, GitHub state, or interactive input — the sandbox cannot do these and the worker must never try
- Review of the worker's own output (see Guard Rails)

## Invocation Contract

Six rules, each traced to an observed failure:

1. **Close stdin.** Append `</dev/null`. With inherited non-tty stdin the CLI blocks on "reading additional input" forever.
2. **Always run in the background** with output redirected to a log file. Foreground shells cap execution time below real task duration; the log file keeps the worker transcript out of the orchestrator's context. Read only the log tail.
3. **Pin the working directory** with the CLI's project-dir flag (`-C <repo>` for codex) and grant write access only to the working tree (`--sandbox workspace-write`).
4. **Scale reasoning effort to task class**: `medium` for mechanical fixes with named lines; `high` for anything with a design decision (this SOP deliberately normalizes to these two tiers even where the CLI offers more). Brief quality dominates the effort knob — invest in the brief first.
5. **Declare the sandbox scope in the brief** (see §Sandbox Scope Clause). Repo instruction files are written for networked orchestrators; a sandboxed worker following them stalls on unreachable services.
6. **The orchestrator owns everything outside the working tree**: commit, push, PR, CI polling, review dispatch, identity checks. The brief says "do NOT commit" and the worker leaves changes uncommitted.

Reference invocation (codex; flags verified on codex-cli 0.142.x — re-verify against your installed version):

```bash
codex exec --skip-git-repo-check --sandbox workspace-write \
  --ask-for-approval never -C <repo> \
  -m <model> -c model_reasoning_effort=<medium|high> \
  "$(cat brief.md)" </dev/null > worker-log.txt 2>&1 &
```

## Task Brief Template

Every brief carries these seven blocks; omitting one is the leading cause of scope drift or unusable reports.

```markdown
Fix <issue ref> in this repo (<one-line project description>). Work strict TDD:
write the failing tests FIRST, confirm RED, implement, confirm GREEN.

## The bug / the task
<precise description; name files and approximate lines>

## Required behavior (acceptance criteria)
<numbered, testable, lifted from the issue>

## Design guardrails
<the shape of the fix: data structures, attachment semantics, compatibility
requirements. Written after the orchestrator reads 50–100 lines of the target
code — this is what buys first-try success.>

## Out of scope
<adjacent defects by issue number, e.g. "the duplicate reorder loops are
issue #NNN's scope — do not consolidate them">

## Sandbox scope clause
<verbatim from §Sandbox Scope Clause below>

## Verification (run all; all must be clean)
<the project's full local gate: test suite, linter, formatter, type checker>

## Constraints
- Do NOT commit. Leave changes in the working tree.
- Match surrounding code style; no drive-by refactoring.
- Finish with a report: files changed, tests added, RED evidence (failing
  output before the fix), verification results, design decisions made.
```

## Sandbox Scope Clause

Paste into every brief:

> IGNORE any instruction in this repo's CLAUDE.md / AGENTS.md that requires
> network access or external services (multi-model review panels, `gh`,
> package publishing, agent-helper calls). You are a sandboxed implementation
> worker: your scope ends at the working tree plus the local verification
> commands listed above. Review and GitHub operations are the orchestrator's
> job.

Projects whose CLAUDE.md doubles as AGENTS.md (symlink) should also add a short "Sandboxed worker scope" section there saying the same thing — the brief clause protects orchestrated dispatches; the repo section protects manual ones.

## Orchestrator Verification (mandatory, after every dispatch)

Per COR-1619 §Verification, specialized:

1. **Scope check**: `git diff --stat` + read the full diff. Any file outside the brief's declared surface → reject or re-dispatch.
2. **Independent re-run** of the full local gate (never trust the worker's report alone).
3. **End-to-end reproduction**: re-run the original bug's reproduction; confirm the observable behavior changed.
4. Only then: commit (orchestrator is the author, identity per `<gh-write-identity>`, with the runtime's co-author convention), push, PR — per the project's COR-1622 instantiation (`<gh-write-identity>`, `<pr-push-remote>`).
5. Review panel dispatch per COR-1602/COR-1617 Phase 8 (>=3 independent providers, each >=`<panel-pass-threshold>`, no blocking findings) — never inside the worker sandbox.

## Failure Modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| CLI silent, "reading additional input from stdin" | inherited non-tty stdin | `</dev/null` (Invocation rule 1) |
| Run killed at shell timeout mid-task | foreground execution cap | background + log file (rule 2) |
| Background run stalls silently; log ends at a command the model wants to run | approval policy `on-request`/`untrusted` pauses for a confirmation no UI can deliver | pin `--ask-for-approval never` in the invocation |
| Worker wastes minutes on ConnectionRefused, retrying external services | repo instructions mandate networked steps | Sandbox Scope Clause in brief + repo section (rule 5) |
| Worker report claims green but diff touches undeclared files | brief lacked out-of-scope block | seven-block template; reject at scope check |
| Report unusable (no RED evidence, no file list) | brief lacked report format | Constraints block mandates report shape |
| Changes committed by worker with wrong identity | brief lacked "do NOT commit" | rule 6; orchestrator owns git |

## Guard Rails

- The worker never reviews its own output; panel review is dispatched to distinct providers by the orchestrator (author bias — same reason human authors don't approve their own PRs).
- A worker report is a claim, not a verification. Every dispatch ends with the orchestrator's independent gate re-run.
- When `<test-writer-worker-agent>` is set (COR-1507), the RED brief and GREEN brief go to distinct instances; the GREEN brief forbids editing tests.
- Provider quirks discovered during dispatch (degenerate responses, session bugs) belong in the project's calibration notes, not silently worked around.

## Examples

- alfred #282: two one-line output fixes + 2 regression tests, effort=medium, first-try, merged.
- alfred #283: metadata-block round-trip preservation (new dataclass field + render path), effort=high, design guardrails in brief, first-try, triad 9.5/9.5/9.1, zero blocking.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-07-03 | Initial version — promoted from alfred session practice (#282/#283 dispatches) | Claude Code |
