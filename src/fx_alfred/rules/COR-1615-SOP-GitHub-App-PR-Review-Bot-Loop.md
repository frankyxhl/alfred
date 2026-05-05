# SOP-1615: GitHub App PR Review Bot Loop

**Applies to:** All projects using the COR document system
**Last updated:** 2026-05-05
**Last reviewed:** 2026-05-05
**Status:** Active
**Related:** COR-1612 (Respond To PR Review Comments), COR-1613 (Council Review)
**Task tags:** [github, github-app, pull-request, pr-review, review, bot-review, codex, copilot]
**Authored from:** BAB-1504-SOP-GitHub-Codex-PR-Review-Loop

---

## What Is It?

A procedure for driving a GitHub App pull-request review bot loop from trigger to completion. It covers when to request a review, how to interpret reactions and review objects, how to avoid duplicate requests, how to match results to the current PR head commit, and when to hand off actionable findings to COR-1612.

This SOP is bot-agnostic. It covers both first-party GitHub/Copilot review apps and connector-installed reviewers such as `chatgpt-codex-connector[bot]`, as long as the review is produced by a GitHub App or bot on the PR.

---

## Why

GitHub App review bots are useful but easy to misread. A reaction on a request comment can mean "queued" rather than "complete"; a review can cover an older commit; and flat comment APIs can show old inline comments near new diff lines. Without a standard loop, operators can merge without a current-head review, re-fix stale comments, or spam duplicate review requests that make the PR timeline harder to audit.

---

## When to Use

- A PR is open and an operator asks for a GitHub App review bot pass.
- A branch has been pushed after addressing PR feedback and needs review on the new head commit.
- A workflow treats a GitHub App review bot as one detector in the PR readiness gate.
- The operator needs to distinguish pending bot work from a completed review result.

## When NOT to Use

- Local review before a PR exists.
- Multi-reviewer decision making that is not GitHub App bot polling; use COR-1613 and the selected COR-1600 through COR-1605 workflow.
- Responding to already-fetched review findings; use COR-1612 for classification, fixes, replies, and post-fix polling.
- CI failure diagnosis with no PR review comments; use the project CI/debug route.
- The current GitHub identity is not allowed to create visible PR comments under the active USR/PRJ routing policy.

---

## Prerequisites

- Know the repository and PR number, for example `OWNER/REPO` and `PR_NUM`.
- Confirm `gh` is installed and authenticated.
- Confirm the visible-write account is the intended account for this project before creating PR comments.
- Know the local branch state and remote PR head:
  `git status --short --branch` and `gh pr view "$PR_NUM" --repo "$OWNER/$REPO" --json headRefOid`.
- Do not put private hostnames, local filesystem paths, tokens, Tailscale IPs, or other local environment details into public PR text.

---

## Status Vocabulary

| Signal | Meaning | What to do |
|--------|---------|------------|
| Request comment such as `@codex review` | A manual review request was posted | Wait; do not post another request immediately |
| Reviewer assignment such as `@copilot` | A GitHub reviewer-style bot was requested | Wait for review; do not also post a comment trigger unless both detectors are intentionally desired |
| Reaction such as `eyes` on the request | The reviewer has noticed or queued the request | Keep polling; review is not complete yet |
| Positive reaction with no new comments | The reviewer may have no suggestions | Confirm the signal applies to the current head before treating it as clear |
| Review body names a reviewed commit | Review completed for that commit | Compare the commit with current `headRefOid` |
| Inline bot comments | Actionable or advisory findings | Classify and handle via COR-1612 |
| Review is for an older commit | Current head is not covered | Request or wait for a review of the current head |
| Thread is outdated or resolved | Comment no longer applies to current diff | Do not treat it as a fresh blocker unless the issue still exists |

---

## Commands

Set variables:

```bash
OWNER="github-owner"
REPO="github-repo"
PR_NUM="123"
```

Confirm identity before visible writes:

```bash
gh auth status
```

Read PR state and recent review objects:

```bash
gh pr view "$PR_NUM" --repo "$OWNER/$REPO" \
  --json number,state,isDraft,mergeable,reviewDecision,headRefName,headRefOid,latestReviews,comments,statusCheckRollup
```

Trigger a manual review when the project uses a comment-requested bot:

```bash
gh pr comment "$PR_NUM" --repo "$OWNER/$REPO" --body '@codex review'
```

Request a review when the project uses a reviewer-assignment bot:

```bash
gh pr edit "$PR_NUM" --repo "$OWNER/$REPO" --add-reviewer @copilot
```

Fetch inline review comments:

```bash
gh api "repos/$OWNER/$REPO/pulls/$PR_NUM/comments" --paginate \
  --jq '.[] | {id, user: .user.login, path, line, commit_id, created_at, body, html_url}'
```

Fetch review summaries:

```bash
gh api "repos/$OWNER/$REPO/pulls/$PR_NUM/reviews" --paginate \
  --jq '.[] | {id, state, user: .user.login, commit_id, submitted_at, body}'
```

When thread state matters, use a GraphQL or project helper that exposes `isOutdated` and `isResolved`; REST flat comments do not expose the full thread state.

