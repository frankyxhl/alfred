# SOP-1620: Self-Pacing Loop Primitives

**Applies to:** Claude-Code-runtime orchestrators adopting COR-1617; alternative runtimes substitute their own primitive
**Last updated:** 2026-05-17
**Last reviewed:** 2026-05-17
**Status:** Active
**Related:** COR-1617 (umbrella; uses these primitives in §1 idle-with-retry, §8 iterate, §10 merge-watch, §12 loop restart; §11 retrospective is synchronous — no primitive needed), COR-1622 (parameter schema — `<wakeup-tool>`, `<idle-cap>`, `<merge-watch-cap>`)

---

## What Is It?

The runtime primitives that let an orchestrator self-pace a long-running multi-phase loop without an external scheduler:

1. **Wakeup tool** — schedule a future re-entry of the orchestrator with a self-contained prompt.
2. **Stop-marker** — a durable filesystem signal that suppresses scheduled wakes until removed.
3. **Branch guard** — observable git state that distinguishes "loop continuing on watched branch" from "user has switched off to do something else."
4. **Stateless counter** — round count carried in the wake prompt itself, since wakes are self-contained turns with no external state.
5. **Status communication** — operator-visibility contract: every wake-arming pairs with a status surface. Runtime-independent — applies under ANY wakeup mechanism (Claude Code `ScheduleWakeup`, cron, lock file, etc.).

Primitives 1–4 are runtime-specific (factored out of COR-1617 so an alternative non-Claude-Code orchestrator can substitute equivalents — cron + lock file + branch check + counter-token-in-cron-arg — and reuse the rest of the cluster unchanged). **Primitive 5 is runtime-independent and binding regardless of substitution**: any consumer of any Primitive-1 substitute MUST satisfy Primitive 5 (status surface), or it is not a valid substitution.

---

## Why

Three failure modes when wakeup mechanics are improvised inline:

1. **Cache-miss thrash** — the prompt cache has a 5-minute TTL. Wakes at exactly 300 s are the worst-of-both: pay the cache miss without amortising it. Codifying cadence rules below prevents this drift.
2. **Wake-on-wrong-branch** — a wake fires while the user has switched off the watched branch to do something else; the wake auto-runs phase logic and stomps on in-flight work. The branch guard makes wakes idempotent against user state changes.
3. **Stop-instruction-arrives-after-arm** — the user types "stop" between an `arm wake` call and the wake firing. With no marker, the wake fires anyway. The stop-marker addresses this race.

---

## When to Use

- COR-1617 §1 idle-with-retry (no eligible candidate; arm a recheck wake).
- COR-1617 §8 iterate (post-R-push; arm a poll wake for CI + bot review).
- COR-1617 §10 merge-watch (PR mergeable; arm a watch wake until human merges).
- COR-1617 §12 loop restart (post-handoff; arm a 60 s wake to re-enter phase 1).

## When NOT to Use

- One-shot tasks that complete inside a single conversation turn.
- Active-polling situations where the next signal is seconds away — use a single longer wait inside the same turn rather than chaining short wakes.

---

## Primitive 1: Wakeup tool

The default `<wakeup-tool>` is Claude Code's `ScheduleWakeup`. It takes three parameters:

| Param | Purpose | Constraints |
|-------|---------|-------------|
| `delaySeconds` | When to wake up | runtime clamps to `[60, 3600]` |
| `prompt` | What to fire on wake-up — usually a poll instruction referencing the just-pushed head SHA, R-number, idle-counter, or merge-watch-counter | self-contained (the wakeup is a fresh turn) |
| `reason` | One-sentence telemetry shown to the user | be specific: e.g. `Poll PR #<N> R<m> bot review on head <sha>` |

**MUST-DO after every R-push** — call the wakeup tool immediately. Forgetting is a real SOP violation: the orchestrator goes idle and bot/CI signals accumulate unobserved. The only exceptions are (a) the user just instructed something else, OR (b) the PR is already mergeable and the orchestrator is handing off.

