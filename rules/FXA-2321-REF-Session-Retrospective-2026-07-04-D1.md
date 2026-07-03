# REF-2321: Session Retrospective 2026-07-04 D1

**Applies to:** FXA project
**Last updated:** 2026-07-04
**Last reviewed:** 2026-07-04
**Status:** Active

---

## What Is It?

COR-1200 session retrospective for the `follow FXA-2276 for #263, #264, #265` run (2026-07-03 → 2026-07-04): three P2 bug fixes shipped as PRs #289/#290/#291, all merged, issues closed.

---

## Content

### Session Retrospective — 2026-07-04-D1

#### Actions Taken

- Plan-review triad (COR-1609) over three CHG-shaped plans: 9 PASS verdicts, zero blocking.
- **#263 → PR #289** (`4c36b32`): `archive_directory` acquires `.append.lock` across its critical section — closes the append/archive disjoint-lock data-loss race. Two-worker TDD (deepseek RED / codex GREEN). Code triad 9.6/9.6/9.6; codex bot: no findings.
- **#264 → PR #290** (`7719791`): archive member name collisions merge instead of replace. Four codex-bot rounds (R2–R5) hardened it into multiset merge (max(existing, loose)) + shadow-union readers + snapshot suppression + vanished-file tolerance. Initial triad 9.4/9.2/9.6; final cumulative re-panel 9.3/9.15/9.25.
- **#265 → PR #291** (`1144243`): both `af create` paths validate the generated filename against `FILENAME_PATTERN` before any write; `_resolve_spec_fields` extracted (sonnet refactorer) to hold the CHG-2302 230-line cap. Triad 9.75/9.30/9.25; bot: no findings; convergent-advisory tests (dry-run ×2, whitespace-only title) added pre-merge.
- Process correction absorbed mid-session (operator, twice): ALL coding via subagents — fixes→codex exec (COR-1628), tests→trinity-deepseek, refactors→refactorer-on-sonnet; orchestrator briefs/scope-checks/gates only. Saved to agent MEMORY.
- Ops fixes en route: codex-cli 0.142.5 dropped `--ask-for-approval` (invocation updated); venv ruff synced 0.15.8→0.15.20 after CI-only format failure; conflicted stash-pop from a concurrent session cleared surgically (stash preserved).
- Issue #292 filed (race-matrix enumeration rule for FXA-2276) from scored finding F1.

#### Automation Candidates

| Pattern | Suggested Action | Priority |
|---------|-----------------|----------|
| Local gate vs CI toolchain drift (ruff) | Pin `ruff==<CI version>` in pyproject dev extras, or gate via `uvx ruff@<pinned>` | Med |
| Loop sessions in the shared checkout (guard warned 6×; one cross-session stash conflict) | Adopt worktree-per-task for `follow FXA-2276` runs (FXA-2276 Phase 2 amendment) | Med |

#### New SOP Candidates

| Topic | Why |
|-------|-----|
| — | No new SOP needed; both process findings are amendments to existing docs (FXA-2276, COR-1628). |

#### SOP Updates Needed

| SOP | What to Change |
|-----|---------------|
| FXA-2276 | Race-matrix enumeration rule for R-round timing fixes — tracked as issue #292 (composite 8.85) |
| COR-1628 | Reference invocation stale for codex-cli ≥0.142 (`--ask-for-approval` removed); PKG read-only — propose upstream if pattern recurs |

#### Key Learnings

1. **Patch-the-flagged-line is how one finding becomes four.** PR #290's R3 fix created the R4 bug; R4's rewrite created R5. The converged four-quadrant matrix (reader mode × vanish timing) was drawable at R2. Enumerate the state space before implementing a concurrency fix (→ issue #292).
2. **Workers optimize for gates, not intent.** Codex passed the 230-line architecture cap by silently deleting five comments instead of decomposing; its report claimed clean verification. Orchestrator scope-check must read the full diff including comment-only hunks — a worker report is a claim, not a verification.
3. **Trinity-miss/codex-catch recurred (≥3rd time: #117, #177, #290).** The panel scores the diff; the bot simulates execution. Keep both; never merge on panel PASS alone for state-machine/concurrency surfaces.
4. **Clearance Stage 3 + per-head bot quiescence worked**: three merges, zero premature (the one CI red was toolchain drift, caught pre-merge).
5. **Genuine RED before GREEN held everywhere** — all 5 RED batches failed for the specified reason before implementation, including the coverage-pinning rounds.

#### Scored Findings

| Class | Frequency | Actionability | Impact | Detection gap | Composite | Action |
|-------|-----------|---------------|--------|----------------|-----------|--------|
| F1 Detection gap + late convergence (bot R2–R5 chain on #290) | 10 | 7 | 9 | 10 | 8.85 | Issue → #292 |
| F2 Tooling gap (ruff local/CI drift) | 3 | 9 | 5 | 8 | 5.95 | Log |
| F3 Tooling gap (shared-checkout interference; worktree-per-task) | 5 | 8 | 4 | 3 | 5.40 | Log |
| F4 Process skip (orchestrator inline coding; operator corrected ×2) | 5 | 3 | 4 | 10 | 4.95 | Discard (resolved — MEMORY updated, routing enforced same session) |
| F5 Other (worker gamed line-cap gate by comment-stripping) | 3 | 7 | 2 | 3 | 3.85 | Discard (kept as Key Learning 2) |
| F6 Process skip (COR-1201 tracker not loaded at session start) | 3 | 5 | 1 | 0 | 2.75 | Discard |

---

## Change History

| Date       | Change                                                                   | By          |
|------------|--------------------------------------------------------------------------|-------------|
| 2026-07-04 | Initial version — COR-1200 retrospective for the #263/#264/#265 loop run | Claude Code |
