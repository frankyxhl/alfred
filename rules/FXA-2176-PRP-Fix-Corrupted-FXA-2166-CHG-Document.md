# PRP-2176: Fix-Corrupted-FXA-2166-CHG-Document

**Applies to:** FXA project
**Last updated:** 2026-04-01
**Last reviewed:** 2026-04-01
**Status:** Approved

---

## What Is It?

Repair the corrupted CHG document FXA-2166 so it passes `af validate` and accurately records the change it describes.

---

## Problem

FXA-2166 (CHG: Extract Invoke Index Update Helper) has garbled body text: stray line numbers, incomplete step lists, duplicated "CHG FXA-2166)" fragments, and a missing Change History table. `af validate --json` reports: "Missing Change History table." The document cannot be used as a change record in its current state.

## Proposed Solution

Rewrite the body of FXA-2166 using content from its companion PRP (`rules/FXA-2165-PRP-Extract-Invoke-Index-Update-Helper.md`, readable via `af --root <project-root> read FXA-2165`) as the authoritative source of truth:

1. Reconstruct the "What" section from FXA-2165's description
2. Add "Why" section (deduplication rationale)
3. Add "Steps" section summarizing the 3-file change
4. Add the required Change History table
5. Preserve existing metadata (Status: Approved, Date, Requested by, Priority, Change Type)

**Files changed:** `rules/FXA-2166-CHG-Extract-Invoke-Index-Update-Helper.md` only.

**No code changes.** Document-only fix.

**No SOPs affected.** FXA-2166 is a CHG record, not referenced by any active SOP.

## Risk

- **Reconstructed content may not match original intent.** Mitigation: FXA-2165 (the companion PRP) contains the full specification; the CHG body is derived from it. Cross-check against the actual code changes if ambiguity arises.
- **Rollback:** Revert the single file to its previous (corrupted) state via `git checkout HEAD -- rules/FXA-2166-*.md`. The corrupted state is no worse than current.

## Open Questions

None.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-01 | Initial version | — |
| 2026-04-01 | R1: Add Risk section, explicit "No SOPs affected", full FXA-2165 path (Gemini feedback) | Claude Code |
