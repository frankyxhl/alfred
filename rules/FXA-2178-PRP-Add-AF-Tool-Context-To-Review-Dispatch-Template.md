# PRP-2178: Add-AF-Tool-Context-To-Review-Dispatch-Template

**Applies to:** FXA project
**Last updated:** 2026-04-01
**Last reviewed:** 2026-04-01
**Status:** Approved

---

## What Is It?

Add `af` command usage instructions to FXA-2100's Review Prompt Template so that dispatched reviewers (Codex, Gemini) can find and read alfred_ops documents.

---

## Problem

When dispatching review tasks via `/trinity`, reviewer agents don't know how to use the `af` CLI. During the 2026-04-01 evolve-sop run, Gemini's agent reported FXA-2165 as "missing" because it searched the filesystem directly instead of using `af read FXA-2165`. This caused a false -2 deduction on Solution Completeness and -2 on Feasibility, dropping the PRP score below the pass threshold.

The current Review Prompt Template in FXA-2100 only says:
```
Read these source files: <file list>
```
It provides no guidance on project-specific tools needed to locate documents.

## Proposed Solution

Add a **conditional** "Tool Context" guidance note to FXA-2100's Review Prompt Template section. This is a template example, not a mandatory inclusion — the dispatcher (Leader) decides whether to include it based on the review target.

Append to the Review Prompt Template in FXA-2100:

```
[OPTIONAL — include when reviewing documents managed by project-specific tools]
[TOOL CONTEXT] This project uses the `af` CLI for document management:
- Read a document: af --root <project-root> read <ACID>
- List documents: af --root <project-root> list
- Validate documents: af --root <project-root> validate
Use these commands to locate referenced documents.
```

Add a note after the template: "When dispatching reviews for projects with specialized CLIs (e.g., `af` for alfred_ops), include a Tool Context block so reviewers can access referenced documents. Omit for pure code reviews where standard file reads suffice."

**Insertion semantics:** This is a template example showing the Leader how to provide tool context. It is NOT automatically appended to every dispatch. The Leader includes it when the review involves project-managed documents.

**How this reaches FXA-2148/FXA-2149 dispatches:** FXA-2100 is the canonical Review Prompt Template for the FXA project. The evolve SOPs (FXA-2148 Step 16, FXA-2149 equivalent) instruct the Leader to "dispatch via `/trinity`" but do not define their own prompt template — the Leader composes each dispatch prompt at runtime, referencing FXA-2100's template as the base. By adding Tool Context guidance to FXA-2100, the Leader gains awareness of when and how to include it in ALL dispatch types (code reviews, PRP reviews, CHG reviews). FXA-2148/2149 are in the prohibited mutation surface and cannot be edited; this approach works through Leader behavior, not SOP text.

**Files changed:** `rules/FXA-2100-SOP-Leader-Mediated-Development.md` only.

**No SOPs affected** besides FXA-2100 itself. FXA-2148 and FXA-2149 are explicitly out of scope (prohibited mutation surface per FXA-2146).

## Risk

- **False-positive guidance.** If the Tool Context block is included in dispatches for non-alfred_ops projects, reviewers may attempt to use `af` commands that don't apply. Mitigation: the block is marked `[OPTIONAL]` and the note explicitly says "omit for pure code reviews."
- **Omission by dispatcher.** If the Leader forgets to include the block, reviewers fall back to filesystem search (current behavior). This is a graceful degradation, not a failure.
- **Rollback.** Revert via `git checkout HEAD -- rules/FXA-2100-*.md`. No behavioral impact on existing workflows.

## Open Questions

None.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-01 | Initial version | — |
| 2026-04-01 | R1: Clarify conditional/optional semantics, add structured Risk section, define insertion semantics (Codex feedback) | Claude Code |
| 2026-04-01 | R2: Explain how template reaches FXA-2148/2149 dispatches via Leader behavior, note prohibited mutation surface (Codex R1 feedback) | Claude Code |
