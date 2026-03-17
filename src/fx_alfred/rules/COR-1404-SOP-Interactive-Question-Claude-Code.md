# SOP-1404: Interactive Question — Claude Code Implementation

**Applies to:** Projects using Claude Code
**Last updated:** 2026-03-17
**Last reviewed:** 2026-03-17

---

## What Is It?

The Claude Code implementation of COR-1403 (Interactive Question Principle). Specifies how to use the `AskUserQuestion` tool for interactive option selection.

---

## Tool

**AskUserQuestion** — Claude Code's built-in interactive selection tool.

---

## Usage

```
AskUserQuestion(questions=[{
    "question": "Which approach should we use?",
    "header": "Approach",
    "options": [
        {"label": "Option A (Recommended)", "description": "Why this is good"},
        {"label": "Option B", "description": "Why this is different"}
    ],
    "multiSelect": false
}])
```

---

## Rules

1. **Use `AskUserQuestion`** for all multiple-choice questions per COR-1403
2. **`header`** — keep under 12 characters, acts as a short label
3. **`options`** — 2-4 options, each with `label` and `description`
4. **`multiSelect`** — set to `true` only when choices are not mutually exclusive
5. **`preview`** — use for comparing code snippets, UI mockups, or config examples
6. **Recommended option** — put it first in the list and append "(Recommended)" to the label

---

## Examples

| Scenario | header | Options |
|----------|--------|---------|
| Architecture choice | "Architecture" | 2-3 approaches with trade-off descriptions |
| Version format | "Format" | Format options with preview showing examples |
| Next priority | "Priority" | 2-4 tasks with impact descriptions |

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-17 | Initial version, split from COR-1403 | Claude Code |
