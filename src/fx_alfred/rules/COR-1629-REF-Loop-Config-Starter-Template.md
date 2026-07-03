# REF-1629: Loop Config Starter Template

**Applies to:** Any project adopting the COR-1617 Multi-Agent Workflow Loop
**Last updated:** 2026-07-03
**Last reviewed:** 2026-07-03
**Status:** Active
**Tags:** workflow
**Related:** COR-1622 (parameter schema — normative key definitions), COR-1617 (umbrella SOP), COR-1628 (sandboxed worker CLI lane), COR-1507 (two-worker TDD)
**Disposition:** optional-overlay

---

## What Is It?

A copy-paste starter for the PRJ-layer instantiation document that COR-1622 requires of every adopting project. COR-1622 defines the keys normatively and shows a worked example with one project's historical values; this REF is the blank form: every key, a placeholder, and a short prompt for what to put there — with the sandboxed-worker (COR-1628) and two-worker-TDD (COR-1507) options pre-wired as commented choices.

Time to instantiate a new repo: about ten minutes with `af create`.

## How to Use

1. `af create REF --prefix <PRJ-PREFIX> --area workflow --title "Multi-Agent Loop Configuration" --layer project`
2. Paste the template below into the created document; replace every `⟨…⟩` placeholder.
3. Delete the option comments you did not take.
4. `af validate --root .` and reference the doc's ACID from your project's routing doc.

Key definitions, valid enums, and defaults are normative in COR-1622 — when this template and COR-1622 disagree, COR-1622 wins.

## Template

```markdown
## Identity & Repo

| Key | Value |
|-----|-------|
| `<repo>` | ⟨owner/name⟩ |
| `<repo-owner>` | ⟨owner⟩ |
| `<repo-trusted-reactor-list>` | [⟨owner⟩] |
| `<gh-write-identity>` | ⟨gh account for all public writes; verify via gh auth status⟩ |
| `<pr-push-remote>` | ⟨origin for single-remote repos; fork name otherwise; default: fork⟩ |

## Intake

| Key | Value |
|-----|-------|
| `<consent-signal>` | rocket ⟨default; enum per COR-1622: rocket, +1, heart, hooray, eyes⟩ |
| `<intake-quality-mode>` | ⟨default: 1FA; 2FA if an intake bot applies quality labels⟩ |
| `<intake-quality-label>` | ⟨unset, or e.g. blueprint-ready⟩ |
| `<intake-quality-applier-set>` | ⟨unset, or [bot-login, owner]⟩ |

## Review Panel

| Key | Value |
|-----|-------|
| `<panel-providers>` | ⟨e.g. [glm, deepseek, minimax]; ≥3 viable verdicts required⟩ |
| `<weights-doc>` | ⟨scalar ACID, or map {CHG: …, ADR: …, RFC: …, inline-PR-body: …}⟩ |
| `<spec-format>` | ⟨default: CHG; or ADR / RFC / inline-PR-body⟩ |
| `<panel-pass-threshold>` | 9.0 |

## Workers

| Key | Value |
|-----|-------|
| `<worker-agent>` | ⟨option A: subagent worker, e.g. "trinity-glm via droid exec"⟩ |
|  | ⟨option B: sandboxed CLI per COR-1628, e.g. "codex exec (COR-1628 lane)" — brief template, invocation contract, and verification checklist in COR-1628⟩ |
| `<worker-min-loc>` | 30 |
| `<test-writer-worker-agent>` | ⟨unset = two-worker split OFF; set to a different model or a verified-fresh :instance suffix to enable COR-1507, e.g. "trinity-glm:writer"⟩ |

## Convergence & Retry

| Key | Value |
|-----|-------|
| `<max-r-count>` | 10 |
| `<max-r-count-extension>` | 3 |
| `<convergence-severity>` | advisory |
| `<cli-retry-attempts>` | 3 |
| `<cli-retry-backoff-seconds>` | 600 |
| `<cli-retry-on-failure>` | ⟨default: pause-and-ask; or mark-non-viable / abort-loop⟩ |

## Bots & Readiness

| Key | Value |
|-----|-------|
| `<bot-actors>` | ⟨e.g. [chatgpt-codex-connector[bot]]; [] if none⟩ |
| `<required-check-policy>` | branch-protection-required-or-all-statusCheckRollup |
| `<review-decision-policy>` | APPROVED_OR_NULL |
| `<merge-state-policy>` | CLEAN |
| `<human-gate-owner>` | ⟨default: repo-owner; change only if delegated⟩ |

## Runtime

| Key | Value |
|-----|-------|
| `<wakeup-tool>` | ScheduleWakeup |
| `<idle-cap>` | 12 |
| `<merge-watch-cap>` | 24 |
```

## Recommended Repo Additions (non-loop)

- **CLAUDE.md "Sandboxed worker scope" section** (if `<worker-agent>` is a COR-1628 lane and AGENTS.md symlinks to CLAUDE.md): the clause text is in COR-1628 §Sandbox Scope Clause.
- **Provider calibration notes**: known CLI quirks (degenerate responses, retry recipes) — keep in a project or user-level doc the orchestrator reads before writing worker prompts.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-07-03 | Initial version — extracted from FXA-2276 instantiation experience + COR-1628 lane | Claude Code |
