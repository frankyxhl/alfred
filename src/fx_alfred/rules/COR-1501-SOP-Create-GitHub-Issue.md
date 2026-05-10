# SOP-1501: Create GitHub Issue

**Applies to:** Repos using the Iterwheel intake bots (`iterwheel-blueprint[bot]` for body intake, `iterwheel-stack[bot]` for `stack-*` label pairs). The procedure (template, CLI, verify) generalizes; the label tables below reflect alfred's labels and must be substituted for repos with a different label set.
**Last updated:** 2026-05-10
**Last reviewed:** 2026-05-10
**Status:** Active
**Last executed:** 2026-05-10 (issue #126)

---

## What Is It?

A standardized process for creating GitHub issues as task tickets. Ensures every issue has clear context, acceptance criteria, and traceability.

---

## Why

Consistent issue structure makes triage faster, reduces back-and-forth clarification, and ensures traceability from requirement to implementation.

---

## When to Use

- Creating a new task, bug report, or enhancement request
- Tracking SOP-driven work items
- Recording follow-ups from session retrospectives

## When NOT to Use

- Trivial fixes that can be done in the current session without tracking
- Discussion-only topics better suited for GitHub Discussions or comments
- Work already captured in an existing open issue

---

## Prerequisites

- GitHub repo with remote configured
- `gh` CLI installed and authenticated (`gh auth status`)

---

## Issue Template

This SOP defers to each repo's `.github/ISSUE_TEMPLATE/blueprint.md` (the Iterwheel Blueprint template) as the source of truth. Repos that have the `iterwheel-blueprint[bot]` installed require the H2 sections below; the bot applies the `blueprint-ready` label + 🚀 reaction only when every section is present and at least one concrete `- [ ]` item appears under `## Acceptance Criteria`.

```markdown
## Work Type

<short paragraph: code / docs / refactor / repo hygiene / governance / SOP / infra>

## Problem / Goal

<what is broken / missing / desired — user-visible outcome, not implementation>

## Context

- **Source:** <SOP number, session retrospective, prior PR, or user request>
- **Related files:** <list of relevant files or paths>
- **Related issue:** <other issue numbers, if any>
- **Depends on:** <blocker issue numbers, if any>

## Expected Outcome

<one paragraph describing the end state a future reader could verify against>

## Acceptance Criteria

- [ ] First concrete, verifiable criterion
- [ ] Add more as needed

## Reproduction Steps / Task Plan

1.
2.
3.

## Priority

P2 — <one-line justification>

## Requester / Owner

- **Requester**: @<github-handle>
- **Owner**: TBD

## Out of Scope (optional)

<explicit non-goals; delete the section if not applicable>
```

---

## Steps

### 1. Determine issue type and area

This repo (alfred) uses paired `stack-type-*` + `stack-area-*` labels (the `iterwheel-stack[bot]` may auto-classify, but pre-applying the correct pair speeds intake). The pair replaces older single-label conventions like `sop` / `automation` / `bug` / `enhancement` / `docs` — do not use those on alfred.

If you are following this SOP from a non-alfred repo, run `gh label list --repo <owner>/<repo>` first to enumerate the actual labels there, and substitute the correct pair into Step 3's `--label` argument; the framework (`stack-type-*` + `stack-area-*` pair model, blueprint template, `[Type]:` title chip, `--repo` flag, `gh issue view` verify) is portable, but the specific label values below are not.

**Type labels** (`stack-type-*` — pick exactly one):

| Label | Use when |
|-------|----------|
| `stack-type-task` | General work item or governance ticket (default for SOP-driven work) |
| `stack-type-bug` | Something is broken |
| `stack-type-feature` | New capability |
| `stack-type-docs` | Documentation-only change |
| `stack-type-refactor` | Internal restructuring with no behavior change |
| `stack-type-chore` | Repo hygiene / housekeeping |
| `stack-type-ci` | CI / build pipeline change |
| `stack-type-test` | Test-only change |
| `stack-type-spike` | Investigation / time-boxed prototype |

**Area labels** (`stack-area-*` — pick exactly one):

| Label | Use when |
|-------|----------|
| `stack-area-github` | GitHub-side surface (Actions, issues, repo config) |
| `stack-area-automation` | Scripts, Makefile targets, agents |
| `stack-area-docs` | Documentation surfaces (`docs/`, `rules/`, governance) |
| `stack-area-ci` | CI workflows, build / publish |
| `stack-area-tests` | Test infrastructure |
| `stack-area-backend` | Server / library code |
| `stack-area-frontend` | UI / client code |
| `stack-area-infra` | Hosting, runtime, deployment, environments |
| `stack-area-unknown` | Area cannot be determined yet — `iterwheel-stack[bot]` may rewrite this on intake |

If you mis-pair, `iterwheel-stack[bot]` may swap one label after intake (observed on issue #127: hand-applied `stack-area-docs` was replaced with `stack-area-github`). Treat that as confirmation, not a rejection.

### 2. Write the issue

Use the blueprint template under §Issue Template above. Keep the title short (<70 chars); put details in the body.

Title format: `[Task]: <one-line summary>` (matches `.github/ISSUE_TEMPLATE/blueprint.md`'s `title:` field).

Examples:
- `[Task]: Add make add-channel command`
- `[Task]: Codex relay 401 when started via nohup`
- `[Docs]: Add COR-1501 route to FXA-2125 decision tree`

The leading `[<Type>]` chip should align with the `stack-type-*` label (e.g. `[Task]` ↔ `stack-type-task`, `[Docs]` ↔ `stack-type-docs`).

### 3. Create via CLI

```bash
gh issue create \
  --repo <owner>/<repo> \
  --title "[Task]: <one-line summary>" \
  --body "$(cat <<'EOF'
## Work Type

<short paragraph>

## Problem / Goal

<user-visible outcome>

## Context

- **Source:** <SOP-NNNN / session retrospective / user request>
- **Related files:** <paths>
- **Related issue:** <#NNN>
- **Depends on:** <#NNN or None>

## Expected Outcome

<one paragraph end-state>

## Acceptance Criteria

- [ ] <first concrete criterion>

## Reproduction Steps / Task Plan

1.
2.

## Priority

P2 — <justification>

## Requester / Owner

- **Requester**: @<github-handle>
- **Owner**: TBD
EOF
)" \
  --label "stack-type-task,stack-area-docs"
```

The `--repo` flag is required when the working directory is not the target repo's clone (common when following an SOP from a different project).

### 4. Verify

```bash
gh issue view <number> --repo <owner>/<repo>
```

`gh issue list` only confirms the issue exists; `gh issue view` confirms the body rendered correctly and lets you inspect intake-bot signals — look for `blueprint-ready` (intake passed) or `blueprint-requests-revision` (a required H2 section is missing or `- [ ]` is absent under `## Acceptance Criteria`). If revision is requested, edit the body via `gh issue edit <number> --repo <owner>/<repo> --body-file <path>` and re-verify (the same `--repo` rule from Step 3 applies — without it, `gh` falls back to the current working directory's repo).

Once `blueprint-ready` is confirmed, validate content quality per **COR-1506** before assigning to an implementer or submitting for COR-1617 autonomous auto-pick.

---

## Naming Conventions

| Field | Convention |
|-------|-----------|
| Title prefix chip | `[Task]:`, `[Bug]:`, `[Feature]:`, `[Docs]:`, etc. (matches `stack-type-*` family) |
| Labels | One `stack-type-*` + one `stack-area-*` (paired) |
| Assignee | Owner of the work, or unassigned with `Owner: TBD` |
| Milestone | Optional, for grouping related work |

---

## Safety Notes

- One issue per task — don't bundle unrelated work
- Reference SOP numbers in issues for traceability
- Close issues with a comment explaining what was done

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-08 | Initial version | Claude Code |
| 2026-03-14 | PDCA + Johnny Decimal migration: renamed from ALF-1003 to ALF-2101 | Claude Code |
| 2026-03-20 | Added Why/When to Use/When NOT to Use sections per FXA-2223 | Claude Code |
| 2026-05-10 | issue #127: align with current alfred repo conventions — stack-type-* + stack-area-* label pair (replaces old `sop`/`automation`/etc. taxonomy), Iterwheel Blueprint template (replaces Summary/Context template), `[Task]:` title chip, `--repo` flag in CLI example, `gh issue view` verify with intake-bot label check | Claude Opus 4.7 |
| 2026-05-10 | issue #136: added COR-1506 quality-gate pointer after blueprint-ready verify step | Claude Sonnet 4.6 |
