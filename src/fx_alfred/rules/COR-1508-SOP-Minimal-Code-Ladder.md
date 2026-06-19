# SOP-1508: Minimal Code Ladder

**Applies to:** All projects using the COR document system
**Last updated:** 2026-06-19
**Last reviewed:** 2026-06-19
**Status:** Active
**Related:** COR-1500 (TDD Development Workflow), COR-1800 (Evolution Philosophy), COR-1610 (Code Review Scoring), COR-1400 (Atomic SOP Principle)
**Disposition:** optional-overlay
**Workflow input:** task:routed
**Workflow output:** code:minimal
**Workflow provides:** minimal-code-ladder

---

## What Is It?

A write-time gate that runs **before and during** the implementation step of any coding task. It forces the agent to walk a fixed decision ladder — cheapest option first — so the default outcome is *less code*, not more. The principle: the code you never wrote has zero bugs and zero CVEs and scales infinitely.

It is the implementation-time counterpart of COR-1800 (Evolution Philosophy). COR-1800 compresses **structure** at evolve/audit time (`Fitness = same behavior / (LoC + doc words)`); this SOP compresses **new code** at the moment it is written. Same philosophy, different gate.

**Scope (one atom):** this SOP is solely the *write-time ordering gate* — the ranked "reach for the cheaper option first" procedure. It does not re-implement COR-1500 GREEN ("write the minimum code to pass"), COR-1610's Simplicity dimension (review-time scoring), or COR-1800's compression metric (evolve-time structure). It is the missing piece those three assume but none specify: the explicit order in which an agent rules out cheaper options before writing. COR-1500 is `inherit-only`; COR-1508 only *references* it (via `Related:`) and does not overlay it — `optional-overlay` here means projects may overlay COR-1508 itself (see Project Overlay).

