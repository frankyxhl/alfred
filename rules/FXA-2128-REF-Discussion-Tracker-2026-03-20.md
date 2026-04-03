# REF-2128: Discussion Tracker 2026 03 20

**Applies to:** FXA project
**Last updated:** 2026-03-20
**Last reviewed:** 2026-03-20
**Status:** Active

---

## What Is It?

Discussion tracker for 2026-03-20 session.

---

## Discussion Items

| # | Topic | Status | Outcome |
|---|-------|--------|---------|
| D1 | Team agent session resume after accidental stop | Done | ALF-2209 PRP created: /team resume + auto-detect + 30min window |
| D2 | How to present COR-1201 commands in decision tree | Done | Added to FXA-2125 branch 7 with full command list |
| D3 | Enforce review gate before commit | Done | FXA-2134 PRP approved: `af plan` command generates checklist from SOPs, making review steps visible and unskippable |
| D4 | Gemini still gives 10/10 despite noting advisories | Done | COR-1611 Rule 5 strengthened: advisory → max 9.8, blocking → max 9.0, 10.0 only if zero notes on all dimensions |

### D1: Team Agent Session Resume

**Status:** Open
**Topic:** When user accidentally stops a background agent, the underlying CLI session (codex/gemini/glm) is still alive. Currently we dispatch fresh instead of resuming.

**Discussion:**
- `.team/sessions.json` has session IDs for each provider
- Bottom-layer CLI tools support session resume
- Gap: /team skill doesn't check for existing sessions before dispatch
- Need PRP to design resume logic

**Next:** Create ALF-level PRP after ALF-2208 review completes

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version, D1 team session resume | Frank + Claude Code |
