# Alfred — Cross-Platform Agent Skill

Drop-in instructions that teach an AI coding agent to use the **`af` CLI**
(Alfred — Agent Runbook) as its workflow runbook: route with `af guide`, plan
with `af plan`, declare the active SOP, and review before committing.

This bundle is **CLI-dynamic** — it assumes `af` is installed and contains
**instructions only, no scripts**. The agent calls `af` through its own shell.

## What's here

| File | Serves | Trigger |
|------|--------|---------|
| `alfred-contract.md` | canonical source of truth (do not copy directly) | — |
| `claude/SKILL.md` | Claude Code | on-demand (`/alfred` or description match) |
| `agents/AGENTS.md` | Codex · droid · opencode (Copilot also reads root `AGENTS.md`) | always-on |
| `copilot/copilot-instructions.md` | GitHub Copilot | always-on |

The three carriers embed the **same** contract body between
`<!-- alfred-contract:start -->` / `<!-- alfred-contract:end -->` markers.
`tests/test_agent_skill_drift.py` fails CI if any carrier drifts from
`alfred-contract.md`, so always edit the canonical file and re-sync the
carriers — never hand-edit a carrier's marked region.

## Bootstrap (any platform)

```bash
af --version          # need >= 1.19 (root auto-discovery)
# if missing/older:
uv tool install fx-alfred   # or: pipx install fx-alfred / pip install fx-alfred
```

## Placement matrix

| Platform | Copy the carrier to | Scope |
|----------|---------------------|-------|
| Claude Code | `.claude/skills/alfred/SKILL.md` (project) or `~/.claude/skills/alfred/SKILL.md` (global) | on-demand `/alfred` |
| Codex CLI | repo-root `AGENTS.md` or `~/.codex/AGENTS.md` | always-on |
| droid (Factory) | repo-root `AGENTS.md` or `~/.factory/AGENTS.md` | always-on |
| opencode (SST) | repo-root `AGENTS.md` or `~/.config/opencode/AGENTS.md` | always-on |
| GitHub Copilot | `.github/copilot-instructions.md` (also reads repo-root `AGENTS.md`) | always-on |

> **Platform reference is a 2026-06 snapshot.** File names, locations, and
> trigger semantics across these ecosystems change; re-verify against each
> platform's current docs before relying on a placement.

## If the target already has an `AGENTS.md`

**Append — never replace.** Overwriting a collaborator's `AGENTS.md` is data
loss. Paste the contract as a clearly-headed section and review it for any
conflict with instructions already present:

```markdown
## Alfred Workflow

<!-- alfred-contract:start -->
...contract body from alfred-contract.md...
<!-- alfred-contract:end -->
```

Only a fresh repo with no `AGENTS.md` should copy `agents/AGENTS.md` wholesale.

Once pasted into another repo, that copy is **yours to keep in sync** — this
repo's drift-guard test only covers the carriers under `skills/alfred/`.

## Optional: always-on Claude routing

Claude Code skills are on-demand, so `SKILL.md` will not auto-run `af guide` at
session start. If you want that, add a one-line import to the project (or
global) `CLAUDE.md` instead of, or in addition to, the skill:

```markdown
@skills/alfred/alfred-contract.md
```

(`@file` imports require a Claude Code version that supports them; older
versions silently ignore the line.)
