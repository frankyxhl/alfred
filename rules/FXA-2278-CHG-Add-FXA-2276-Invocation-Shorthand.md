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
| `follow FXA-2276` | Looping mode — initial pick is lowest-numbered RANK matching COR-1617 §1 scope-rank tree (RANK 1–4, smaller LoC tie-break), gate-bypassed per COR-1618 §Normative Bypass Clause; on merge re-enter phase 1 via §11 wake; subsequent picks re-apply COR-1618 verify_consent_eligibility in full until queue idle |
| `follow FXA-2276 once` | Single pick, same initial-pick rule, stop after phase 10 (no §11 wake) |
| `follow FXA-2276 for #N` | User-directed pick of issue #N, gate-bypass per COR-1618 §Normative Bypass Clause |

The three variants are mutually exclusive — `follow FXA-2276 once for #N` and other combinations are not defined per FXA-2276 §Invocation (operator picks one). For full semantics, including the looping-mode continuation gate behavior and stop-marker durability, see FXA-2276 §Invocation as the canonical reference (this CHG documents *what changed*; FXA-2276 §Invocation documents *how it works*).

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
| 2026-05-09 | Initial version — drafted retroactively to satisfy COR-1104 §3 documentation requirement for PR #120's §Invocation addition. **This is a procedural deviation from COR-1104**, not a sanctioned shortcut: COR-1104's flow is `Status: Proposed` → plan-review → implement, but PR #120's implementation landed first as orchestrator-direct (~17-line single-file edit, fits COR-1619 direct lane); the CHG is captured here to keep the project's spec record intact. The deviation is acknowledged openly rather than concealed. Future routine post-implementation CHGs (if they recur) would warrant a PKG-layer SOP codifying the pattern with explicit gates — out of scope for this CHG. | Claude Opus 4.7 |
| 2026-05-09 | R3 (PR #120 review): deepseek panel A3+A4 advisories — initial change-history row cited (1) "COR-1617 §3 shortcut for post-implementation drafting" which does not exist in the PKG SOP, and (2) "FXA-2275 / PR #117 post-push precedent" which is a one-time operator decision, not a documented rule. Both citations were aspirational/loose. Removed; replaced with explicit acknowledgement that this is a procedural deviation, not a precedent-backed shortcut. | Claude Opus 4.7 |
| 2026-05-09 | R4 (PR #120 review): codex bot R3 P2 + glm R3 cosmetic advisory (convergent) — FXA-2278 §What table (rows 21, 23) carried pre-R3 terminology (`Continuation mode`, `lowest-rank-ID`, `§Bypass`) while FXA-2276 had been corrected. Cross-doc-propagation drift class (same as PR #119 R2→R5). Fixed via comprehensive sweep this round, not one-at-a-time: §What table now uses corrected terminology (`Looping mode`, `lowest-numbered RANK + LoC tie-break`, `§Normative Bypass Clause`); composition-rule note added pointing readers at FXA-2276 §Invocation as canonical reference. | Claude Opus 4.7 |
