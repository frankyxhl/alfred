# PRP-2307: Append Only Usage Ledger For Evolve Signals

**Applies to:** FXA project
**Last updated:** 2026-06-21
**Last reviewed:** 2026-06-21
**Status:** Approved
**Related:** GitHub issue #233, FXA-2230, FXA-2231, COR-1205, FXA-2148, FXA-2146
**Reviewed by:** Claude Code R2: PASS 9.0; Codex CLI R2: PASS 9.2

---

## What Is It?

This PRP proposes the issue #233 delivery slice: turn Alfred's existing Phase-0 activity-log scaffolding into a user-layer, append-only command usage ledger that records real `af guide` and `af plan` routing behavior, then make the Evolve SOP consume that ledger as a primary signal source.

The scope is deliberately narrower than the full historical FXA-2231 five-phase agent activity log rollout. This slice completes the command-registration and Alfred-command telemetry path needed by Evolve, while preserving the existing COR-1205 / FXA-2230 activity-log contract as the compatibility base.


---

## Problem

Alfred's Evolve signal collection currently derives Necessity signals by rescanning documents and, optionally, session logs. That gives retrospective inference, not usage telemetry. As a result, Evolve cannot reliably see which SOPs are never routed, which `af plan --task` requests produce no SOP matches, or which SOPs are frequently used in actual workflows.

Issue #233 identifies an existing implementation foothold: `src/fx_alfred/core/activity_log.py` and the `log*` command modules exist as Phase-0 scaffolding, but `src/fx_alfred/cli.py` does not register them and the high-value command capture points (`guide_cmd.py` and `plan_cmd.py`) do not append anything.

## Scope

In scope for this PR:

- Register `af log`, `af log-validate`, and `af log-archive` in the LazyGroup command table.
- Implement the minimal activity-log core needed for append, validation, archive, and iteration of COR-1205 JSONL records.
- Add a first-party Alfred command usage record shape that extends COR-1205 without breaking existing `alfred.activity/v1` records.
- Make `af guide` append a best-effort row with the routing document ids it surfaced.
- Make `af plan` append a best-effort row with explicit SOP ids, auto-composed SOP ids, task text when present, and zero-match task routing gaps.
- Keep first-party command usage writes in the user layer under `Path.home() / ".alfred"`, so tests using `isolate_home` never touch the real home directory.
- Update FXA-2148 Signal Collection so Evolve reads the ledger for never-routed/planned SOPs, zero-match `af plan --task` calls, and per-SOP usage frequency.
- Add focused pytest coverage for append/read-back, command registration, guide/plan best-effort append, zero-match plan telemetry, validation, archive behavior, and best-effort write failure.

Out of scope for this PR:

- Daemons, schedulers, cron jobs, SSE, background samplers, or runtime UI.
- Cross-agent native hook integrations for Claude Code, Codex CLI, Cursor, Copilot, Gemini CLI, or other tools.
- Full completion of every phase in FXA-2231, including release/version bump and reference Claude Code Stop hook.
- Remote log shipping, embeddings, semantic search, or automatic Evolve actions based on the telemetry.
- Secret scanning beyond the existing privacy rule that command rows must not store prompt bodies, env values, tokens, or raw file contents.


## Proposed Solution

## Design

Reuse the existing `core/activity_log.py` scaffolding as the shared implementation module. This PRP realizes the core/log-command parts of FXA-2231 while adding the #233 first-party command usage telemetry needed by Evolve.

### Relationship to FXA-2231

FXA-2231 remains the historical implementation CHG for the broader Agent Activity Log Protocol. This PRP supersedes and realizes FXA-2231 Phases 2-4 for the current codebase:

- Phase 2: `af log` writer and `core/activity_log.py` validation/composition helpers.
- Phase 3: `af log-validate` reader/validator.
- Phase 4: `af log-archive` archival command and scanner-skip behavior where applicable.

FXA-2231 Phase 5 remains future work: reference Claude Code Stop hook, release packaging notes, and any cross-agent native integrations. This PR must update FXA-2231 and the Phase-0 scaffold docstrings so they no longer claim Phases 2-4 are still pending after FXA-2307 lands.

### Storage and Layer Behavior

There are two write paths, intentionally different:

1. `af log` CLI follows COR-1205 layer resolution exactly:
   - `--root <DIR>` writes to `<DIR>/rules/logs/YYYY-MM-DD.jsonl`;
   - project cwd writes to that project's `rules/logs/YYYY-MM-DD.jsonl`;
   - no project context falls back to `Path.home() / ".alfred" / "logs" / "YYYY-MM-DD.jsonl`.

2. first-party `af guide` / `af plan` usage telemetry always writes to:

   ```text
   Path.home() / ".alfred" / "logs" / "YYYY-MM-DD.jsonl"
   ```

   This user-layer path is deliberate: guide/plan usage is personal routing telemetry and should not churn project `rules/logs/` or project git. Use `Path.home()` directly so the existing `isolate_home` fixture controls the location in tests.

