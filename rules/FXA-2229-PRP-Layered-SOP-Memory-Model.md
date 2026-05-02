# PRP-2229: Layered SOP Memory Model

**Applies to:** FXA project
**Last updated:** 2026-05-02
**Last reviewed:** 2026-04-29
**Status:** Draft
**Related:** OpenClaw memory lifecycle, Elliot Chen "State of AI Agent Memory 2026", Tim Kellogg "Agent Memory Patterns"

---

## What Is It?

This PRP proposes a layered SOP memory model for Alfred, inspired by
OpenClaw's memory lifecycle but adapted to Alfred's document-first
governance model.

The goal is not to copy OpenClaw's runtime memory subsystem. The useful idea
to borrow is the separation of memory by lifecycle and responsibility:
short-term working notes, deliberate consolidation, durable knowledge, and
explicit recall. In Alfred, those layers should map to existing document
types and CLI surfaces instead of becoming a hidden autonomous memory store.

---

## Problem

Alfred already has strong document types and governance, but its SOP context
model is still mostly organized by ownership and path:

- `PKG` for package defaults.
- `USR` for user-level preferences.
- `PRJ` for project-level context.

That separation is useful, but it does not fully answer a different question:
what lifecycle is this piece of context in?

Several existing documents already behave like memory layers:

- `COR-1201-SOP-Discussion-Tracking` captures in-session working memory.
- `COR-1200-SOP-Session-Retrospective` consolidates what happened in a
  session.
- ADR, REF, SOP, PRP, and CHG documents carry durable decisions, references,
  procedures, proposals, and implementation history.
- `af guide`, `af plan`, and `af search` expose pieces of recall.

The gap is that Alfred does not yet make this lifecycle explicit. As a result,
agents must infer when a session note should become durable knowledge, where a
repeated observation belongs, and which documents should be recalled before
work starts. This can lead to lost context, duplicated notes, overgrown SOPs,
or durable documents being updated without enough review.


## Scope

This proposal covers the design of the memory model and the SOP/CLI changes
needed to make it usable.

In scope:

- Define Alfred's memory layers and their responsibilities.
- Clarify the promotion path from short-term notes to durable documents.
- Update existing SOPs so discussion tracking, retrospectives, and routing
  share the same lifecycle vocabulary.
- Identify future CLI recall improvements that can be implemented in later
  changes.

Out of scope:

- Copying OpenClaw's runtime memory manager, background sync loop, subagent
  model, or vector database architecture.
- Adding hidden prompt injection or automatic unreviewed writes to long-term
  SOPs.
- Requiring embeddings or semantic search in the first implementation slice.
- Replacing Alfred's existing document types with a generic `MEMORY.md`.


## Proposed Solution

Adopt a layered memory model for Alfred's SOP system:

1. Core law

   Stable rules that constrain all work. This layer is represented by COR
   documents such as routing rules, document schemas, and session protocols.

2. User operating preferences

   User-level defaults and preferences. This layer is represented by USR
   documents and should be recalled when work depends on the user's standing
   preferences.

3. Project operating context

   Project-level routing, conventions, and background. This layer is
   represented by PRJ documents and project-specific REF/SOP documents.

4. Short-term working memory

   In-session facts, open decisions, hypotheses, and follow-ups. This layer is
   represented by the discussion tracker. It is useful context, not durable
   truth.

5. Consolidation

   End-of-session synthesis that decides what should be kept, discarded, or
   promoted. This layer is represented by the session retrospective.