---

## Steps

### 1. Resolve the current PR head

Run `gh pr view` and record `headRefOid`. A review only clears the head commit it actually reviewed.

### 2. Confirm write identity before triggering review

Run `gh auth status`. If the authenticated account is not the intended visible-write account for the project, stop and fix authentication before creating PR comments.

### 3. Decide whether a trigger is needed

Trigger review only when the current head lacks a completed review result, the operator explicitly requested a new pass, or a push changed the head after the last review request. Do not trigger another review while an existing request for the same head is still pending.

### 4. Trigger one review request for the head

Post or request the project-specific review once. Examples:

- Comment-triggered reviewer: `gh pr comment "$PR_NUM" --repo "$OWNER/$REPO" --body '@codex review'`
- Reviewer-assignment bot: `gh pr edit "$PR_NUM" --repo "$OWNER/$REPO" --add-reviewer @copilot`
- Repository-configured automatic review: no manual trigger; record that the head is waiting for the configured GitHub App reviewer

Record the current `headRefOid`, request mechanism, and request timestamp in the session notes or PR checklist.

### 5. Poll without spamming

Wait 3-5 minutes between polls. Re-read PR state, latest reviews, top-level comments, and inline comments. Repeated request comments before the previous request has resolved add noise and can obscure the audit trail.

### 6. Interpret reactions conservatively

Treat queue or acknowledgement reactions as in-progress signals, not approval. A positive no-comment signal can clear the head only when it is tied to the current request or current head and no newer actionable comments exist.

### 7. Match review result to the current head

If the review body or API object names a reviewed commit, compare it with current `headRefOid`. If the reviewed commit is stale, the current head is not clear. If the reviewer does not expose an explicit reviewed commit, use the best available evidence: request timestamp, review `commit_id`, PR head at review submission time, and absence of newer pushes.

### 8. Fetch actionable findings

Use the COR-1612 three-surface fetch pattern: inline review comments, review summaries, and top-level PR conversation comments. If a comment may be stale, fetch thread-aware state before treating it as a fresh blocker.

### 9. Process findings through COR-1612

Classify each finding as blocking, advisory, question, or incorrect. Fix blocking issues and adopted advisories in focused commits, reply with verified behavior claims, and keep reviewer-thread resolution discipline per COR-1612.

### 10. Restart after every push

Every push creates a new `headRefOid`. Return to Step 1, then request or wait for a review of that new head. A clean review of the old head does not clear the new one. Do not assume re-review is automatic; some reviewers must be explicitly requested again after a push.

### 11. Stop only when the current head is clear

The loop is complete when the latest bot result applies to current `headRefOid`, no new actionable comments remain, required checks are settled, and no review request for the current head is still pending.

---

## Completion Criteria

- Current `headRefOid` is recorded.
- Latest review result is matched to current `headRefOid`, or a no-suggestion signal is tied to the current request/head.
- No new actionable PR comments remain unhandled.
- Relevant validation or CI has passed after the last fix push.
- Any remaining blockers are explicitly external to the GitHub App review loop.

---

## Pitfalls

- **Mistaking acknowledgement for approval:** queue reactions are not completed reviews.
- **Reviewing the wrong commit:** a review of one SHA does not clear a later push.
- **Duplicate triggers:** repeated request comments while one is pending make the timeline noisy.
- **Flat-comment staleness:** REST comment lists do not prove a thread still applies to the current diff.
- **Wrong visible-write identity:** project/user routing may require a specific GitHub account for public comments.
- **Private environment leakage:** never include local-only network or host details in public PR text.

---

## Examples

### Example 1 - Queue reaction only

1. The operator posts one review request.
2. The reviewer reacts with an acknowledgement.
3. `gh pr view` still shows no review for the current `headRefOid`.
4. Correct action: wait and poll again. Do not treat the reaction as approval and do not post another request.

### Example 2 - Fix push after a blocking comment

1. A review of `abc123` reports a blocking inline comment.
2. The operator fixes it locally, validates, commits, and pushes `def456`.
3. The old review is stale because it covered `abc123`.
4. Correct action: restart the loop for `def456`.

### Example 3 - Copilot reviewer request

1. The PR needs GitHub Copilot code review.
2. The operator requests Copilot as reviewer with `gh pr edit "$PR_NUM" --repo "$OWNER/$REPO" --add-reviewer @copilot`.
3. After a fix push, the operator does not assume Copilot will re-review automatically.
4. Correct action: restart the loop for the new head and request re-review if the project requires it.

### Example 4 - Old inline comment appears near a new diff line

1. The flat comments endpoint returns an old bot comment.
2. The diff line has moved since the original review.
3. The operator fetches thread-aware state and sees the thread is outdated.
4. Correct action: do not re-fix the stale comment unless the underlying issue still exists.

---

## References

- OpenAI Codex GitHub integration: https://developers.openai.com/codex/integrations/github
- GitHub Copilot code review: https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-05 | Initial COR-level version promoted from BAB-1504, generalized from Codex-specific Babs wording to GitHub App PR review bots. | Codex |
