# CHG-2199: Implement COR 1800 REF Evolution Philosophy

**Applies to:** All projects using the COR document system
**Last updated:** 2026-04-04
**Last reviewed:** 2026-04-04
**Status:** Completed
**Date:** 2026-04-04
**Requested by:** Frank
**Priority:** Medium
**Change Type:** Normal
**Related:** FXA-2198 (PRP), FXA-2146 (PRJ evolution philosophy)

---

## What

Create `COR-1800-REF-Evolution-Philosophy.md` in the PKG layer (`src/fx_alfred/rules/`). This is a new universal reference document containing evolution principles, evaluation rubrics, thresholds, signal source catalog, guard rails, and COR-to-PRJ override contract. Content is defined in PRP FXA-2198.

## Why

The evolution methodology is currently locked inside FXA-specific documents (FXA-2146, FXA-2148, FXA-2149). Other projects cannot reuse the approach without copy-pasting. COR-1800 provides a shared foundation that any project can inherit and override.

## Impact Analysis

- **Systems affected:** PKG layer (bundled COR documents in `src/fx_alfred/rules/`)
- **Rollback plan:** `git revert` the commit that adds the file; no existing files are modified

## Implementation Plan

1. Create `src/fx_alfred/rules/COR-1800-REF-Evolution-Philosophy.md` with content per PRP FXA-2198:
   - Core Principle (Compression as Intelligence)
   - Evolution Cycle (universal, project-agnostic)
   - Evaluation Rubric (code evolution + document evolution default weights)
   - Thresholds (candidate discard < 7.0, review pass >= 9.0)
   - Signal Sources (reference catalog)
   - Guard Rails (prohibited mutation surface)
   - COR-to-PRJ Override Contract (full-replace per table semantics)
   - Relationship to Project SOPs (diagram)
2. Run `af validate --root .` to confirm document passes validation
3. Run `af read COR-1800` to confirm document is discoverable

## Testing / Verification

- `af validate --root .` reports 0 issues for COR-1800
- `af read COR-1800` returns the document content
- `af list --source pkg --type REF` includes COR-1800
- Document follows COR-0002 format contract (metadata, sections)

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-04 | Initial version based on PRP FXA-2198 | Claude Code |