The implementation must keep these two paths separate. Do not route guide/plan telemetry through the public `af log` CLI layer resolver.

### Record Contract

Keep the existing `schema: "alfred.activity/v1"` literal and required fields from COR-1205. For first-party Alfred command usage rows:

- use `agent: "other"` and `agent_name: "af"` rather than extending the v1 agent whitelist;
- use `event: "note"`;
- use existing `refs` for surfaced/composed SOP ids, not a new `sop_ids` field;
- add a documented optional command-usage extension to COR-1205.

New optional command-usage fields:

| Field | Type | Constraint |
|-------|------|------------|
| `command` | string | One of `guide`, `plan`, `log`, `log-validate`, `log-archive`; 1-32 chars. |
| `usage_kind` | string | One of `routing_docs`, `plan_explicit`, `plan_task`, `plan_task_gap`, `manual_log`. |
| `task_text` | string | Optional sanitized CLI `--task` value; 1-200 chars, no newlines, no NUL bytes. |
| `task_text_sha256` | string | Optional lowercase hex SHA-256 of the raw UTF-8 CLI `--task` argument before sanitization or truncation when `task_text` is omitted or redacted. |
| `task_text_redacted` | boolean | Optional; `true` only when sensitive-looking content was omitted or replaced. Omit otherwise. |
| `result_count` | integer | Non-negative; number of routing docs surfaced or SOP refs composed. |

Validator behavior:

- Unknown optional fields remain invalid for v1 writers unless COR-1205 lists them.
- `refs` entries must match canonical `PREFIX-ACID` shape, dedupe, and stay within the existing cap.
- `task_text_redacted: false` is invalid; omit the field unless redaction occurred.
- `task_text_sha256` must be exactly 64 lowercase hex chars.
- `agent_name: "af"` records are first-party Alfred command telemetry and must be excluded from any future "spike in agent: other" third-party whitelist-trigger heuristic.
- All command-usage fields participate in the 4 KiB line cap.
- Zip-member violation paths must standardize COR-1205 / FXA-2231 on `archive.zip::<member>:<lineno>:` notation, not `archive.zip!<member>:<lineno>:`.

### Privacy Policy for `task_text`

`af plan --task` accepts free-form user input, so the ledger must not treat raw task text as automatically safe.

Implement a small sanitizer before writing `task_text`:

- collapse whitespace and remove newlines;
- truncate to 200 characters;
- redact token-like substrings and env-assignment patterns such as `KEY=value`, `*_TOKEN=...`, `*_KEY=...`, `sk-...`, `ghp_...`, and similar high-signal credential shapes;
- if redaction occurred or the text still looks sensitive after sanitization, omit `task_text`, write `task_text_sha256`, and set `task_text_redacted: true`.

The ledger stores only the CLI `--task` argument after sanitization. It must never store expanded prompt bodies, tool arguments, env values, or raw file contents.

### Commands

`af log` remains the COR-1205 universal writer surface. It must:

- accept a summary and standard COR-1205 fields;
- auto-fill timestamp, schema, session id, and unknown agent version when omitted;
- follow COR-1205 layer resolution;
- append one JSONL line with O_APPEND semantics;
- expose `--help` and return non-zero on invalid input;
- share validation with guide/plan append helpers.

`af log-validate` validates a file or directory of activity JSONL records, including current COR-1205 loose-file and `archive.zip` reader semantics.

`af log-archive` must implement the current COR-1205 five-step archival contract, including try-lock, tmpfile, atomic replace, raw-file cleanup, stale-tmp cleanup, corrupt archive handling, and `::` zip violation notation. Do not ship a partial "good enough" archive command under the `af log-archive` name.

### Best-effort Guide/Plan Hooks

Add framework-agnostic helper functions in `core/activity_log.py`, then call them from command modules inside a narrow fail-open wrapper so logging cannot break the user command.

`af guide` appends after determining active routing docs:

```json
{
  "event": "note",
  "summary": "af guide surfaced workflow routing documents",
  "agent": "other",
  "agent_name": "af",
  "command": "guide",
  "usage_kind": "routing_docs",
  "refs": ["COR-1103", "WUK-2100", "FXA-2125"],
  "result_count": 3
}
```

`af plan` appends after SOP composition/collection:

- explicit-only plans use `usage_kind: "plan_explicit"` and record explicit SOP ids in `refs`;
- `--task` plans use `usage_kind: "plan_task"`, sanitized `task_text` when safe, and all composed SOP ids in `refs`;
- zero-match `--task` calls use `usage_kind: "plan_task_gap"`, `result_count: 0`, and empty `refs`;
- failed `--task` composition should still write a best-effort gap/failure row when enough context is available, then preserve the original user-visible error behavior and exit code.

### Evolve Signal Reader

