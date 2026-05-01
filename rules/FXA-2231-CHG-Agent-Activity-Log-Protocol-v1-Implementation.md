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
| `src/fx_alfred/rules/COR-1205-REF-Agent-Activity-Log-Format.md` | Canonical data contract — sourced from PRP-2230 storage/format/archival sections, plus 30-day retention + 256 MiB soft-cap policy added (see Phase 1) | ~160 |
| `src/fx_alfred/rules/COR-1206-SOP-Emit-Agent-Activity.md` | Implementation guide — sourced from PRP-2230 trigger/mapping sections, plus per-agent integration examples, `.gitignore` snippet (`rules/logs/`), and the **scanner-skip enforcement rule** for `rules/logs/` subtree | ~200 |
| `src/fx_alfred/core/activity_log.py` | Framework-agnostic schema + validator + reader (no Click). Constants: `SCHEMA_LITERAL`, `AGENT_WHITELIST`, `EVENT_ENUM`, `RECORD_LINE_CAP_BYTES = 4096`, `FILE_SIZE_CAP_BYTES = 8 * 1024 * 1024`, `RETENTION_DAYS_DEFAULT = 30`, `DIR_SOFT_CAP_BYTES = 256 * 1024 * 1024`. Functions: `validate_record(dict) → list[Violation]`, `iter_records(path_or_dir) → Iterator[(source, lineno, dict)]` (transparently reads loose `.jsonl` and `archive.zip` entries), `compose_record(...) → bytes` (truncation + `summary_truncated` flag), `archive_directory(dir, force=False) → ArchiveResult`. | ~340 |
| `src/fx_alfred/commands/log_cmd.py` | Click command for `af log`. Layer resolution per PRP-2230 (`./rules/logs/...` for PRJ; `~/.alfred/logs/...` for USR), auto-fill `ts`/`schema`/`session_id`/`agent_version`, pre-condition rotation check, **lazy startup archival** of any closed-day raw files, atomic O_APPEND write ≤ 4096 bytes, exit codes 0/2/3/4. | ~150 |
| `src/fx_alfred/commands/log_validate_cmd.py` | Click command for `af log-validate`. Default-target = today's PRJ log via shared layer resolution. Path-vs-dir-vs-zip dispatch. Per-line check via `core/activity_log.validate_record`. Reads zip entries transparently via `core/activity_log.iter_records`. Output `<path>:<lineno>: <field>: <reason>` for loose, `<dir>/archive.zip!<member>:<lineno>:` for zip entries. Exit codes 0/1/2/4/5. | ~110 |
| `src/fx_alfred/commands/log_archive_cmd.py` | **NEW (this amendment).** Click command for `af log-archive`. Calls `core/activity_log.archive_directory` on the resolved log directory. Idempotent. Exit codes 0/2/4/5. `--force` flag to overwrite a corrupt existing archive. | ~80 |
| `hooks/emit-activity.sh` | Reference Claude Code `Stop` hook. Reads `$CLAUDE_*` env vars, builds `af log ... \|\| true` invocation. Idempotent on re-source. | ~40 |
| `tests/test_activity_log_schema.py` | TDD: `validate_record` unit tests covering all v1 rules including the cases pinned in PRP-2230 acceptance criteria (`summary_truncated: false`, line > 4096 bytes, `agent: "other"` without `agent_name`, etc.) | ~250 |
| `tests/test_activity_log_archive.py` | **NEW (this amendment).** TDD: `archive_directory` atomicity (temp + rename + unlink), idempotency on empty dir, recovery from stale `archive.zip.tmp`, refusal-with-`--force` semantics on corrupt existing archive, round-trip (raw → zip → reader yields same records). | ~180 |
| `tests/test_activity_log_reader.py` | **NEW (this amendment).** TDD: `iter_records` transparent reads — pure-loose dir, pure-zip dir, mixed dir, single `.jsonl` file, single `.zip` file. Verifies `(source, lineno, dict)` tuples for both loose and zip entries. | ~120 |
| `tests/test_log_cmd.py` | TDD: layer resolution (rules/logs/), auto-fill, line-size cap with `summary_truncated`, pre-condition rotation handoff, **lazy startup archival**, exit codes, fail-open mode | ~240 |
| `tests/test_log_validate_cmd.py` | TDD: file vs dir vs zip dispatch, default target, violation output format (loose + zip notation), exit codes incl. corrupt-zip case | ~150 |
| `tests/test_log_archive_cmd.py` | **NEW (this amendment).** TDD: archive command CLI surface (CLI args, exit codes, output, `--force`). | ~80 |
| `tests/test_scanner_skip_rules_logs.py` | **NEW (this amendment).** Regression test: place `rules/logs/2026-05-02.jsonl` and `rules/logs/archive.zip` under a project; verify `af list`, `af search`, `af status`, `af validate` all skip them without warnings. Locks the scanner-skip contract from `COR-1206`. | ~80 |
| `tests/test_hook_emit_activity.py` | TDD: hook script smoke test (real `af log` invocation, validate output) | ~40 |

