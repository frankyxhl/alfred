# CHG-2320: Promote Sandboxed Worker CLI Dispatch To COR Layer

**Applies to:** FXA project
**Last updated:** 2026-07-03
**Last reviewed:** 2026-07-03
**Status:** Completed
**Date:** 2026-07-03
**Requested by:** Frank Xu (session request: make the codex-worker pipeline reusable across all GitHub projects)
**Priority:** Medium
**Change Type:** Normal
**Targets:** src/fx_alfred/rules/COR-1628-SOP-Sandboxed-Worker-CLI-Dispatch.md (new), src/fx_alfred/rules/COR-1629-REF-Loop-Config-Starter-Template.md (new), src/fx_alfred/rules/COR-0000-REF-Document-Index.md

---

## What

Two new PKG-layer documents promoting the validated codex-worker dispatch practice from session memory to the shared COR layer:

- **COR-1628 SOP — Sandboxed Worker CLI Dispatch**: the dispatch contract for implementation workers running as external one-shot sandboxed CLIs (reference: `codex exec`). Invocation contract (6 rules), seven-block task-brief template, sandbox scope clause, orchestrator verification checklist, failure-mode table, guard rails.
- **COR-1629 REF — Loop Config Starter Template**: a copy-paste blank instantiation form for COR-1622 with the COR-1628 worker lane and COR-1507 two-worker options pre-wired. Normative definitions stay in COR-1622; the template defers to it on conflict.


## Why

The alfred #282/#283 dispatches proved the lane works (first-try 2/2, triad 9.1–9.5, ~⅕–⅓ orchestrator token cost) but every hard-won operational rule lived only in one machine's session memory. Concretely observed and unrecoverable by other adopters without promotion:

- `codex exec` hangs forever on inherited non-tty stdin (burned a 10-minute timeout)
- foreground shells kill real-length runs
- the sandboxed worker read the repo's orchestrator-facing CLAUDE.md (via the AGENTS.md symlink) and spent 3+ minutes retrying trinity review against a network it does not have
- COR-1622 instantiation currently requires reading a 300-line schema doc with only a historical worked example as guidance

PKG layer is the correct home: it ships with `pip install fx-alfred`, so every repo running `af` inherits both docs. Project-specific values (identities, providers) remain per-project via COR-1622 instantiation — the same separation COR-1622 itself established (its Why cites the identical promotion rationale from TRN-1008).


## Impact Analysis

- **Systems affected:** PKG rules corpus only (two new docs + COR-0000 index rows). No code paths change; `af` behavior identical.
- **Consumers:** COR-1628/1629 are `optional-overlay` — adopters opt in by pointing `<worker-agent>` at a sandboxed CLI lane or using the starter template. Non-adopters see two extra `af list` rows.
- **No cascade:** COR-1617/1619/1622 are referenced, not edited. COR-1628 specializes COR-1619's WORKER leaves without amending them.
- **Rollback plan:** delete the two COR docs, revert the COR-0000 rows, revert this CHG to Rolled Back, `af index` to refresh the PRJ index.


## Implementation Plan

1. Author COR-1628 following COR-1619's section conventions; content sourced from the verified session evidence (alfred #282/#283 logs).
2. Author COR-1629 with the complete COR-1622 key list (verified against the schema doc at authoring time).
3. Add COR-0000 index rows + change-history entry.
4. Validate: full pytest (docs drift/format tests), `af validate`, `af fmt --check` on the new docs.
5. Triad review (COR-1602, COR-1609 rubric for this CHG + doc quality), then PR.

---

## Change History

| Date       | Change                                                   | By          |
|------------|----------------------------------------------------------|-------------|
| 2026-07-03 | Initial version                                          | Claude Code |
| 2026-07-03 | Implemented: COR-1628 + COR-1629 authored, index updated | Claude Code |
