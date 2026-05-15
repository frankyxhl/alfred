# SOP-1623: PR Review Thread Watchdog

**Applies to:** FXA project
**Last updated:** 2026-05-15
**Last reviewed:** 2026-05-15
**Status:** Active
**Related:** COR-1615, COR-1612, COR-1623
**Inherits from:** COR-1623

---

## What Is It?

An Alfred-project adapter that turns `COR-1623` from a per-thread verification
procedure into an explicitly started watch loop. It scans open Alfred PRs,
selects only PRs that meet the review-thread verification trigger, and then
hands those candidates to `COR-1615`, `COR-1612`, and `COR-1623` in order.
It does not redefine `COR-1623` evidence, classification, or resolution rules.

## Why

`COR-1623` intentionally does not run as a daemon. It verifies a known candidate
thread after the PR review loop suggests that a bot may be blocked by diff-window
limits. Alfred still needs a local project convention for the operator request
"watch the repo for review-thread cleanup opportunities" so agents know when
they may self-scan open PRs instead of waiting for a PR number.

---

## Adapter Boundary

`FXA-1623` owns Alfred-local discovery and scheduling: repository default,
poll interval, candidate PR gates, stop conditions, and final reporting.

`COR-1623` owns per-thread verification: thread fetch shape, PR head source
comparison, classification, evidence requirements, and resolution safety. If
this adapter diverges from `COR-1623`, use `COR-1623` for the per-thread
decision and update this adapter afterward.

## When to Use

- The operator explicitly asks to watch, scan, or keep checking Alfred PR review
  threads.
- A session has just pushed review fixes and must self-poll under `COR-1612`.
- The repo may have open PRs with bot review threads that are unresolved even
  though fixes appear to be present.

## When NOT to Use

- As an unbounded background daemon. This SOP only runs inside an active session
  or an explicitly configured scheduler.
- When there are no open PRs.
- When open threads are clearly design discussions or genuinely unimplemented
  requests; route those through `COR-1612` instead.
- When CI or current-head bot review has not completed yet; use `COR-1615` to
  reach a stable head first.

---

## Defaults

- **Repository:** `frankyxhl/alfred`
- **Poll interval:** 5 minutes
- **Default watch window:** 30 minutes or until no candidate PR remains,
  whichever comes first
- **Candidate PR:** open, non-draft, current-head CI green, GitHub App review
  complete for the current `headRefOid`, and at least one unresolved review
  thread
- **Escalation:** stop and report if a thread is `GENUINELY-OPEN` or
  `NEEDS-FOLLOWUP`; do not hide real work by resolving it

## Steps

1. **Declare the watch window** — State the repository, poll interval, and stop
   time before the first scan. If the operator did not specify values, use the
   defaults above.
2. **List candidate PRs** — Scan open PRs:

   ```bash
   gh pr list --repo frankyxhl/alfred --state open \
     --json number,title,isDraft,headRefOid,reviewDecision,statusCheckRollup,url
   ```

   Stop the loop if this returns no open PRs. If the command fails because of
   auth, rate-limit, network, or GitHub API errors, report the error and retry
   on the next poll; do not treat a failed scan as an empty repo.
3. **Apply the coarse gate** — Skip draft PRs, PRs with failing/pending required
   checks, and PRs whose latest GitHub App review does not match the current
   `headRefOid`. Use `COR-1615` for current-head matching. Re-check the PR
   `headRefOid` immediately before classifying threads; if it changed since
   Step 2, restart the gate for that PR.
4. **Enumerate unresolved threads** — For each gated PR, run `COR-1623` Step 1
   to fetch unresolved, non-outdated review threads. If no unresolved threads
   remain, mark the PR clear for this SOP.
5. **Classify each candidate thread** — For each unresolved thread, run
   `COR-1623` Steps 2-4 and classify it as `RESOLVED-IN-CODE`,
   `GENUINELY-OPEN`, or `NEEDS-FOLLOWUP`.
6. **Act by classification** —
   - `RESOLVED-IN-CODE`: post or reply with file-path-and-line evidence, then
     wait for the original reviewer to resolve the GitHub thread. Do not
     self-resolve, even when visible write actions are authorized.
   - `GENUINELY-OPEN`: leave the thread open and route to `COR-1612` for a fix
     or explicit response.
   - `NEEDS-FOLLOWUP`: leave the thread open and report the remaining gap.
7. **Poll or stop** — If the watch window remains open, sleep for the poll
   interval and return to Step 2. In shell sessions, the default 5-minute poll
   interval is `sleep 300`. Stop immediately when all open PRs are clear, when
   the watch window expires, or when a real follow-up is required.
8. **Report outcome** — Summarize scanned PRs, thread classifications, actions
   taken, validation commands, and any PRs that still need human/operator work.

---

## Examples

Default operator request:

> Watch Alfred PR review threads for 30 minutes and close resolved bot threads.

Agent execution:

1. State: "Using `FXA-1623`: repo `frankyxhl/alfred`, 5-minute interval,
   30-minute window."
2. Run the PR list command from Step 2.
3. For every gated PR, apply `COR-1615`; if current-head review is complete,
   enumerate unresolved threads.
4. For each unresolved thread, run `COR-1623` classification.
5. Reply only to `RESOLVED-IN-CODE` threads with evidence, route real gaps
   through `COR-1612`, and report the final PR/thread list.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-15 | Initial version: Alfred-local watchdog adapter for scanning open PRs and invoking COR-1615/COR-1612/COR-1623 only when candidate review threads exist. | Codex |
| 2026-05-15 | Trinity review fixes: align RESOLVED-IN-CODE action with COR-1612/COR-1623 no-self-resolve policy, remove misleading `mergeable` scan field, and document scan failure, head-change, and poll sleep behavior. | Codex |