### Files to be modified

| File | Nature | Estimated LOC |
|---|---|---|
| `src/fx_alfred/cli.py` | Register `log`, `log-validate`, `log-archive` via `LazyGroup` (mirror existing pattern; one entry per command) | small (~9) |
| `src/fx_alfred/core/scanner.py` | **Amendment.** Add `rules/logs/` to the hard-skip set so `scan_documents()` never recurses into it. Implementation = explicit dirname check; mirrors how `__pycache__` and `.git` are handled. | small (~4) |
| `src/fx_alfred/rules/COR-1200-SOP-Session-Retrospective.md` | Add **single additive bullet** in step 1 directing agent to read `./rules/logs/<today>.jsonl` (and `archive.zip` if relevant) first. Exact wording pinned in this CHG (see Phase 1). 6-step structure unchanged. | small (~3) |
| `.gitignore` (project root) | Add `rules/logs/` per amended PRP-2230 default git policy | 1 line |
| `src/fx_alfred/CHANGELOG.md` | v1.9.0 entry covering activity log protocol (path, archival, three new commands) | small |
| `pyproject.toml` | Version bump 1.8.0 → 1.9.0 | small |
| `CLAUDE.md` (project root) | One-paragraph note on `af log` + `af log-validate` + `af log-archive` (mirroring existing CLI docs) | small |

### Systems affected

- **af CLI**: 3 new commands (`log`, `log-validate`, `log-archive`) registered via `LazyGroup`. No existing command behavior changes.
- **PKG documents**: 2 new (`COR-1205` REF, `COR-1206` SOP). 1 modified (`COR-1200` step 1 additive bullet only).
- **Schema/validation infra**: new `core/activity_log.py` module. `core/` remains Click-free (consistent with FXA-2230 Decisions §"vendor-neutral protocol"). `core/scanner.py` gets a 4-line hard-skip addition for `rules/logs/`.
- **No FXA-2229 dependency**: this CHG ships independently. PRP-2230 line 160 requires this; the test suite verifies it (see Phase 5 acceptance).

### Rollback plan

Rollback is a per-phase revert:

- **Phase 5 (hook + release)** — `git revert <Phase-5-merge>`; activity log directory persists but no new emits, version stays at the previous release.
- **Phase 4 (`af log-archive` + scanner-skip)** — `git revert <Phase-4-merge>`; archival reverts to manual (or none); existing archives stay readable. Scanner-skip rule reverts — `af` document scanners again rely on the implicit `*.md`-only filename match.
- **Phase 3 (`af log-validate`)** — `git revert <Phase-3-merge>`; existing logs become un-validated but readable.
- **Phase 2 (`af log`)** — `git revert <Phase-2-merge>`; agents can no longer emit but the contract docs remain. Existing logs remain valid JSONL on disk.
- **Phase 1 (docs)** — `git revert <Phase-1-merge>`; deletes the two new PKG docs. Validators referencing them become inert (Phase 1 is doc-only, no code consumes it yet).
- **Full rollback** — `git revert` Phase 5 → Phase 4 → Phase 3 → Phase 2 → Phase 1 in reverse order. The protocol is observability-only; reverting cannot corrupt application state.

