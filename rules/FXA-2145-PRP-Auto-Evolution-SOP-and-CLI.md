# PRP-2145: Auto-Evolution SOP and CLI

**Applies to:** FXA project
**Last updated:** 2026-03-30
**Last reviewed:** 2026-03-30
**Status:** Approved

---

## Scope

**In scope (Phase 1):**

- `FXA-2146-REF-Evolution-Philosophy.md` — north star document (ACID pre-assigned: FXA-2146)
- `FXA-XXXX-SOP-Evolve-SOP.md` — evolve-sop procedure (ACID assigned in CHG)
- `FXA-XXXX-SOP-Evolve-CLI.md` — evolve-cli procedure (ACID assigned in CHG)
- `FXA-XXXX-REF-Evolve-Run-*.md` — per-run log documents (ACID dynamically assigned at run time)

**Out of scope (Phase 1):**

- `af evolve-sop` / `af evolve-cli` CLI commands — deferred to Phase 2
- Subprocess wiring in `af` itself — deferred to Phase 2
- Cron scheduling — deferred to Phase 2
- Changes to existing COR-* documents or existing `af` commands

**Branch naming (change-producing runs only):** When a run produces a passing change, it opens a GitHub issue (`gh issue create`), then creates a branch `chore/<issue-number>-evolve-sop-YYYYMMDD` or `chore/<issue-number>-evolve-cli-YYYYMMDD`, conforming to COR-1502. The PR auto-closes the issue on merge. No-op runs (no candidate passes the Evaluator) create only the run log REF and exit — no issue or branch is created.

---

## What Is It?

Two independent self-improvement SOPs for the alfred project, invoked via `claude -p`:

- **`FXA-XXXX-SOP-Evolve-SOP`** — periodically discovers improvements to SOPs and documents, creates PRPs/CHGs, implements them, and opens a PR for human review
- **`FXA-XXXX-SOP-Evolve-CLI`** — periodically discovers improvements to the `fx_alfred` Python codebase, creates CHGs/PRPs following alfred's own document lifecycle, implements them, and opens a PR for human review

Both SOPs are executed by Claude Code via `claude -p`, pointing to the respective SOP file. Claude's built-in tools (Read, Write, Edit, Bash, Glob, Grep) handle all file operations and shell commands. After implementation, Codex and Gemini perform parallel code review before the branch is pushed.

**Phase 2:** `af evolve-sop` / `af evolve-cli` CLI commands will be added as thin wrappers invoking `claude -p` as a subprocess. Deferred until the manual flow is validated.

---

## Problem

Alfred's SOPs and CLI code currently improve only through manual human-initiated sessions. There is no automated feedback loop to:

1. Detect drift between SOPs and actual usage patterns
2. Identify code quality issues, missing tests, or refactoring opportunities
3. Apply the "compression as intelligence" principle continuously — converting natural language logic into deterministic Python and reducing redundancy

---

## Proposed Solution

### Evolution Philosophy (REF document)

A new `FXA-2146-REF-Evolution-Philosophy.md` document defines the north star for all evolution decisions. Both evolve SOPs read this at the start of each run.

```
North Star: Compression as Intelligence
  — same behavior, minimum code + documentation

Direction Priority:
  1. Determinism first: natural language → Python code
  2. Minimization second: shortest unambiguous expression

Fitness Function: same behavior / (lines of code + document words)
```

### Feature A: Evolve-SOP

**Information sources (Generator input):**

| Source | How collected |
|--------|--------------|
| Document health | `af validate --json` |
| Content analysis | Read all SOPs, check logic gaps vs COR-0002 |
| GitHub Issues | Issues labeled `agent-input` |
| Session logs | Claude Code session history for SOP violation patterns |

**Generator → Evaluator separation:**

Claude first produces a candidate improvement list (Generator role), then switches prompt context to evaluate each candidate (Evaluator role — skeptical by default):

| Dimension | Weight | Measures |
|-----------|--------|---------|
| Necessity | 30% | Evidence from validate output / issues / logs |
| Consistency | 25% | No conflict with other SOPs or COR-0002 |
| Atomicity | 20% | Preserves COR-1400 (one SOP = one thing) |
| Actionability | 15% | Agent can execute the SOP more precisely after change |
| Impact | 10% | How frequently referenced; how significant the improvement |

Candidates scoring < 7.0 are discarded. The threshold and weights are stored in the REF document and can be updated via the standard PRP/CHG lifecycle — not by the evolve SOP directly.

**Execution path:** See `### Execution path (D4 resolved)` below — that section is the single authoritative path for all changes.

### Feature B: Evolve-CLI

**Information sources (Generator input):**