6. Durable knowledge

   Reviewed knowledge that should survive future sessions. This layer splits
   into two sub-layers that have fundamentally different characteristics:
   static facts versus dynamic skills. Mixing them in a single retrieval or
   update strategy pollutes both — facts need correctness and discoverability;
   skills need currency and executability.

   6a. Knowledge — static facts

       Stable reference points, past decisions, and implementation records.
       These are facts that have been validated once and rarely change. Their
       value is accuracy and discoverability. They answer "what is true" and
       "what happened."

       - REF for stable reference knowledge.
       - ADR for accepted decisions.
       - CHG for completed implementation history.

   6b. Procedural — dynamic skills

       Repeatable workflows, design patterns, and execution manuals that
       agents follow and refine over time. These are not static text — they
       are validated execution flows whose value is in being current and
       actionable. They answer "how to do this" and "how this was done
       before."

       This sub-layer captures alternative alpha: execution norms and
       patterns that exist inside teams and projects but would never appear
       in public pre-training data. It is the hardest layer to build and the
       highest-value layer when built correctly.

       - SOP for repeatable procedure.
       - PRP for proposed work or design.

   The distinction matters for implementation: static knowledge can be
   aggressively compressed and retrieved via keyword or tag matching; dynamic
   skills need fresher updates, task-aware retrieval, and a feedback loop
   from execution results back into the procedure.

7. Recall surface

   Explicit tools that retrieve relevant context before or during work. Today
   this includes `af guide`, `af plan`, and `af search`. The first
   implementation slice (per § Decisions § "Implementation slice scope")
   adds **`af recall <task>`** as a skeleton command — see acceptance criteria
   for the three-section output contract. Ranked search and embedding-based
   retrieval remain deferred to later slices once the SOP semantics settle.

   Recall is not binary — different documents need different injection
   strategies. The recall surface should distinguish three injection classes:

   | Class | When | Examples |
   |-------|------|----------|
   | **Always-inject** | Every session, every task start | COR-1103 routing, active discussion tracker |
   | **On-demand** | Retrieved when the task or context matches | Project SOPs, REF docs, relevant CHG history |
   | **Never-inject** | Archived or explicitly excluded from prompt context | Deprecated documents, rejected PRPs, archived discussion trackers |

   COR's existing `Always included: true` metadata field is the starting
   point. A generalized `Recall` metadata field (`always | on-demand | never`)
   would let any document declare its injection class without hardcoding
   which specific documents get injected.

### Promotion Rules

Use a reviewed promotion path instead of automatic long-term memory writes:

- New observations start in the discussion tracker.
- Session-end synthesis happens in the retrospective.
- Durable facts → REF documents (static knowledge).
- Accepted design decisions → ADR documents (static knowledge).
- Completed implementation history → CHG documents (static knowledge).
- Repeated procedures → SOP documents (dynamic procedural).
- Proposed future work → PRP documents (dynamic procedural).
- Unresolved or weak observations stay in the tracker, an issue, or the next
  PRP until reviewed.

This keeps Alfred's memory auditable: every durable memory has a type, a file,
and a review path.

A cross-layer feedback loop is also in scope:

- A PRJ-layer SOP that proves repeatedly valuable across projects may be
  promoted to a COR SOP in the PKG layer. This captures alternative alpha
  that starts as project-specific procedure and matures into global
  governance.
- The reverse path does not apply: COR documents should not be automatically
  downgraded based on per-project usage patterns.

This feedback loop gives Alfred a mechanism for the PKG layer to learn from
PRJ layer experience — the COR layer is not permanently frozen but evolves
through deliberate, reviewed promotion of proven patterns.

### SOP Changes

Recommended document changes:

- Add `COR-1203-SOP-Promote-Session-Memory` to define the promotion workflow
  from tracker to retrospective to durable document.
- Add `COR-1204-REF-Memory-Layer-Model` as the canonical reference for the
  layer definitions.
- Update `COR-1103-SOP-Contextual-SOP-Routing` so routing chooses context by
  lifecycle as well as document scope.
- Update `COR-1200-SOP-Session-Retrospective` to include a promotion table
  that distinguishes knowledge types from procedural types:
  keep, discard, defer, promote to REF (static knowledge), promote to ADR
  (static knowledge), record as CHG (static knowledge), promote to SOP
  (dynamic procedural), promote to PRP (dynamic procedural).