## Implementation Plan

Per PRP-2230 line 204 workflow: **`COR-1101 (CHG, current) → COR-1500 TDD per phase`**. Each phase is one PR with red-green-refactor commits per COR-1500. Phases are executable in order; Phase N can begin only after Phase N-1 merges.

### Phase 0 — Branch + scaffolding

- Create branch `fx/2231-chg-agent-activity-log` (this CHG itself lives here pre-merge).
- Create empty placeholder files for `core/activity_log.py`, `commands/log_cmd.py`, `commands/log_validate_cmd.py`, `commands/log_archive_cmd.py`, `hooks/emit-activity.sh` (so subsequent phases can stage individually).
- Add `.gitignore` entry for `rules/logs/`.
- No tests yet; no behavior change.

### Phase 1 — Documents (`COR-1205`, `COR-1206`, `COR-1200` additive bullet, retention policy)

- **`COR-1205-REF-Agent-Activity-Log-Format`**: write the canonical data contract sourced from PRP-2230 (storage location + format + archival sections). Add the **retention policy section** (4/4 PRP satellite advisory):
  - Default retention: keep activity log files (loose `*.jsonl` and entries inside `archive.zip`) for **30 days**; older entries MAY be deleted by the agent runtime or by user cron.
  - Aggregate disk-space soft cap: **256 MiB per `rules/logs/` directory** (raw + zip combined). Beyond this the runtime SHOULD warn; deletion is user-driven, not automatic.
  - Compression policy: closed days are stored only inside `archive.zip` (zip's DEFLATE provides 7–10× on JSONL). No additional gzip layer in v1.
- **Tighten POSIX wording** (4/4 PRP satellite advisory): cite "Linux/macOS/BSD `O_APPEND` provides per-write atomicity for regular files at the kernel level (inode lock); `PIPE_BUF` (≥ 4096) is the related guarantee for pipes/FIFOs and motivates the line-size cap upper bound. The 4 KiB cap is conservative — well within atomicity windows on every supported OS."
- **`COR-1206-SOP-Emit-Agent-Activity`**: write the implementation guide. Sourced from PRP-2230 trigger + mapping sections. Add:
  - Per-agent integration recipes (one paragraph each for the 7 mapping table entries).
  - The `.gitignore` snippet (`rules/logs/`).
  - **Scanner-skip enforcement rule** (PRP-2230 amendment Decision §"Storage location"): all `af` document scanners (`list`, `search`, `status`, future `validate`) MUST hard-skip `rules/logs/`. The directory is reserved for `*.jsonl`, `*.partN.jsonl`, `archive.zip`, `archive.zip.tmp`. Any `.md` file dropped there MUST be ignored by `af list` rather than treated as a document.
  - Compliance test command: `af log-validate <one-session-log.jsonl>` must pass.
- **`COR-1200` step 1 additive bullet** (3/4 PRP satellite advisory — exact wording pinned here):
  > **Before reconstructing actions:** if `./rules/logs/<today UTC>.jsonl` exists (or `./rules/logs/archive.zip` contains today's entry), read it via `af log-validate` (verifies schema) and use its `task.done` / `doc.created` / `doc.updated` / `decision` events as the ground truth for what happened this session. The chat-history reconstruction below remains the fallback when the log is empty or absent.
- No code yet. Phase 1 is documentation-only and ships independently if needed.
- **`af validate` must report 0 issues** before merge.

**Phase 1 Definition of Done:**
- 2 new PKG docs land, 1 modified PKG doc lands, `.gitignore` updated with `rules/logs/`.
- All amended PRP-2230 doc-acceptance criteria satisfied (storage location, archival, scanner-skip rule, retention, gitignore policy).

### Phase 2 — `af log` command (TDD)

Red-Green-Refactor per COR-1500:

1. **Red.** Write `tests/test_log_cmd.py` first. Test cases (each a separate test function):
   1. `test_layer_resolution_root_flag` — `af log --root /tmp/proj "msg" --event note --agent claude-code` writes to `/tmp/proj/rules/logs/<today>.jsonl`.
   2. `test_layer_resolution_cwd_with_rules_dir` — cwd has `./rules/`; no `--root` → writes to `./rules/logs/<today>.jsonl`.
   3. `test_layer_resolution_user_fallback` — no `--root`, no project markers → writes under `~/.alfred/logs/`.
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
   17. `test_lazy_archival_on_startup` — pre-populate dir with `<yesterday>.jsonl`; invoke `af log` for today → yesterday is folded into `archive.zip` BEFORE today's record is written; raw yesterday file unlinked.
   18. `test_lazy_archival_failure_does_not_block_emit` — pre-populate corrupt `archive.zip` (truncated bytes); invoke `af log` → today's record still written; archival warning printed to stderr; exit code 0.
2. **Green.** Implement `core/activity_log.py` (validator + composer + `archive_directory` helper) and `commands/log_cmd.py`. Wire into `cli.py` LazyGroup.
3. **Refactor.** Extract any duplication between `log_cmd` and the (yet-unwritten) `log_validate_cmd` / `log_archive_cmd` into `core/activity_log.py`.

**Phase 2 Definition of Done:**
- All 18 unit tests pass.
- `af log --help` shows the new command.
- `af log "test" --event note --agent claude-code --agent-version 0.0.1 --root /tmp/x` writes a valid JSONL line that validates externally with `python3 -m json.tool < /tmp/x/rules/logs/<today>.jsonl`.

### Phase 3 — `af log-validate` command (TDD)

Red-Green-Refactor per COR-1500:

1. **Red.** Write `tests/test_log_validate_cmd.py` (loose-only cases) + `tests/test_activity_log_reader.py` (zip transparency). Test cases:
   1. `test_default_target_today_prj_log` — no `PATH` arg → validates today's PRJ log at `./rules/logs/<today>.jsonl`.
   2. `test_path_is_file` — explicit JSONL file → validates only that file.
   3. `test_path_is_directory` — directory → validates every loose `*.jsonl` / `*.partN.jsonl` AND every entry inside `archive.zip` if present (union view).
   4. `test_path_is_zip` — `path/to/archive.zip` → validates every member inside as a JSONL file.
   5. `test_violation_missing_required_field` — record without `ts` → exit 1, output cites field `ts` and the line number.
   6. `test_violation_wrong_type_session_id` — `session_id: 12345` (int not string) → exit 1.
   7. `test_violation_agent_not_in_whitelist` — `agent: "qodo"` → exit 1.
   8. `test_violation_agent_other_without_agent_name` — `agent: "other"` and no `agent_name` → exit 1 (PR #78 R1 regression).
   9. `test_violation_summary_truncated_false` — `summary_truncated: false` → exit 1 (must be omitted, not false; PR #78 R1 spec).
   10. `test_violation_summary_truncated_true_no_size_correlation` — `summary_truncated: true` on a 1024-byte record → 0 violations (regression for PR #78 R2 fix; validator must not require near-cap size).
   11. `test_violation_line_too_long` — synthetic 4097-byte line → exit 1.
   12. `test_violation_malformed_schema_literal` — `schema: "alfred.activity/v0.9"` → exit 1.
   13. `test_violation_inside_zip_uses_bang_notation` — invalid record packed inside `archive.zip` → output uses `<dir>/archive.zip!2026-04-15.jsonl:N: <field>: <reason>` form.
   14. `test_corrupt_zip_exits_5` — truncated zip file → exit code 5; clear error message.
   15. `test_quiet_on_success` — clean file → empty stdout, exit 0.
   16. `test_output_format` — violation output matches `<path>:<lineno>: <field>: <reason>` for loose, `<dir>/archive.zip!<member>:<lineno>:` for zip members.
2. **Green.** Implement `commands/log_validate_cmd.py` and `core/activity_log.iter_records` (the union-reader). Reuse `core/activity_log.validate_record`.
3. **Refactor.** Extract zip-vs-loose dispatch into `core/activity_log.iter_records` so `log_archive_cmd` (Phase 4) can reuse it.

**Phase 3 Definition of Done:**
- All 16 tests pass.
- `af log-validate --help` shows the command.
- Round-trip integration test: `af log` → `af log-validate` → 0 violations.
- Zip-aware integration test: pack a known-good `<yesterday>.jsonl` into `archive.zip`, then `af log-validate ./rules/logs/` → 0 violations.

### Phase 4 — `af log-archive` command + scanner-skip enforcement (TDD)

This phase covers the two amendments introduced after the original CHG-2231 draft: explicit archival CLI surface, and the `rules/logs/` scanner-skip rule with regression test.

1. **Red.** Write `tests/test_log_archive_cmd.py` + `tests/test_activity_log_archive.py` + `tests/test_scanner_skip_rules_logs.py`. Test cases:
   - **`log_archive` CLI behavior:**
     - `test_archive_idempotent_empty_dir` — empty dir → exit 0, no output.
     - `test_archive_only_today_present` — only `<today>.jsonl` exists → exit 0, file untouched.
     - `test_archive_one_closed_day` — `<yesterday>.jsonl` exists → folded into `archive.zip`, raw file unlinked, today's file untouched.
     - `test_archive_with_existing_zip` — `archive.zip` already contains old days; new closed days union-merged into it.
     - `test_archive_atomic` — kill `af log-archive` mid-run (forced) → `archive.zip.tmp` exists, original `archive.zip` intact, no data loss.
     - `test_archive_recovers_from_stale_tmp` — pre-existing stale `archive.zip.tmp` → unlinked at start of next run.
     - `test_archive_corrupt_existing_zip_exit_5` — truncated `archive.zip` → exit 5 without `--force`; with `--force` the corrupt file is replaced.
     - `test_archive_force_flag` — `--force` flag on a corrupt archive → succeeds, replaces the archive with one containing only the closed-day raw files.
   - **Scanner-skip regression:**
     - `test_af_list_skips_rules_logs` — drop `rules/logs/2026-05-02.jsonl`, `rules/logs/archive.zip`, even a misplaced `rules/logs/FXA-9999-PRP-Test.md` → `af list` output is unchanged from baseline. No warnings.
     - `test_af_search_skips_rules_logs` — drop `rules/logs/2026-05-02.jsonl` containing the literal "FOOBAR123" → `af search FOOBAR123` returns 0 hits.
     - `test_af_status_skips_rules_logs` — same fixture as above → `af status` document counts unchanged from baseline.
     - `test_af_validate_skips_rules_logs` — same fixture → `af validate` reports 0 issues (does not flag the misplaced `.md`, does not try to parse the `.jsonl` as a doc).
2. **Green.** Implement `commands/log_archive_cmd.py` and `core/activity_log.archive_directory`. Add the `rules/logs/` skip set to `core/scanner.py` (mirroring how `__pycache__` and `.git` are handled).
3. **Refactor.** Verify `core/activity_log.iter_records` (from Phase 3) is reused by the archive logic for the union-of-existing-zip-plus-closed-day-raw computation.

**Phase 4 Definition of Done:**
- All 12 tests pass (8 archive + 4 scanner-skip).
- `af log-archive --help` shows the command.
- `core/scanner.py` skip set includes `rules/logs/`; comment cites COR-1206.
- Manual integration: pre-populate `./rules/logs/` with 30 days of synthetic `.jsonl` (~30 MiB raw); run `af log-archive`; verify resulting `archive.zip` ≤ 5 MiB and contains all 30 entries.

### Phase 5 — Reference Claude Code `Stop` hook + release

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
- **CHANGELOG + version bump**: v1.9.0 entry calling out: new `rules/logs/` location, new commands `af log` / `af log-validate` / `af log-archive`, hybrid raw+zip archival, scanner-skip rule for `rules/logs/`.
- **`pyproject.toml`**: 1.8.0 → 1.9.0.
- **CLAUDE.md note**: one paragraph in "Essential Commands" documenting `af log` / `af log-validate` / `af log-archive` mirroring the existing `af guide` / `af plan` style.
- **Integration test**: real-session smoke test — invoke the hook over a contrived 5-turn session, validate that `af log-validate ./rules/logs/` reports 0 violations and the file contains 5 `task.done` records.

**Phase 5 Definition of Done:**
- Hook script executable + passes shellcheck.
- Hook integration test passes.
- `af log-validate` over the integration test fixture reports 0 violations.
- All amended PRP-2230 acceptance criteria satisfied; "no reverse dependency on FXA-2229" verified by deliberate test harness on a tree without FXA-2229 changes.
- Release v1.9.0 ships.

## Acceptance Criteria

This CHG is complete when:

- All 5 phases land via separate PRs against `main`, each with strict ≥ 9.0 review per COR-1602 (default 2 reviewers per phase, since this is implementation rather than the PRP itself).
- All amended PRP-2230 acceptance criteria are met:
  - `COR-1205` REF in PKG with v1 schema fully specified, including archival policy and reserved-subtree rule for `rules/logs/` ✓ (Phase 1).
  - `COR-1206` SOP in PKG with mandatory triggers, per-agent mapping table covering ≥ 5 agents + `other`, `.gitignore` snippet (`rules/logs/`), and scanner-skip enforcement rule ✓ (Phase 1).
  - `af log` writes records that pass `af log-validate` including layer resolution, auto-fill, line-cap, pre-condition rotation, **lazy startup archival** ✓ (Phase 2).
  - `af log-validate` reports violations on all pinned synthetic invalid cases AND transparently reads `archive.zip` entries ✓ (Phase 3).
  - `af log-archive` performs atomic archival with stale-tmpfile recovery and corrupt-archive `--force` semantics ✓ (Phase 4).
  - `af` document scanners (`list`, `search`, `status`, `validate`) verifiably skip `rules/logs/` per regression test ✓ (Phase 4).
  - `COR-1200` step 1 has the additive bullet referencing `./rules/logs/<today>.jsonl` ✓ (Phase 1).
  - Reference Claude Code `Stop` hook ships, passes `af log-validate` over a real session ✓ (Phase 5).
  - No reverse dependency on FXA-2229 ✓ (Phase 5 dedicated test).
- 4/4 PRP satellite advisories addressed:
  - L84 retention policy: `COR-1205` defines 30-day default + 256 MiB soft cap on `rules/logs/` ✓ (Phase 1).
  - L85 POSIX wording: tightened in `COR-1205` to cite kernel `O_APPEND` semantics rather than `PIPE_BUF` ✓ (Phase 1).
- All new tests are TDD-first per COR-1500 (red commit precedes green commit in each phase's PR).
- `af validate` reports 0 issues across all phases.
- Release v1.9.0 ships with `CHANGELOG.md` entry calling out activity log protocol (path, archival, three new commands, scanner-skip rule).

## Decisions

### One CHG with 5 phases, not 5 CHGs

The work is ~1700 LOC total (~900 of which are tests after the path/archive amendment). One CHG with phase-PRs is cleaner than 5 separate CHGs. Phase boundaries provide review surface; CHG-level coherence keeps the protocol-implementation pairing visible. Phase counts grew from 4 → 5 when the amendment added `af log-archive` and the scanner-skip regression test.

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
| 2026-05-02 | Sync to PRP-2230 amendment (PR #80, route A): (a) Path migrated from `./logs/agent-activity/` to `./rules/logs/` throughout. (b) New file `commands/log_archive_cmd.py` and `core/activity_log.archive_directory` for atomic zip archival. (c) New tests: `test_activity_log_archive.py`, `test_activity_log_reader.py`, `test_log_archive_cmd.py`, `test_scanner_skip_rules_logs.py`. (d) Phase decomposition expanded 4 → 5 (Phase 4 = af log-archive + scanner-skip enforcement; Phase 5 = reference hook + v1.9.0 release). (e) `core/scanner.py` modification listed in 'Files to be modified' to add `rules/logs/` to skip set. (f) Phase 2 test count 16 → 18 (lazy archival on startup); Phase 3 test count 13 → 16 (zip-aware paths). (g) Total LOC estimate updated 1300 → 1700, tests 700 → 900. | Frank + Claude (sync to amended PRP) |
