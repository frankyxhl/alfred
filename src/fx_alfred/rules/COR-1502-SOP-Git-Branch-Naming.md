# SOP-1502: Git Branch Naming

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-12
**Last reviewed:** 2026-03-12
**Status:** Active

---

## What Is It?

A standardized naming convention for git branches. Ensures every branch is traceable to an issue, communicates intent at a glance, and keeps the repository organized.

---

## Why

Consistent branch names make it easy to trace work back to issues, understand branch purpose at a glance, and keep the repository navigable as the team scales.

---

## When to Use

- Creating any new branch in a project that uses the COR document system
- Naming branches for features, fixes, chores, docs, refactors, tests, or hotfixes

---

## When NOT to Use

- Repositories that have their own established branch naming convention outside the COR system
- Temporary local-only branches that will never be pushed to a remote

---

## Branch Name Format

```
<type>/<issue-number>-<short-description>
```

- **type** — categorizes the work (see table below)
- **issue-number** — GitHub issue number for traceability
- **short-description** — 2-5 words in kebab-case summarizing the change

---

## Type Prefixes

| Prefix | Use When |
|--------|----------|
| `feat/` | Adding a new feature |
| `fix/` | Fixing a bug |
| `chore/` | Tooling, CI/CD, configuration, dependencies |
| `docs/` | Documentation only |
| `refactor/` | Code restructuring without behavior change |
| `test/` | Adding or updating tests only |
| `hotfix/` | Urgent production fix (branches from `main`, merges back immediately) |

---

## Rules

1. **All lowercase** — no capital letters
2. **Kebab-case** — use hyphens (`-`) to separate words, never underscores or spaces
3. **Always include issue number** — every branch must trace to a GitHub issue
4. **Keep it short** — description should not exceed 5 words
5. **No special characters** — only `a-z`, `0-9`, `-`, and `/`

---

## Examples

| Issue | Branch Name |
|-------|-------------|
| #1 pyproject.toml + CalVer | `feat/1-pyproject-calver` |
| #2 CI/CD pipeline | `chore/2-ci-pipeline` |
| #3 Attachment upload | `feat/3-attachment-upload` |
| #15 Pane parser crash | `fix/15-pane-parser-crash` |
| #20 Update README | `docs/20-update-readme` |

---

## Steps

### Creating a branch

```bash
# From up-to-date main
git checkout main
git pull origin main

# Create and switch to new branch
git checkout -b feat/1-pyproject-calver
```

### Merging back

```bash
# Push branch and create PR
git push -u origin feat/1-pyproject-calver
gh pr create --title "[enhancement] Add pyproject.toml and CalVer" --body "Closes #1"
```

---

## Safety Notes

- Never push directly to `main` — always use a branch + PR
- Delete branches after merge to keep the repo clean
- If no issue exists yet, create one first (see project's Create-GitHub-Issue SOP)

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-12 | Initial version, synced from BLA-1008 | Claude Code |
| 2026-03-14 | PDCA + Johnny Decimal migration: renamed from ALF-1008 to ALF-2401 | Claude Code |
| 2026-03-20 | Added Why/When to Use/When NOT to Use sections per ALF-2210 | Claude Code |
