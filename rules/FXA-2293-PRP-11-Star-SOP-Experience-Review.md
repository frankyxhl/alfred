# PRP-2293: 11-Star SOP Experience Review

**Applies to:** FXA project
**Last updated:** 2026-05-17
**Last reviewed:** 2026-05-17
**Status:** Implemented

---

## What Is It?

A proposal to add an experience-design review lens for Alfred SOPs, inspired by Airbnb's "11-star experience" exercise. The lens imagines an impossible-ideal execution experience for a target SOP, then works backward to feasible 6–8 star improvements that reduce friction, clarify execution, and strengthen failure recovery.

This is **not** a proposal to implement an 11-star workflow. The 11-star step is a discovery tool; the deliverables it produces are ordinary inline-CHG edits routed through existing Alfred governance (`Evolve-SOP`, COR-1610 scoring, PRP/CHG lifecycle).

---

## Problem

Alfred's existing SOP evolution machinery — `Evolve-SOP`, COR-1800 evolution philosophy, COR-1610 code-review scoring, `af validate` — answers "is this SOP **structurally correct**?" and "is the candidate change **scored above threshold**?" Neither answers "**is this SOP comfortable to execute**?"

Empirical friction modes observed on Alfred SOPs that are structurally valid but operator/agent-hostile:

- SOP is executable but requires too much implicit context (agent must reconstruct the unstated invariant).
- First-step ambiguity — agent does not know where to enter.
- Failure recovery paths are unclear or missing.
- No worked examples / expected outputs / decision gates.
- Composability with `af plan`, task tags, routing is left to the reader.

These are real costs (every PR #164-style R-cascade has some component of "the SOP didn't tell me what good looks like"), but they don't surface in the current scoring rubrics because the rubrics are correctness-axis, not experience-axis.


## Scope

**In scope:**
- A review *method* (set of questions / a star-ladder exercise) that an author or reviewer can apply to a target SOP before proposing changes.
- Integration contract with `Evolve-SOP`: this method *produces candidates*; `Evolve-SOP` *scores and governs* them.
- A decision among Options A/B/C below.

**Out of scope (this PRP):**
- Creating any new CLI command (`af experience-review` etc.).
- Replacing or modifying `Evolve-SOP`'s scoring rubric.
- Promoting any of this to the COR (PKG) layer. Future-extension discussion only.
- Drafting the candidate SOP/REF documents themselves — that work follows the chosen option as inline CHGs.


## Proposed Solution

Three options. Decision is the primary deliverable of this PRP.

### Option A — Add new SOP + REF pair (the brief's original shape)

- New `FXA-22xx-REF-11-Star-Experience-Philosophy.md` (star ladder, principles).
- New `FXA-22xx-SOP-11-Star-SOP-Experience-Review.md` (6-phase review procedure: guard checks → identify journey → build ladder → work backward → score candidates → route outcome).
- Score rubric: friction reduction (25%) / failure recovery (20%) / actionability (20%) / composability (15%) / evidence (10%) / atomicity (10%).

**Pros:** Discoverable as a named workflow; clean separation from `Evolve-SOP`.
**Cons:** Adds two new docs and a new process surface. Risk of overlap with `Evolve-SOP` ("which one do I run?"). Increases agent decision burden — exactly the kind of meta-process accretion CLD-1800 compresses *away*.

### Option B — Fold into Evolve-SOP as a new scoring dimension or pre-step

- No new doc. Add an "Experience review" pre-candidate step in `Evolve-SOP` (or a new dimension in the existing rubric, e.g. "Execution comfort 15%").
- Star-ladder exercise becomes an optional method, documented inline.

**Pros:** No new surface; reuses existing governance. One front door for SOP improvement work.
**Cons:** Star-ladder method gets buried inside an unrelated scoring doc. Less discoverable; harder to invoke as a stand-alone exercise.

### Option C — Do nothing

Document this PRP as Rejected with rationale: existing `Evolve-SOP` + COR-1610 + retrospective loops are sufficient; experience-axis friction is already captured indirectly via reviewer R-cascades.

**Pros:** Zero new surface. Aligns with CLD-1800 compression-first philosophy.
**Cons:** Leaves the structural-vs-experience axis gap unaddressed. Future authors continue to ship SOPs that pass `af validate` but operators struggle to execute.


## Open Questions

1. **Which option?** Author leans toward Option B (fold-in) over Option A (new SOP pair) to avoid meta-process accretion, but the brief originally proposed Option A. Needs operator input.
2. **Is the experience-axis gap real and Alfred-local?** Brief cites general SOP-friction patterns. Need ≥ 1 concrete Alfred-local incident where the gap caused measurable cost (an R-cascade root-caused to "SOP didn't tell me what good looks like" rather than "code was wrong"). Without this, Option C is the COR-1800 / CLD-1800 default.
3. **Author-side or reviewer-side?** Brief frames it as both ("author or reviewer"). These have different SOP homes (COR-1501 author-side, COR-1506 reviewer-side). Probably should pick one for the first iteration.
4. **Relationship to #167** (COR-1501 §Quality Criteria, currently open)? #167 adds *author-side write-time targets* — overlaps Option B's "fold into Evolve-SOP". Worth resolving #167 first so this PRP can build on or supersede.
5. **Filename ACID for Option A docs**: PRP currently uses `FXA-22xx` placeholder. If Option A is selected, replace with concrete next-available ACIDs at CHG-draft time (per #167 §Quality Criteria target 4: spec fully pre-committed).

---

## Change History

| Date       | Change                                                                                                                                                      | By              |
|------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------|
| 2026-05-17 | Initial version — reshape ~/Downloads/20260517/alfred-11-star-sop-experience-review-issue.md from inline-CHG brief into PRP with Option A/B/C decision open | Claude Opus 4.7 |
| 2026-05-17 | issue #183: Option B selected and implemented — star-ladder folded into FXA-2148 §Phase 2 Step 8 with cascade-renumber Phase 3+ 8–29 → 9–30. PRP closed.    | Claude Opus 4.7 |
