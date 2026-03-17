# SOP-1405: Interactive Question — GitHub Copilot Implementation

**Applies to:** Projects using GitHub Copilot (VS Code / CLI)
**Last updated:** 2026-03-17
**Last reviewed:** 2026-03-17

---

## What Is It?

The GitHub Copilot implementation of COR-1403 (Interactive Question Principle). Specifies how to use interactive question tools across Copilot environments.

---

## VS Code — Prompt Files

In VS Code prompt files (`.github/copilot-instructions.md` or `.prompt.md`), reference the built-in tool:

```
#tool:vscode/askQuestion
```

This tool is documented in VS Code prompt-file tooling and allows agents to gather user input during workflows.

Note: the exact tool name may appear as `vscode/askQuestion` or `vscode/askQuestions` depending on the VS Code version. Check your environment's available tools.

---

## Copilot CLI

In interactive mode (the default), the CLI supports user prompts natively. The agent can pause execution to gather user input while maintaining session context. This behavior is environment-dependent and may vary by CLI version.

---

## Future

Full `AskUserQuestion`-style interactive sessions (with structured options UI) are tracked in [VS Code Issue #285321](https://github.com/microsoft/vscode/issues/285321) (status: Open/Backlog). When this lands, this SOP should be updated.

The underlying ask-user primitive was implemented in [VS Code Issue #285952](https://github.com/microsoft/vscode/issues/285952) (status: Closed, landed Jan 2026).

---

## Rules

1. **Use `vscode/askQuestion`** in VS Code prompt files for user input per COR-1403
2. **Use interactive prompts** in Copilot CLI sessions
3. **2-4 options** with clear labels — same as COR-1403
4. **One question per message** — same as COR-1403
5. **Mark recommended option** — put it first and append "(Recommended)"

---

## Fallback

If the tool is unavailable (older Copilot version, unsupported environment), fall back to numbered lists:

```
Pick one:

1. **Option A (Recommended)** — description
2. **Option B** — description

Reply with the number.
```

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-17 | Initial version, split from COR-1403 | Claude Code |
| 2026-03-17 | Corrected: distinguish documented prompt-file tooling from open feature requests; clarify CLI behavior is environment-dependent | Claude Code |
