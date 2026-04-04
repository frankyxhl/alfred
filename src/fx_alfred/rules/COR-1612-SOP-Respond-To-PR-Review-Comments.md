# SOP-1612: Respond To PR Review Comments

**Applies to:** All projects using the COR document system
**Last updated:** 2026-04-04
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

### 1. Fetch all review comments

```bash
gh api repos/{owner}/{repo}/pulls/{number}/comments --jq '.[] | {id, path, line, body}'
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
2. Reply on GitHub with commit hash and what changed
3. Push the fix

**Advisory:**
1. If adopting: fix, reply with commit hash
2. If declining: reply with reasoning why the change is not needed

**Question:**
1. Reply with explanation on GitHub

**Incorrect:**
1. Reply on GitHub: explain why the suggestion is incorrect or inapplicable
2. Escalate to user for confirmation before proceeding

### 4. Push all fixes in one commit

Group all blocking and adopted advisory fixes into a single commit referencing the PR:

```bash
git commit -m "fix: address PR review comments (#<PR>)"
```

### 5. Wait for CI

Verify CI passes after the fix commit.

### 6. Do NOT self-resolve threads

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
This suggestion is incorrect — COR-0002 requires Date before Severity for INC documents (see template inc.md:7-8). No change needed.
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
