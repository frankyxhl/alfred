# CHG-2286: Explicit UTF-8 For Alfred Document IO

**Applies to:** FXA project
**Last updated:** 2026-05-17
**Last reviewed:** 2026-05-17
**Status:** Approved
**Related:** GitHub issue #161
**Date:** 2026-05-17
**Requested by:** @frankyxhl
**Priority:** Medium
**Change Type:** Normal
**Targets:** src/fx_alfred/core/document.py; src/fx_alfred/core/skills.py; src/fx_alfred/core/compose.py; src/fx_alfred/core/preferences.py; src/fx_alfred/commands/_helpers.py; src/fx_alfred/commands/changelog_cmd.py; src/fx_alfred/commands/create_cmd.py; src/fx_alfred/commands/fmt_cmd.py; src/fx_alfred/commands/guide_cmd.py; src/fx_alfred/commands/index_cmd.py; src/fx_alfred/commands/plan_cmd.py; src/fx_alfred/commands/read_cmd.py; src/fx_alfred/commands/search_cmd.py; src/fx_alfred/commands/update_cmd.py; src/fx_alfred/commands/validate_cmd.py
**Closes:** #161

---

## What

Pass `encoding="utf-8"` explicitly to every Alfred document/template/preferences/index text I/O call site in `src/fx_alfred/`, so that `af` commands read and write Alfred-owned text files deterministically regardless of the host's `locale.getpreferredencoding()`. Widen `core.document.Resource` Protocol so the `encoding` keyword is part of the contract for both `pathlib.Path` and `importlib.resources.Traversable` implementations. Add a regression test that simulates a non-UTF-8 preferred encoding (e.g. GBK / ASCII) and asserts the affected commands still succeed on a file containing non-ASCII bytes.

In-scope call surfaces (22 sites total):

- `Path.read_text()` / `Traversable.read_text()` — 15 call sites (4 in `core/`: `document.py`, `skills.py`, `compose.py`, `preferences.py`; 11 in `commands/` across 9 modules: `guide_cmd`, `read_cmd`, `plan_cmd` ×2, `search_cmd`, `validate_cmd` ×2, `fmt_cmd`, `update_cmd`, `changelog_cmd`, `create_cmd`). The `Resource` Protocol declaration in `core/document.py:23` and the docstring reference at `core/document.py:87` are NOT call sites — Protocol method definitions remain bare.
- `Path.write_text()` — 3 sites in `create_cmd.py` x2 and `index_cmd.py`.
- `open(spec_path, "r")` — 2 sites in `create_cmd.py` and `update_cmd.py` (user-supplied spec files; Alfred-controlled format).
- `os.fdopen(fd, "w")` inside atomic-write helpers — 2 sites in `commands/_helpers.py::atomic_write` and `core/preferences.py::_atomic_write`.

## Why

GitHub issue #161 reports that `af read COR-1205`, `af guide`, `af create sop --dry-run`, and other commands raise `UnicodeDecodeError: 'gbk' codec can't decode byte 0x94` on Windows installations whose Python text encoding resolves to GBK (the default for `zh-CN` Windows locales). The root cause is that 22 production I/O calls in `src/fx_alfred/` rely on the platform default `locale.getpreferredencoding(False)` instead of pinning UTF-8.

Alfred's bundled rules, templates, and document index are UTF-8 by contract (COR-0002 §Encoding implicitly assumes UTF-8 throughout — every PKG document is UTF-8 on disk, and `af validate` does not check encoding). Reading those files under GBK/CP1252/Shift-JIS/etc. corrupts or crashes on any byte that is invalid in the host encoding. The user-facing crash on `af read COR-1205` makes Alfred unusable for Windows users in non-UTF-8 locales without the `PYTHONUTF8=1` workaround.

A complementary issue exists on write — Alfred-emitted `.md` files (CHG/PRP/SOP under `af create`, regenerated index under `af index`) currently inherit the platform encoding. On a non-UTF-8 host, an Alfred-created document containing non-ASCII characters in title/body would be unreadable by Alfred on a UTF-8 host (round-trip corruption). Forcing UTF-8 on both sides closes the loop.

