# PRP-2156: Extract Duplicated Helpers And Add Gate Detection Tests

**Applies to:** FXA project
**Last updated:** 2026-03-30
**Last reviewed:** 2026-03-30
**Status:** Draft

---

## What Is It?

Two changes to improve fx_alfred code quality, discovered by Evolve-CLI run FXA-2155.

---

## Problem

**A) Duplicated functions.** `_render_section_content()` and `_validate_spec_status()` are copied identically in both `create_cmd.py` and `update_cmd.py`. If validation rules or rendering logic change, both copies must be updated — a maintenance risk.

**B) Untested gate-detection semantics.** `_parse_steps_for_json()` in `plan_cmd.py` (lines 54-69) detects `[GATE]` and `✓` markers to set a boolean `gate` field in JSON output. Existing tests (`test_json_output.py:215-222`) verify the `gate` field *exists* in the step schema but do NOT test the detection logic itself — no test asserts `gate: true` for a `[GATE]`-tagged step or `gate: false` for a plain step. Plan_cmd.py overall coverage: 85%.

## Scope

**In scope:**
- Extract `_render_section_content()` and `_validate_spec_status()` to `_helpers.py` (change A)
- Add unit tests for `_parse_steps_for_json()` gate detection semantics (change B)

**Out of scope:**
- Other duplicated patterns (e.g., prefix/ACID regex validation in spec mode)
- Coverage gaps in other commands (status_cmd, validate_cmd, etc.)
- Refactoring `_helpers.py` beyond adding the two extracted functions
- Changes to `_parse_steps_for_json()` behavior itself

**Bundling rationale:** Both changes are mechanical, touch disjoint files (A: _helpers/create_cmd/update_cmd; B: test_plan_cmd), and share a single evolve-run context (FXA-2155). Combined they form one reviewable unit small enough for a single PR.

## Proposed Solution

**A)** Move `_render_section_content()` and `_validate_spec_status()` from both `create_cmd.py` and `update_cmd.py` into `commands/_helpers.py`. Update imports in both files. No API or behavior change.

Files modified:
- `src/fx_alfred/commands/_helpers.py` — add 2 functions + imports (`Any` from typing, `DocType`/`ALLOWED_STATUSES` from schema)
- `src/fx_alfred/commands/create_cmd.py` — remove 2 functions, import from `_helpers`
- `src/fx_alfred/commands/update_cmd.py` — remove 2 functions, import from `_helpers`

**B)** Add direct unit tests for `_parse_steps_for_json()` in `tests/test_plan_cmd.py` (where all other plan tests live). These test the function directly, not via CLI, because the gate-detection logic is internal parsing — the CLI-level `plan --json` schema tests already live in `test_json_output.py` and remain untouched.

Exact test cases:
1. Numbered step without markers → `gate: false`
2. Step ending with literal `✓` → `gate: true`
3. Step containing `[GATE]` → `gate: true`
4. Step with `### 1.` heading prefix (regex: `^(?:###\s+)?\d+\.\s+`) → parsed correctly
5. Mixed content: numbered steps + non-numbered lines → only numbered steps extracted
6. Empty input → returns `[]`

Files modified:
- `tests/test_plan_cmd.py` — add test function(s)

## Risks and Trade-offs

1. **Helper centralization scope creep.** `_helpers.py` currently contains only scan/find wrappers. Adding validation/render helpers broadens its role. Mitigated by: both new functions are Click-coupled (raise `ClickException`), consistent with _helpers.py's existing purpose as the Click-wrapping layer. No core/ changes.
2. **Regression from extraction.** Moving functions could break imports or miss a caller. Mitigated by: full `pytest` suite (374 tests) covers all code paths through both `create_cmd` and `update_cmd` spec modes. Hard gate: 100% pytest pass required.
3. **Marker contract ambiguity.** The `✓` marker is the literal Unicode character U+2713 (CHECK MARK). `[GATE]` is the literal string `[GATE]`. These are the exact strings matched in `plan_cmd.py:67`. Tests will use these exact literals.
4. **Overlapping test placement.** `test_json_output.py` tests schema presence; new tests in `test_plan_cmd.py` test detection logic. No overlap — different concerns.

## Open Questions

None. Both changes are mechanical and self-contained.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-30 | Initial version | — |
| 2026-03-30 | R2: Address Codex feedback — add Scope section, Risks section, tighten Problem B, specify exact test cases and placement | Evolve-CLI |