Add reader helpers that Evolve can use without Click imports:

- iterate activity records in a date window;
- aggregate SOP usage counts from `refs`;
- return plan routing gaps where `command == "plan"` and `usage_kind == "plan_task_gap"`;
- compute never-routed/planned SOPs by comparing all currently scanned SOP ids against usage counts.

Update FXA-2148 Phase 2 Signal Collection to read this ledger before optional session-log scanning and to record:

- never-routed/planned SOPs in the window;
- `af plan --task` zero-match routing gaps;
- per-SOP usage frequency.

### Implementation Plan

1. Add RED tests for `core/activity_log.py` append/read/validate helpers against `isolate_home`.
2. Add RED CLI tests proving `af log`, `af log-validate`, and `af log-archive --help` are registered.
3. Add RED tests for `af log` COR-1205 layer resolution: `--root`, project cwd, and user fallback.
4. Implement the COR-1205 activity-log helper and command wrappers.
5. Add RED tests for `guide` and `plan` usage rows, including write-failure best-effort behavior.
6. Add RED tests for `task_text` sanitization/redaction, including token/env-like input.
7. Implement guide/plan append hooks.
8. Add RED tests for the Evolve aggregation helpers and FXA-2148 doc update.
9. Add scanner-skip regression tests proving `af list`, `af search`, `af status`, and `af validate` skip `rules/logs/`.
10. Update COR-1205, FXA-2148, FXA-2231, and scaffold docstrings.
11. Run focused pytest, ruff, format check, `af validate`, then broader pytest if the changed surface warrants it.

### Acceptance Criteria

- `af log --help`, `af log-validate --help`, and `af log-archive --help` succeed.
- `af log` follows COR-1205 layer resolution for `--root`, project cwd, and user fallback.
- `af log-archive` implements the COR-1205 five-step archival contract; no partial archive command ships.
- `af guide` writes a valid best-effort user-layer record with surfaced routing doc ids in `refs`.
- `af plan` writes a valid best-effort user-layer record with composed/explicit SOP ids in `refs` and sanitized task text where safe.
- `af plan --task` zero-match behavior is visible in the ledger and preserves existing user-visible behavior and exit code.
- Write failures in activity logging do not break `guide` or `plan`.
- `isolate_home` tests prove guide/plan usage writes stay under the patched fake home.
- Evolve aggregation helpers report usage frequency, never-used SOP ids, and zero-match task gaps from fixture ledger records.
- COR-1205 documents the command-usage optional fields and their validator constraints.
- Scanner-skip tests prove `rules/logs/` remains invisible to document scanners.
- FXA-2148 Signal Collection documents the ledger-reader step and passes `af validate`.
- FXA-2231 and scaffold docstrings are updated so Phases 2-4 are no longer described as unimplemented after this PR.
- No daemon, scheduler, or background service is added.

### Validation Commands

```bash
.venv/bin/pytest tests/test_activity_log*.py tests/test_log*_cmd.py tests/test_guide_cmd.py tests/test_plan_cmd.py -v --tb=short
.venv/bin/pytest -v --tb=short
.venv/bin/ruff check .
.venv/bin/ruff format --check .
af validate --root /Users/frank/Projects/alfred
```

### Risks

- Scope creep into all remaining FXA-2231 release/hook work. Mitigation: explicitly supersede only Phases 2-4 and leave Phase 5 future.
- Schema drift from COR-1205. Mitigation: update COR-1205 in the same PR with exact optional field constraints and validator behavior.
- Hidden privacy leak through `task_text`. Mitigation: sanitize/redact, hash omitted values, and test sensitive-looking inputs.
- Logging failure breaking core commands. Mitigation: best-effort helper with explicit failure tests.


## Open Questions

None blocking implementation.

Resolved design decisions:

1. `af log` keeps COR-1205 layer resolution. The user-layer-only behavior applies only to internal first-party `guide` / `plan` usage telemetry.
2. Use existing `refs` for SOP ids instead of a new `sop_ids` field.
3. Use `agent: "other"` plus `agent_name: "af"` for first-party Alfred command usage rows rather than extending the v1 agent whitelist.
4. Extend COR-1205 with command-usage optional fields and validator constraints in the same PR.
5. FXA-2307 supersedes/realizes FXA-2231 Phases 2-4; FXA-2231 Phase 5 remains future work.
6. `af log-archive` must implement the full COR-1205 archive contract if it is registered.
7. All logging hooks stay fail-open for user commands.


---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-06-21 | Initial version | — |
| 2026-06-21 | R2 plan review revision: resolve Claude/Codex blockers around COR-1205 layer resolution, archive scope, schema constraints, privacy, and FXA-2231 disposition | Moth |
| 2026-06-21 | Plan review R2 passed: Claude Code 9.0 and Codex CLI 9.2, no blockers; minor advisories incorporated before implementation | Moth |
