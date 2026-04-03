# PRP-2170: Evolve CLI Batch C3 C5

**Applies to:** FXA project
**Last updated:** 2026-04-01
**Last reviewed:** 2026-04-01
**Status:** Draft

---

## What Is It?

Batch proposal for two code quality improvements from Evolve-Run FXA-2167. (C4 dropped after Codex R1 review — guards are defensive for malformed documents, not dead code.)

---

## Problem

**C3 — parser.py redundant branch (lines 219-228):**
```python
if len(cells) >= 3:
    rows.append(HistoryRow(date=cells[0], change=cells[1], by=cells[2]))
else:
    rows.append(HistoryRow(
        date=cells[0] if cells else "",
        change=cells[1] if len(cells) > 1 else "",
        by=cells[2] if len(cells) > 2 else "",  # unreachable: len < 3 guaranteed
    ))
```
The else branch's `cells[2] if len(cells) > 2` is unreachable (we're in else because len < 3). The two branches can be unified.

**~~C4 — DROPPED:~~** `fmt_cmd.py` guards are defensive handling for malformed documents where `num_cols` may not be 3. Codex R1 correctly identified that `num_cols` is derived at runtime from the actual header, not hardcoded. These guards are intentional tolerance, not dead code.

**C5 — status_cmd.py untested path (lines 22-30):**
The empty-docs JSON output path (`{"total": 0, ...}`) has no test coverage (status_cmd is at 89%).

## Proposed Solution

**C3:** Replace both branches with a single unconditional HistoryRow construction using safe defaults:
```python
rows.append(HistoryRow(
    date=cells[0] if cells else "",
    change=cells[1] if len(cells) > 1 else "",
    by=cells[2] if len(cells) > 2 else "",
))
```

**C5:** Add two tests for the empty-docs branch: one with `--json` flag, one without. The empty-docs path is defensive code — PKG docs are always loaded by `scanner.py` regardless of `--root`, so `scan_or_fail` never returns `[]` in normal operation. Tests must mock `scan_or_fail` to return `[]` using `unittest.mock.patch` (following the pattern established in `tests/test_helpers.py:23`). Justification: the branch guards against future scanner changes that might return empty lists; testing it via mock ensures the defensive code works correctly if that assumption ever changes.

## Scope

**In scope:**
- `core/parser.py` (C3 — simplify branch)
- `tests/test_fmt_cmd.py` (C3 — edge-case test: create a document with <3 column Change History row, verify `parse_metadata` produces correct HistoryRow with safe defaults)
- `tests/test_status_cmd.py` (C5 — two new tests using `unittest.mock.patch` on `scan_or_fail`)

**Out of scope:** `commands/fmt_cmd.py` (C4 dropped). No CLI interface changes.

## Risks

- **C3:** Behavior-preserving simplification. The unified branch produces identical HistoryRow objects for all inputs. Edge-case test verifies <3 cells handling via `parse_metadata` in `test_fmt_cmd.py`.
- **C5:** Test-only, mock-dependent. Requires `unittest.mock.patch` on `scan_or_fail` (same pattern as `test_helpers.py:23` which patches `scan_documents`). The mock is necessary because PKG layer always provides docs. Risk: mock-dependent test may drift from real scanner behavior, but this is acceptable for defensive branch coverage.

## Open Questions

None — all resolved.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-01 | Initial version | — |
| 2026-04-01 | R2: dropped C4 per Codex R1 (8.4) — guards are defensive, not dead code; fixed scope to list test files | Claude |
| 2026-04-01 | R3: fixed H1, pinned C3 test to test_document.py, specified C5 mock strategy, tempered risk claims | Claude |
| 2026-04-01 | R4: fixed C5 reachability claim (PKG always loads), pinned C3 test to test_fmt_cmd.py, corrected mocking precedent to test_helpers.py:23, justified C5 defensive testing | Claude |
