# CHG-2231: Agent Activity Log Protocol v1 Implementation

**Applies to:** FXA project (af CLI + PKG documents + reference Claude Code hook)
**Last updated:** 2026-05-02
**Last reviewed:** 2026-05-02
**Status:** Proposed
**Date:** 2026-05-02
**Requested by:** Frank Xu
**Priority:** Medium (foundational observability infra; no production-blocking issue)
**Change Type:** Normal
**Targets:** PRP-2230 implementation — single CHG, multi-phase TDD per COR-1500
**Depends on:** PRP-2230 must be merged first (it is — see PR #78); no dependency on FXA-2229 (PRP-2230 line 160 requires independence)

---

## What

Implement the v1 of the **Agent Activity Log Protocol** defined in PRP-2230: ship the two PKG documents (`COR-1205` REF data contract + `COR-1206` SOP implementation guide), the two CLI surfaces (`af log` writer + `af log-validate` checker), the `COR-1200` retrospective additive bullet, and one reference Claude Code `Stop` hook script.

This CHG also folds in the two **4/4 satellite advisories** from the strict review (PRP `## Change History` 2026-05-02 row): a long-term retention/aggregate-disk-space policy beyond per-file 8 MiB rotation, and a tightened POSIX wording for the `O_APPEND` atomicity rationale.

## Why

PRP-2230 was approved by all four strict reviewers (Codex 9.9 / GLM 9.9 / Gemini 9.8 / DeepSeek 9.8) on 2026-05-02 and merged via PR #78 (with 3 follow-on review rounds catching real schema bugs that all four PRP reviewers had missed). The protocol is now the canonical contract for cross-agent activity capture — nothing else lands without consuming it. This CHG is the implementation realization.

The protocol is the **emit surface** counterpart to FXA-2229's recall surface. Once shipped, every coding agent (Claude Code first; Copilot, Cursor, Cline, Aider, Codex CLI, Gemini CLI in follow-on CHGs) can drop session work into one shared, machine-readable JSONL log, turning `COR-1200 step 1` ("List all actions taken this session") from recollection into replay.

## Impact Analysis

### Files to be created

| File | Nature | Estimated LOC |
|---|---|---|
| `src/fx_alfred/rules/COR-1205-REF-Agent-Activity-Log-Format.md` | Canonical data contract — verbatim from PRP-2230 lines 60–89 with retention policy added (see Phase 1) | ~140 |
| `src/fx_alfred/rules/COR-1206-SOP-Emit-Agent-Activity.md` | Implementation guide — verbatim from PRP-2230 lines 91–113 plus per-agent integration examples and `.gitignore` snippet | ~180 |
| `src/fx_alfred/core/activity_log.py` | Framework-agnostic schema + validator (no Click). Constants: `SCHEMA_LITERAL`, `AGENT_WHITELIST`, `EVENT_ENUM`, `RECORD_LINE_CAP_BYTES = 4096`, `FILE_SIZE_CAP_BYTES = 8 * 1024 * 1024`, `RETENTION_DAYS_DEFAULT`. Functions: `validate_record(dict) → list[Violation]`, `validate_file(path) → list[Violation]`, `compose_record(...) → bytes` (with truncation + `summary_truncated` flag handling). | ~250 |
| `src/fx_alfred/commands/log_cmd.py` | Click command for `af log`. Layer resolution per PRP-2230 lines 124–127, auto-fill `ts`/`schema`/`session_id` (UUIDv4 fallback)/`agent_version` (`"unknown"` sentinel fallback), pre-condition rotation check, atomic O_APPEND write ≤ 4096 bytes, exit codes 0/2/3/4. | ~120 |
| `src/fx_alfred/commands/log_validate_cmd.py` | Click command for `af log-validate`. Default-target = today's PRJ log via shared layer resolution. Path-vs-dir dispatch. Per-line check via `core/activity_log.validate_record`. Output `<path>:<lineno>: <field>: <reason>`. Exit codes 0/1/2/4. | ~80 |
| `hooks/emit-activity.sh` | Reference Claude Code `Stop` hook. Reads `$CLAUDE_*` env vars, builds `af log ... \|\| true` invocation. Idempotent on re-source. | ~40 |
| `tests/test_activity_log_schema.py` | TDD: `validate_record` unit tests covering all v1 rules including the 7 specific cases listed in PRP-2230 acceptance criteria L159 (`summary_truncated: false`, line > 4096 bytes, `agent: "other"` without `agent_name`, etc.) | ~250 |
| `tests/test_log_cmd.py` | TDD: layer resolution, auto-fill, line-size cap with `summary_truncated`, pre-condition rotation handoff to `.partN.jsonl`, exit codes, fail-open mode | ~200 |
| `tests/test_log_validate_cmd.py` | TDD: file vs dir dispatch, default target, violation output format, exit codes | ~120 |
| `tests/test_hook_emit_activity.py` | TDD: hook script smoke test (real `af log` invocation, validate output) | ~40 |

### Files to be modified

| File | Nature | Estimated LOC |
|---|---|---|
| `src/fx_alfred/cli.py` | Register `log` and `log-validate` via `LazyGroup` (mirror existing pattern; one entry per command) | small (~6) |
| `src/fx_alfred/rules/COR-1200-SOP-Session-Retrospective.md` | Add **single additive bullet** in step 1 directing agent to read `logs/agent-activity/<today>.jsonl` first. Exact wording pinned in this CHG (see Phase 1). 6-step structure unchanged. | small (~3) |
| `.gitignore` (project root) | Add `logs/agent-activity/` per PRP-2230 line 87 default git policy | 1 line |
| `src/fx_alfred/CHANGELOG.md` | v1.9.0 entry covering activity log protocol | small |
| `pyproject.toml` | Version bump 1.8.0 → 1.9.0 | small |
| `CLAUDE.md` (project root) | One-paragraph note on `af log` + `af log-validate` (mirroring existing CLI docs) | small |

### Systems affected

- **af CLI**: 2 new commands (`log`, `log-validate`) registered via `LazyGroup`. No existing command behavior changes.
- **PKG documents**: 2 new (`COR-1205` REF, `COR-1206` SOP). 1 modified (`COR-1200` step 1 additive bullet only).
- **Schema/validation infra**: new `core/activity_log.py` module. `core/` remains Click-free (consistent with FXA-2230 Decisions §"vendor-neutral protocol").
- **No FXA-2229 dependency**: this CHG ships independently. PRP-2230 line 160 requires this; the test suite verifies it (see Phase 4 acceptance).

### Rollback plan

Rollback is a per-phase revert:

- **Phase 4 (hook + integration)** — `git revert <Phase-4-merge>`; activity log directory persists but no new emits.
- **Phase 3 (`af log-validate`)** — `git revert <Phase-3-merge>`; existing logs become un-validated but readable.
- **Phase 2 (`af log`)** — `git revert <Phase-2-merge>`; agents can no longer emit but the contract docs remain. Existing logs remain valid JSONL on disk.
- **Phase 1 (docs)** — `git revert <Phase-1-merge>`; deletes the two new PKG docs. Validators referencing them become inert (Phase 1 is doc-only, no code consumes it yet).
- **Full rollback** — `git revert` Phase 4 → Phase 3 → Phase 2 → Phase 1 in reverse order. The protocol is observability-only; reverting cannot corrupt application state.

## Implementation Plan

Per PRP-2230 line 204 workflow: **`COR-1101 (CHG, current) → COR-1500 TDD per phase`**. Each phase is one PR with red-green-refactor commits per COR-1500. Phases are executable in order; Phase N can begin only after Phase N-1 merges.

### Phase 0 — Branch + scaffolding

- Create branch `fx/2231-chg-agent-activity-log` (this CHG itself lives here pre-merge).
- Create empty placeholder files for `core/activity_log.py`, `commands/log_cmd.py`, `commands/log_validate_cmd.py`, `hooks/emit-activity.sh` (so subsequent phases can stage individually).
- Add `.gitignore` entry for `logs/agent-activity/`.
- No tests yet; no behavior change.

### Phase 1 — Documents (`COR-1205`, `COR-1206`, `COR-1200` additive bullet, retention policy advisory)

- **`COR-1205-REF-Agent-Activity-Log-Format`**: write the canonical data contract. Source = PRP-2230 lines 60–89. Add the **retention policy section** to address the 4/4 satellite advisory:
  - Default retention: keep activity log files for **30 days**; older `YYYY-MM-DD*.jsonl` files MAY be deleted by the agent runtime or by user cron. Implementation MAY ship `af log-validate --gc` as a follow-on (out of scope for this CHG).
  - Aggregate disk-space soft cap: **256 MiB per `logs/agent-activity/` directory**. Beyond this the runtime SHOULD warn; deletion of oldest files is user-driven, not automatic.
  - Compression: out of scope for v1; v2 may revisit gzipping rotated files.
- **Tighten POSIX wording** (4/4 satellite advisory): replace "POSIX guarantees atomicity for writes ≤ `PIPE_BUF`" with "Linux/macOS/BSD `O_APPEND` provides per-write atomicity for regular files at the kernel level (inode lock); `PIPE_BUF` (≥ 4096) is the related guarantee for pipes/FIFOs and motivates the line-size cap upper bound. The 4 KiB cap is conservative — well within atomicity windows on every supported OS."
- **`COR-1206-SOP-Emit-Agent-Activity`**: write the implementation guide. Source = PRP-2230 lines 91–113. Add:
  - Per-agent integration recipes (one paragraph each for the 7 mapping table entries).
  - The `.gitignore` snippet (`logs/agent-activity/`) called out in PRP-2230 line 87.
  - Compliance test command: `af log-validate <one-session-log.jsonl>` must pass.
- **`COR-1200` step 1 additive bullet** (3/4 satellite advisory — exact wording pinned here):
  > **Before reconstructing actions:** if `./logs/agent-activity/<today UTC>.jsonl` exists, read it via `af log-validate` (verifies schema) and use its `task.done` / `doc.created` / `doc.updated` / `decision` events as the ground truth for what happened this session. The chat-history reconstruction below remains the fallback when the log is empty or absent.
- No code yet. Phase 1 is documentation-only and ships independently if needed.
- **`af validate` must report 0 issues** before merge.

**Phase 1 Definition of Done:**
- 2 new PKG docs land, 1 modified PKG doc lands, `.gitignore` updated.
- All PRP-2230 line 154–155 doc-acceptance criteria satisfied.

### Phase 2 — `af log` command (TDD)

Red-Green-Refactor per COR-1500:

1. **Red.** Write `tests/test_log_cmd.py` first. Test cases (each a separate test function):
   1. `test_layer_resolution_root_flag` — `af log --root /tmp/proj "msg" --event note --agent claude-code` writes to `/tmp/proj/logs/agent-activity/<today>.jsonl`.
   2. `test_layer_resolution_cwd_with_rules_dir` — cwd has `./rules/`; no `--root` → writes under cwd.
   3. `test_layer_resolution_user_fallback` — no `--root`, no project markers → writes under `~/.alfred/`.
   4. `test_autofill_ts_session_id_schema` — minimal invocation gets all three auto-filled.
   5. `test_autofill_session_id_from_env` — `$ALFRED_SESSION_ID=fixed-id` → that id appears in record.
   6. `test_autofill_agent_version_from_env` — `$ALFRED_AGENT_VERSION=2.5.1` → that string appears.
   7. `test_autofill_agent_version_unknown_sentinel` — neither flag nor env → `"unknown"` literal in record.
   8. `test_line_size_cap_summary_truncation` — large `summary` → truncated; `summary_truncated: true` set.
   9. `test_line_size_cap_files_trimming` — large `files` array → trimmed from end; `summary_truncated: true` set; final record well below 4096 bytes (regression for PR #78 R2 fix).
   10. `test_rotation_pre_condition` — file at 8 MiB - 200 B + 1024 B record → rolls over to `.part1.jsonl` BEFORE write; original file stays ≤ 8 MiB (regression for PR #78 R3 fix).
   11. `test_rotation_part_n_increment` — `.part1.jsonl` already exists at 8 MiB → next rollover creates `.part2.jsonl`.
   12. `test_atomic_append_concurrent` — 100 parallel `af log` invocations → 100 distinct lines, no interleaving (uses subprocess pool).
   13. `test_exit_code_validation_error` — invalid `--agent foo-not-in-whitelist` → exit code 3.
   14. `test_exit_code_filesystem_error` — read-only target dir → exit code 4.
   15. `test_fail_open_in_hook` — `af log <bad-args> || true` → shell exit 0 (caller pattern).
   16. `test_record_passes_log_validate` — round-trip: write via `af log`, read back via `af log-validate` → 0 violations.
2. **Green.** Implement `core/activity_log.py` (validator + composer) and `commands/log_cmd.py`. Wire into `cli.py` LazyGroup.
3. **Refactor.** Extract any duplication between `log_cmd` and the (yet-unwritten) `log_validate_cmd` into `core/activity_log.py`.

**Phase 2 Definition of Done:**
- All 16 unit tests pass.
- `af log --help` shows the new command.
- `af log "test" --event note --agent claude-code --agent-version 0.0.1 --root /tmp/x` writes a valid JSONL line that validates externally with `python3 -m json.tool < /tmp/x/logs/agent-activity/<today>.jsonl`.

### Phase 3 — `af log-validate` command (TDD)

Red-Green-Refactor per COR-1500:

1. **Red.** Write `tests/test_log_validate_cmd.py`. Test cases:
   1. `test_default_target_today_prj_log` — no `PATH` arg → validates today's PRJ log.
   2. `test_path_is_file` — explicit JSONL file → validates only that file.
   3. `test_path_is_directory` — directory → validates every `*.jsonl` and `*.partN.jsonl` recursively at depth 1.
   4. `test_violation_missing_required_field` — record without `ts` → exit 1, output cites field `ts` and the line number.
   5. `test_violation_wrong_type_session_id` — `session_id: 12345` (int not string) → exit 1.
   6. `test_violation_agent_not_in_whitelist` — `agent: "qodo"` → exit 1.
   7. `test_violation_agent_other_without_agent_name` — `agent: "other"` and no `agent_name` → exit 1 (PR #78 R1 regression).
   8. `test_violation_summary_truncated_false` — `summary_truncated: false` → exit 1 (must be omitted, not false; PR #78 R1 spec).
   9. `test_violation_summary_truncated_true_no_size_correlation` — `summary_truncated: true` on a 1024-byte record → 0 violations (regression for PR #78 R2 fix; validator must not require near-cap size).
   10. `test_violation_line_too_long` — synthetic 4097-byte line → exit 1.
   11. `test_violation_malformed_schema_literal` — `schema: "alfred.activity/v0.9"` → exit 1.
   12. `test_quiet_on_success` — clean file → empty stdout, exit 0.
   13. `test_output_format` — violation output matches `<path>:<lineno>: <field>: <reason>`.
2. **Green.** Implement `commands/log_validate_cmd.py`. Reuse `core/activity_log.validate_record`.
3. **Refactor.** None expected — Phase 3 is mostly thin Click wrapper.

**Phase 3 Definition of Done:**
- All 13 tests pass.
- `af log-validate --help` shows the command.
- Round-trip integration test: `af log` → `af log-validate` → 0 violations.

### Phase 4 — Reference Claude Code `Stop` hook + integration

- **`hooks/emit-activity.sh`**:
  ```bash
  #!/usr/bin/env bash
  # Claude Code Stop hook. Emits a task.done activity log record.
  # Reads $CLAUDE_TURN_DESCRIPTION (set by harness) for summary;
  # falls back to "claude-code turn complete" if absent.
  af log "${CLAUDE_TURN_DESCRIPTION:-claude-code turn complete}" \
    --event task.done \
    --agent claude-code \
    --agent-version "${CLAUDE_VERSION:-unknown}" \
    || true
  ```
- **`tests/test_hook_emit_activity.py`**: smoke test invoking the hook with a tmpdir as `--root`, then calling `af log-validate` over the result.
- **CHANGELOG + version bump**: v1.9.0 entry; pyproject.toml 1.8.0 → 1.9.0.
- **CLAUDE.md note**: one paragraph in the "Essential Commands" section documenting `af log` + `af log-validate` mirroring the existing `af guide` / `af plan` style.
- **Integration test**: real-session smoke test — invoke the hook over a contrived 5-turn session, validate that `af log-validate` reports 0 violations and the file contains 5 `task.done` records.

**Phase 4 Definition of Done:**
- Hook script executable + passes shellcheck.
- Hook integration test passes.
- `af log-validate` over the integration test fixture reports 0 violations.
- All PRP-2230 acceptance criteria satisfied (lines 154–161 verifiable; line 160 "no reverse dependency on FXA-2229" verified by deliberate test harness on a tree without FXA-2229 changes).

## Acceptance Criteria

This CHG is complete when:

- All 4 phases land via separate PRs against `main`, each with strict ≥ 9.0 review per COR-1602 (default 2 reviewers per phase, since this is implementation rather than the PRP itself).
- All PRP-2230 acceptance criteria (lines 154–161 of the merged PRP) are met:
  - `COR-1205` REF in PKG with v1 schema fully specified ✓ (Phase 1).
  - `COR-1206` SOP in PKG with mandatory triggers, optional triggers, per-agent mapping table covering ≥ 5 agents + `other` ✓ (Phase 1).
  - `af log` writes records that pass `af log-validate` including all 6 layer/auto-fill/cap/rotation behaviors per spec ✓ (Phase 2).
  - `af log-validate` reports violations on the 6 specific synthetic invalid cases ✓ (Phase 3).
  - `COR-1200` step 1 has the additive bullet ✓ (Phase 1).
  - Reference Claude Code `Stop` hook ships, passes `af log-validate` over a real session ✓ (Phase 4).
  - No reverse dependency on FXA-2229 ✓ (Phase 4 dedicated test).
- 4/4 PRP satellite advisories are addressed:
  - L84 retention policy: `COR-1205` defines 30-day default + 256 MiB soft cap ✓ (Phase 1).
  - L85 POSIX wording: tightened in `COR-1205` to cite kernel `O_APPEND` semantics rather than `PIPE_BUF` ✓ (Phase 1).
- All new tests are TDD-first per COR-1500 (red commit precedes green commit in each phase's PR).
- `af validate` reports 0 issues across all phases.
- Release v1.9.0 ships with `CHANGELOG.md` entry calling out activity log protocol.

## Decisions

### One CHG with 4 phases, not 4 CHGs

The work is small enough (~1300 LOC total, ~700 of which are tests) that one CHG with phase-PRs is cleaner than 4 separate CHGs. Phase boundaries provide review surface; CHG-level coherence keeps the protocol-implementation pairing visible.

### `core/activity_log.py` keeps Click-free

Per PRP-2230 Decisions §"vendor-neutral protocol" + Section 6 advisory: schema constants and `validate_record` live in `core/`, callable by library consumers without Click. The Click commands are thin wrappers that import from `core/`. This matches the existing project pattern (`core/parser.py`, `core/scanner.py`, etc. — none import Click).

### Reference hook stays the only ref impl in this CHG

PRP-2230 line 49 + line 159: only Claude Code reference hook ships in v1. Copilot / Cursor / Cline / Aider / Codex CLI / Gemini CLI integrations are explicitly **out of scope** for this CHG — each will be its own follow-on CHG once at least one downstream consumer ships against the v1 contract.

### Version bump to v1.9.0, not v2.0.0

The protocol is additive (new CLI commands, new doc types, no breaking change to existing `af` surface). Per Alfred's existing semver pattern (v1.8.0 was the last user-facing feature), v1.9.0 is the right increment. v2.0.0 stays reserved for an actual breaking change.

---

## Open Questions

- Should Phase 1 also ship a `COR-1207-SOP-Activity-Log-Retention` SOP describing the 30-day default and `af log-validate --gc` future flag, or is folding retention rules into `COR-1205` enough? *Default: fold into COR-1205 to avoid SOP proliferation; promote to its own SOP only when a third caller (beyond Claude Code and the future cron consumer) needs to read it.*
- Should the integration test in Phase 4 actually invoke a real Claude Code session, or simulate one via a fixture? *Default: simulate via fixture (deterministic, CI-friendly); real-session smoke test is a manual pre-release check, not an automated test.*

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-02 | Initial version. Implements PRP-2230 (Agent Activity Log Protocol v1) which passed strict 4-reviewer review on the same date and was merged via PR #78 (with 3 follow-on review rounds covering 4 schema/CLI bug fixes). Folds the 4/4 PRP satellite advisories (L84 retention policy + L85 POSIX wording) into Phase 1. | Frank + Claude |
