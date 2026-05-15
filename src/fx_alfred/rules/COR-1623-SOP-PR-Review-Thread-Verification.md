# SOP-1623: PR Review Thread Verification

**Applies to:** All projects using GitHub PR review workflows
**Last updated:** 2026-05-15
**Last reviewed:** 2026-05-15
**Status:** Active
**Related:** COR-1617 (§Phase 8 Iterate — composable sub-procedure for bot thread verification), COR-1615 (GitHub App PR Review Bot Loop)

---

## What Is It?

A 4-step procedure for auditing GitHub PR review threads against actual source file content. Produces a per-thread classification (RESOLVED-IN-CODE / GENUINELY-OPEN / NEEDS-FOLLOWUP) with file-path-and-line evidence, replacing bot verdicts that may be wrong due to truncated diff windows.

---

## Why

GitHub review bots (clearance bots, SWM bots) decide whether a thread is resolved by inspecting the PR diff. Their diff window is often truncated — they cannot reliably distinguish "the fix exists but I can't see it in the diff" from "no fix exists." This produces false-positive OPEN verdicts that block merges unnecessarily.

A human or agent following this procedure reads the actual file content (not the diff) and classifies each thread with concrete evidence in minutes. Demonstrated on PR #141 (alfred), where 2 of 4 "unresolved" threads were confirmed fixed by direct file inspection.

---

## When to Use

- During COR-1617 §Phase 8 Iterate, after CI passes and bot review is complete on the current HEAD, when threads remain unresolved despite fixes being present
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
- Open threads are enumerated in Step 1 of this SOP (or obtained from a prior COR-1615 or COR-1612 inspection)

---

## Steps

### Step 1 — Enumerate open threads

Fetch unresolved, non-outdated review threads from the PR via paginated GraphQL (supports `isResolved` / `isOutdated` filtering):

```bash
gh api graphql --paginate -f query='
  query($owner:String!,$repo:String!,$number:Int!,$endCursor:String){
    repository(owner:$owner,name:$repo){
      pullRequest(number:$number){
        reviewThreads(first:100, after:$endCursor){
          nodes{ id isResolved isOutdated path line originalLine
            comments(first:1){nodes{body}} }
          pageInfo{hasNextPage endCursor}
        }}}}' \
  -f owner=<owner> -f repo=<repo> -F number=<pr> \
  --jq '.data.repository.pullRequest.reviewThreads.nodes[]
    | select((.isResolved == false) and (.isOutdated == false))
    | {id, path, line: (.line // .originalLine),
       body: (.comments.nodes[0].body // "" | .[0:120])}'
```

Fallback via REST when GraphQL is unavailable or API lag hides thread nodes (no `isResolved` / `isOutdated` fields; compare against GitHub UI thread count to identify resolved or outdated threads):

```bash
gh api repos/<repo>/pulls/<pr>/comments \
  --paginate \
  --jq '.[] | select(.in_reply_to_id == null) |
    {id: .id, path: .path, line: (.line // .original_line),
     body: (.body | .[0:120])}'
```

Note: the GraphQL primary returns global node IDs (`PRRT_kwDO…`); the REST fallback returns numeric comment IDs. Choose the matching reply command in §Verification Report.

Record each unresolved thread: thread ID, file path, line number, and the finding summary (first ~120 chars of the lead comment).

### Step 2 — Locate the claim

For each thread, identify the exact source location it references:

1. Extract `path` (file path) and `line` (line number) from the thread record.
2. If `line` is null — thread on a deleted line or an outdated diff position — use the lead comment text to identify the construct (function name, variable, section heading) and `grep` for it instead.

Note: the Step 1 commands emit the current line anchor when available (`line`), falling back to the original line anchor (`originalLine` in GraphQL, `original_line` in REST). Line anchors can still drift when files change after a comment is posted. Use the construct name as a fallback locator when line numbers no longer point to the reviewed code. If the file no longer exists (deleted), classify the thread as NEEDS-FOLLOWUP unless the reviewer's concern was the file's existence itself.

### Step 3 — Verify against source

Read the actual file at the identified location — **not** the diff:

```bash
# Via git (local checkout) — LINE is the line number from Step 1
LINE=<line>
START=$(( LINE > 20 ? LINE - 20 : 1 ))
END=$(( LINE + 20 ))
sed -n "${START},${END}p" <path>

# Via GitHub API (no local checkout needed)
gh api "repos/<repo>/contents/<path>?ref=<branch-sha>" \
  --jq '.content' | base64 -d | sed -n "${START},${END}p"
```

Note: the Contents API returns `content: null` for files larger than 1 MB — use the local checkout method for large files.

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

Post the report (write the filled-in template to a file first, then post):

```bash
gh pr comment <pr> --repo <repo> --body-file /tmp/thread-verification-report.md
```

