# PRP-2126: AF Create Routing Shortcut

**Applies to:** FXA project
**Last updated:** 2026-03-20
**Last reviewed:** 2026-03-20
**Status:** Rejected
**Related:** ALF-2206, FXA-2124, COR-1103

---

## What Is It?

Add a shortcut command to quickly create workflow routing documents for USR and PRJ layers, so new machines and new projects can set up routing with one command instead of manual file creation.

---

## Problem

After ALF-2206, `af guide` scans three layers for routing documents (`*-SOP-Workflow-Routing*.md`). PKG is bundled in the package, but USR and PRJ need to be created manually on each machine/project:

1. User must know the naming convention (`*-SOP-Workflow-Routing*.md`)
2. User must know to set `Status: Active`
3. User must know the section structure (USER CONTEXT / PROJECT CONTEXT / GOLDEN RULES)
4. Without USR/PRJ routing docs, `af guide` shows "no active routing document found" for those layers

A shortcut command eliminates this friction.

## Scope

**In scope:**
- New command or subcommand: `af create routing` (or `af init routing`)
- Creates a USR or PRJ routing document from a template
- Auto-detects layer: if `--layer user` → USR, otherwise → PRJ
- Pre-fills with placeholder content matching the expected section structure

**Out of scope:**
- Changing `af guide` behavior (already done in FXA-2124)
- Auto-populating routing docs from existing project SOPs
- Syncing USR layer across machines (dotfiles concern)

## Proposed Solution

### Command signature

```bash
af create routing [--layer user|project] [--prefix PREFIX]
```

- `--layer user`: creates in `~/.alfred/` (USR layer)
- `--layer project` (default): creates in `./rules/` (PRJ layer)
- `--prefix`: project prefix (e.g., FXA, ALF). Required for PRJ, defaults to ALF for USR.
- ACID: auto-assigned via `--area` logic from existing `af create`

### Template: USR routing doc

```markdown
# SOP-{{ACID}}: Workflow Routing USR

**Applies to:** All projects
**Last updated:** {{DATE}}
**Last reviewed:** {{DATE}}
**Status:** Active

---

## What Is It?

User-level workflow routing supplement. Cross-project preferences and rules.

---

## User Context

- (add your cross-project preferences here)

## User Golden Rules

```
(add your cross-project rules here)
```

---

## Change History

| Date | Change | By |
|------|--------|----|
| {{DATE}} | Initial version | — |
```

### Template: PRJ routing doc

```markdown
# SOP-{{ACID}}: Workflow Routing PRJ

**Applies to:** {{PREFIX}} project
**Last updated:** {{DATE}}
**Last reviewed:** {{DATE}}
**Status:** Active

---

## What Is It?

Project-level workflow routing. Project-specific SOP mappings and workflows.

---

## Project Context

- (add your project-specific SOP mappings here)

## Project Golden Rules

```
(add your project-specific rules here)
```

---

## Change History

| Date | Change | By |
|------|--------|----|
| {{DATE}} | Initial version | — |
```

### Behavior

1. Check if a routing doc already exists in the target layer (scan for `*-SOP-Workflow-Routing*.md`)
2. If exists and Active → error: "Routing document already exists: <filename>"
3. If exists and Deprecated → allow creation (new one takes precedence)
4. Create the document using the appropriate template
5. Print: "Created <filename>. Run `af guide` to verify."

## Open Questions

1. Should this be `af create routing` (subcommand of create) or `af init routing` (new top-level command)?
2. Should the command auto-detect the project prefix from existing PRJ documents?

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version | Frank + Claude Code |