The `prompt` MUST include enough context for the woken orchestrator to act without re-deriving:

1. PR number + R-number + head SHA (so the woken turn knows what to check).
2. Summary of what this R fixed (so the woken turn can spot regressions).
3. Trigger pattern context — continuation vs loop-driven (per COR-1617 §1).
4. The applicable counter token (idle-wake, merge-watch — see Primitive 4).

---

## Primitive 2: Stop-marker

A durable filesystem signal that suppresses every scheduled wake until removed.

**Location**: `$(git rev-parse --git-path trinity-loop-stopped)` — inside the git object store, worktree-compatible (in linked worktrees `.git` is a file, not a directory; `git rev-parse --git-path` resolves correctly in all cases). No `.gitignore` entry needed; the path is inside `.git/`.

**Set**: when the user types `stop`, `pause`, `hold`, or any explicit halt instruction in chat. The orchestrator MUST: (1) NOT arm the next wake, AND (2) `touch "$(git rev-parse --git-path trinity-loop-stopped)"`.

**Check** (every wake's `prompt=` MUST include this guard FIRST, before any other logic):

```
FIRST: if -e $(git rev-parse --git-path trinity-loop-stopped),
       wake is no-op (user has stopped the loop;
       do NOT enter phase 1 or arm next wake).
```

**Remove**: orchestrator removes on receiving a fresh user instruction that resumes the loop (`/loop` invocation, a new pick directive, explicit "resume"); OR the operator removes manually with `rm "$(git rev-parse --git-path trinity-loop-stopped)"`.

The marker addresses the case where a previously-armed wake is still pending when the stop instruction arrives — that wake will fire later, but the marker is a durable signal it can inspect.

---

## Primitive 3: Branch guard

The wake's `prompt=` MUST include a SECOND guard (after the stop-marker check) that compares current branch against the expected branch:

- For idle-with-retry and loop-restart wakes: expected branch is `main`.
- For merge-watch wakes: expected branch is the watched-PR branch, embedded as a token in the prompt at arm time (e.g. `merge-watch wake N of <merge-watch-cap> for branch <BRANCH_NAME>`).

```
SECOND: run `git rev-parse --abbrev-ref HEAD`. If not <expected>,
        a user-directed pick intervened — wake is no-op.
        Do NOT auto-switch-and-pull.
```

The operator decides when to resume; the wake never overrides in-flight user work.

---

## Primitive 4: Stateless counter

Wakes are self-contained turns; there is no external state between them. The counter is therefore embedded **in the wake prompt itself** at arm time.

| Loop | Token format | Cap |
|------|--------------|-----|
| Idle-with-retry | `idle wake N of <idle-cap>` | `<idle-cap>` (default 12 → 6 h @ 1800 s) |
| Merge-watch | `merge-watch wake N of <merge-watch-cap> for branch <BRANCH_NAME>` | `<merge-watch-cap>` (default 24 → 12 h @ 1800 s) |
| Retrospective | (synchronous — no counter; runs in same turn as Phase 10 cleanup) | — |
| Loop restart | (no counter — single fire post-handoff) | — |

**On wake**, the orchestrator reads N from the prompt. If N == cap, fire the stop condition (surface to user, do NOT arm next wake). If N < cap, arm the next wake with `prompt=` containing `... wake <N+1> of cap`. A successful eligible candidate (idle) or merge-detected (merge-watch) resets the counter — next idle/merge-watch starts again at 1.

---

## Primitive 5: Status communication

Every wake-arming MUST be paired with a status surface — either an in-chat message to the operator, a PR comment, or both. Silent wake-and-yield is forbidden.

**Required elements** per wake-arming:

1. **What just happened** — the R-round / fix / observation that triggered this wake.
2. **What the wake will check** — concrete predicate (e.g. "CI status + codex review on commit `<sha>`").
3. **Counter state** — declare every counter that applies in the current wake context, or `n/a` if none apply. The applicable counters depend on wake type per Primitive 4: §Phase 8 per-R-push reports R-count; idle-with-retry reports `idle wake N of <idle-cap>` only (no R-count); merge-watch reports `merge-watch N of <merge-watch-cap> for branch <BRANCH_NAME>` only; loop-restart reports `n/a` (single fire post-handoff, no counter per Primitive 4). Reporting a counter that the wake type doesn't have is itself a Primitive 5 violation.

**Forbidden anti-pattern — "silent wake-and-yield"**: arming a `<wakeup-tool>` callback and ending the orchestrator turn with no chat message and no PR comment. The operator then cannot distinguish "still iterating" from "stalled" from "crashed" until the wake fires (up to 270 s later — past the prompt-cache TTL).

**Why this is a primitive, not a soft convention**: in cache-warm windows (≤ 270 s wakes) the next bot/CI signal often arrives *before* the wake fires, so silent yield trades operator visibility for a few saved tokens — a bad ratio. In longer wakes (idle 1800 s, merge-watch 1800 s) the silence is even more confusing.

This primitive binds every consumer of COR-1620 wake mechanics — §Phase 1 idle-with-retry (COR-1617), §Phase 8 per-R-push, §Phase 10 merge-watch, §Phase 12 loop-restart.

---

## Cadence rules

| Situation | Cadence |
|-----------|---------|
| Active polling on a freshly-pushed HEAD (CI + bot + panel) | **270 s** — stays inside 5-minute prompt-cache TTL |
| Hard minimum | **60 s** — runtime rate-limits below this; no signal benefit |
| Forbidden | **300 s exact** — cache-miss boundary; pay the miss without amortising |
| Long-running CI or panel review (> 5 min) | **1200–1800 s** — pay one cache miss, get a longer wait |
| No work pending (idle-with-retry, merge-watch) | **1800–3600 s** — don't burn ticks on nothing |
| Post-handoff loop-restart | **60 s** — captures the burst window where operator may signal a queued issue immediately after merge |

**Anti-pattern — chained short sleeps**: `<wakeup-tool>(60); <wakeup-tool>(60); ...` is detected and clamped/blocked by the runtime. Use a single longer delay.

---

## Stop / failure conditions

Five conditions terminate or pause the loop:

**(a) Wakeup tool failure** (runtime unavailable, schema rejection, ≥3 consecutive arm failures): fall back to manual operator re-run. Surface: "Idle wake could not be armed; please re-trigger phase 1 manually when ready." The "≥3 consecutive arm failures" check is **synchronous** — count arm-call failures within the same session; no external counter needed because the failure occurs during the arming call itself.

**(b) Max-consecutive-idle stop**: at `<idle-cap>` consecutive idle wakes, surface: "Loop has been idle for <idle-cap × cadence>; pausing. Signal an issue or instruct phase 1 manually to resume." Counter mechanism per Primitive 4.

**(c) User stop chat input**: per Primitive 2.

**(d) Session termination**: wakeup jobs die with the orchestrator session. After session restart, the operator re-invokes phase 1 manually.

**(e) Cron + idle-retry concurrency**: if both an external cron AND idle-with-retry are armed simultaneously, both can fire phase 1 within the same minute. Coordination relies on COR-1617's claim-comment debounce — no new mechanism needed.

**(f) Active-work cancellation for merge-watch**: per Primitive 3 — branch mismatch makes the wake a no-op without auto-switch.

---

## Sample wake prompt (post-R-push)

```
ScheduleWakeup(
  delaySeconds=270,
  reason="Poll PR #<N> R<m> bot review on head <sha>",
  prompt="PR #<N> R<m> head <sha> poll. R<m> fixed <one-line summary>.
          FIRST: if -e $(git rev-parse --git-path trinity-loop-stopped),
                 wake is no-op (user has stopped the loop).
          SECOND: run git rev-parse --abbrev-ref HEAD; if not the
                  expected PR branch, wake is no-op.
          THIRD: check (1) new bot comments/reviews on <sha> across all
                 three endpoints (per COR-1615), (2) PR mergeable status,
                 (3) bot 👍 reaction. If new findings, fix per COR-1621.
                 If clean, hand off to user for merge.
          Trigger pattern: continuation."
)
```

---

## Guard Rails

- Never sleep > 270 s when cache is warm and you're actively polling. The 5-minute cache TTL is a real cost.
- Never use 300 s exactly. Pick 270 s (cache-warm) or ≥ 1200 s (one-miss-amortised).
- Never arm a wake without the FIRST stop-marker guard and SECOND branch guard in the prompt.
- Never run a counter externally. Counters live in the wake prompt; otherwise wake-state is lost across the runtime boundary.
- Never auto-switch-and-pull on wake when the branch guard mismatches. Operator decides resume.
- Never end a turn with a wake armed and no status surfaced. Silent wake-and-yield is a Primitive 5 violation.

---

## Substituting an alternative runtime

A non-Claude-Code orchestrator MAY substitute the four primitives with equivalents and reuse COR-1617 unchanged:

| Primitive | Claude Code default | Possible alternative |
|-----------|---------------------|----------------------|
| Wakeup tool | `ScheduleWakeup` | cron + sentinel file polled by a long-running process |
| Stop-marker | `.git/trinity-loop-stopped` | same path, or `/var/lock/<project>-stopped` |
| Branch guard | `git rev-parse --abbrev-ref HEAD` | same |
| Stateless counter | wake prompt embedding | crontab tag + small state file under `.git/` |

Set `<wakeup-tool>` in the project's COR-1622 instantiation accordingly.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-09 | Initial version — extracted from TRN-1008 §1 idle-with-retry / §8 / §10 / §11 + §Failure Modes (a)–(f) for COR-1617 cluster promotion (alfred#115) | Claude Opus 4.7 |
| 2026-05-10 | FXA-2283: §When to Use — §11 loop restart → §12 loop restart; Related metadata — add §11 retrospective (synchronous); §Primitives table — add Retrospective row (synchronous, no counter) | Claude Code |
| 2026-05-17 | issue #165: add §Primitive 5 (Status communication contract) — forbid silent wake-and-yield. Every wake-arming MUST pair with a status surface (chat update or PR comment) covering (a) what just happened, (b) what the wake will check, (c) counter state. Binds every consumer of COR-1620 wake mechanics. New §Guard Rails bullet enforces. | Claude Opus 4.7 |
| 2026-05-17 | issue #165 R2 (PR #182 codex bot P2): R1 wording "R-count and any wake-counter" was over-prescriptive — idle-with-retry has no R-round (no PR) and loop-restart has no counter per Primitive 4, so demanding R-count for those wake types creates impossible requirements. Fix: Counter-state element now context-specific — declare every counter that applies, or `n/a` if none apply; per-wake-type mapping spelled out (Phase 8 → R-count; idle → idle-wake-counter; merge-watch → merge-watch-counter + branch; loop-restart → n/a). Reporting a counter the wake type doesn't have is itself a violation. | Claude Opus 4.7 |
| 2026-05-17 | issue #165 R3 (PR #182 codex bot P2): §What Is It? overview only enumerated Primitives 1–4, and the runtime-substitution sentence said an alternative non-Claude-Code orchestrator can substitute "the primitives" — mechanical follower could omit Primitive 5 (status communication) entirely when substituting cron + lock file + branch check. Fix: overview now lists 5 primitives; substitution paragraph explicitly marks Primitives 1–4 as runtime-specific and **Primitive 5 as runtime-independent / binding regardless of substitution** — any consumer of any Primitive-1 substitute MUST satisfy Primitive 5 (status surface) or it is not a valid substitution. | Claude Opus 4.7 |
