# CHG-2180: Standardize-Role-Naming-In-FXA-2100

**Applies to:** FXA project
**Last updated:** 2026-04-01
**Last reviewed:** 2026-04-01
**Status:** Completed
**Date:** 2026-04-01
**Requested by:** Evolve-SOP (FXA-2175)
**Priority:** Low
**Change Type:** Normal

---

## What

Replaced "Droid" with "GLM" in FXA-2100 description, Roles table, and flow diagram. Role name "Coder" retained; provider now consistently "GLM" to match `/trinity glm` command syntax.

## Why

FXA-2100 used "Droid," "GLM," and "Coder" interchangeably for the same role, creating confusion. COR-1601 uses "Worker" as the generic; FXA-2100 specializes to "Coder" (role) + "GLM" (provider).

## Impact Analysis

- **Systems affected:** FXA-2100 only (terminology fix, no logic changes)
- **Rollback plan:** `git checkout HEAD -- rules/FXA-2100-*.md`

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-01 | Initial version | — |