- Update `COR-1201-SOP-Discussion-Tracking` to state that discussion items are
  short-term working memory and are not durable truth until promoted.

### CLI Direction

Initial implementation should remain simple and document-first:

- Keep current `af guide` and `af plan` behavior as the primary recall entry
  points.
- Ship a minimal **`af recall <task>`** command skeleton in the first
  implementation slice (per § Decisions § "Implementation slice scope"),
  reusing the existing tag-matching algorithm from `core/compose.py` —
  three output sections per acceptance criteria, no ranking, no embeddings.
  *(This supersedes the earlier draft wording that called `af recall`
  "later" — § Decisions promoted it into the first slice.)*
- Consider `af search --ranked` as a lower-risk intermediate step before
  semantic search.
- Treat embeddings or hybrid search as optional later infrastructure, not as a
  prerequisite for this design.

### Anti-Goals

This proposal intentionally avoids:

- Hidden memory injection.
- A single giant memory file.
- Automatic background edits to durable documents.
- Treating every session note as permanent knowledge.
- Making recall depend on a vector service before the governance model is
  clear.

### Acceptance Criteria

This proposal is complete when:

- Alfred has a canonical document describing the memory layers.
- Discussion tracking and retrospective SOPs use the layer vocabulary.
- The routing SOP explains how to recall context by lifecycle.
- There is a documented promotion path from session memory to durable
  ADR/REF/SOP/PRP/CHG documents.
- Any future CLI recall feature can be implemented against this model without
  redefining the governance rules.
- Schema introduces a `Recall` metadata field with values
  `always | on-demand | never`; `Always included: true` continues to work as
  a deprecated alias.
- An `af recall <task>` command exists (skeleton form) and returns three
  sections: (1) **always-inject documents** — full body rendered for direct
  prompt-context insertion; (2) **on-demand candidates** matched by
  tag/lifecycle — full body rendered; (3) **hidden (`never`-inject)
  entries** — listed by `PREFIX-ACID` and title only, with no body or
  metadata rendered (operator-visible diagnostic so the user can verify
  what was deliberately excluded from context, without that content
  contaminating the prompt). The third section's "omitted from output"
  refers to *bodies*, not the *list of names* — the diagnostic value of
  the never-inject section comes from the names being visible.
- `af validate` checks `Recall` field values and warns when `Recall` and
  `Always included` are both set with conflicting semantics.

---

## Decisions

The decisions below converge previously open questions on this PRP into
agreed outcomes. They constrain implementation. Items still requiring
discussion remain in `## Open Questions`.

### Implementation slice scope

First implementation slice = **Documents + Schema + `af recall` command
skeleton**.

- Documents: `COR-1203-SOP-Promote-Session-Memory`,
  `COR-1204-REF-Memory-Layer-Model`, updates to
  `COR-1103-SOP-Contextual-SOP-Routing`,
  `COR-1200-SOP-Session-Retrospective`, and
  `COR-1201-SOP-Discussion-Tracking`; plus a PRJ-side complementary REF for
  project-specific alpha.
- Schema: introduce `Recall: always | on-demand | never` metadata field.
- CLI: ship a minimal `af recall <task>` command skeleton with three output
  sections (always-inject / on-demand / hidden) using the existing
  tag-matching algorithm from `core/compose.py`. No ranking, no embeddings.

This converges the previously open question "Should the first implementation
slice be SOP-only, or should it also add a small `af recall` command?".

### `Recall` field replaces `Always included`

Introduce `Recall: always | on-demand | never` as the canonical metadata
field. Keep `Always included: true` as a **deprecated alias** for
`Recall: always` for at least one minor version (compatibility window).

- New documents must use `Recall`.
- `af fmt` writes `Recall`.
- `af validate` warns when both `Recall` and `Always included` are set with
  conflicting semantics.

This converges the previously open question "Should the `Always included: true`
metadata field be generalized into a `Recall` field…".

### COR-1204 placement

The canonical memory layer model lives in **both layers**:

- PKG: `COR-1204-REF-Memory-Layer-Model` carries the canonical layer
  architecture, lifecycle vocabulary, promotion rules, and recall injection
  classes.
- PRJ: project-side REF documents carry project-specific alpha — procedures
  and patterns that don't generalize to PKG.

The PRJ→COR feedback loop documented under "Promotion Rules" governs how
proven PRJ patterns get promoted to PKG.

This promotes the preliminary answer recorded against the original first
open question to a binding decision.

### Implementation Workflow

This PRP follows the standard meta-workflow:

`COR-1102 (PRP, current) → COR-1602 strict review (Codex + Gemini, both ≥ 9.0) → COR-1101 CHG → COR-1500 TDD per phase`

Implementation will be split into the following phases (detailed
decomposition belongs in the CHG, not in this PRP):

- Phase 0 — PRP cleanup
- Phase 1 — Documents (COR-1203, COR-1204, updates to
  COR-1103/1200/1201, PRJ REF)
- Phase 2 — Schema (`Recall` field, deprecation of `Always included`)
- Phase 3 — `af recall` command skeleton
- Phase 4 — Tests + integration


## Open Questions

- Should user preferences have their own explicit promotion path, separate
  from project memory?
- Should project summaries become a first-class REF type, or remain ordinary
  REF documents with tags?
- What minimum ranking behavior is good enough for recall before introducing
  embeddings or hybrid search?
- Should knowledge-type documents (REF, ADR, CHG) and procedural-type
  documents (SOP, PRP) use different retrieval strategies out of the box?
  Procedural documents are task-specific and need fresher updates; static
  knowledge is reference-oriented and benefits from aggressive caching.

---

## Change History

| Date       | Change                                                                                                                                                                                                                                                                                       | By                           |
|------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------|
| 2026-04-29 | Initial version | Codex |
| 2026-04-29 | Split Durable knowledge into 6a (static knowledge: REF/ADR/CHG) and 6b (dynamic procedural: SOP/PRP); added recall priority injection classes (always / on-demand / never); added PRJ→COR SOP promotion feedback loop; added two new Open Questions | Droid |
| 2026-05-01 | Converge 4 open questions into ## Decisions: scope = docs+schema+af recall skeleton; Recall field with Always included as deprecated alias; COR-1204 lives in PKG with PRJ-side REF complement; standard PRP→Review→CHG→TDD workflow. Add Recall and af recall items to Acceptance Criteria. | Droid (orchestrator) + Frank |
| 2026-05-02 | Address PR #82 Codex bot inline review (2 P2 blockings on commit d6536d1): (1) [L256] Acceptance criterion was internally contradictory: 'returns three sections' AND 'hidden entries omitted from output' — implementers cannot satisfy both. Disambiguated: third section lists hidden never-inject entries by PREFIX-ACID + title only (no body) — operator-visible diagnostic so user can verify what was deliberately excluded from context, without that content contaminating the prompt. The 'omitted from output' wording referred to bodies, not the list of names — clarified inline. (2) [L152, L222] Two stale 'later af recall' references in the body of the PRP (Recall surface section + CLI Direction section) directly contradicted the new Decisions section that promoted af recall into the first implementation slice. Same self-contradiction class Codex bot has reliably caught throughout the PRP-2230 amendment series. Both updated to reference Decisions section + clarify that ranking + embeddings remain deferred (not af recall itself). | Frank + Claude (PR #82 Codex bot review fix) |

---

## References

- Elliot Chen, "State of AI Agent Memory 2026" — X article (2026-04-29).
  Layered memory architecture: episodic, preference, agent memory (skills /
  procedural), multimodal. Distinction between static memory and dynamic
  skills as the foundational cut for agent memory design.
- Tim Kellogg, "Agent Memory Patterns" (2026-04-27).
  Three mutable memory types: files (hierarchical data), memory blocks
  (learnable system prompt), and skills (indexed files with progressive
  disclosure). Skills as experience cache.