Adapted from the open-source *Ponytail* ruleset (the "lazy senior developer" laziness ladder, https://github.com/DietrichGebert/ponytail), restated in COR terms and bound to the TDD workflow.

---

## Why

AI coding agents default to *adding* — a new helper, a new abstraction, a new dependency, a speculative config layer — because adding looks like progress. The cost lands later: every line is a line to test, secure, review, and maintain. COR-1800 already prunes this at evolve time, but pruning after the fact is more expensive than not writing the code. This SOP moves the compression decision to the cheapest possible moment: before the line exists. Making "reach for the cheaper option first" an explicit, ordered gate turns minimalism from a vibe into a checkable procedure.

---

## When to Use

- During the GREEN and REFACTOR phases of COR-1500 — every time the answer to "what code do I write?" is being decided.
- Before introducing a new abstraction, helper, dependency, config layer, or file.
- During code review (reviewer walks the ladder against the diff — see COR-1610 integration below).

## When NOT to Use

- For documents, SOPs, or non-code artefacts (those are governed by COR-1800 / COR-1400 atomicity).
- As an excuse to skip required safety work — see the Safety Floor below. Minimalism never overrides correctness, security, validation, error handling, accessibility, or tests.

---

## Steps

Walk these rungs **top to bottom** and stop at the first one that satisfies the requirement. Each rung must be ruled out before descending to the next.

1. **Does this need to exist?** Can the requirement be deleted, deferred, or satisfied by existing behavior? (YAGNI) If yes, stop — write nothing.
2. **Standard library.** Does the language's stdlib already do this? If yes, use it.
3. **Native platform / framework feature.** Does the runtime, framework, or platform already provide it? If yes, use it.
4. **Installed dependency.** Does a dependency already in the lockfile cover it? If yes, use it. No *new* dependency without ruling this out first.
5. **One line / one expression.** Can it be a single expression instead of a new function, class, or file? If yes, write the one line.
6. **Minimum viable build.** Only now: build the smallest thing that passes the test. No speculative generality, no "we might need it later."

A new abstraction, file, or dependency introduced without explicitly clearing the rungs above it is a ladder violation and must be justified in the PR body or removed.

---

## Intensity Posture

The agent declares the active posture at the start of the implementation step (per COR-1402): default **full**, unless the user authorizes **off** for the task (or a project overlay sets a different repo default — see Project Overlay). An explicit per-task user instruction takes precedence over an overlay default.

| Posture | Behavior |
|---------|----------|
| `full` *(default)* | Walk all 6 rungs. Any net-new abstraction, file, or dependency must be justified against the rung that was cleared to reach it. |
| `off` | Gate disabled. **User-authorized only** — an agent may not self-select `off`. Record the authorizing instruction in the task's working notes. |

A project overlay MAY re-introduce finer gradations (e.g. an advisory-only or a deletion-offset posture) if it demonstrates the need (see Project Overlay).

---

## Safety Floor (Hard, Non-Negotiable)

Minimalism is bounded. The ladder must **never** be used to drop:

- Input validation and boundary checks
- Error and failure handling
- Security controls (authz, authn, secret handling, injection defenses)
- Accessibility requirements
- The tests required by COR-1500

"Fewer lines" that removes any of the above is not minimalism — it is a defect. Reviewers reject it.

---

## Deferred-Simplification Debt

When the ladder finds a simplification that cannot be made safely *right now* (e.g. it would require a larger refactor out of scope), record it rather than silently keeping the bigger code: one line per deferral (`surface — what could be simpler — why deferred`) in the task's working notes, or as a CHG (COR-1101) when the simplification is a tracked structural change.

---

## Integration Points

- **COR-1500 (TDD):** this gate runs *inside* GREEN ("write the minimum code to pass") and REFACTOR (rung 1 re-check: does this still need to exist?). The ladder is how "minimum" is operationalized.
- **COR-1610 (Code Review Scoring):** the ladder *operationalizes* COR-1610's existing **Simplicity** dimension — it gives reviewers a concrete rule for scoring it: flag any new abstraction, file, or dependency that skipped a cheaper rung. It adds no new dimension; it makes the existing one checkable.
- **COR-1800 (Evolution Philosophy):** ladder violations that already shipped become signal sources for the evolve loop's Compression-ratio and Scope-restraint dimensions.

---

## Examples

**Task: "Add retry-with-backoff to the HTTP client."** (posture: `full`)

- Rung 1 — needed? The flaky endpoint is third-party and out of our control, so yes.
- Rung 2 — stdlib? No backoff in stdlib `http`.
- Rung 3 — framework? The client wraps `httpx`; check if it ships retries. It does not by default.
- Rung 4 — installed dependency? `tenacity` is already in the lockfile. ✅ **Stop here.** Decorate the call with `@tenacity.retry(...)` — three lines, no new code path, no new dependency.

A naive agent would have written a custom retry loop with sleep, jitter, and a max-attempts counter (~30 lines, its own bug surface). The ladder cut it to a decorator.

**Task: "Build a `UserProfileFormatterFactory` to render display names."** (posture: `full`)

- Rung 1 — needed? The requirement is "show `First Last`, falling back to email." A factory is speculative generality. ✅ **Stop at rung 1.** This is one expression: `f"{u.first} {u.last}".strip() or u.email`. Record nothing as debt — there was nothing to defer.

---

## Project Overlay (optional)

Projects MAY overlay this SOP (`**Overlays:** COR-1508`) to add substantive project-specific content, e.g.:

- The project's standard-library / framework catalog of "things you should reach for before writing" (rungs 2–3).
- The lockfile dependencies that count for rung 4.
- The default intensity posture for the repo.

A cosmetic restatement is not a valid overlay (per COR-0002 Disposition rules).

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-06-19 | Initial draft — adapts the Ponytail "laziness ladder" into a COR write-time gate bound to COR-1500; adds intensity postures, safety floor, deferred-debt log, and COR-1610/1800 integration points. | Claude Code |
| 2026-06-19 | COR-1600 review round 1 (2 reviewers, both FIX): added one-atom scope disclaimer + inherit-only clarification; moved COR-1500 to Related (no illegal overlay); reframed COR-1610 integration as operationalizing the existing Simplicity dimension; clarified `ultra` borrows COR-1800's metric (not the evolve gate); made `off` user-authorized-only; made posture resolution deterministic; defined "material" deferral + lite/off logging; dropped dangling COR-1207 relation. | Claude Code |
| 2026-06-19 | COR-1600 review round 2: both reviewers 9.0/10 PASS. Promoted Draft → Active. | Claude Code |
| 2026-06-19 | Trim per #218 (make the minimal-code SOP minimal): Intensity Posture reduced to `full` (default) + `off` (user-authorized) — removed `lite`/`ultra` and the posture-resolution prose, deferring gradations to a project overlay; Deferred-Simplification Debt compressed to one line (dropped the per-posture material-deferral protocol); Examples `ultra`→`full` to keep the posture reference valid. | Claude Code |
| 2026-06-19 | Trinity review round (DeepSeek 9.8, MiniMax 9.3, both PASS): adopted the shared advisory — co-located the overlay-default precedence pointer in the Intensity Posture paragraph. | Claude Code |
| 2026-06-19 | Per #221: added one clause stating an explicit per-task user instruction takes precedence over an overlay default (resolves the user-vs-overlay precedence gap without re-introducing the removed numbered resolution algorithm). | Claude Code |
| 2026-06-19 | Per #222: unified task-notes terminology — `off` row "task log" → "task's working notes" to match the Deferred-Simplification Debt section (no semantic change). | Claude Code |
