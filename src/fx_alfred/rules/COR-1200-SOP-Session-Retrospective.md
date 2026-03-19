# SOP-1200: Session Retrospective

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-17
**Last executed:** —

---

## What Is It?

A self-review process executed at the end of every session. Its purpose is to extract reusable patterns, identify inefficiencies, and continuously improve the document system by turning repeated work into automation (commands, scripts, Makefile targets) and undocumented processes into new SOPs.

---

## When to Run

- Before ending a session
- After completing a significant task or milestone
- When context is about to be compacted

---

## Steps

### 0. Close all discussion items

Before starting the retrospective, ensure all D items are resolved:

1. Run `D list open`
2. For each Open/WIP item: `D done`, `D defer`, or continue working
3. No Open/WIP items should remain

See COR-1201 (Discussion Tracking) for the full D item protocol.

### 1. List all actions taken this session

Review the conversation and list every meaningful action:
- Files created, edited, or deleted
- Commands run
- Configurations changed
- Issues encountered and resolved

### 2. Identify repeated patterns

Ask yourself:
- Did I do the same sequence of steps more than once?
- Did I copy-paste similar commands or configs?
- Did I manually do something that could be scripted?

**If yes** → Candidate for a new command, Makefile target, or script.

### 3. Identify undocumented processes

Ask yourself:
- Did I follow a multi-step process that isn't covered by an existing SOP?
- Did I have to figure something out from scratch that should be documented?
- Did I teach someone (or get taught) a workflow?

**If yes** → Candidate for a new SOP.

### 4. Identify improvements to existing SOPs

Ask yourself:
- Did I follow an existing SOP but hit a gap or error in it?
- Is there a step missing or outdated?

**If yes** → Update the relevant SOP and add a Change History entry.

### 5. Record findings

Save the retrospective as a REF document using af:

```bash
af create ref --prefix <PREFIX> --area <RETRO_AREA> --title "Session Retrospective YYYY-MM-DD-DN"
```

Where `<RETRO_AREA>` is your project's retrospective area (e.g., 12 for COR Check phase, or whichever area your project assigns to retrospectives), and DN is the day sequence number (D1 for first session of the day, D2 for second, etc.).

Fill in the template with the sections below. The document is automatically indexed.

```markdown
## Session Retrospective — YYYY-MM-DD-DN

### Actions Taken
- <bullet list of what was done>

### Automation Candidates
| Pattern | Suggested Action | Priority |
|---------|-----------------|----------|
| <repeated task> | <script/Makefile/command> | High/Med/Low |

### New SOP Candidates
| Topic | Why |
|-------|-----|
| <process name> | <reason it should be standardized> |

### SOP Updates Needed
| SOP | What to Change |
|-----|---------------|
| COR-NNNN or ALF-NNNN | <description> |

### Key Learnings
- <numbered list of insights worth remembering for future sessions>
```

### 6. Execute improvements

- Create new SOPs immediately if they're small
- File larger improvements as TODOs for the next session
- Update existing SOPs before ending the session

---

## Example

After today's session, a retrospective might find:

| Pattern | Action |
|---------|--------|
| Created 3 channels manually with same steps | Already became SOP-1001 |
| Codex relay needed separate launchd plist | Add to SOP-1001 or create SOP for launchd setup |
| Kept editing relay-config.json by hand | Consider a `make add-channel` command |

Example save command:

```bash
af create ref --prefix ALF --area 12 --title "Session Retrospective 2026-03-17-D2"
```

---

## Safety Notes

- Don't skip this step — the 5 minutes spent here saves hours later
- Be honest about what went wrong, not just what went right
- Small improvements compound over time

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-08 | Initial version | Claude Code |
| 2026-03-14 | PDCA + Johnny Decimal migration: renamed from ALF-1002 to COR-1200 | Claude Code |
| 2026-03-17 | Step 5: add explicit af create ref command, add Key Learnings section, add example save command, use YYYY-MM-DD-DN title format for multiple sessions per day | Claude Code |
| 2026-03-19 | Added Step 0: close all D items before retrospective (references COR-1201) | Claude Code |
