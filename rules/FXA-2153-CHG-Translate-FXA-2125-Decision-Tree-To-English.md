# CHG-2153: Translate FXA-2125 Decision Tree To English

**Applies to:** FXA project
**Last updated:** 2026-03-30
**Last reviewed:** 2026-03-30
**Status:** Completed
**Date:** 2026-03-30
**Requested by:** —
**Priority:** Medium
**Change Type:** Normal

---

## What

Translate the Chinese-language Project Decision Tree section in FXA-2125 (Workflow Routing PRJ) to English. Preserve structure, SOP references, command examples, and indentation.

## Why

COR-0002 Language section and COR-1401 Policy §1 both require all documents to be written in English. The decision tree is currently entirely in Chinese, which is a format contract violation. PRP FXA-2151 approved (Codex 9.5, Gemini 9.4).

## Impact Analysis

- **Systems affected:** FXA-2125 only
- **Rollback plan:** `git revert` the commit

## Implementation Plan

1. Translate all 9 Chinese decision-tree entries to English
2. Preserve SOP IDs, command literals, and tree structure
3. Run `af validate` to confirm 0 issues

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-30 | Initial version | — |
