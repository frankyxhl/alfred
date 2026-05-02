# CHG-2232: Subsection Guard Symmetry in COR-1612 Step 6

**Applies to:** FXA project
**Last updated:** 2026-05-03
**Last reviewed:** 2026-05-03
**Status:** Proposed
**Date:** 2026-05-03
**Requested by:** Frank Xu (deferred from PR #85, trinity 4-reviewer 3:1 MERGE-AS-IS vote)
**Priority:** Low
**Change Type:** Normal
**Targets:** COR-1612 §Step 6 stop-condition #1 example block

---

## What

Audit the §Step 6 stop-condition #1 example block in COR-1612 (currently 130+ lines under one ` ```bash ``` ` fence) and decide, **for each named sub-block**, whether it should be:

- **A) Standalone-copyable** — re-declare every required `${VAR:?...}` guard at the top of the sub-block, mirroring the `PR_OWNER` / `PR_NUM` pattern that already exists in the unified-filter sub-block.
- **B) Parent-fence-dependent** — leave guards unduplicated, but add an explicit prose note above the sub-block listing the variables it inherits and the line where they're declared.

Currently the file mixes both implicitly: the unified-filter sub-block re-declares `PR_OWNER` / `PR_NUM` (looks standalone-copyable) but leaves `OWNER` / `REPO` / `LAST_PUSH_TS` unguarded (relies on parent fence). Bot finding #3177031936 on PR #85 flagged the asymmetry.

## Why

GLM's insight from the PR #85 trinity vote (decisive in the 3:1 MERGE-AS-IS outcome): the unified-filter sub-block already references `$LAST_PUSH_TS` — a variable computed ~100 lines earlier in the same fence. So the sub-block is **already not standalone-copyable**. Re-guarding `OWNER` / `REPO` would create false independence symmetry — suggesting the block stands alone when it actually doesn't (it depends on `$LAST_PUSH_TS` either way).

The right fix is to decide intent **per sub-block**, not blanket-add guards. Otherwise every future bot iteration finds another asymmetry to flag.

Sub-blocks currently in the §Step 6 stop-cond #1 example fence:

1. **Timestamp computation** (top of fence) — declares `OWNER` / `REPO`, computes `HEAD_SHA`, `TOTAL_RUNS`, `LAST_PUSH_TS`. Standalone-copyable.
2. **Truncation pre-check** — depends on `OWNER` / `REPO` / `HEAD_SHA`. Could be either; currently relies on parent fence.
3. **Paginate fallback** — depends on `OWNER` / `REPO` / `HEAD_SHA` / `TOTAL_RUNS`. Currently parent-fence-dependent.
4. **Commit-time fallback** — depends on `LAST_PUSH_TS` / `HEAD_SHA`. Parent-fence-dependent.
5. **Unified-filter** — re-declares `PR_OWNER` / `PR_NUM` / `REPLY_ACTORS`; uses `OWNER` / `REPO` / `PR_NUM` / `LAST_PUSH_TS`. Asymmetric: half guarded, half not. **The bot finding's locus.**

## Impact Analysis

- **Systems affected:** `src/fx_alfred/rules/COR-1612-SOP-Respond-To-PR-Review-Comments.md` (single PKG-layer file)
- **Estimated diff:** ~10-20 lines net (depends on which sub-blocks are made standalone-copyable vs annotated)
- **No logic changes:** pure documentation harmonization
- **Rollback plan:** revert the single commit; no migration / no consumer impact (PKG doc consumers re-pull on fx-alfred upgrade)

## Implementation Plan

1. **Per sub-block decision:** review the 5 sub-blocks listed in §Why and assign each to category (A) standalone-copyable or (B) parent-fence-dependent.
2. **For (A) sub-blocks:** add `${VAR:?...}` guards at the top of the sub-block for every variable referenced.
3. **For (B) sub-blocks:** add a prose note above the bash fence — e.g. *"Continuation of §Step 6 stop-cond #1 example. Inherits `OWNER`, `REPO`, `HEAD_SHA`, `LAST_PUSH_TS` from the timestamp-computation sub-block above (line N)."*
4. **Run `bash -n` sweep** on all fenced bash blocks after edit (consistent with §Step 8 mandate).
5. **Local strict-shell test** of each (A) sub-block standalone with `set -euo pipefail` and unset vars to confirm guards fire.
6. **Trinity multi-model panel** review on the resulting diff. This is a meta-question about which sub-blocks are independent units; panel judgment is more useful than further bot-loop iteration.

## Approval

- [ ] Approved by: <reviewer> on <date>

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-03 | Initial version — deferred from PR #85 trinity 3:1 vote (Codex/Gemini/GLM MERGE-AS-IS, DeepSeek FIX) | Claude Code |
