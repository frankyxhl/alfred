# SOP-1505: Branch and Identity Hygiene

**Applies to:** All projects using the COR document system; required by COR-1617 phase 2
**Last updated:** 2026-05-09
**Last reviewed:** 2026-05-09
**Status:** Active
**Related:** COR-1502 (Git Branch Naming), COR-1617 (Multi-Agent Workflow Loop), COR-1622 (parameter schema — `<gh-write-identity>`, `<pr-push-remote>`)
**Disposition:** inherit-only

---

## What Is It?

The pre-flight gate that every new PR branch must pass before any local commit or remote push. Two checks, run in order:

1. **Branch base** — the new branch is created from a freshly-fetched `origin/main`, with no uncommitted local state shadowing the upstream tree.
2. **GitHub identity** — the active `gh` account matches the project's configured `<gh-write-identity>` so that PRs, issue comments, and review submissions are authored by the intended account.

---

## Why

Three failure modes recur when this gate is skipped:

1. **Stale-branch base** — branching off a local `main` that lags `origin/main` produces phantom-reference bugs: a panel reviewer (or CI) flags a file the local thinks exists but origin has already moved or deleted. Fixing the symptom (re-add the file) compounds the divergence.
2. **Silent overwrite of untracked drafts** — `git checkout main` with untracked files in `tmp/`, `samples/`, or new spec drafts can destroy hours of unstaged work. `git status -uno` (tracked-only) is not sufficient; only `--porcelain` (which includes untracked) protects.
3. **Wrong-identity commits** — pushing under the wrong `gh` account creates GitHub-visible artifacts (PRs, issue comments, review approvals) authored by an identity the project did not authorize. Per global guidance, this is a CLAUDE.md-level violation requiring immediate close-and-replace.

---

## When to Use

- Before creating any new branch that will become a PR.
- Before the first push of a session, even on a branch already created — re-pin base + identity.
- Before any GitHub-visible write (PR open, issue comment, review submission).

## When NOT to Use

- Local-only branches that will never push to origin or fork (experimentation, scratch work).
- Repositories that have no fork-PR workflow (direct-commit-to-main is governed by other SOPs and is out of scope here).

---

## Steps

### 1. Branch base (pre-create)

```bash
git fetch origin main
git status --porcelain        # MUST be empty (covers tracked + untracked)
                              # if non-empty: stash with `git stash -u`,
                              # commit elsewhere, or abort
git log origin/main --oneline -3   # verify expected merge state
```

The `--porcelain` flag is non-negotiable. Earlier wordings used `-uno` (tracked-only) and silently destroyed untracked drafts when `git checkout main` ran. If `--porcelain` reports any line, stash (`git stash -u`) or move it before continuing.

### 2. Branch create (create-only)

```bash
git switch -c <type>/<issue-number>-<short-description> origin/main || {
    # Lowercase -c is create-only and FAILS if the branch already exists.
    # This protects against silently overwriting unpushed work from an
    # aborted earlier attempt or a parallel session. Uppercase -C
    # (force-create-or-reset) is forbidden here because it would reset an
    # existing branch with unpushed commits to origin/main and orphan them.
    echo "ERROR: branch already exists. Manual intervention required:" >&2
    echo "  1. Resume — git switch <branch> and verify base is origin/main" >&2
    echo "  2. Fresh — git branch -D <branch> (only after confirming no" >&2
    echo "     unpushed commits matter), then re-run" >&2
    echo "  3. Stash unpushed work elsewhere first, then choose 1 or 2" >&2
    exit 1
}
```

Branch naming follows COR-1502 (`<type>/<issue-number>-<short-description>`).

### 3. Identity gate (pre-push)

```bash
gh auth status               # must show: <gh-write-identity> active
```

If the wrong account is active, abort. Public artifacts authored by the wrong identity are a CLAUDE.md-level violation.

When this SOP runs inside COR-1617, `<gh-write-identity>` comes from the project's COR-1622 instantiation. Outside that context, the identity is whatever the project's contribution guide names; if no guide exists, surface the question to the user before proceeding.

---

## Guard Rails

- Never use `git status -uno`. Untracked-file blindness is the failure mode.
- Never use `git switch -C` (uppercase) to create a branch. Force-create silently overwrites unpushed work.
- Never push to `origin/main` from this branch. Push to `<pr-push-remote>` (default `fork`).
- Never bypass the identity gate. A passing `gh auth status` is the consent signal for any GitHub-visible write.

---

## Failure Modes

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `git status --porcelain` reports `?? tmp/...` | Untracked draft from a prior session | `git stash -u` or move file out of repo before branching |
| `git switch -c` exits non-zero with "already exists" | Aborted prior attempt OR parallel session | Choose option 1/2/3 from the error message; do NOT auto-delete |
| `gh auth status` shows wrong account | Multi-account `gh` host with stale active marker | `gh auth switch -u <gh-write-identity>` then re-run check |
| PR opened under wrong identity discovered post-push | Identity gate skipped | Close PR; re-open from `<gh-write-identity>`; report both PRs to the user |

---

## Examples

Parameterized invocation (substitute your project's `<gh-write-identity>` and `<pr-push-remote>` from its COR-1622 instantiation):

```bash
git fetch origin main
git status --porcelain                                    # (empty)
git switch -c <type>/<issue-number>-<short-description> origin/main           # (created)
gh auth status                                            # must show <gh-write-identity> active
# ... commits ...
git push <pr-push-remote> <type>/<issue-number>-<short-description>
```

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-09 | Initial version — extracted from TRN-1008 §2 for COR-1617 cluster promotion (alfred#115) | Claude Opus 4.7 |
| 2026-05-09 | R2: §Examples replaced literal `ryosaeba1985` with parameterized `<gh-write-identity>` per glm R1 P1 finding (de-Babs leak) | Claude Opus 4.7 |
| 2026-05-09 | R3: §Examples now uses `<issue-number>`/`<short-description>` to match §Steps + COR-1502 canonical names (was `<issue>`/`<slug>`); deepseek R2 advisory | Claude Opus 4.7 |
| 2026-05-09 | FXA-2277: `<fork-remote>` references renamed to `<pr-push-remote>` (3 sites — frontmatter Related, §Guard Rails, §Examples + §Examples shell snippet). Semantic invariant preserved. | Claude Opus 4.7 |
