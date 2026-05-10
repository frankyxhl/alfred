# SOP-1623: PR Review Thread Verification

**Applies to:** All projects using GitHub PR review workflows
**Last updated:** 2026-05-10
**Last reviewed:** 2026-05-10
**Status:** Active
**Related:** COR-1617 (§Phase 11 Retrospective — composable sub-procedure), COR-1615 (GitHub App PR Review Bot Loop)

---

## What Is It?

A 4-step procedure for auditing GitHub PR review threads against actual source file content. Produces a per-thread classification (RESOLVED-IN-CODE / GENUINELY-OPEN / NEEDS-FOLLOWUP) with file-path-and-line evidence, replacing bot verdicts that may be wrong due to truncated diff windows.

---

## Why

GitHub review bots (clearance bots, SWM bots) decide whether a thread is resolved by inspecting the PR diff. Their diff window is often truncated — they cannot reliably distinguish "the fix exists but I can't see it in the diff" from "no fix exists." This produces false-positive OPEN verdicts that block merges unnecessarily.

A human or agent following this procedure reads the actual file content (not the diff) and classifies each thread with concrete evidence in minutes. Demonstrated on PR #141 (alfred), where 2 of 4 "unresolved" threads were confirmed fixed by direct file inspection.

---

## When to Use

- During COR-1617 §Phase 11 Retrospective, when a PR has threads marked unresolved by a bot
- Any time a bot flags a thread as OPEN/NEEDS_HUMAN_JUDGMENT and the fix appears to be present in the codebase
- Before pushing an additional round solely to address threads the bot cannot confirm as resolved

## When NOT to Use

- When the thread is clearly genuinely open (no corresponding fix was attempted)
- When the thread discusses a design decision rather than a concrete change — these cannot be verified by file inspection alone
- When the bot's diff window is not the limiting factor (the bot read the full file and still flagged the thread)

---

## Prerequisites

- `gh` CLI authenticated with read access to the repo
- The PR branch is checked out locally (or files are accessible via `gh api`)
- The list of open threads has been collected (COR-1617 §Phase 11 provides this)

---

## Steps

### Step 1 — Enumerate open threads

Fetch all unresolved review threads from the PR:

```bash
gh pr view <pr> --repo <repo> --json reviewThreads \
  --jq '.reviewThreads[] | select(.isResolved == false) |
    {id: .id, path: .path, line: .line,
     body: (.comments.nodes[0].body | .[0:120])}'
```

For the raw per-comment view (useful when `reviewThreads` is empty due to API lag):

```bash
gh api repos/<repo>/pulls/<pr>/comments \
  --paginate \
  --jq '.[] | select(.in_reply_to_id == null) |
    {id: .id, path: .path, line: .original_line,
     body: (.body | .[0:120])}'
```

Record each unresolved thread: thread ID, file path, line number, and the finding summary (first ~120 chars of the lead comment).

### Step 2 — Locate the claim

For each thread, identify the exact source location it references:

1. Extract `path` (file path) and `line` (line number) from the thread record.
2. If `line` is null — thread on a deleted line or an outdated diff position — use the lead comment text to identify the construct (function name, variable, section heading) and `grep` for it instead.

Note: `original_line` is the line number at comment-post time; it may differ from the current line if the file changed since. Use the construct name as a fallback locator when line numbers have drifted.

### Step 3 — Verify against source

Read the actual file at the identified location — **not** the diff:

```bash
# Via git (local checkout)
sed -n '<start>,<end>p' <path>

# Via GitHub API (no local checkout needed)
gh api "repos/<repo>/contents/<path>?ref=<branch-sha>" \
  --jq '.content' | base64 -d | sed -n '<start>,<end>p'
```

Use a window of ±20 lines around the flagged line to capture context.

Check whether the fix is present:
- Does the flagged code/text still exist?
- Is the replacement or addition the reviewer requested now in place?
- Is the surrounding context consistent with the change?

### Step 4 — Classify

Assign one of three classifications to each thread:

| Classification | Condition | Evidence to record |
|----------------|-----------|-------------------|
| **RESOLVED-IN-CODE** | The fix is present in the source file; bot could not confirm due to truncated diff | File path, line range, quoted snippet confirming fix |
| **GENUINELY-OPEN** | The issue the reviewer flagged is still present; no fix attempt found | File path, line range, quoted snippet showing issue persists |
| **NEEDS-FOLLOWUP** | A fix was attempted but is incomplete, addresses only part of the concern, or introduces a new issue | File path, line range, current state quote + description of remaining gap |

### Verification Report

Post the classification as a PR comment using this template:

```
## PR Review Thread Verification Report

Verified against: <branch-sha>

| Thread | Path | Line | Classification | Evidence |
|--------|------|------|----------------|----------|
| #<id> | `<path>` | <line> | RESOLVED-IN-CODE | `<quoted snippet>` — fix present |
| #<id> | `<path>` | <line> | GENUINELY-OPEN | `<quoted snippet>` — issue still present |
| #<id> | `<path>` | <line> | NEEDS-FOLLOWUP | Fix at line <N> addresses X but not Y |

**Summary:** <n> RESOLVED-IN-CODE · <n> GENUINELY-OPEN · <n> NEEDS-FOLLOWUP
```

After posting: resolve the RESOLVED-IN-CODE threads explicitly on GitHub so bots see the updated state. Do not resolve GENUINELY-OPEN or NEEDS-FOLLOWUP threads.

---

## Pitfalls

- **Read the file, not the diff.** The diff is what the bot reads and why it fails. Always read actual file content at the current HEAD.
- **`original_line` drifts.** If the file changed after the review comment was posted, `original_line` no longer points to the right place. Use the construct name and `grep` to re-locate.
- **Deletion ≠ fix.** If the flagged code was deleted rather than replaced with a correct version, verify whether deletion satisfies the reviewer's concern — it may or may not.
- **RESOLVED-IN-CODE is not the same as thread resolved.** Post the report and then resolve threads explicitly on GitHub; bots read thread resolution state, not comments.
- **Classify by file content, not author intent.** What the author said they would do is irrelevant — classify by what is in the file at the verified SHA.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-10 | Initial version — 4-step procedure (Enumerate / Locate / Verify / Classify) for auditing PR review threads against source file content. Addresses false-positive bot verdicts observed on PR #141 (alfred). Composable with COR-1617 §Phase 11 Retrospective. Issue #142. | Claude Sonnet 4.6 |
