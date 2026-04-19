# PRP-2210: Close three edge-arm coverage gaps with tests

**Applies to:** FXA project
**Last updated:** 2026-04-19
**Last reviewed:** 2026-04-19
**Status:** Draft

---

## What Is It?

A proposal to add three narrow tests that close documented coverage gaps in `af list`, the `atomic_write`
helper, and `af validate`. No source code changes. Part of an automated evolve-CLI run (FXA-2209) executed
per SOP FXA-2149.

---

## Problem

The fx-alfred codebase is healthy by every aggregate signal (660/660 tests pass, 0 ruff issues,
96% coverage, 224/224 docs valid per `af validate`). The evolve-CLI run still identified three specific
coverage gaps that are worth closing because each locks a behaviour that is either a **public contract**
or a **failure-path invariant** — the kind of thing that should have a named test, not merely be
"observed to work" by other tests touching it incidentally.

### Gap 1 — `af list --json` empty-result output (list_cmd.py:66)

`commands/list_cmd.py` emits `[]` when filters match no documents:

```python
if not docs:
    if json_output:
        click.echo("[]")
    else:
        click.echo("No documents found.")
    return
```

JSON consumers (CI pipelines, pre-commit hooks, `af plan` tooling itself) depend on `--json` mode always
emitting valid JSON. The empty-array shape is a public contract with no test pinning it.

### Gap 2 — `atomic_write` double-failure arm (helpers.py:86–87)

`commands/_helpers.atomic_write` writes via temp file + `os.replace`. On failure it attempts to clean up,
and it must **not mask the original exception** when cleanup itself fails:

```python
except Exception:
    try:
        os.unlink(tmp_path_str)
    except OSError:
        pass       # line 87 — swallow unlink failure
    raise          # re-raise the ORIGINAL exception from the outer try
```

An existing test (`test_atomic_write_cleanup_on_failure` at `tests/test_helpers.py:144`) covers the
**outer** cleanup path: patches `os.replace` to raise, verifies the temp file is unlinked and the
`OSError` propagates. That test leaves lines 86–87 uncovered (confirmed by
`pytest --cov=fx_alfred.commands._helpers`, which reports `Missing: …, 86-87, …`).

Lines 86–87 only fire when `os.unlink` *also* raises — the double-failure case (e.g., the temp file was
removed out-of-band between `mkstemp` and cleanup). The contract being tested is:
**when both `os.replace` and `os.unlink` fail, the original exception from `os.replace` propagates, not
the unlink exception.** Breaking this would silently change which error an operator sees, masking the
real cause of an atomic-write failure.

### Gap 3 — `af validate` malformed Change-History header (validate_cmd.py:60, 70)

`_validate_history_header` has two early-return arms for malformed input:

```python
if len(lines) < 2:
    return ["Change History table header is missing or incomplete"]
# ...
if not header_line:
    return ["Change History table header is missing"]
```

These produce user-facing diagnostics on malformed documents. Neither arm has a test; a regression that
broke the detection (e.g., returning an empty list instead of the diagnostic) would silently accept
malformed documents into the corpus.

## Proposed Solution

Add one new test file **or** extend existing test files (whichever is idiomatic in the repo) covering:

1. **test_list_cmd_json_empty** — invoke `af list --json --type=XXX` with a filter that matches nothing,
   assert stdout is exactly `[]\n` and JSON-parses to `[]`.
2. **test_atomic_write_double_failure_preserves_original_error** — patch **both** `os.replace` (to raise
   `OSError("replace failed")`) **and** `os.unlink` (to raise `OSError("unlink failed")`). Call
   `atomic_write(path, content)` and assert `pytest.raises(OSError, match="replace failed")` — the
   original replace error must be the one that propagates, proving the inner `except OSError: pass` arm
   at line 86–87 swallowed the unlink error without masking the real cause. (Patching `os.replace`
   alone is already covered by the existing `test_atomic_write_cleanup_on_failure`; patching both is
   what actually exercises lines 86–87.)
3. **test_validate_history_header_missing_table** — call `_validate_history_header("")` (no lines) and
   assert the result equals `["Change History table header is missing or incomplete"]` (line-60 arm).
   Then call `_validate_history_header("Trailing text only\nMore text\n")` (>= 2 lines but no line
   starting with `|`) and assert the result equals `["Change History table header is missing"]`
   (line-70 arm).

### Test scope

- No new production code; no new files in `src/fx_alfred/`.
- All three tests live in `tests/` directory, following existing test file naming.
- Each test is < 20 lines.
- No new dependencies; uses `pytest` + `unittest.mock.patch` (already used elsewhere).

### Non-goals

- Not refactoring `create_cmd.py` duplication (C3 candidate, discarded at score 5.65).
- Not hardening `_next_acid_in_area` against int input (C4 candidate, deferred).
- Not changing CLI surface, JSON shape, or any diagnostic string.

### Risks

- **Gap 2 — platform-dependent cleanup.** Patching `os.replace` (rather than `os.fdopen` or
  `tempfile.mkstemp`) is deliberate: by the time `os.replace` raises, the `with` block at
  `_helpers.py:79` has already closed the file descriptor, so the temp file state is well-defined
  on POSIX and Windows alike. Patching `os.unlink` in addition is the *only* way to exercise
  lines 86–87 — the inner arm never fires unless unlink itself errors. Patching earlier points in
  the outer `try` block (e.g., `tempfile.mkstemp`) would hit a different code path entirely.
- **Gap 3 — diagnostic-string coupling.** These tests pin exact user-facing strings, which means
  any future rewording of the diagnostic must touch the test. Accepted tradeoff: the entire point
  of the test is to catch a silent regression that replaces the diagnostic with an empty list,
  and the coupling itself is what makes that detection robust.
- **Coverage vs. behaviour.** All three tests add coverage for code paths that are already
  behaviourally correct. The risk is theatre — tests that exist only to move a percentage.
  Mitigation: each test asserts a specific observable outcome (JSON shape, filesystem invariant,
  exact diagnostic string), not merely "runs without error".

## Open Questions

None. All three tests target documented, currently-implemented behaviour. No design decisions required.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-19 | Initial version | — |
| 2026-04-19 | Fill problem + proposed solution from FXA-2209 run (C1/C2/C5 bundle) | Frank + Claude |
| 2026-04-19 | R1 → R2 fixes (Codex 9.1 PASS / Gemini 7.7 FIX): correct Gap 3 line-60 diagnostic quotation; commit Gap 2 patch target to `os.replace`; add Risks section | Frank + Claude |
| 2026-04-19 | R2 → R3 fix: Gap 2 re-scoped to double-failure case (lines 86–87 require patching os.unlink too, not just os.replace — existing test already covers single-failure path) | Frank + Claude |
