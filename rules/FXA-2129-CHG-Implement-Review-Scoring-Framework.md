# CHG-2129: Implement Review Scoring Framework

**Applies to:** FXA project
**Last updated:** 2026-03-20
**Last reviewed:** 2026-03-20
**Status:** Completed
**Date:** 2026-03-20
**Requested by:** Frank
**Priority:** High
**Change Type:** Normal
**Related:** ALF-2208, COR-1602, COR-1102, COR-1103

---

## What

Create 4 new COR-level SOPs and update 3 existing ones per ALF-2208 PRP:

1. Create COR-1608-SOP-PRP-Review-Scoring.md
2. Create COR-1609-SOP-CHG-Review-Scoring.md
3. Create COR-1610-SOP-Code-Review-Scoring.md
4. Create COR-1611-SOP-Reviewer-Calibration-Guide.md
5. Update COR-1602: replace scoring section with rubric references
6. Update COR-1102: add OQ hard gate + fix stale matrix reference
7. Update COR-1103: add scoring rubric to OVERLAYS

## Why

Review quality is inconsistent — Gemini inflates scores, Codex uses different dimensions each time. Standardized rubrics per artifact type + shared calibration guide ensures reproducible reviews.

## Impact Analysis

- **Systems affected:** PKG layer (7 COR documents), requires package rebuild
- **Rollback plan:** `git revert` + rebuild

## Implementation Plan

1. Create COR-1608, COR-1609, COR-1610, COR-1611 in PKG rules
2. Update COR-1602 scoring section
3. Update COR-1102 OQ hard gate + stale reference
4. Update COR-1103 OVERLAYS
5. Run `af validate` — 0 issues
6. Commit + push + release

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version, pre-approved (PRP already passed COR-1602 strict) | Claude Code |