After posting: for each RESOLVED-IN-CODE thread, reply referencing the relevant report row as evidence. Per COR-1612 §Step 7, do not self-resolve — the original reviewer must resolve the thread. Do not reply to GENUINELY-OPEN or NEEDS-FOLLOWUP threads; address their findings in the next round.

Reply commands (choose based on ID type from Step 1):

```bash
# GraphQL reply (uses global node ID from primary command)
gh api graphql -f query='mutation($t:ID!,$b:String!){
  addPullRequestReviewThreadReply(input:{pullRequestReviewThreadId:$t,body:$b}){
    comment{url}}}' \
  -f t="<PRRT_...>" -f b="Verified RESOLVED-IN-CODE — see verification report."

# REST reply (uses numeric comment ID from fallback — dedicated replies endpoint)
gh api repos/<repo>/pulls/<pr>/comments/<comment-id>/replies \
  -f body="Verified RESOLVED-IN-CODE — see verification report."
```

---

## Pitfalls

- **Read the file, not the diff.** The diff is what the bot reads and why it fails. Always read actual file content at the current HEAD.
- **Line numbers drift.** The `line` field in Step 1 output is GitHub's current line anchor when available, otherwise the original anchor. If the file changed after GitHub computed that anchor, it can still point to the wrong place. Use the construct name and `grep` to re-locate.
- **Deletion ≠ fix.** If the flagged code was deleted rather than replaced with a correct version, verify whether deletion satisfies the reviewer's concern — it may or may not.
- **RESOLVED-IN-CODE is not the same as thread resolved.** Post the report and reply to each RESOLVED-IN-CODE thread with the relevant evidence row. Bots read thread resolution state; per COR-1612 §Step 7, only the original reviewer can resolve a thread — prompt them if timely resolution is critical.
- **Pagination is part of correctness.** Do not remove GraphQL `--paginate`, `$endCursor`, or `pageInfo`; without them, PRs with more than 100 review threads silently omit later threads.
- **Classify by file content, not author intent.** What the author said they would do is irrelevant — classify by what is in the file at the verified SHA.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-10 | Initial version — 4-step procedure (Enumerate / Locate / Verify / Classify) for auditing PR review threads against source file content. Addresses false-positive bot verdicts observed on PR #141 (alfred). Composable with COR-1617 §Phase 8 Iterate. Issue #142. | Claude Sonnet 4.6 |
| 2026-05-10 | R1 fixes (DeepSeek panel): B1 — replaced invalid `gh pr view --json reviewThreads` with `gh api graphql` primary + REST fallback (field not supported by gh CLI); B2 — removed self-resolve instruction (contradicts COR-1612 §Step 7); A1 — fixed prerequisite claim (Phase 11 does not enumerate threads; Step 1 does); A2 — added deleted-file classification note; A4 — documented REST/GraphQL field-name difference (`original_line` vs `originalLine`). | Claude Sonnet 4.6 |
| 2026-05-10 | R2 advisories (GLM P2-1/P2-2/P2-3/P2-4): Step 3 — Contents API returns null >1 MB (added note); sed placeholder replaced with `$((LINE±20))` arithmetic; pitfall renamed from `original_line drifts` to `Line numbers drift` (GraphQL path outputs `line` not `original_line`); posting command changed from inline `--body` to `--body-file /tmp/thread-verification-report.md`. | Claude Sonnet 4.6 |
| 2026-05-10 | R2 fix (GLM B1): REST reply command used wrong pattern (`POST /comments` with `in_reply_to_id`); replaced with dedicated replies endpoint (`POST /comments/<id>/replies`) which only requires `body`. | Claude Sonnet 4.6 |
| 2026-05-10 | R2 fix (DeepSeek B1): GraphQL `first:100` caps at 100 — replaced "Fetch all" claim with accurate "Fetch up to 100"; added Pitfalls entry directing to REST `--paginate` for large PRs; clarified REST fallback description. | Claude Sonnet 4.6 |
| 2026-05-10 | R1 fixes (GLM panel): P0 — corrected remaining Phase 11 references to Phase 8 Iterate (Related: header, §When to Use, §Change History); P1-1 — added `gh pr comment` command for posting report; P1-2 — added GraphQL/REST thread reply commands (COR-1612 §Step 7 requires reply-not-resolve); P2-1 — noted GraphQL node ID vs REST numeric ID difference for reply commands. | Claude Sonnet 4.6 |
| 2026-05-15 | PR #153 review follow-up: Step 1 now uses paginated GraphQL with `$endCursor` / `pageInfo`, filters out outdated threads, emits current `line` before falling back to original anchors, and the REST fallback mirrors current-line preference. Step 3 clamps the `sed` context start to line 1. | Codex |
