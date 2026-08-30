# CHG-2329: Enable Semantic-Release Automation: SEMANTIC_RELEASE_PAT

**Applies to:** FXA project
**Last updated:** 2026-08-30
**Last reviewed:** 2026-08-30
**Status:** Approved
**Date:** 2026-08-30
**Requested by:** Frank Xu (owner request via pfc, 2026-08-30)
**Priority:** High
**Change Type:** Normal
**Targets:** repository secret `SEMANTIC_RELEASE_PAT` (frankyxhl/alfred), rules/FXA-2328 status

---

## What

An operator runbook that turns FXA-2328's automated release pipeline on:
create a GitHub classic PAT, store it as the `frankyxhl/alfred` repository
secret `SEMANTIC_RELEASE_PAT`, and verify the merge-to-main →
`cd-release.yml` → `publish.yml` → PyPI chain fires end to end. No code
changes — one secret plus this runbook. FXA-2328's status moves from
Proposed to In Progress (implemented, awaiting the secret).

## Why

`cd-release.yml` (FXA-2328) needs a real-account token: it checks out,
pushes the version-bump commit and tag to `main`, and creates the GitHub
Release that triggers `publish.yml`. The default `GITHUB_TOKEN` cannot do
this — events created by `GITHUB_TOKEN` never fire downstream workflows, so
a release it made would leave the PyPI publish step dead. v1.29.0
(2026-08-30) shipped via the FXA-2102 manual fallback for exactly this
reason: the pipeline's first automated run (the #330 merge) failed at
checkout with `Input required and not supplied: token`.

## Impact Analysis

- **Systems affected:** one repository secret plus documents (this runbook, FXA-2328 status, REF-0000 index row). No runtime code.
- **Security:** the PAT value never touches a file, a commit, or a chat — `gh secret set` takes it from the clipboard straight into GitHub's encrypted secret store. Expiry is chosen at creation; rotating is just steps 2–3 again.
- **Rollback plan:** `gh secret delete SEMANTIC_RELEASE_PAT --repo frankyxhl/alfred`. Releases fall back to the FXA-2102 manual flow (proven by v1.29.0); retire this runbook if it stays unused.

## Implementation Plan

Executable step by step by Frank's local Codex session (or Frank himself).

1. **Context** — read FXA-2328 and this doc. `gh auth status` shows which
   account drives `gh`; any account with write access can create the PAT,
   but it must belong to someone who can push the release commit to `main`
   (e.g. `frankyxhl` or `ryosaeba1985`).
2. **HUMAN-ONLY — create the PAT in the GitHub UI.** github.com →
   Settings → Developer settings → Personal access tokens → Tokens
   (classic) → Generate new token (classic). Scope: `repo`. Pick an expiry
   that matches your rotation appetite (e.g. 90 days or custom; FXA-2328
   calls this a one-time operator action, but a finite lifetime is good
   hygiene — repeat steps 2–3 to rotate). GitHub shows the token value
   **exactly once**: copy it to the clipboard immediately. It must never be
   pasted into a file, a commit, a message, or shell history.
3. **Store it** — `gh secret set SEMANTIC_RELEASE_PAT --repo frankyxhl/alfred`,
   then paste from the clipboard and press Enter. Nothing is written to
   disk; do not redirect into a file and do not pass the value inline.