## Out of Scope

- Changing Alfred's document format or contract (still UTF-8 on disk; only enforcement changes).
- Changing terminal/stdout encoding behavior (separate concern from file I/O).
- Recommending `PYTHONUTF8=1` to Alfred users (the fix removes the need).
- User-supplied spec files for `af create --spec FILE` / `af update --spec FILE` beyond pinning UTF-8 read; spec format itself is unchanged.
- Test-only fixture I/O in `tests/` (those run on UTF-8 hosts in CI; non-blocking and outside the bug's reported surface).
- Stdlib log files / `tempfile.mkstemp` raw bytes / git-output capture (not Alfred document I/O).

## Impact Analysis

- **Systems affected:** `src/fx_alfred/core/` (document, skills, compose, preferences) and `src/fx_alfred/commands/` (all read/write/spec-load helpers); the `Resource` Protocol in `core/document.py`.
- **Behavioral impact:** On UTF-8 hosts: no observable change (UTF-8 == UTF-8). On non-UTF-8 hosts (Windows GBK/CP1252, etc.): `af read`, `af guide`, `af create`, `af search`, `af validate`, `af fmt`, `af update`, `af index`, `af plan`, `af changelog`, `af star` (preferences) now succeed on UTF-8-encoded bundled documents and Alfred-owned writes round-trip correctly.
- **Compatibility:** `Path.read_text(encoding="utf-8")` and `Traversable.read_text(encoding="utf-8")` are both supported in Python ≥ 3.10 (project minimum per `pyproject.toml`). The Protocol signature widening (`encoding: str | None = None` default arg) is source-compatible with all current call sites that pass no encoding kwarg. The Protocol is `@runtime_checkable`, but `runtime_checkable` only checks attribute *presence* at `isinstance()` time — not signature shape — so widening the abstract signature is binary-compatible at runtime. The widening is, however, a **type-level breaking change** for any out-of-tree implementer that defined `read_text(self) -> str` against the narrow signature; none exist in the alfred repo today (verified by symbol search), but downstream Alfred-derivative projects that subclass or implement `Resource` should be aware.
- **Pre-existing non-UTF-8 files (Windows edge case):** After this change, an Alfred PRJ/USR document that a user manually saved as GBK / CP1252 / etc. (e.g. edited under Windows Notepad without UTF-8 mode) will raise `UnicodeDecodeError` from `af read` where v1.17.1 might have read it successfully if the user's host locale matched. The same applies to user-authored `--spec FILE` inputs to `af create` / `af update`. This is the *correct* behaviour (Alfred document format is UTF-8 by contract), but Windows users with pre-existing non-UTF-8 documents will need to re-save them as UTF-8. Documented here so the rollout note in the PR / release CHANGELOG calls it out; not a separate migration tool.
- **Risk surface:** Low. Mechanical change at each call site; semantically equivalent on UTF-8 hosts; strictly correct on non-UTF-8 hosts. The two material risks (Protocol type-level break; pre-existing non-UTF-8 documents) are addressed above.
- **Rollback plan:** Keep all 22 call-site edits + Protocol update + new regression test in a single implementation commit. Rollback = revert that commit (and the CHG/index commit if separated); `af validate`, `pytest`, `ruff` re-run will confirm the rollback.

## Acceptance Criteria

- A1: Every `Path.read_text()` / `Resource.read_text()` / `Traversable.read_text()` *call site* in `src/fx_alfred/` whose target is an Alfred-owned document, template, preferences file, or index passes `encoding="utf-8"` explicitly. Verified via: `grep -rnE '\.read_text\(\s*\)' src/fx_alfred/ --include='*.py' | grep -v -E '(def read_text|"""|read_text\(\))$' | wc -l` returns `0` (excludes the Protocol method definition at `core/document.py:23` and the docstring mention at `core/document.py:87`, which legitimately remain bare).
- A2: Every `Path.write_text(content)` call in `src/fx_alfred/` whose target is an Alfred-owned document or index passes `encoding="utf-8"`. Verified via: `grep -rn '\.write_text(' src/fx_alfred/ --include='*.py'` shows `encoding="utf-8"` at each match.
- A3: Atomic-write helpers (`commands/_helpers.py::atomic_write` and `core/preferences.py::_atomic_write`) open their temp fd with `encoding="utf-8"`. Verified via: `grep -rn 'os.fdopen' src/fx_alfred/ --include='*.py'` shows `encoding="utf-8"` at each match.
- A4: Spec-file read sites (`create_cmd.py:279`, `update_cmd.py:209`) open with `encoding="utf-8"`. Verified via: `grep -rn 'open(spec' src/fx_alfred/ --include='*.py'` shows `encoding="utf-8"` at each match.
- A5: `core.document.Resource` Protocol's `read_text` signature accepts an optional `encoding: str | None = None` parameter so call sites passing `encoding="utf-8"` type-check against both Path and Traversable implementations. The widening preserves `@runtime_checkable` isinstance behaviour (which is attribute-presence only).
- A6: A new regression test at `tests/test_utf8_io.py` MUST exercise the failure mode deterministically on UTF-8 hosts. Two complementary tests required:
  - **A6.1 (behavioural):** Monkeypatch `io.text_encoding` (NOT `locale.getpreferredencoding` — empirically verified during plan-review R1 that the latter is bypassed because `Path.read_text(encoding=None)` resolves the locale at the C level via `_PyOS_GetLocaleEncoding`, not via Python-level `locale.getpreferredencoding` / `locale.getencoding`). With `io.text_encoding` patched to return `"ascii"` when called with `None`, write a file containing bytes valid in UTF-8 but invalid in ASCII (e.g. `"中文测试".encode("utf-8")`), then call the patched-callsite (e.g. `af read`-equivalent helper) and assert it returns the decoded UTF-8 string without `UnicodeDecodeError`. Before the production fix, the same test MUST raise `UnicodeDecodeError` (RED state, verified by running the test against current `main` head before applying the call-site edits).
  - **A6.2 (mechanical / belt-and-suspenders):** A static-assertion test that runs the four greps from A1–A4 and asserts each returns `0` matches (no bare `read_text()`, no bare `write_text(content)`, no bare `os.fdopen(fd, "w")`, no bare `open(spec_path, "r")`). This catches future regressions where a new contributor adds an unpinned I/O site without exercising the runtime path.
- A7: `.venv/bin/pytest -v --tb=short` (all tests including the new A6 regressions), `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`, and `af validate --root /Users/frank/Projects/alfred` all pass.
- A8: `af` smoke commands listed in issue #161 (`af read COR-1205`, `af guide`, `af create sop --prefix ADM --acid 2000 --title "Machine Admin Operation Workflow" --dry-run`) succeed locally without `PYTHONUTF8=1`. On the Linux/macOS dev host this is already true; the A6.1 behavioural test exercises the equivalent failure path the Windows GBK locale would hit, providing CI-deterministic regression coverage.

## Implementation Plan

1. Widen `core.document.Resource` Protocol signature: `def read_text(self, encoding: str | None = None) -> str: ...`. Both `pathlib.Path.read_text` and `importlib.resources.abc.Traversable.read_text` already accept this kwarg, so no implementation change at the providers — only the Protocol declaration tightens what callers may pass. Note: `@runtime_checkable` `isinstance()` is attribute-presence only, so widening the abstract signature is binary-compatible at runtime; it is a type-level tightening, not a runtime constraint.
2. **RED phase (test-writer worker per COR-1500 RED):** Add `tests/test_utf8_io.py` per A6 (both A6.1 behavioural via `io.text_encoding` monkeypatch AND A6.2 mechanical grep assertion). Run the new tests against current `main` HEAD — they MUST fail (A6.1 raises `UnicodeDecodeError`; A6.2 grep returns ≥ 1 match for each of the four patterns). Record the RED state's failing output in the test-writer's commit message. This is the explicit RED gate; do NOT proceed to step 3 until RED is confirmed.
3. **GREEN phase (implementer worker per COR-1500 GREEN):** Pass `encoding="utf-8"` at every `.read_text()` call site in `src/fx_alfred/core/` and `src/fx_alfred/commands/` enumerated under §What. 15 sites total.
4. Pass `encoding="utf-8"` at every `.write_text(content)` call site in the same modules. 3 sites total.
5. Update `open(spec_path, "r")` → `open(spec_path, "r", encoding="utf-8")` in `commands/create_cmd.py:279` and `commands/update_cmd.py:209`.
6. Update `os.fdopen(fd, "w")` → `os.fdopen(fd, "w", encoding="utf-8")` in `commands/_helpers.py::atomic_write` and `core/preferences.py::_atomic_write`.
7. Re-run the A6 tests — both MUST now pass (GREEN gate). Run `.venv/bin/pytest -v --tb=short`, `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`, and `af validate --root /Users/frank/Projects/alfred`. All must pass before phase 7 push.
8. Update CHG `Last updated` + Change History row with each plan-review iteration outcome. Trinity panel via `Skill(trinity)` per the alfred loop-iteration default panel `[glm, deepseek, minimax]` (the alfred triad per memory `feedback_alfred_panel_default_fast_review.md`; PRJ binding pending issue #170); weights = COR-1609.
9. After PASS, dispatch implementation per COR-1619. Per the convention proposed in issue #171 (two-worker TDD split) and the user's 2026-05-17 directive, step 2 (RED test authoring) and steps 3–6 (GREEN implementation) SHOULD be split across two distinct worker instances — test-writer worker first, implementer worker second — so the implementer cannot author-bias the tests. Both commits verified locally by the orchestrator per COR-1619 §Verification.
10. Open PR `Closes #161` per COR-1505 / phase 7. PR body uses bare `Closes #161` token on its own line.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-17 | Initial draft for issue #161 — UTF-8 enforcement at all Alfred document I/O sites | Claude Opus 4.7 |
| 2026-05-17 | R2 fixes from plan-review panel `[glm, deepseek, minimax]` (R1 verdict: all FIX; convergent blockers): (a) §What ¶3 read_text count "16" → "15" (3/3 reviewers; total of 22 was already correct); (b) §Acceptance A6 + §Implementation Plan steps 2/7 rewrote test strategy to use `io.text_encoding` monkeypatch (per minimax B1 empirical proof that `locale.getpreferredencoding` patches are bypassed by the C-level `_PyOS_GetLocaleEncoding` lookup); (c) added A6.2 mechanical grep regression assertion (deepseek + minimax); (d) §Impact added Protocol-widening type-level note (deepseek E + glm) and pre-existing non-UTF-8 file edge case (glm + deepseek A); (e) §Implementation Plan added explicit RED gate as step 2 and folded the two-worker TDD split per issue #171 user directive; (f) tightened A1 grep regex (deepseek D); (g) §Implementation Plan step 8 updated panel default to the alfred triad per memory + issue #170. | Claude Opus 4.7 |
| 2026-05-17 | R2 panel verdicts: glm 9.40 PASS, deepseek 9.35 PASS (both COR-1609); minimax 8.93 with malformed-rubric (used CLD-1800 evolution dimensions instead of COR-1609 CHG dimensions). | Claude Opus 4.7 |
| 2026-05-17 | R3 dispatch (minimax-only, CHG unchanged from R2): minimax 9.4 PASS under corrected COR-1609 rubric. **Panel gate met** — all 3 reviewers ≥ 9.0 with blocking empty. Status → Approved; proceed to Phase 5 dispatch with two-worker split (test-writer → implementer). | Claude Opus 4.7 |
