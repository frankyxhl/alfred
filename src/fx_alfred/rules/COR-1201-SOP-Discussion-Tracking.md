# SOP-1201: Discussion Tracking

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-19
**Last reviewed:** 2026-03-19
**Status:** Active

---

## What Is It?

A lightweight protocol for tracking discussion items (D items) within a session. Each discussion point gets a numbered identifier, a lifecycle status, and is persisted to a tracking file in real-time so nothing is lost if the session is interrupted.

---

## Concepts

- **D item**: A numbered discussion point within a day's session (D1, D2, D3, ...)
- **Tracker file**: A REF document per day that records all D items, updated in real-time
- **Daily reset**: D numbers start from D1 each day; a new tracker file is created per day

---

## Commands

| Command | Action | Example |
|---------|--------|---------|
| `D new <topic>` | Create next D item (auto-increment), status Open | `D new af rename` → D17 (Open) |
| `D list` | Show all active D items (excludes Archived) | |
| `D list all` | Show all D items including Archived | |
| `D list open` | Show only Open + WIP items | |
| `D show <n>` | Show full details of D item including discussion notes | `D show 12` |
| `D start <n>` | Mark as WIP (Work In Progress) | `D start 12` |
| `D done <n>` | Mark as Done | `D done 12` |
| `D defer <n>` | Mark as Deferred (carry to next session) | `D defer 13` |
| `D reopen <n>` | Reopen a Done or Deferred item → Open | `D reopen 13` |
| `D archive` | Archive all Done items (remove from active list) | |
| `D<n> <text>` | Shorthand: reference/continue discussion on D<n> | `D12 还需要加测试` |

---

## Lifecycle

```
          D new
            │
            ▼
         ┌──────┐     D start     ┌──────┐
         │ Open │───────────────▶│ WIP  │
         └──────┘                └──────┘
            │                       │
            │ D defer               │ D done / D defer
            ▼                       ▼
       ┌──────────┐          ┌──────┐
       │ Deferred │          │ Done │
       └──────────┘          └──────┘
            │                    │
            │ D reopen           │ D reopen
            ▼                    ▼
         ┌──────┐            ┌──────┐
         │ Open │            │ Open │
         └──────┘            └──────┘

         Done ──── D archive ────▶ Archived (hidden from D list)
```

---

## Tracker File

### Location

```
<project>/rules/<PREFIX>-NNNN-REF-Discussion-Tracker-YYYY-MM-DD.md
```

Created via `af create ref` at the start of each day's first session, or manually if `af create` is not available for the prefix.

### Format

```markdown
# REF-NNNN: Discussion Tracker YYYY-MM-DD

## Active Items

| DN | Status | Parent | Source | Created | Updated | Topic |
|----|--------|--------|--------|---------|---------|-------|
| D1 | Done | — | User | 09:00 | 09:15 | Retrospective save location |
| D12 | WIP | — | User | 10:30 | — | af update command |
| D15 | Open | D12 | Codex | 14:00 | — | H1 validation fix |

## Archived Items

| DN | Parent | Source | Topic |
|----|--------|--------|-------|
| D1 | — | User | Retrospective save location |

## Discussion Notes

### D1: Retrospective save location
- **Decision**: FXA project layer, area 21
- **Result**: Created FXA-2108

### D12: af update command
- **Decision**: PRP-2104 → 3 rounds review → implement
- **Result**: Committed d6a968d
```

### Real-time persistence

**Every state change must be written to the tracker file immediately:**
- `D new` → append row to Active Items table + create Discussion Notes section
- `D start/done/defer/reopen` → update Status column in Active Items
- `D archive` → move rows from Active to Archived, remove from Active
- `D<n> <text>` → append note to Discussion Notes section for D<n>

This ensures no data is lost if the session is interrupted.

---

## Cross-Session Rules

### Same day, new session
- Read existing tracker file for today
- Continue D numbering from where it left off
- Deferred items remain in Active Items with status Deferred

### New day
- Create new tracker file with D1
- Deferred items from previous day: create new D items and note `(from YYYY-MM-DD D<n>)` in Topic

---

## Interaction Rules

### User writes `D<n>` at start of message
- If D<n> exists → continue that discussion
- If D<n> is the next sequential number → treat as `D new` (auto-create)
- If D<n> skips numbers → ask user to confirm

### Agent behavior
- On `D new`: immediately write to tracker file, respond with `D<n> (Open): <topic>`
- On status change: immediately update tracker file, respond with `D<n> (<new status>)`
- On any D item work completion: proactively suggest `D done <n>`

---

## Session End Checklist

Before running COR-1200 (Session Retrospective):
1. Run `D list open`
2. For each Open/WIP item, decide: `D done`, `D defer`, or continue working
3. All items must be Done, Deferred, or Archived before retrospective begins

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-19 | Initial version | Frank + Claude |
