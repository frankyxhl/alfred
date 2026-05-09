# CHG-2278: Add FXA-2276 Invocation Shorthand

**Applies to:** FXA project
**Last updated:** 2026-05-09
**Last reviewed:** 2026-05-09
**Status:** Proposed
**Date:** 2026-05-09
**Requested by:** Frank (via session 2026-05-09)
**Priority:** Low
**Change Type:** Normal
**Targets:** FXA-2276

---

## What

Add a new top-level §Invocation section to FXA-2276 documenting three alfred-specific shorthand phrases the operator types in chat to start the COR-1617 multi-agent workflow loop with FXA-2276's parameters:

| Phrase | Behavior |
|---|---|
| `follow FXA-2276` | Continuation mode — pick lowest-rank-ID rocket-eligible issue, run phases 2–10, on merge re-enter phase 1 until queue idle |
| `follow FXA-2276 once` | Single pick, stop after phase 10 (no §11 wake) |
| `follow FXA-2276 for #N` | User-directed pick of issue #N, gate-bypass per COR-1618 §Bypass |

The phrases extend COR-1617 §1's User-driven trigger row's existing phrase list (`"pick next issue" / "do <PREFIX>-<NNNN>" / "auto-pick"`) with alfred-specific synonyms. They are not a new SOP — they are a project-specific synonym layer for the existing User-driven trigger pattern.

## Why

When the operator wants to invoke the COR-1617 loop with alfred's parameters, the canonical phrasing per COR-1617 §1 is one of `"pick next issue" / "do <PREFIX>-<NNNN>" / "auto-pick"`. These are generic. They do not signal *which* parameter set to load — alfred has FXA-2276; trinity has its own equivalent (TRN-1209 or similar); a third project would have a third REF.

Naming the alfred parameter set in the invocation phrase (`follow FXA-2276`) makes the parameter loading explicit and unambiguous. It also gives the orchestrator a single doc to load (FXA-2276) which contains both the parameter values *and* (post this CHG) the invocation semantics — one source of truth.

The variants `once` and `for #N` cover common operator intents: a single pick (no autonomous continuation) and a directed pick (specific issue), respectively. Both are user-driven trigger patterns per COR-1617 §1; the distinction is whether the orchestrator loops or stops.

## Impact Analysis

**Files changed**

- `rules/FXA-2276-REF-Multi-Agent-Loop-Configuration.md` — new §Invocation section between §Parameter Values and §Adoption Status by Phase; one new row in §Change History.

**Behavioural impact**

- Orchestrator recognizes `follow FXA-2276` (and the two variants) as User-driven trigger #1 mandates per COR-1617 §1.
- Existing canonical phrases (`"pick next issue"`, `"do <PREFIX>-<NNNN>"`, `"auto-pick"`) continue to work unchanged.
- No PKG SOP change. COR-1617, COR-1618, COR-1622 are untouched. Trinity's instantiation is untouched.

**Out of scope** (explicitly deferred)

- Promoting the invocation-shorthand pattern to PKG-layer COR-1617 (would require a separate CHG against the PKG cluster). Per-project synonyms should live at PRJ layer where the parameter values are.
- Other phrase variants beyond the three proposed (`per FXA-2276`, `loop FXA-2276`, etc.). If the operator finds the three insufficient, file a follow-up CHG.
- Stop-marker extensions (e.g. `cancel FXA-2276`) — COR-1620 §Primitive 2 already covers stop semantics via `stop` / `pause` / `hold`; no project-specific synonym needed yet.

## Implementation Plan

1. Add §Invocation section to FXA-2276 between §Parameter Values and §Adoption Status by Phase. Section contains: short intro paragraph, the three-row phrase table, and a closing paragraph noting how the phrases compose with COR-1620's stop-marker (`stop` / `pause` / `hold`) for early termination.
2. Add change-history row dated 2026-05-09 referencing FXA-2278.
3. Run `af validate --root .` to confirm no structural issues.
4. (Companion in same PR) Save a memory entry at `~/.claude/projects/-Users-frank-Projects-alfred/memory/feedback_alfred_loop_invocation_shorthand.md` so future sessions recognize the convention without re-deriving from FXA-2276 every time.
5. Open PR; codex bot review + trinity panel review (both per the standard COR-1617 §4 flow).

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-09 | Initial version — backfilled to retrofit PR #120 with proper Phase 3 (CHG sizing) per COR-1104. The PR's actual implementation landed first (orchestrator-direct, single-file edit); this CHG documents the spec retroactively per the FXA-2275 / PR #117 post-push precedent for trivial doc edits. | Claude Opus 4.7 |
