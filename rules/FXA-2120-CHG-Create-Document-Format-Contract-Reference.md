# CHG-2120: Create Document Format Contract Reference

**Applies to:** FXA project
**Last updated:** 2026-03-20
**Last reviewed:** 2026-03-20
**Status:** Completed
**Date:** 2026-03-20
**Requested by:** Frank
**Priority:** High
**Change Type:** Normal
**Related:** FXA-2116, FXA-2119

---

## What

Create COR-0002-REF in PKG layer (`fx_alfred/src/fx_alfred/rules/`). This reference document defines the mandatory metadata format for all Alfred documents.

Contents:
- H1 format rules (`# <TYP>-<ACID>: <Title>`, ACID=0000 Index exempt)
- Metadata format rules (bold style, no list prefix, no annotations, field ordering)
- Required fields per document type (table)
- Allowed Status values per document type (table)
- Optional fields per document type (table)
- Change History section rules

**Note:** FXA-2119 PLN Decision #1 overrides FXA-2116 PRP regarding REF Status. The original PRP said REF has no Status; the confirmed decision gives REF the same Status values as SOP (Active / Draft / Deprecated).

### Optional Fields (confirmed)

The optional fields table extends beyond FXA-2116 PRP's original list. The additions (`Date`, `Requested by`, `Priority`, `Change Type`) were confirmed by Frank during COR-1602 review as CHG/INC-specific optional fields that reflect existing usage patterns.

| Field | Used by | Source |
|-------|---------|--------|
| Related | PRP, CHG, ADR | FXA-2116 PRP |
| Reviewed by | PRP, CHG | FXA-2116 PRP |
| Last executed | SOP | FXA-2116 PRP |
| Severity | INC | FXA-2116 PRP |
| Date | CHG, INC | COR-1602 review decision |
| Requested by | CHG | COR-1602 review decision |
| Priority | CHG | COR-1602 review decision |
| Change Type | CHG | COR-1602 review decision |

## Why

FXA-2116 (Document Format Contract) requires a single source of truth for document format rules. Without it, `af validate` has no codified spec to enforce, and `af create` templates have no contract to follow. This document is the foundation for CHG-2121, CHG-2122, and CHG-2123.

## Impact Analysis

- **Systems affected:** PKG layer (bundled rules), requires package rebuild to distribute
- **Rollback plan:** `git revert` the commit that adds the file + rebuild package

## Implementation Plan

1. Manually create `COR-0002-REF-Document-Format-Contract.md` in `fx_alfred/src/fx_alfred/rules/`
2. Content derived from FXA-2116 PRP Proposed Solution + FXA-2119 PLN confirmed decisions (including REF Status override)
3. Run existing test suite to verify no regression
4. Commit

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version | Claude Code |
| 2026-03-20 | Round 1 revision: added compliant metadata, H1 rules, optional fields table, REF Status override note, rollback detail | Claude Code |
| 2026-03-20 | Round 2 revision: added explicit authority for extended optional fields (COR-1602 review decision) | Claude Code |