4. **Verify** — `gh secret list --repo frankyxhl/alfred` lists
   `SEMANTIC_RELEASE_PAT`. Then trigger the chain with a trivial
   conventional-commit PR (branch → merge — e.g. a one-line `docs:`
   touch-up; `docs` maps to a patch bump per FXA-2328). Bind every check
   to **that merge's exact runs** — a bare `gh run list --limit 1` can
   show an older run before the new one is dispatched, which would let
   FXA-2328 close without validating this chain:
   ```bash
   MERGE_SHA=$(gh pr view <PR#> --repo frankyxhl/alfred --json mergeCommit --jq .mergeCommit.oid)

   # cd run — poll until dispatch lists it (bounded: 30 × 10 s), then watch
   CD_RUN=""
   for i in $(seq 30); do CD_RUN=$(gh run list --repo frankyxhl/alfred --workflow=cd-release.yml \
       --commit "$MERGE_SHA" --json databaseId --jq '.[0].databaseId'); [ -n "$CD_RUN" ] && break; sleep 10; done
   [ -n "$CD_RUN" ] || { echo "cd-release run for $MERGE_SHA never appeared"; exit 1; }
   gh run watch "$CD_RUN" --repo frankyxhl/alfred --exit-status   # green → version-bump commit + tag + GitHub Release

   # the release THIS cd run created — createdAt after the run started (the
   # release concurrency group serialises cd runs); NOT the repo-global latest,
   # so a non-release-worthy merge fails loudly instead of re-verifying an old release
   CD_START=$(gh run view "$CD_RUN" --repo frankyxhl/alfred --json createdAt --jq .createdAt)
   TAG=$(gh release list --repo frankyxhl/alfred --limit 20 --json tagName,createdAt \
       --jq ".[] | select(.createdAt > \"$CD_START\") | .tagName" | head -n1)
   [ -n "$TAG" ] || { echo "cd-release green but created no release (merge not release-worthy?)"; exit 1; }

   # publish run — dispatched by the release event on the tagged release commit;
   # poll until discoverable (bounded: 30 × 10 s), then watch
   PUB_RUN=""
   for i in $(seq 30); do PUB_RUN=$(gh run list --repo frankyxhl/alfred --workflow=publish.yml \
       --event release --limit 10 --json databaseId,displayTitle \
       --jq ".[] | select(.displayTitle == \"$TAG\") | .databaseId"); [ -n "$PUB_RUN" ] && break; sleep 10; done
   [ -n "$PUB_RUN" ] || { echo "publish run for $TAG never appeared"; exit 1; }
   gh run watch "$PUB_RUN" --repo frankyxhl/alfred --exit-status
   pip index versions fx-alfred             # (or the PyPI JSON API) shows the TAG version
   ```
   Both run lookups poll until the run is listed instead of one
   instantaneous query. The publish run's head SHA is **not** `MERGE_SHA`
   on this path: cd-release commits the CHANGELOG promotion and
   semantic-release commits the version bump, and the tag lands on that
   release commit — hence the `release`-event + tag-title binding. Re-running
   the old failed
   run (`gh run rerun 33302010976`) replays the #330 commit — prefer the
   branch→merge trigger, which exercises the chain as designed.
5. **Close out** — once step 4 passes end to end, the owner flips
   **FXA-2328 → Completed** (and its REF-0000 index row), noting the
   passing run in FXA-2328's Change History. Until then FXA-2328 stays
   **In Progress — implemented, awaiting the secret**, and merges to
   `main` keep a harmless red ✗ on `cd-release.yml` (checkout fails; the
   FXA-2102 manual flow remains the shipping path).

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-08-30 | Initial version — operator runbook (owner request via pfc); FXA-2328 flipped Proposed → In Progress (implemented, awaiting the secret) | alfred (pi/GLM) |
| 2026-08-30 | R1 (codex P2 on PR #335): step 4 now binds the merge's exact run IDs (`gh run list --commit "$MERGE_SHA"` + `gh run watch --exit-status`) instead of `--limit 1` listings, which could show an older run and let FXA-2328 close unvalidated | alfred (pi/GLM) |
| 2026-08-30 | R2 (codex P2 on PR #335): the publish run's head SHA is the tagged release commit (CHANGELOG promotion + version-bump commits precede the tag on the automated path), not MERGE_SHA — publish binding switched from `--commit "$MERGE_SHA"` to `--event release` + `displayTitle == "$TAG"` | alfred (pi/GLM) |
| 2026-08-30 | R3 (codex P2 ×2 on PR #335): both run lookups now poll until the run is listed (bounded 30 × 10 s loops) instead of one instantaneous query; TAG is derived from the cd run's own time window (`createdAt` after `gh run view $CD_RUN --json createdAt`), so a non-release-worthy merge fails loudly instead of re-verifying the repo-global latest release | alfred (pi/GLM) |