| Source | How collected |
|--------|--------------|
| Test failures | `pytest --json-report` |
| Code quality | `ruff check --output-format=json` |
| Coverage gaps | `pytest --cov --cov-report=json` |
| Source analysis | Read `fx_alfred/src/fx_alfred/`, identify duplication / missing edge handling |
| SOP vs code gap | `af --root /path/to/fx_alfred list --type SOP` to enumerate SOPs, then `af --root /path/to/fx_alfred read <ACID>` to inspect each SOP's Steps section vs actual implementation |

**Evaluator rubric:**

| Dimension | Weight | Measures |
|-----------|--------|---------|
| Test verifiability | 35% | pytest can cover the change; result is observable |
| Scope restraint | 30% | Change boundary is clear, does not cascade into unrelated modules |
| Backward compatibility | 20% | Existing CLI interface unchanged |
| Necessity | 15% | Concrete evidence (test failure / lint / duplication) not "feels improvable" |

Candidates scoring < 7.0 are discarded.

**Execution path:** See `### Execution path (D4 resolved)` below — that section is the single authoritative path for all changes.

**Prerequisites (declared here, added to `pyproject.toml` in CHG):** `pytest-json-report`, `pytest-cov` — required for the signal collection step.

**Source path:** `fx_alfred/src/fx_alfred/` (relative to alfred repo root).

### Invocation mechanism

**Phase 1 (initial):** Operator runs manually from the terminal:

```bash
# All af commands require --root pointing to alfred_ops, or run from that directory.
claude -p "Follow the SOP at $(af --root /path/to/fx_alfred where FXA-XXXX-SOP-Evolve-SOP)"
```

No subprocess wiring in `af` itself at this stage. No new `af` commands in Phase 1. This lets the operator observe the full session before any automation.

**Phase 2 (future):** Once the manual flow is validated, `af evolve-sop` / `af evolve-cli` commands are added as thin wrappers that invoke `claude -p` as a subprocess. Failure handling and exit code contract defined in the CHG for Phase 2.

### Evolution run log (IPC contract)

Every evolution run — whether it produces a change or not — creates a REF document recording the session:

```
FXA-XXXX-REF-Evolve-Run-YYYYMMDD-HHMMSS.md
```

ACID is dynamically assigned by the evolve SOP at run time via:

```bash
af --root /path/to/fx_alfred create ref --prefix FXA --area 21 --title "Evolve-Run-YYYYMMDD-HHMMSS"
```

Contents: signals collected, candidates generated, Evaluator scores and discards, review scores (Codex + Gemini), final decision (change implemented / no change / aborted), and the resulting CHG/PRP ACID if applicable.

**No-op run persistence (Phase 1):** No-op runs (no candidate passes the Evaluator) create the run log REF in `alfred_ops/rules/` via `af create ref` — the same path as all other documents. The file remains as an uncommitted working-tree file; the operator decides whether to delete it, commit it, or commit it and then archive it (`af update <identifier> --status Deprecated`).

This REF is the IPC contract between the evolve SOP and any downstream automation. It is also the audit trail for tuning Evaluator thresholds.

**Review gate rule:** Both Codex and Gemini must score `>= 9.0`. Review is dispatched via `/trinity` (USR-layer skill — prerequisite for running the evolve SOPs). If either reviewer scores below, the evolve SOP iterates following COR-1602 round rules, which is the standard review mechanism invoked by COR-1102 at the PRP stage. In Phase 1 the operator observes the full session and can interrupt at any point.

### Execution path (D4 resolved)

Regardless of change size, the path is always:

```
PRP → Codex+Gemini review PRP → CHG → implement → hard gate → Codex+Gemini review code → git push → PR
```

No "small change" shortcut. The PRP step ensures every evolution decision is documented before implementation begins.

### Git / PR pattern

Every run that produces a passing change:

1. Opens a GitHub issue (`gh issue create`), then creates branch `chore/<issue-number>-evolve-sop-YYYYMMDD` or `chore/<issue-number>-evolve-cli-YYYYMMDD` from `main`
2. Implements changes on the branch
3. Passes all hard gates (`af validate` or `pytest + ruff`)
4. Passes Codex + Gemini review (both >= 9.0, iterate until pass)
5. `gh pr create` with a standard PR template (template to be defined in CHG)
6. PR description auto-populated from the run log REF document: signals, discards, scores, change summary
7. Human merges (Phase 1); auto-merge possible in Phase 2

**External tooling:** `gh` CLI for all GitHub operations. Requires `gh auth login` pre-configured.

### Cron (future)

```bash
# Enable when ready — not part of initial implementation
0 */8  * * *  cd /path/to/alfred && af evolve-sop
0 */12 * * *  cd /path/to/alfred && af evolve-cli
```

---

## Open Questions

