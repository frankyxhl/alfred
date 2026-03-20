# SOP-1403: Interactive Question Principle

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-17
**Last reviewed:** 2026-03-17
**Status:** Active

---

## What Is It?

A constraint requiring agents to use the platform's interactive selection tool instead of plain text when asking the user to choose between options. This ensures consistent UX and reduces friction.

---

## Why

Interactive selection tools reduce user friction and eliminate ambiguity compared to plain-text option lists.

---

## When to Use

- Choosing between approaches or architectures
- Selecting a configuration or parameter
- Deciding next steps or priorities
- Any multiple-choice situation

## When NOT to Use

- Open-ended questions with no predefined options ("What do you want to build?")
- Yes/no confirmations where the context is obvious
- Follow-up clarifications within an ongoing discussion

---

## Rule

When asking the user a question that involves choosing between options:

1. **Always use the platform's interactive selection tool** — never present choices as plain text
2. **Provide 2-4 options** with clear labels and descriptions
3. **Mark a recommended option** when you have a preference — add "(Recommended)" to the label
4. **One question per message** — don't batch multiple unrelated questions

See platform-specific SOPs for the exact tool to use:
- Claude Code: COR-1404
- GitHub Copilot: COR-1405

---

## How to Check

Ask yourself:
1. Am I presenting 2 or more options to the user?
2. Could the user answer by selecting rather than typing?

If both are yes → use the interactive selection tool.

---

## Examples

| Violation | Fix |
|-----------|-----|
| "Do you want A, B, or C?" as plain text | Use the interactive selection tool with 3 options |
| Listing options with bullet points and asking "which one?" | Use the interactive selection tool |
| Asking two questions in one message | Split into two separate interactive questions |

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-17 | Initial version | Claude Code |
| 2026-03-17 | Generalized to platform-agnostic principle, moved Claude Code specifics to COR-1404 | Claude Code |
| 2026-03-20 | Added Why/When to Use/When NOT to Use sections per ALF-2210 | Claude Code |
