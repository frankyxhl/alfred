# SOP-1200: Session Retrospective

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-17
**Last reviewed:** 2026-03-17
**Status:** Active
**Last executed:** —

---

## What Is It?

A self-review process executed at the end of every session. Its purpose is to extract reusable patterns, identify inefficiencies, and continuously improve the document system by turning repeated work into automation (commands, scripts, Makefile targets) and undocumented processes into new SOPs.

---

## Why

Retrospectives turn ad-hoc improvements into durable automation and SOPs, compounding efficiency gains across sessions.

---

## When to Use

- Before ending a session
- After completing a significant task or milestone
- When context is about to be compacted

---

## When NOT to Use

- During a session that made no meaningful changes (e.g., read-only exploration)
- When the session was trivially short with nothing to reflect on

---

## Steps

### 0. Close all discussion items

Before starting the retrospective, ensure all D items are resolved:

1. Run `D list open`
2. For each Open/WIP item: `D done`, `D defer`, or continue working
3. No Open/WIP items should remain

See COR-1201 (Discussion Tracking) for the full D item protocol.

### 1. List all actions taken this session

**Before reconstructing actions:** if `./rules/logs/<today UTC>.jsonl` exists (or today's entry is inside `./rules/logs/archive.zip`), read its event records as the ground truth for what happened this session. Use the records' `task.done` / `doc.created` / `doc.updated` / `decision` events to populate "Actions Taken" below; the chat-history reconstruction is the fallback when the log is empty or absent.

Two-step recipe — validate first (optional schema check), then read:

```bash
# Resolve UTC dates (cross-platform — GNU date on Linux, BSD date on macOS).
# These are real shell variables; the recipe is copy-paste runnable.
TODAY=$(date -u +%F)
YESTERDAY=$(date -u -d 'yesterday' +%F 2>/dev/null \
            || date -u -v-1d +%F)   # GNU first (-d), BSD/macOS fallback (-v-1d)

# Resolve THIS session's id so cross-tool contamination is filtered out
# (multiple agent sessions can share a UTC day). If $ALFRED_SESSION_ID
# wasn't exported during the session, leave SID empty — the filter falls
# back to whole-day view (with a caveat: results may include other agents'
# work). Tip to find your session_id retroactively:
#   jq -r '.session_id' ./rules/logs/${TODAY}.jsonl | sort -u
SID="${ALFRED_SESSION_ID:-}"

# Event-extraction jq filter, parameterised by --arg sid:
#   - When $sid is non-empty, only records with matching session_id pass
#   - When $sid is empty, all records pass (whole-day view)
JQ_FILTER='select(
    (.event == "task.done" or .event == "doc.created"
     or .event == "doc.updated" or .event == "decision")
    and ($sid == "" or .session_id == $sid)
  )
  | "\(.ts)  \(.event)  \(.summary)\(if .refs then "  refs=" + (.refs|join(",")) else "" end)"'

# 1. (Optional) Verify schema before relying on the log. Quiet on success,
#    prints "<path>:<lineno>: <field>: <reason>" on violations.
#    Validating the directory picks up today's .jsonl, any .partN.jsonl
#    rollover (per COR-1205 §Rotation), and entries inside archive.zip.
#
#    Feature-check guard: `af log-validate` ships in CHG-2231 Phase 3
#    (target v1.9.0). Before then the subcommand isn't registered, so a
#    bare invocation halts `set -e` callers. The check below silently
#    skips validation when the command isn't available — the actual log
#    read in step 2 still runs.
if af log-validate --help >/dev/null 2>&1; then
  af log-validate ./rules/logs/
else
  echo "INFO: af log-validate not yet available (CHG-2231 Phase 3 not shipped); skipping schema check" >&2
fi

# 2. Read today's event stream. JSONL is one-per-line so plain jq works.
#    Concatenate ${TODAY}.jsonl AND any ${TODAY}.partN.jsonl rollover with
#    explicit existence guards so the recipe stays `set -e` safe whether or
#    not rollover happened.
{
  if [ -e "./rules/logs/${TODAY}.jsonl" ]; then cat "./rules/logs/${TODAY}.jsonl"; fi
  for f in ./rules/logs/${TODAY}.part*.jsonl; do
    if [ -e "$f" ]; then cat "$f"; fi
  done
} | jq -r --arg sid "$SID" "$JQ_FILTER"

# 3. Yesterday's records (after archival). `unzip -p` accepts globs, so
#    "${YESTERDAY}*.jsonl" picks up ${YESTERDAY}.jsonl AND any
#    ${YESTERDAY}.partN.jsonl entries inside archive.zip.
#
#    Three-state guard distinguishing real errors from benign skip cases:
#    (a) no archive.zip → silent skip (fresh project / first day)
#    (b) archive corrupt or unreadable → STDERR warning + don't halt
#        (we do NOT want a corrupt archive to block today's retrospective;
#        the warning surfaces the issue without losing the rest of the run)
#    (c) archive readable but no <yesterday>*.jsonl entry → silent skip
#        (quiet day — normal state, not an error)
#    (d) archive readable AND has matching entries → extract
#
#    The previous one-liner form (`if [ -e ] && unzip -l ... >/dev/null;
#    then ... fi`) collapsed (b) and (c) into the same false branch and
#    silently dropped corruption errors — that masking is now gone.
if [ -e "./rules/logs/archive.zip" ]; then
  if ! unzip -l ./rules/logs/archive.zip >/dev/null 2>&1; then
    echo "WARNING: ./rules/logs/archive.zip exists but is unreadable" \
         "(corruption / IO error / permission). Yesterday's records skipped." \
         "Recover: af log-archive --force." >&2
  elif unzip -l ./rules/logs/archive.zip "${YESTERDAY}*.jsonl" >/dev/null 2>&1; then
    unzip -p ./rules/logs/archive.zip "${YESTERDAY}*.jsonl" \
      | jq -r --arg sid "$SID" "$JQ_FILTER"
  fi
fi
```

Note: `af log-validate` is a **schema checker** (quiet on success, emits only violations); it does not output the event stream itself. Read the JSONL bytes via `jq` (or `cat`) to extract events. The glob in step 2 covers both the base `<today>.jsonl` and any `<today>.partN.jsonl` rollover segments per COR-1205 §Rotation. The `--arg sid` parameter constrains output to the current session when `$ALFRED_SESSION_ID` is exported; otherwise the recipe shows the whole-day view (call out that other agents' work may be mixed in). *(See COR-1205 for the activity log format and COR-1206 for the per-agent emit protocol — both **scaffolded in CHG-2231 Phase 0**; mandatory triggers and CLI surfaces land across Phases 2–5; target release v1.9.0.)*

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

**If yes** → Candidate for a new command, Makefile target, or script. Score the finding per §Scoring below; proceed with the indicated action.

### 3. Identify undocumented processes

Ask yourself:
- Did I follow a multi-step process that isn't covered by an existing SOP?
- Did I have to figure something out from scratch that should be documented?
- Did I teach someone (or get taught) a workflow?

**If yes** → Candidate for a new SOP. Score the finding per §Scoring below; proceed with the indicated action.

### 4. Identify improvements to existing SOPs

Ask yourself:
- Did I follow an existing SOP but hit a gap or error in it?
- Is there a step missing or outdated?

**If yes** → Update the relevant SOP and add a Change History entry. Score the finding per §Scoring below; proceed with the indicated action.

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

### Scored Findings
| Class | Frequency | Actionability | Impact | Detection gap | Composite | Action |
|-------|-----------|---------------|--------|----------------|-----------|--------|
| <class> | <0–10> | <0–10> | <0–10> | <0–10> | <n.n> | Log / Discard |
```

### 6. Execute improvements

- Create new SOPs immediately if they're small
- File larger improvements as TODOs for the next session
- Update existing SOPs before ending the session

---

## Scoring

Use this rubric to decide whether a retro finding warrants a tracked GitHub issue, a log entry, or discard.

### Signal taxonomy

Six finding classes. Classify each retro finding into the most specific matching class:

| Class | Description |
|-------|-------------|
| **Recurrent finding** | Same finding type appeared in ≥2 distinct contexts (rounds, PRs, or sessions) |
| **Detection gap** | Primary detector (trinity panel) missed what secondary caught (codex bot, human) |
| **Late convergence** | Finding required R3+ rounds to resolve — not caught or prevented early |
| **Process skip** | A mandatory SOP guard rail or step was not executed |
| **Tooling gap** | Repeated manual step that could be scripted or added as an `af` command |
| **Other** | Finding does not match any class above; describe in one sentence |

### Scoring rubric

Score 0–10 on each dimension. Composite = Σ(weight × score).

| Dimension | Weight | 0 | 5 | 10 |
|-----------|--------|---|---|-----|
| **Frequency** | 35% | First time seen in any context | Appeared in 2 distinct contexts | ≥3 distinct PRs or sessions |
| **Actionability** | 30% | Vague ("be more careful"); no concrete target | Has a target SOP/file but amendment wording unclear | Specific target section + one-sentence amendment drafted now |
| **Impact** | 20% | No visible slowdown | Caused +1 review round or ~30 min lost | Caused R3+ or equivalent user rework / >1 h lost |
| **Detection gap** | 15% | Caught by primary (trinity) on first pass | Caught by primary on re-review after initial miss | Missed by primary entirely; caught by secondary (codex) or human |

### Action thresholds

| Composite | Action |
|-----------|--------|
| **≥ 7.5** | **Create GitHub issue** — include the drafted amendment in the issue body (per COR-1501 §Step 3: gh issue create). Present score breakdown to user before creating. |
| **5.0 – 7.4** | **Log only** — record in §Step 5 `### Scored Findings` with composite, dimension scores, and class. Re-evaluate on next iteration; Frequency score rises if the class recurs, potentially crossing the issue threshold. |
| **< 5.0** | **Discard** — noise, one-off, or already covered by an existing MEMORY entry or open issue. |

> **Threshold geometry note:** Reaching the Issue band (≥7.5) requires at least two dimensions to score strongly. Frequency=10 with all other dims at 5 yields only 6.75 (Log band) — intentional: a high-frequency but low-impact, vague, internally-caught finding warrants tracking, not an issue. Actionability is the second-strongest lever; Frequency=10 + Actionability=10 yields 6.5 at minimum (others at 0, Log band) and 8.25 with others at 5 (Issue band). Reaching the Issue band from Freq+Act=10 requires at least Impact=5 (composite = 7.5, exactly at threshold).

### Calibration examples

**Example 1 — First codex catch, trinity missed** (`--repo` gap, PR #131 R1):
Frequency=0, Actionability=8, Impact=5, Detection gap=10
→ 0×0.35 + 8×0.30 + 5×0.20 + 10×0.15 = **4.9 → Discard** (first occurrence; if this class recurs next PR, Frequency rises to 5 and composite crosses into Log band at 6.65)

**Example 2 — Same class recurs in the next PR**:
Frequency=5, Actionability=9, Impact=5, Detection gap=10
→ 1.75 + 2.70 + 1.00 + 1.50 = **6.95 → Log and re-evaluate**

**Example 3 — Third PR, same class** (pattern confirmed):
Frequency=10, Actionability=9, Impact=5, Detection gap=8
→ 3.50 + 2.70 + 1.00 + 1.20 = **8.40 → Create issue**

**Example 4 — Single late-convergence, high impact, no recurrence**:
Frequency=0, Actionability=9, Impact=10, Detection gap=5
→ 0 + 2.70 + 2.00 + 0.75 = **5.45 → Log**

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
| 2026-03-20 | Added Why/When to Use/When NOT to Use sections per FXA-2223 | Claude Code |
| 2026-05-10 | Added §Scoring (signal taxonomy, 4-dim rubric, action thresholds, 4 calibration examples); §Step 5 template: added Scored Findings subsection; §Steps 2/3/4: added §Scoring reference per FXA-2282 / issue #134 | Claude Code |