1. **Evaluator calibration**: ~~Starting thresholds are untested.~~ **Resolved**: Initial values are `< 7.0` discard and `>= 9.0` review pass, matching the existing COR-1608/1609/1610 rubric standard. Thresholds and weights are stored in the Evolution Philosophy document and can be updated via the standard PRP/CHG lifecycle after the first 5–10 runs — not by the evolve SOP directly.

2. **Session log format**: ~~Need to confirm Claude Code session log location and format.~~ **Resolved**: Session logs are an optional signal source. If unavailable or format-incompatible, the evolve SOP skips this source and proceeds with `af validate` + content analysis + GitHub Issues. No hard dependency on session logs.

3. **Codex + Gemini review integration**: ~~Exact invocation mechanism to be decided.~~ **Resolved**: The evolve SOP instructs Claude (via `claude -p`) to dispatch review using the trinity skill (`/trinity`). Consistent with USR-layer rule.

4. **Evolution Philosophy document layer**: ~~Should the Evolution Philosophy document live at PRJ or USR layer?~~ **Resolved**: PRJ layer (`FXA-2146`) for now. Future consideration: if evolution is to run across multiple machines sharing the same repo, the run logs and philosophy doc are already synchronized via git — no additional mechanism needed for Phase 1.

5. **Risk section**: ~~Failure modes need to be enumerated.~~ **Resolved** — see Risks section below.

---

## Risks

| Risk | Consequence | Mitigation |
|------|-------------|------------|
| evolve SOP modifies itself | Evolution logic corrupted; next run unpredictable | evolve SOPs explicitly prohibited from modifying `FXA-XXXX-SOP-Evolve-*` and `FXA-2146-REF` |
| Fitness function perverse incentive | Deleting code scores high but may remove necessary logic | pytest hard gate + human PR review |
| PR accumulation | One PR per run floods the repo | Check for open evolve PR before starting; skip if one exists |
| External signal noise | Spam `agent-input` labels trigger meaningless changes | Evaluator Necessity 30% weight filters weak candidates |
| Infinite review loop | Codex/Gemini never reach 9.0 | Follows COR-1602 round limits; Phase 1 operator can interrupt at any point |
| Run log accumulation | REF files grow unbounded | Periodic archival via `af update <identifier> --status Deprecated` |
| No-op run repo noise | Uncommitted REF file accumulates in alfred_ops/rules/ | No-op run logs are uncommitted working-tree files; operator decides to commit, archive, or delete |

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-30 | Initial version from brainstorming session | Frank + Claude |
| 2026-03-30 | Resolved all 3 Open Questions before review | Frank + Claude |
| 2026-03-30 | Incorporate R1 review feedback: D1 IPC/invocation, D4 execution path, D5 gh CLI; flag D2/D3 as open | Frank + Claude |
| 2026-03-30 | Resolve R2 blocking issues: D6 add Scope section (Phase 1 = docs only, af commands deferred), D7 remove stale execution paths from Feature A/B, D8 fix source path + pytest prereqs + COR-1602 alignment | Frank + Claude |
| 2026-03-30 | Resolve R3 blocking issues: D9 What Is It rewritten as SOPs not af commands, D10 branch naming via gh issue create (COR-1502 compliant), D11 fix stale source path in Feature B, D12 run-log ACID dynamically assigned, D13 archival status Deprecated, D14 review loop termination via COR-1602 | Frank + Claude |
| 2026-03-30 | Resolve R4 blocking issues: D15 af create ref command fully specified, D16 clean up af evolve-* terminology to SOP names, D17 FXA-2146 ACID pre-assigned in Scope | Frank + Claude |
| 2026-03-30 | Resolve R5 blocking issues: D18 run-log REF added to Scope, D19 no-op run behavior clarified (no issue/branch on no-op), D21 Feature B SOP inspection via af read, D22/D23 trinity USR prereq + COR-1602/COR-1102 relationship, D24-D26 af update syntax fix + no-op noise risk added; D20 rejected as false positive | Frank + Claude |
| 2026-03-30 | Resolve R6 blocking issues: D27 FXA-2146 mutation boundary clarified (threshold updates via PRP/CHG only), D28 no-op run log committed to main with chore commit, D29 af commands updated with --root alfred_ops throughout | Frank + Claude |
| 2026-03-30 | Resolve R7 blocking issue: D30 no-op run log local-only in Phase 1 (not committed to git), avoiding branch/PR rule contradiction | Frank + Claude |
| 2026-03-30 | Resolve R8 blocking issue: D31 no-op run log written to alfred_ops/rules/ via af create ref (same as all docs), stays as uncommitted working-tree file; operator decides to commit/archive/delete | Frank + Claude |
| 2026-03-30 | R9 PASS: Gemini 9.8 + Codex 9.1. PRP approved. Minor advisory fixes: no-op risk row updated to D31 semantics, archive option clarified to require prior commit | Frank + Claude |
