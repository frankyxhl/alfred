# Changelog

## v1.19.0 (2026-06-11)

Quality-and-correctness release: nine reviewed PRs (#190–#198) clearing the
2026-06-10 full-project review backlog. Every change passed a three-model
review panel (30 verdicts, all >= 9.0) plus per-PR bot review.

### New Features

- **Project-root auto-discovery** — when `--root` is absent, every command
  resolves the nearest ancestor directory whose `rules/` contains Alfred
  documents (non-COR), falling back to the working directory exactly as
  before. Run `af` from any project subdirectory. Explicit `--root` always
  wins. (FXA-2300, #196)
- **`af validate` unknown-TYPE warnings** — a filename TYPE code outside the
  known set (SOP/PRP/CHG/ADR/REF/PLN/INC) now emits a per-document warning
  instead of silently skipping Status and type-specific checks. Text mode
  prints `~`-prefixed lines and the summary appends `, N warning(s)`; `--json`
  results gain an additive `warnings` array. Warnings never affect the exit
  code. (FXA-2296, #192)

### Bug Fixes

- **`af plan` silently dropped steps** — `extract_section` terminated
  sections at `#`-prefixed lines inside fenced code blocks (e.g. bash
  comments), truncating the Steps sections of 10 bundled/user SOPs
  (COR-1612 rendered 1 of 8 authored steps). Section boundary detection is
  now fence-aware. (FXA-2294, #190)
- **Step renderers counted body lines as steps** — with sections no longer
  truncated, nested numbered lists and fenced numbered lines could inflate
  checklists (COR-1612: 21 items for 8 steps, duplicate indices). Renderers
  now apply flush-left + fence-aware + heading-form-preference discipline;
  validation stays permissive so loop/branch references keep resolving.
  (FXA-2294 R2, #190)
- **CJK content escaped in `--json`** — `af list/read/status` emitted
  `ensure_ascii` JSON, turning Chinese document content into `\uXXXX`
  escapes. All command JSON now goes through one emitter: indented,
  raw UTF-8. (FXA-2301, #197)

### Improvements

- **CI matrix + type/format gates** — tests now run on Python 3.10, 3.12,
  and 3.14 (the `requires-python >= 3.10` claim was previously untested);
  `pyright` and `ruff format --check` are CI-enforced. (FXA-2298, #194)
- **`core/` is now enforceably framework-agnostic** — `compose.py` (the lone
  violator) raises domain `CompositionError` instead of `ClickException`;
  an architecture guard test forbids Click imports under `core/` forever.
  (FXA-2295, #191)
- **Fence tracking has one implementation** — five inline CommonMark fence
  loops consolidated onto `parser.iter_lines_with_fence_state`, guarded by
  a fingerprint test. (FXA-2294/2299, #190/#195)
- **`plan_cmd` decomposed** — the 376-line main function is now 76 lines of
  orchestration over 8 named functions; duplicate todo builders merged onto
  one classification path; an AST ratchet caps command-function length
  (pre-existing oversized functions pinned shrink-only). Verified
  byte-identical CLI output across 7 modes. (FXA-2302, #198)
- **Unified JSON/exit conventions** — one `emit_json` helper, named
  `SCHEMA_VERSION` constants, `ctx.exit` everywhere; three architecture
  guards keep the conventions enforced. (FXA-2301, #197)
- **Agent runbook refreshed with drift guards** — project CLAUDE.md caught
  up (6 undocumented commands, 19 missing modules, broken smoke paths);
  `tests/test_docs_drift.py` pins the command list and module inventory to
  the code. (FXA-2297, #193)

### Stats

- 1000 tests (65 new), all passing on 3.10/3.12/3.14
- 11 permanent architecture/drift guard tests added
- 0 breaking changes (CLI surface unchanged; JSON additions are additive;
  `core.compose` consumers: `CompositionError` replaces `ClickException`)

### Install / Upgrade

```bash
pip install fx-alfred==1.19.0       # install specific version
pipx install fx-alfred              # first install
pipx upgrade fx-alfred              # upgrade existing
```

## v1.18.0 (2026-05-17)

Minor release introducing one new CLI subcommand (`af issue lint`) plus a
substantial PKG SOP set adding the two-worker TDD dispatch pattern,
status-communication contract, and author-side issue-quality targets.

### New Features

- **`af issue lint <body-file>`** — Phase 1 MVP pre-creation linter for
  GitHub issue bodies. Detects TBD-after-PR-review anti-patterns
  (5 canonical phrases, case-insensitive substring match). Supports
  `--json` output and `-` for stdin. Closes #169. (#179)

### Docs / SOP

- **PRP-1507 / COR-1500 / COR-1619 / COR-1622 — Two-Worker TDD Dispatch**
  (#177, #178). New opt-in pattern for substantive code-bearing dispatches:
  a test-writer worker writes the failing tests, an implementer worker
  reads only the tests + spec + production source to make them pass —
  structural cross-validation against implement-to-fit bias. Bundled
  CHGs land COR-1500 §Phase 1 Worker assignment + Phase 2 implementer
  reading constraint, COR-1619 new §Two-Worker TDD Dispatch sub-section
  with 8-step contract + symmetric outage fallback + Phase 8 routing,
  COR-1619 §Decision Tree with new gating nodes, COR-1622 new
  `<test-writer-worker-agent>` schema row. Alfred opts in via FXA-2276:
  `<test-writer-worker-agent> = trinity-deepseek` distinct from
  `<worker-agent> = trinity-glm`.
- **COR-1620 §Primitive 5 — Status Communication Contract** (#182).
  Forbids silent wake-and-yield. Every wake-arming MUST pair with a
  status surface (chat update or PR comment) covering: what happened,
  what the wake will check, and applicable counter state. Runtime-
  independent — binding regardless of `<wakeup-tool>` substitution.
- **COR-1501 §Quality Criteria** (#181). Five author-side write-time
  targets for GitHub issue bodies (anchor verbatim, cell-by-cell diff
  for table edits, ≤100 LoC budget, fully pre-committed spec,
  greppable references). Complements the reviewer-side COR-1506 gate.
- **COR-1617 §Phase 1 ↔ COR-1618 §Normative Bypass reconciliation**
  (#180). New "Loop-start (user-initiated)" trigger row covers
  non-naming loop-starter phrases (`pick next issue`, `auto-pick`,
  bare `follow FXA-2276`); only phrases that name a target issue
  (`do PREFIX-NNNN`, `follow FXA-2276 for #N`) qualify for the
  consent-gate bypass. COR-1506 scope extended to rows 2-4. FXA-2276
  deviation note removed.

### Stats

- 935 tests (29 new), all passing.
- 0 breaking changes.
- New CLI subcommand: `af issue lint`.

### Install / Upgrade

```bash
pip install fx-alfred==1.18.0       # install specific version
pipx install fx-alfred              # first install
pipx upgrade fx-alfred              # upgrade existing
```

## v1.17.1 (2026-05-17)

PRJ-layer documentation release. No CLI / behavior changes; new review-loop
watchdog SOP and pre-merge bot sweep gate.

### Docs

- **FXA-1623 PR Review Thread Watchdog** — new PRJ SOP for monitoring open PRs
  for unresolved review threads, with keep-alive on empty scans. (#157, #158)
- **FXA-2285 Pre-Merge GH Bot Review Sweep Gate** — new CHG for a pre-merge
  GitHub App review sweep gate in the agent guide. (#159)
- **FXA-2125 / FXA-2276** — branch 10 entry-point and bypass scoping
  tightening in workflow routing. (#164)
- **COR-1602 / COR-1612 / COR-1615** — review-loop refinements for multi-model
  parallel review, PR review comment responses, and GitHub App bot loop.

### Stats

- 900 tests, all passing.
- 0 breaking changes.

### Install / Upgrade

```bash
pip install fx-alfred==1.17.1       # install specific version
pipx install fx-alfred              # first install
pipx upgrade fx-alfred              # upgrade existing
```

## v1.17.0 (2026-05-15)

Docs-shipped-as-PKG-SOPs release. No CLI / behavior changes; new bundled COR
documents and review-loop SOP refinements.

### Added

- **COR-1623 PR Review Thread Verification** — new PKG SOP for auditing
  unresolved GitHub PR review threads against exact source content at the PR
  head SHA. Covers paginated GraphQL thread enumeration, current-line anchors,
  outdated-thread filtering, fork/head-repository fetches, and per-thread
  classifications (`RESOLVED-IN-CODE`, `GENUINELY-OPEN`, `NEEDS-FOLLOWUP`).
  (PR #153)
- **COR-1506 Review GitHub Issue Quality** — new PKG SOP for post-intake
  quality review of GitHub issues after `iterwheel-blueprint[bot]` grants
  `blueprint-ready`. Scores problem evidence, acceptance criteria, task plan,
  dependencies, and scope boundaries with a weighted rubric. (PR #154)
- **AGENTS.md** symlink to `CLAUDE.md` so Codex and Claude agents read the
  same project instructions from the repo root. (PR #153)

### Changed

- **COR-1617 §Phase 8** — added an R-count cap with adaptive extension for
  review-loop convergence control. (PR #152)
- **COR-1622** — parameterized COR-1617 failure-mode retry behavior through
  the loop configuration schema. (PR #149)
- **COR-1802** — clarified Step 8 template-reference scope and synced the
  FXA-2281 implementation-plan wording. (PRs #150, #151)

### Stats

- 900 tests, all passing.
- 270 documents validated, 0 issues.
- 0 breaking changes.

### Install / Upgrade

```bash
pip install fx-alfred==1.17.0       # install specific version
pipx install fx-alfred              # first install
pipx upgrade fx-alfred              # upgrade existing
```

## v1.16.0 (2026-05-10)

Docs-shipped-as-PKG-SOPs release. No CLI / behavior changes; new bundled COR
documents and SOP refinements.

### Added

- **COR-1802 Build Weighted Decision Matrix** — 8-step process for designing,
  calibrating, and validating weighted scoring rubrics. Includes
  MECE/isolation tests, anchor rules, calibration with known cases, and a
  worked example using COR-1610. (PR #137)
- **COR-1200 §Scoring** — weighted retrospective scoring rubric for Session
  Retrospective: Frequency, Actionability, Impact, Detection gap; threshold
  ≥7.5 = create issue. (PR #138)
- **COR-1617 §Phase 11 Retrospective** — synchronous retrospective phase:
  metrics block, pattern check, CHG nomination, handoff. Loop restart
  renumbered to §12. (PR #141)
- **COR-1622 §Resilience** — CLI/provider-failure retry parameters:
  `<cli-retry-attempts>`, `<cli-retry-backoff-seconds>`, and
  `<cli-retry-on-failure>`. (PR #147)

### Stats

- 900 tests, all passing.
- 267 documents validated, 0 issues.

## v1.15.0 (2026-05-10)

Docs-shipped-as-PKG-SOPs release. No CLI / behavior changes; SOP corrections and refinements.

### Changed

- **COR-1501 Create GitHub Issue** — aligned with current alfred/iterwheel conventions:
  `Applies to:` scoped to repos using iterwheel intake bots; label taxonomy completed with
  `stack-area-infra` and `stack-area-unknown` (9 types, 9 areas); Step 4 edit command uses
  `--body-file`; portability note added for non-alfred repos. (alfred#127, PRs #131)
- **COR-1617 §Phase 10/11** — loop advances when PR becomes mergeable
  (`mergeStateStatus == "CLEAN"`) instead of waiting for merge commit; reduces loop
  latency by ~60 s per iteration. (FXA-2280, PR #129)
- **COR-1617 §Phase 7** — closing-token prescription tightened: bare `Closes #<N>`
  required; verify via `gh pr view <N> --json closingIssuesReferences` before merge;
  phrasings with intervening words silently fail GitHub's auto-linker. (PR #132)

### Fixed

- Nav labels in PKG SOPs now use canonical `PREFIX-ACID` format instead of `TYPE-ACID`. (PR #125)

## v1.14.0 (2026-05-09)

Docs-shipped-as-PKG-SOPs release. No CLI / behavior changes; new bundled COR documents.

### Added

- **COR-1617 Multi-Agent Workflow Loop cluster** — promoted from trinity
  TRN-1008 (alfred#115, PRs #117 + #119). Eleven-phase umbrella SOP
  composing existing PKG SOPs, plus the supporting cluster:
  - `COR-1617` — Multi-Agent Workflow Loop (umbrella).
  - `COR-1618` — Auto-pick consent gate.
  - `COR-1619` — Worker dispatch contract.
  - `COR-1620` — Loop primitives (wakeup, idle-with-retry,
    merge-watch, stop-marker).
  - `COR-1621` — Triage tree + severity vocabulary (P0–P3).
  - `COR-1622` — Parameter schema (instantiated per-project).
- **COR-1612 §Scoping bot reviews via PR body (optional, GitHub App
  review bots only)** — codifies the PR-body scope-hint technique
  observed empirically on alfred PR #117 R11–R12 + PR #119 R1–R5
  (FXA-2279, PR #122). Includes recommended template, when-most-useful
  / when-NOT-useful heuristics, the non-substitution caveat, and the
  evidence table.
- **COR-1615 §Operator Checklist pointer** to COR-1612 §Scoping for
  operators on long iteration loops (FXA-2279, PR #122).
- **`.github/ISSUE_TEMPLATE/blueprint.md`** — Iterwheel Blueprint
  intake template (alfred#116, PR #121). Markdown form (not Issue
  Forms YAML) so the rendered body uses the H2 section headings the
  `iterwheel-blueprint[bot]` intake check detects.

### Changed

- `pyproject.toml` version bump 1.13.0 → 1.14.0.

### Removed

- None.

## v1.13.0 (2026-05-07)

Minor release: per-user document bookmarking via `af star`.

### Added

- **`af star <ID>`** — bookmark a document by its identifier. Accepts
  `PREFIX-ACID` (e.g. `COR-1202`), case-insensitive prefix
  (`cor-1202`), or ACID-only (`1202`). Idempotent. Errors on no-match
  or ambiguous-ACID inputs. (FXA-2274)
- **`af unstar <ID>`** — remove a bookmark. Best-effort resolution:
  works on stale bookmarks (doc deleted), errors on ambiguous
  ACID-only when multiple stored entries match, prefers stale starred
  entries over a different live doc with the same ACID.
- **`af starred [--json]`** — sorted list of bookmarked docs. Marks
  entries that no longer resolve as `(missing)` in text mode and as
  `"missing": [...]` alongside `"starred_docs"` in JSON mode (schema
  version `"1"`).
- **`~/.alfred/preferences.yaml`** — new per-user preferences file
  with a `starred_docs:` key. Created on first `af star`. Atomic
  writes via `tempfile.mkstemp()` + `os.replace()`. Forward-compat:
  unknown top-level keys survive `star`/`unstar` round-trips.

### Internal

- New `src/fx_alfred/core/preferences.py` — framework-agnostic atomic
  YAML I/O with `PreferencesError`, dedup-on-read, and unknown-key
  preservation. Reusable by future per-user-preference features.

### Removed

- The `af tag star/unstar/list` commands and `af list --starred` flag
  introduced briefly on `main` (FXA-2273) were **deleted before
  reaching PyPI**. They starred tag *values* rather than documents,
  which proved overengineered for the actual `Tags:` coverage in real
  document bases (5 of 238 docs in this repo). `af star` is the
  simpler primitive that matches operator intent: bookmark the doc
  itself, no `Tags:` dependency.

### Stats

- 899 tests passing, coverage 95.01%, 0 breaking changes for PyPI
  users (v1.12.0 had neither `af tag` nor `af star`).

### Install / Upgrade

```bash
pip install fx-alfred==1.13.0       # install specific version
pipx install fx-alfred              # first install
pipx upgrade fx-alfred              # upgrade existing
```

## v1.12.0 (2026-05-07)

Minor release: new Contract-First Delivery Workflow SOP, pytest test
governance enforcement, and skills-absorption round 5.

### Added

- **COR-1616 Contract-First Delivery Workflow** — PKG SOP promoted from
  Babs `BAB-1503` per issue #106 into a project-neutral, reusable
  reviewed-delivery loop covering plan review, TDD/BDD/E2E pressure,
  implementation review, privacy/artifact cleanup, identity-correct PR,
  PR review loop, and post-merge reconciliation. Includes Browser-Harness
  BDD Policy, Pitfalls section, and an Adapter SOP example so projects
  can rebase existing SOPs onto `Inherits from: COR-1616`.
  Reviewed via Trinity multi-model parallel review (Gemini, GLM, Codex,
  DeepSeek) — 4/4 PASS in round 2 against the COR-1608 PRP rubric.
  (PR #107)

### Changed

- **COR-1103 Workflow Routing** now surfaces COR-1616 in OVERLAYS and
  Golden Rules so `af guide` routes reviewed delivery slices through the
  new SOP. (PR #107)
- **COR-0000 Document Index** updated to list COR-1616. (PR #107)

### Tests

- **Pytest test governance** enforced: every test file now declares an
  explicit pytest marker, with a CI gate (`tests/test_pytest_markers.py`)
  that fails the build if a new test file lands without one. Reduces
  silent-skip risk and drift in test classification. (PR #103, PR #104)

### Docs

- **Skills-absorption round 5** — COR-1207 (Working in Unfamiliar Code:
  Zoom-Out), COR-1208 (Session Startup Sanity Check), and FXA-2248 SOP
  Outcome Notebook absorbed into the Alfred SOP graph. (PR #105)

### Stats

- 869 tests passing, 0 breaking changes.

### Install / Upgrade

```bash
pip install fx-alfred==1.12.0       # install specific version
pipx install fx-alfred              # first install
pipx upgrade fx-alfred              # upgrade existing
```

## v1.11.0 (2026-05-06)

Feature release: new governance, review, and execution-contract SOPs.

### Added

- **COR-1801 Pattern Promotion** — PKG SOP for promoting project-local
  practices into reusable COR rules, with evidence, risk, rollback, and
  de-promotion criteria. (PR #98, FXA-2239)
- **COR-1705 Code Review Classification System** — REF defining gate/automated/
  human review classifications and P0/P1/P2 severity language for code review
  checklists. (PR #100, FXA-2241)
- **COR-1706 Code Review Structural Checks** — SOP for architecture, API,
  database, and structural review concerns. (PR #100)
- **COR-1707 Code Review Cross-Cutting Concerns** — SOP for security,
  observability, concurrency, migrations, and operational concerns. (PR #100)
- **COR-1708 Code Review Domain-Specific Checks** — SOP for frontend, backend,
  configuration, infrastructure, documentation, and review-quality checks.
  (PR #100)
- **COR-1709 Code Review AI-Assisted Code + Quick Reference** — SOP for
  AI-assisted code review risks and compact PR review checklists. (PR #100)
- **COR-1614 Multi Phase Execution Contract** — PKG SOP promoted from BAB-2218
  for turning approved multi-phase work into reviewable execution slices with
  authority references, operator defaults, validation gates, privacy rules, and
  stop conditions. (PR #101, FXA-2242)

### Changed

- **COR-1615 GitHub App PR Review Bot Loop** now includes a pre-trigger
  finalization gate and decision tree so known closeout/status/index/fixup
  commits happen before manually requesting bot review. This reduces wasted
  review passes while preserving current-head review correctness. (PR #102,
  FXA-2243)
- **COR-1103 Workflow Routing** now routes approved multi-phase continuous
  execution through COR-1614 and links pattern-promotion work to COR-1801.
  (PR #98, PR #101)
- **COR-1613 Council Review** releases its deferred hard-coded COR-1614
  decision-library fallback; any future split uses the next open COR ACID at
  that time. (PR #101)
- **COR-1602 Workflow Multi Model Parallel Review** now links to the expanded
  code-review checklist family. (PR #100)

### Docs

- Added FXA-2240/2241 records for migrating Code Review Checklist v2.0 into
  COR-1705 through COR-1709.
- Added FXA-2242 as the COR-1614 promotion record.
- Added FXA-2243 as the COR-1615 pre-trigger finalization gate record.

### Stats

- 214 documents, 0 validation issues.
- 0 breaking changes.

### Install / Upgrade

```bash
pip install fx-alfred==1.11.0       # install specific version
pipx install fx-alfred              # first install
pipx upgrade fx-alfred              # upgrade existing
```

## v1.10.0 (2026-05-05)

Feature release: agent-editable helpers and reusable skill documents.

### Added

- **`af agent call`** — explicitly gated PRJ/USR Python helper execution with `ALFRED_AGENT_TOOLS=1`, PRJ-over-USR resolution, async helper support, string-only `--arg key=value`, and JSON success/error envelopes. (FXA-2236, issue #94)
- **`af agent run`** — explicitly gated Python script runner using the current interpreter, no shell, and process-style JSON envelopes with `stdout`, `stderr`, and `exit_code`. (FXA-2236)
- **`af skill list/read`** — read-only discovery and reading for REF/SOP documents explicitly tagged with `Tags: skill`, including deterministic task scoring across `Task tags`, `Tags`, title, and body. (FXA-2236)
- **`af plan --with-skills`** — task-scoped skill recommendations appended to text plans and emitted as top-level `recommended_skills` in JSON schema version `3`. (FXA-2236)
- **FXA-2237 usage REF** — examples and safety guidance for agent helpers and skill documents.

### Safety

- Normal `af guide`, `af plan`, `af validate`, and `af skill` paths do not import or execute `agent_helpers.py`.
- Helper execution refuses unless the exact opt-in gate `ALFRED_AGENT_TOOLS=1` is set before import or script execution.

## v1.9.1 (2026-05-05)

Patch release: PKG SOP promotion for GitHub App PR review bot loops.

### Added

- **COR-1615 GitHub App PR Review Bot Loop** — PKG SOP promoted from BAB-1504. Standardizes GitHub App PR review bot triggering, conservative reaction interpretation, current-head matching, stale-thread checks, and handoff to COR-1612 for actionable findings. Covers both OpenAI Codex Connector (`@codex review`) and GitHub Copilot reviewer assignment (`@copilot`). (PR #91, FXA-2234)

## v1.9.0 (2026-05-03)

Feature release: new PKG SOP families from the skills-absorption initiative (Rounds 0–1 of 4).

### Added

- **COR-1613 Council Review** — decision-mechanism contract for any multi-reviewer negotiated decision. 14-mechanism library (Core 4 + Advanced 10), Review Unit YAML schema, 6-step workflow, universality contract with greppable token blocklist. (PR #88, FXA-2113)
- **COR-1503 Diagnose Feedback Loop** — 6-phase disciplined diagnosis loop for hard bugs and performance regressions: build feedback loop → reproduce → hypothesise (3-5 ranked falsifiable) → instrument (one variable/round) → fix → regression-test. Phase enforcement gates, escape-hatch anti-abuse rules, non-determinism floor (≥30% over ≥20 trials). (PR #89, FXA-2116)
- **COR-1504 Diagnose Phase Gates** — detailed evidence-artefact specification REF for COR-1503 phase gates. (PR #89)
- **COR-1103 routing entries** for COR-1613 and COR-1503 (OVERLAYS, PRIMARY ROUTE, Golden Rules, Workflow-Selection footnote).

### Changed

- **COR-1612** extended with per-thread reply discipline and 3-endpoint comment fetching.
- **COR-1613** §When NOT to Use includes half-diagnosed-fix prohibition from COR-1503.

### Internal

- 73 PKG documents, 0 validate issues.
- 4-LLM Council Review used per COR-1613 across all PRPs in this release.

## v1.8.0 (2026-04-29)

Feature release: branching ASCII rendering in `af plan --graph`, Mermaid sub-step IDs, and breaking `todo[].index` format extension.

### Added

- **Branching ASCII rendering** — `af plan --graph` supports nested and flat branch layouts driven by SOP `Workflow branches:` metadata. Three-way Audit Ledger goldens prove geometry invariants. (CHG-2226, CHG-2227)
- **Mermaid sub-step IDs** — Mermaid output now includes sub-step nodes (`S1_3a`, `S1_3b`, `S1_3c`) with edges connecting parent → siblings → convergence, matching the ASCII renderer. (CHG-2227 Phase 7)
- **`wcwidth` dependency** — declared explicitly (was previously transitive via `branch_geometry`).

### Changed

- **`_BRANCHES_RENDERER_READY` defaults to `True`** — `af plan --graph` renders branches by default when SOPs declare `Workflow branches:`. (CHG-2227 Phase 8a)
- **`af validate` accepts `Workflow branches:` SOPs** — validator recognizes the new `Workflow branches:` metadata block. (CHG-2226)

### Breaking

- **`todo[].index` format extends from `^\\d+\\.\\d+$` to `^\\d+\\.\\d+[a-z]?$`** — sub-step IDs (e.g., `3.1a`) are now valid indices. Consumers parsing this with strict numeric regex must update.

### Internal

- New modules: `core/branch_geometry.py`, `core/branch_layout.py`, plus branching integration in `core/dag_graph.py`, `core/ascii_graph.py`, `core/mermaid.py`, `core/workflow.py`, `core/phases.py`.
- 835 tests passing, pyright 0 errors, ruff clean.

### Install / Upgrade

```bash
pip install fx-alfred==1.8.0       # install specific version
pipx install fx-alfred              # first install
pipx upgrade fx-alfred              # upgrade existing
```

## v1.7.1 (2026-04-26)

Patch release: housekeeping migration to resolve a duplicate-ACID block and consolidate the PRJ document namespace. No CLI behavior changes.

### Changed

- **PKG `COR-0002` (Document Format Contract)** — added Section Rule 4 clarifying that author-project ID attributions in `## Change History` rows (e.g. `per FXA-2223`) are PRJ-layer provenance from the document's authoring project and are not bundled in the package. Informational, not a broken reference. (FXA-2219 CHG)
- **PKG `COR-*` Change-History attribution rewrites** — 29 historical attribution rows that previously cited `ALF-2210` / `ALF-2208` / `ALF-2206` (renamed PRJ docs in the `fx-alfred` repo) now cite `FXA-2223` / `FXA-2221` / `FXA-2220`. Same opacity to downstream users as before — these were always PRJ-only references — but consistent with the migration. (FXA-2219 CHG)

### Internal (not in PyPI but part of the same release branch)

- Migrated 6 ALF-prefixed PRJ docs in `fx_alfred/rules/` to the `FXA` prefix (PR #63). Resolves a duplicate-ACID error between USR `~/.alfred/ALF-2206` and PRJ `ALF-2206` that was blocking `af guide` / `af plan` / `af read`. PRJ now uses `FXA` exclusively; USR retains the `ALF` namespace.
- Multi-model review (COR-1602): Codex 9.2 PASS, Gemini 9.9 PASS.

## v1.7.0 (2026-04-19)

Feature release: ASCII DAG nested graph layout becomes the new default for `af plan --graph`, with cross-SOP loop metadata expressible for the first time. Full design trail in PRP FXA-2217 and CHG FXA-2218; 720 tests passing including 46+ new ones covering the widening surface and every edge caught during PR #59 review (12 rounds of GitHub bot feedback, all fixed with regression tests).

### New

- **`af plan --graph-layout=nested`** (new default for ASCII) — renders a DAG: each SOP is an outer phase-box containing inner step-boxes connected by `▼` arrows; cross-SOP back-edge loops render as right-side vertical tracks (`◄───┐ / ───┘ max N`) that extend outside the phase boxes, spanning from the target step in an earlier phase down to the source step in a later phase. Matches the mock-up seeded in FXA-2212 REF. (FXA-2217 PRP / FXA-2218 CHG / issue #58)
- **`af plan --graph-layout=flat`** — legacy ASCII renderer (v1.6.2 and earlier behaviour), preserved as an opt-in escape hatch for downstream tooling pinned on the old output shape.
- **`Workflow loops.to` cross-SOP references** — the `to` field in a SOP's `Workflow loops:` metadata now accepts either an `int` (intra-SOP, unchanged) or a `"PREFIX-ACID.step"` string (cross-SOP, new). Cross-SOP loops express "if X fails, jump back to step M in SOP Y" semantics that couldn't be written in v1.6.2. All existing SOPs use `int` → zero migration required.
- **New `af validate` cross-SOP pass (D2/D3)** — first time `af validate` does a cross-document check. Reports cross-SOP targets that don't exist in the corpus (`TST-2100 references COR-9999 — no such SOP in corpus`) and step indices out of range against the target SOP's `## Steps` section.
- **`af plan` runtime checks (D4)** — errors if a cross-SOP loop references a SOP not in the composed plan (`COR-1500 not in composed plan (add positionally: af plan ...)`) or a forward direction (`target SOP precedes source; back-edges only`).

### Changed

- **`af plan --graph` ASCII default is now nested.** Downstream consumers pinned on the v1.6.2 flat shape should pass `--graph-layout=flat` (one flag fix).
- **`af plan --todo` loop-back suffix** — cross-SOP loops now emit `back to PREFIX-ACID.step`; intra-SOP still emits `back to {phase}.{step}`. Previously, widening the underlying `to_step` type without this branch would have produced malformed output like `back to 2.COR-1500.3`.
- **`af plan --json` loops[].to** — cross-SOP loops emit the raw `"PREFIX-ACID.step"` string; intra-SOP still emits `"{phase}.{step}"`.
- **Mermaid rendering** — cross-SOP loops are skipped in Mermaid output with a single `%% (cross-SOP loops omitted — Mermaid layout is ASCII-only in this release)` comment. Extending Mermaid to render cross-SOP edges (via `subgraph` blocks) is deferred to a follow-up PRP.

### Internal

- `_parse_steps_for_json` relocated from `commands/plan_cmd.py` to new `core/steps.py` to avoid `commands → commands` imports from `validate_cmd.py`.
- `LoopSignature.to_step` widened to `int | str`; new `is_cross_sop()` and `cross_sop_target()` helpers.
- `core/phases.py` documentation-only `LoopDict.to_step` widened to match.
- New module `core/dag_graph.py` — ~350 LOC implementing the nested renderer. Reuses only width/padding/truncation primitives from `core/ascii_graph.py`; all layout logic is net-new.

## v1.6.2 (2026-04-19)

Test-only release: two automated evolve-CLI runs (FXA-2149) closed 7 coverage gaps by adding 5 narrow tests. Zero runtime behaviour changes, zero new dependencies, zero public CLI surface changes. Users should see no observable difference.

### Tests

- **FXA-2211 (PR #52)**: three tests pin edge behaviour at `list --json` empty-result `[]` contract (`list_cmd.py:66`), `atomic_write` double-failure invariant (`_helpers.py:86–87`), and `af validate` malformed Change-History early-return arms (`validate_cmd.py:60, 70`).
- **FXA-2215 (PR #55)**: two tests pin edge behaviour at `af plan --todo` raw-section-text fallback (`plan_cmd.py:276`) and `parse_metadata` "heading-but-no-table" early return (`parser.py:194`).

Both runs went through PRP → dual-reviewer scoring (Codex + Gemini on COR-1602 strict) → TDD Red (source mutation) → code review → PR. PRP FXA-2210 needed three rounds (R1 misquote, R2 pass, R3 self-caught Gap 2 scope error). PRP FXA-2214 needed two rounds (R1 caught a broken `str(area)` fix, R2 dropped C4 cleanly). Full review trail in the linked run logs.

### Deferred

- **FXA-2212 (PR #53)**: REF-only seed for a future opt-in `af plan --graph-layout=dag` ASCII DAG renderer. Evaluator discarded at 6.05 on first cold pass (SR=5, Nec=3). Per REF policy: stays as REF, try again next run, promote to PRP on second discard.

### Stats

- 0 runtime changes
- 660 → 665 tests (+5)
- 0 new dependencies
- Coverage: 90 → 83 missed lines (-7)
- 0 breaking changes

### Install / Upgrade

```bash
pip install fx-alfred==1.6.2       # install specific version
pipx install fx-alfred              # first install
pipx upgrade fx-alfred              # upgrade existing
```

## v1.6.1 (2026-04-18)

Patch release: v1.6.0's publish-to-PyPI GitHub Actions workflow failed at the `pyright src/` step with 16 type errors. The errors were static-only — all 660 tests passed — but blocked PyPI publish, so v1.6.0 exists as a GitHub tag only. v1.6.1 ships the identical feature set with the type annotations corrected.

### Fixed

- **`core/phases.py`**: `PhaseDict` split into `_PhaseRequired` (required: `sop_id`, `steps`, `loops`) + optional `provenance` via `total=False` inheritance. Previously `PhaseDict(TypedDict, total=False)` made every field optional, causing `reportTypedDictNotRequiredAccess` on every consumer. Codex R1 had flagged this as advisory during FXA-2206 review; v1.6.1 implements the tightening.
- **`core/mermaid.py`, `core/ascii_graph.py`, `commands/plan_cmd.py`**: annotation + narrowing fixes flowing from the tighter `PhaseDict`. Loop endpoint null-checks in `ascii_graph` use assert-and-skip. `plan_cmd` gains one `# type: ignore[attr-defined]` on `ctx.get_parameter_source` (Click 8.3 ships the method but pyright's bundled stubs don't).
- **`lazy.py`**: unrelated pre-existing `Iterable[str] + list[str]` operator issue.

### Stats

- 0 runtime changes (pure static-type tightening)
- 660 tests still passing
- 0 new dependencies
- 16 pyright errors → 0

### Install / Upgrade

```bash
pip install fx-alfred==1.6.1       # install specific version
pipx install fx-alfred              # first install
pipx upgrade fx-alfred              # upgrade existing
```

## v1.6.0 (2026-04-18)

Major feature release: `af plan` gains auto-composition (`--task`), flat TODO (`--todo`), and graph output (`--graph`) with both terminal-friendly ASCII and GitHub/Obsidian-ready Mermaid. Three new SOP metadata fields (`Task tags`, `Workflow loops`, `Always included`) drive auto-composition and loop visualisation. New PKG SOP **COR-1202: Compose Session Plan** gives every user an ID-addressable entry point for the full session-workflow pattern.

### New

- **`af plan --task "<description>"`** — auto-compose the set of SOPs for a task from its one-sentence description using deterministic tag matching + always-included baseline. No LLM. Explicit positional IDs still work (union/normalise). Fail-closed on true dependency cycles; exits 2 with diagnostic on empty tag match. (FXA-2205 / PR #46)
- **`af plan --todo`** — emit a single continuously-numbered TODO list across all composed SOPs with `[SOP-ID]` provenance on every item, stable `{phase}.{step}` numbering, `⚠️ gate` markers, and `🔁 loop-start` / `🔁 back to N.M (max K)` loop markers. Mutually compatible with `--human` and `--json`. (FXA-2205 / PR #44)
- **`af plan --graph`** — emit a flowchart of the composed plan. Default `--graph-format=both` prints an ASCII box-and-arrow diagram (terminal-friendly, Unicode-width aware) followed by a fenced Mermaid block (GitHub / Obsidian / mermaid.live). `--graph-format=ascii` or `--graph-format=mermaid` pick one. JSON output adds `ascii_graph` + `graph_mermaid` keys. (FXA-2205 PR #45 / FXA-2206 PR #47)
- **`Workflow loops:` SOP metadata** — optional list of intra-SOP back-edges `[{id, from, to, max_iterations, condition}]`. Renders as dashed back-edges in Mermaid, `◄──┐ / ─────┘ max N` in ASCII, and `🔁 back to N.M (max K)` in TODO. `core/workflow.validate_loops()` enforces back-edge-only (`from > to`), positive `max_iterations`, and in-range step indices. (FXA-2205 / PR #43)
- **`Task tags:` SOP metadata** — optional list of keywords used by `--task` auto-matching. Free-form; advisory lint warning planned for singletons. Backfilled on COR-1500/1602/1608/1609/1610/1611 and FXA-2148/2149 as the pilot corpus. (FXA-2205 / PR #46, FXA-2206 / PR #47)
- **`Always included: true` SOP metadata** — optional boolean for SOPs that must be pulled into every `--task` composition (session baseline). Backfilled on COR-1103 (routing) and COR-1402 (declare-active-SOP). (FXA-2205 / PR #43)
- **`core/ascii_graph.py`** — new pure-stdlib ASCII box-and-arrow renderer with Unicode visual-width handling (CJK, emoji, variation selectors) and balanced-width-invariant test. (FXA-2206 / PR #47)
- **`core/phases.py`** — new shared `PhaseDict` / `StepDict` / `LoopDict` `TypedDict` contracts, formalising what was previously an implicit shape between `render_mermaid` and `_build_mermaid_phases`. `PhaseDict` uses `total=False` to keep legacy builders typecheckable. (FXA-2206 / PR #47)
- **COR-1202: Compose Session Plan SOP** — new PKG SOP giving every user a named, ID-addressable procedure for `af plan --task … --todo --graph`. Users can say "follow COR-1202" and get a complete session workflow plan. Includes 7 Steps, 3 worked Examples with expected output, and tag-gap recovery flow. (FXA-2207 / PR #48)
- **COR-1103 intent-router cross-reference** — routes "show me the plan" / "compose session plan" intents to COR-1202; disambiguates from the generic `af plan <SOP_IDs>` manual-checklist bullet. (FXA-2207 / PR #48)

### Fixed

- **Compose resolver**: `resolve_sops_from_task` now passes `workflow_edges` to `compose_order`, so Kahn's topological sort actually uses `Workflow input`/`Workflow output` metadata instead of always falling through to the layer+ASCII tiebreak. (FXA-2205 / PR #46)
- **Compose empty-match check**: now keyed on `tag_cands` + `positional_set`, not `candidates == always_set`; previously an always-included SOP that also had a matching `Task tags` entry would wrongly trigger exit 2. (FXA-2205 / PR #46, bot P2)
- **Compose positional IDs**: `--task` mode now accepts ACID-only IDs via `core.scanner.find_document` (normalised to PREFIX-ACID), matching the legacy `af plan <id>` semantics. (FXA-2205 / PR #46, bot P2)
- **ASCII renderer** inter-phase border off-by-one: `└─┬─┘` separator line previously rendered at `box_width + 1`. (FXA-2206 / PR #47)
- **ASCII renderer** `⚠️` visual width: `_visual_width` now treats `0x2600-0x27BF` (Misc Symbols + Dingbats) as 2 cells and `0xFE00-0xFE0F` (variation selectors) as 0. Gate step right borders now align. (FXA-2206 / PR #47)
- **`af plan --graph-format=mermaid`**: byte-identical to pre-v1.6 `af plan --graph` output, preserving backward-compat for scripted consumers. (FXA-2206 / PR #47)
- **`af plan`** no longer crashes on SOPs with malformed `Workflow loops` metadata; `parse_workflow_signature` and `parse_workflow_loops` now share the `MalformedDocumentError` warn-and-skip path with `parse_metadata`. (FXA-2205 / PR #44, bot P2)
- **`af plan --todo` marker composition**: gate / loop-start / loop-back markers are now independently composable rather than mutually exclusive. A step that is both a gate and a loop endpoint no longer silently loses its loop annotation. JSON `loop_marker ∈ {null, "loop-start", "loop-back"}` (gate is its own `gate: bool` field). (FXA-2205 / PR #44)
- **`af plan --json` contract**: `workflow_provides` for untyped phases is `[]` (list), not `""` (string); restores type stability. (FXA-2205 / PR #44)

### Improvements

- `Composed from:` header in the flat-TODO and default views now shows provenance markers `(always)` / `(auto)` / `(explicit)` next to every SOP ID. JSON output adds a `composed_from: {always, auto, explicit}` key when `--task` is used.
- Deterministic composition order: Kahn's topological sort with `(layer: PKG→USR→PRJ, then SOP-ID ASCII)` tiebreak guarantees same task + same corpus → same output bytes.
- `af plan` documentation in COR-1103 routing now explicitly distinguishes manual `af plan <SOP_IDs>` (targeted checklist) from the new COR-1202 auto-compose path (full session plan).

### Stats

- 660 tests (80+ new since v1.5.0), all passing
- `core/ascii_graph.py`, `core/compose.py`, `core/mermaid.py`, `core/phases.py` all new modules; 95%+ coverage on each
- 0 new runtime dependencies (still `click` + `pyyaml`)
- 0 breaking changes

### Install / Upgrade

```bash
pip install fx-alfred==1.6.0      # install specific version
pipx install fx-alfred             # first install
pipx upgrade fx-alfred             # upgrade existing
```

## v1.1.0 (2026-03-22)

### New

- `af where IDENTIFIER [--json]` — Print the absolute filesystem path of any document. Composable with shell tools: `vi $(af where FXA-2107)`. JSON output includes `doc_id`, `path`, `source`, `filename`. (FXA-2144)
- `af fmt [DOC_IDS...] [--write] [--check]` — Format documents to canonical style: normalize metadata order, whitespace, and table alignment. `--check` exits 1 if any changes needed (CI-friendly). (FXA-2140)
- `af create --spec FILE` — Spec-driven document creation: pass a YAML/JSON file for batch metadata and section content. (FXA-2143)
- `af update --spec FILE` — Spec-driven batch updates: update metadata fields and section content from a spec file. (FXA-2143)

### Improvements

- `af validate` — Schema-driven validation via new `core/schema.py`: DocType/DocRole enums, per-type `ALLOWED_STATUSES`, `REQUIRED_METADATA`, and `REQUIRED_SECTIONS`. Catches status violations and missing SOP sections precisely.
- `core/normalize.py` — Extracted `slugify()`, `sort_metadata()`, `normalize_date()`, `strip_trailing_whitespace()` as reusable utilities.
- COR-1103 — Golden Rules updated: added COR-1606 (select workflow before multi-agent work), clarified COR-1500 as TDD overlay, added standalone PLN route (branch 4, branches renumbered to 8). Sequence diagram simplified to linear flow.

### Stats

- 374 tests (108 new), all passing
- 0 breaking changes

## v1.0.6 (2026-03-22)

### New

- COR-1004 — New PKG SOP: Create Routing Document. Standardizes language (COR-1401), required sections (PRJ/USR), and decision tree format (ASCII + Mermaid) for all routing documents.

### Improvements

- COR-1103 — Clarified `af plan` ALWAYS rule: per-response decision (not just session-start). Before every response, decide if task needs a checklist; if task has clear steps or spans multiple SOPs, run `af plan <SOP_IDs>` before proceeding.
- COR-1103 — Reduced "Creating Routing Documents" section to a pointer to COR-1004.
- COR-0002 — Added `## Language` section referencing COR-1401 (all documents must be written in English).
- COR-1102, COR-1600–1605 — Updated `/team` references to `/trinity` (skill rename).

### Fixes

- `__init__.py` — Removed stale `__version__ = "0.5.0"` (version is read from package metadata).

## v1.0.5 (2026-03-22)

### Improvements

- `af setup` — All options now say "every time you are about to do a task" (not just session start)
- `af guide` — Tip updated: "Run this before EVERY task to route correctly"
- `ruff format` — Applied to list_cmd, read_cmd, status_cmd (previously uncommitted)

## v1.0.4 (2026-03-21)

### Improvements

- FXA-2102 Release SOP — Added `ruff format --check` to prerequisites
- `plan_cmd.py` — Applied ruff format

## v1.0.3 (2026-03-21)

### Improvements

- COR-1103 — Added workflow sequence diagram (session lifecycle visualization)
- COR-1103 — Added `af plan` to ALWAYS section (session-start checklist)
- COR-1103 — New overlay: "New SOP/doc created → review via COR-1600"
- CLAUDE.md updated to v1.0.2

## v1.0.2 (2026-03-21)

### Improvements

- Renamed to **Alfred — Agent Runbook** (replaces "Alfred Document System")

## v1.0.1 (2026-03-21)

### Improvements

- `af setup` — New standalone command for agent configuration prompts (replaces `af plan --init`)
- `af guide` tip updated to reference `af setup`

## v1.0.0 (2026-03-21)

### First Stable Release

Alfred v1.0.0 marks the completion of the core document management and AI agent workflow system.

### Highlights

- **11 CLI commands** — list, read, create, update, search, validate, status, index, guide, plan, changelog
- **Three-Layer Model** — PKG (bundled COR SOPs) → USR (personal preferences) → PRJ (project-specific)
- **`af guide`** — Dynamic three-layer workflow routing with intent-based decision tree
- **`af plan`** — LLM-optimized workflow checklists from SOPs (3 modes: default, --human, --init)
- **`af validate`** — Metadata format, per-type Status values, SOP section structure checking
- **Review Scoring Framework** — COR-1608/1609/1610 rubrics + COR-1611 calibration guide
- **40+ SOPs standardized** — 5W1H pattern (What, Why, When, When NOT, How)
- **README** — Logo, Mermaid diagrams, complete documentation

### Stats

- 262 tests, all passing
- 86+ documents, 0 validation issues
- 10 new COR SOPs (COR-0002, 1103, 1608-1611, plus updates)

### Install

```bash
pip install fx-alfred==1.0.0
pipx install fx-alfred
pipx upgrade fx-alfred
```

## v0.12.0 (2026-03-21)

### New Command: `af plan` (FXA-2134)
- **`af plan SOP_ID [...]`** — LLM-optimized workflow checklist with phases, hard stops, and RULES
- **`af plan --human`** — Human-readable format
- **`af plan --init`** — Suggested prompts for agent configuration
- **`extract_section()`** — New parser utility for section extraction
- **`af guide`** — Appends `af plan --init` tip

### Stats
- 262 tests (10 new), all passing

## v0.11.1 (2026-03-21)

### Bugfix
- **`af validate`** — Fixed SOP section detection to use exact heading match (`^## Section\s*$`). Prevents false passes on prefix headings like `## Why This Matters`.
- 6 new false-positive regression tests (252 total)

## v0.11.0 (2026-03-20)

### Standardized SOP Section Structure (FXA-2223)
- **SOP template updated** — 5W1H pattern: What Is It?, Why, When to Use, When NOT to Use, Steps
- **`af validate` SOP section checking** — Validates required sections for SOP documents (USR/PRJ layers)
- **COR-1103 updated** — "How to Read an SOP" golden rule + SOP section compliance overlay
- **40 SOPs migrated** — All PKG, USR, PRJ SOPs now have Why, When to Use, When NOT to Use

### Stats
- 246 tests (8 new), all passing
- 86 documents validated, 0 issues

## v0.10.1 (2026-03-20)

### Docs
- **COR-1103** — Added golden rules for COR-1201, COR-1608~1611

## v0.10.0 (2026-03-20)

### Review Scoring Framework (FXA-2221)
- **COR-1608** — PRP Review Scoring rubric (6 weighted dimensions + OQ hard gate)
- **COR-1609** — CHG Review Scoring rubric (5 dimensions, fallback for PLN/ADR)
- **COR-1610** — Code Review Scoring rubric (5 dimensions)
- **COR-1611** — Shared Reviewer Calibration Guide (symmetric rules for all models)
- **COR-1602 updated** — Generic 4-dimension matrix replaced with artifact-specific rubric references
- **COR-1102 updated** — OQ hard gate + stale matrix reference fixed
- **COR-1103 updated** — Scoring rubric added to OVERLAYS

### Stats
- 238 tests, all passing
- 0 breaking changes

## v0.9.1 (2026-03-20)

### Docs
- **COR-1103** — Added USR/PRJ routing doc creation guide

## v0.9.0 (2026-03-20)

### Layered Workflow Routing (FXA-2220)
- **`af guide` enhanced** — Dynamically scans PKG → USR → PRJ for routing documents (`*-SOP-Workflow-Routing*.md`), filters by `Status: Active`, outputs full content per layer with separator headers
- **Quick-start moved** — Document naming, layer system, and create examples now in `af --help` epilog
- **Failure handling** — Graceful handling of missing layers, deprecated docs, malformed docs, and multiple active docs per layer

### Stats
- 238 tests (10 new), all passing
- 0 breaking changes

## v0.8.0 (2026-03-20)

### Workflow Routing (ALF-2205)
- **COR-1103 SOP** — New session-start routing SOP with intent-based router (ALWAYS → PRIMARY ROUTE → OVERLAYS) and golden rules. Replaces COR-1607.
- **COR-1607 deprecated** — Replaced by COR-1103 in the 11xx area
- **COR-1101 fix** — Corrected "use PLN" to "use PRP per COR-1102" in When NOT to Use section

### Stats
- 228 tests, all passing
- 0 breaking changes

## v0.7.0 (2026-03-20)

### Document Format Contract (FXA-2116)
- **COR-0002 Reference** — New document defining mandatory metadata format for all Alfred documents: required fields per type, allowed Status values, optional fields, H1 rules, section rules
- **COR-1607 SOP** — Workflow Routing SOP mapping work types to required SOP sequences
- **Template compliance** — All 7 `af create` templates now emit required fields (Applies to, Last updated, Last reviewed, Status) with correct defaults per type
- **`af validate` enhancements** — Per-type required field checks, Status value validation (rejects invalid values and annotations), ACID=0000 Index document H1 exemption
- **`af index` compliance** — Generated Index documents now include H1, metadata block, and Change History section per contract
- **PKG layer migration** — All 33 COR documents updated with Status field

### Stats
- 228 tests (49 new), all passing
- 0 breaking changes

## v0.6.0 (2026-03-19)

### Internal Improvements
- **DRY scan boilerplate (CHG-1)** — Extracted `scan_or_fail()` and `find_or_fail()` helpers to `commands/_helpers.py`, eliminating 6x repeated try/except blocks across command files
- **Lazy command loading (CHG-2)** — `LazyGroup` subclass loads command modules on demand via `importlib`, removing all eager imports from `cli.py`

### New Features
- **`af list` filtering (CHG-3)** — `--type`, `--prefix`, `--source` options with exact case-insensitive matching and AND logic
- **`--json` output (CHG-4)** — Machine-readable JSON output for `af list`, `af status`, and `af read` commands; combinable with filters
- **`af search` (CHG-5)** — Search document contents with case-insensitive substring matching, shows up to 3 matching lines with line numbers
- **`af validate` (CHG-6)** — Structural health check: validates H1 format, required metadata fields, Change History table, and COR/PKG layer invariant

### Stats
- 179 tests (45 new), all passing
- 0 breaking changes

## v0.5.0 (2026-03-19)

### New Commands
- **`af update`** — Structured metadata updates to existing documents
  - Field updates (`--status`, `--field`): modify existing metadata fields
  - Change History append (`--history`, `--by`): add entries with pipe escaping
  - Document rename (`--title`): changes filename + H1 + auto-indexes
  - Dry run (`--dry-run`): preview changes without writing
  - Atomic writes via temp file for safety
  - PRJ and USR layers only; PKG is read-only
- **`af changelog`** — View this changelog

### New Core Module
- **`core/parser.py`** — Document metadata parser and renderer
  - Supports both `**Key:** value` and `- **Key:** value` metadata formats
  - Round-trip fidelity: preserves formatting of unmodified fields
  - Strict H1 validation against `# <TYP>-<ACID>: <Title>` format

### Code Quality Refactoring
- **`core/source.py`** — Consolidated `Source` type, `SOURCE_LABELS`, `SOURCE_ORDER`, `source_sort_key()`
- **`core/scanner.py`** — Fixed `Traversable` protocol (`iterdir()` returns `Iterator`), removed `read_text()` from `Traversable`
- **`find_document()`** — Moved to core with exception-based API (`DocumentNotFoundError`, `AmbiguousDocumentError`)
- Removed 4 `# type: ignore` comments

### New SOPs (bundled in PKG layer)
- **COR-1102** — Create Proposal (PRP lifecycle)
- **COR-1201** — Discussion Tracking (D item protocol)
- **COR-1602** — Workflow: Multi Model Parallel Review
- **COR-1603** — Workflow: Parallel Module Implementation
- **COR-1604** — Workflow: Competitive Parallel Exploration
- **COR-1605** — Workflow: Sequential Pipeline
- **COR-1606** — Workflow: Selection (decision tree)

### Updated SOPs
- **COR-1200** — Added Step 0 (close D items before retrospective)
- **COR-1600** — Added sequence diagram, iteration mode, review scoring (>=9), Lead Reviewer rule
- **COR-1601** — Added sequence diagram, iteration mode, review scoring

### Documentation
- **README.md** — Added `af update` usage examples and documentation

## v0.4.3 (2026-03-17)

- Added COR-1403/1404/1405 interactive question SOPs
- Improved COR-1200 session retrospective

## v0.4.2 (2026-03-17)

- Test isolation improvements
- `--layer`/`--subdir` support for `af create`
- Docs migration to 3-layer model

## v0.4.0 (2026-03-16)

- `af create` command improvements

## v0.3.4 (2026-03-15)

- `af read` supports PREFIX-ACID format (e.g., `COR-1000`)
