# SOP-1201: Discussion Tracking

**Applies to:** All projects using the COR document system
**Last updated:** 2026-04-02
**Last reviewed:** 2026-04-02
**Status:** Active

---

## What Is It?

A lightweight protocol for tracking discussion items (D items) within a session. Each discussion point gets a numbered identifier, a lifecycle status, and is persisted to a tracking file in real-time so nothing is lost if the session is interrupted.

---

## Why

Prevents discussion points from being lost during long sessions by giving each item a trackable identifier and persistent state.

---

## When to Use

- **Every session** — the agent MUST load or create today's tracker at session start (see Session Start Protocol)
- When a topic comes up that cannot be resolved immediately and needs to be deferred
- When you need to reference a specific discussion point later in the session

---

## When NOT to Use

D items track discussion topics within a session. Use the correct document type for durable records:
- Formal decisions → ADR (COR-1100)
- Bug reports or incidents → INC

---

## Concepts

- **D item**: A numbered discussion point within a day's session (D1, D2, D3, ...)
- **Tracker file**: A REF document per day that records all D items, updated in real-time
- **Daily reset**: D numbers start from D1 each day; a new tracker file is created per day

---

## Session Start Protocol (Mandatory)

At the start of **every session**, the agent MUST execute these steps before any other work:

### Step 1: Find today's tracker

```bash
af search "Discussion Tracker $(date +%Y-%m-%d)"
```

This searches document **content** for today's tracker title. If the project uses `--root`, add it.

### Step 2a: Tracker found → load and continue

1. Read the tracker file with `af read <ACID>`
2. Parse **both** Active Items **and** Archived Items tables
3. Find the highest DN number across both tables (e.g., if Active has D5 and Archived has D7 → max = 7)
4. If both tables are empty (tracker exists but no D items yet), set `next_d = 1`
5. Otherwise, set `next_d = max + 1` (next topic will be D8)
6. Note any Deferred/WIP items — proactively inform the user

### Step 2b: Tracker not found → create new

1. Determine the project prefix and area:
   - Prefix: run `af list` and use the project's existing prefix (e.g., `FXA`, `NRV`)
   - Area: use the project's discussion tracker area (check existing tracker files for the convention, or ask the user on first use)
2. Check for deferred items from the most recent prior tracker:
   ```bash
   af search "Discussion Tracker"
   ```
   Pick the most recent result, read it, extract any Deferred items.
3. Create today's tracker file:
   ```bash
   af create ref --prefix <PREFIX> --area <AREA> --title "Discussion Tracker $(date +%Y-%m-%d)"
   ```
4. If deferred items exist, import them as D1, D2, ... with status **Open** and note `(from YYYY-MM-DD D<n>)` in Topic, then set `next_d = count of imported items + 1`
5. If no deferred items, set `next_d = 1`

### Step 3: Auto-increment on new topics

From this point forward in the session:
- When the user raises a new topic → automatically assign `D{next_d}`, write to tracker, increment `next_d`
- When the user writes `D<n>` with topic text → reference existing item or auto-create if it's the next sequential number
- When the user writes `D<n>` with no topic text → if it exists, continue that discussion; if it's next sequential, ask for topic
- Every state change → immediately persist to the tracker file

### Example

```
Session start → af search "Discussion Tracker 2026-04-02" finds FXA-2150
→ af read FXA-2150 → Active: D3(Open), D4(WIP); Archived: D1, D2
→ max DN across both tables = 4
→ next_d = 5
→ Agent tells user: "Loaded today's tracker (FXA-2150). D3 Open, D4 WIP. Next is D5."

User: "af update 需要支持 --dry-run"
Agent: "D5 (Open): af update --dry-run support"  → writes to tracker, next_d = 6

User: "D5 先做个 PRP"
Agent: updates D5 notes → "Creating PRP..."

User: "另外 af list 的输出格式要改"
Agent: "D6 (Open): af list output format change"  → writes to tracker, next_d = 7
```

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
| D5 | WIP | — | User | 10:30 | — | af update command |
| D6 | Open | D5 | Codex | 14:00 | — | H1 validation fix |

## Archived Items

| DN | Parent | Source | Topic |
|----|--------|--------|-------|
| D1 | — | User | Retrospective save location |
| D2 | — | User | af rename discussion |
| D3 | — | User | Index rebuild |
| D4 | D1 | User | Save location follow-up |

## Discussion Notes

### D5: af update command
- **Decision**: PRP-2104 → 3 rounds review → implement
- **Result**: Committed d6a968d

### D6: H1 validation fix
- **Source**: Codex review found heading mismatch
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
| 2026-03-20 | Added Why/When to Use/When NOT to Use sections per ALF-2210 | Claude Code |
| 2026-04-02 | Added Session Start Protocol (Mandatory): always-on tracker loading, auto-increment algorithm, example; removed single-topic exception from When NOT to Use; updated When to Use to mandate every-session activation | Frank + Claude Code |
| 2026-04-02 | R1 fix: Step 1 use content search (spaces not hyphens); Step 2a scan both Active+Archived for max DN; Step 2b clarify prefix/area lookup, concrete deferred carry-forward with import-first numbering; Step 3 handle bare D<n> edge case; reframe When NOT to Use as artifact precedence | Frank + Claude Code |
| 2026-04-02 | R2 fix: Step 2a add empty-tracker fallback (next_d=1); fix format example (D1 no longer in both Active and Archived); carry-forward status explicitly Open | Frank + Claude Code |
