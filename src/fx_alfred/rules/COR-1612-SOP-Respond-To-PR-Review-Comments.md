# SOP-1612: Respond To PR Review Comments

**Applies to:** All projects using the COR document system
**Last updated:** 2026-04-05
**Last reviewed:** 2026-04-04
**Status:** Draft

---

## What Is It?

The standard process for responding to review comments on a Pull Request. Covers comments from any source — human reviewers, automated tools (Codex, Copilot), or bots. This SOP is a universal overlay that works with any workflow (COR-1600–1605).

---

## Why

Without a standard process, review comments get fixed without replies, missed entirely, or self-resolved without reviewer confirmation. This leads to unverified fixes and broken review trust.

---

## When to Use

- A PR has received review comments (inline, review summary, or bot suggestions)
- After pushing code to a PR that has pending review threads
- Any workflow that involves a PR merge step

---

## When NOT to Use

- Review scoring during COR-1602 parallel review (that's a separate scoring flow)
- Draft PRs where comments are self-notes
- Comments on closed/merged PRs (address in a follow-up PR if needed)

---

## Steps

### 1. Fetch all PR review feedback

Fetch inline review comments, review summary comments, and top-level PR conversation comments:

```bash
# Inline review comments on changed lines
gh api repos/{owner}/{repo}/pulls/{number}/comments --paginate --jq '.[] | {type: "inline", id, path, line, body}'

# Review summary comments (review bodies). Keep CHANGES_REQUESTED reviews even if body is empty.
gh api repos/{owner}/{repo}/pulls/{number}/reviews --paginate --jq '.[] | select(.state == "CHANGES_REQUESTED" or (.body != null and .body != "")) | {type: "review_summary", id, state, body}'

# Top-level PR conversation comments
gh api repos/{owner}/{repo}/issues/{number}/comments --paginate --jq '.[] | {type: "issue_comment", id, body}'
```

### 2. Categorize each comment

Read each comment and classify:

| Category | Definition | Action required |
|----------|-----------|----------------|
| **Blocking** | Code bug, logic error, missing test, security issue | Must fix before merge |
| **Advisory** | Style suggestion, naming preference, minor improvement | Fix or explain why not |
| **Question** | Reviewer asks for clarification | Reply with explanation |
| **Incorrect** | Reviewer suggestion is wrong or inapplicable | Reply with reasoning, escalate to user |

### 3. Process each comment

**Blocking:**
1. Fix the code

**Advisory:**
1. If adopting: fix the code
2. If declining: reply with reasoning why the change is not needed

**Question:**
1. Reply with explanation on GitHub

**Incorrect:**
1. Reply on GitHub: explain why the suggestion is incorrect or inapplicable
2. Escalate to user for confirmation before proceeding

### 4. Push all fixes in one commit

Group all blocking and adopted advisory fixes into a single commit referencing the PR:

```bash
git add <changed-files>
git commit -m "fix: address PR review comments (#<PR>)"
git push
```

### 5. Reply to each fixed comment

After the fix commit is pushed, reply on GitHub for each blocking or adopted advisory comment with:

GitHub only auto-marks line-anchored comments as outdated when the referenced diff line changes. Diff position comments with `line: null` (common for Codex/Copilot bot comments) and issue-level/top-level comments are not auto-outdated, so reply to those manually after the fix lands.

1. The commit hash
2. What changed

### 6. Wait for CI

Verify CI passes after the fix commit.

### 7. Do NOT self-resolve threads

The reviewer (human or bot) must confirm the fix and resolve the thread. Never resolve your own fix.

If the reviewer is an automated tool that cannot resolve, inform the user and let them resolve.

---

## Reply Format

When replying to a comment on GitHub, include:

- **Commit reference:** which commit contains the fix
- **What changed:** brief description of the fix
- **If declining:** reasoning for not making the change

Example:
```
Fixed in abc1234. Narrowed exception catch to `(ValueError, OSError, MalformedDocumentError)`.
```

Example (declining):
```
This suggestion is incorrect — the INC template places Date before Severity (see `src/fx_alfred/templates/inc.md`). No change needed.
```

---

## Pitfalls

- **Self-resolving:** Resolving your own thread is meaningless — the reviewer must verify
- **Silent fixes:** Fixing code without replying on GitHub leaves the thread unresolved and untracked
- **Blanket dismiss:** Dismissing bot suggestions without reading them — automated reviewers can catch real bugs
- **Batch replies:** Replying "fixed all" without per-comment responses makes it hard to verify each fix

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-04 | Initial version per Issue #28 | Claude Code |
| 2026-04-04 | PR review fix: fetch 3 endpoints (inline + review summary + issue comments), add --paginate, fix declining example to cite template not COR-0002 | Claude Code |
| 2026-04-05 | PR review fix: include empty-body CHANGES_REQUESTED reviews, move replies after commit/push, add explicit git push step | Codex |
| 2026-04-05 | Add note that diff-position and top-level comments do not auto-mark outdated | Codex |
