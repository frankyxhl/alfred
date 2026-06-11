# CHG-2295: Compose Domain Exceptions

**Applies to:** FXA project
**Last updated:** 2026-06-12
**Last reviewed:** 2026-06-11
**Status:** Completed
**Date:** 2026-06-11
**Requested by:** Frank Xu (session review finding 2026-06-10; follow-up batch 2026-06-11)
**Priority:** High
**Change Type:** Normal
**Targets:** src/fx_alfred/core/compose.py; src/fx_alfred/commands/plan_cmd.py; tests/test_compose.py; tests/test_architecture.py

---

## What

Remove the Click dependency from `core/compose.py` — the only `core/` module importing Click, in violation of the documented "core/ is framework-agnostic" contract (CLAUDE.md §Key Design Patterns). Introduce a domain exception `CompositionError(message, exit_code=1)` raised by `compose_order` (workflow cycle) and `resolve_sops_from_task` (SOP not found / ambiguous / zero-match, the last with `exit_code=2`). The single production call site (`plan_cmd.py:588`) converts `CompositionError` → `click.ClickException` at the CLI boundary, preserving messages and exit codes byte-for-byte.

Add an architecture guard test (`tests/test_architecture.py`) asserting no `core/*.py` module imports Click — making the contract enforced, not aspirational.

Also correct the module docstring: it claims "Pure stdlib. No filesystem access." while the module imports Click and reads documents via `resolve_resource().read_text()` (compose.py:358).


## Why

The repo's architecture contract says Click lives only in `commands/`; every other core module honors it (scanner raises `LayerValidationError`/`DocumentNotFoundError`/`AmbiguousDocumentError`, converted by `_helpers.scan_or_fail`/`find_or_fail`). `compose.py` breaks the pattern in 4 places (lines 16, 255, 325, 327, 340) and even documents `click.ClickException` as part of its API (docstring line 290). This blocks reuse of composition logic outside Click contexts and was flagged 🔴 high in the 2026-06-10 project review (trinity-reviewed evaluation).


## Out of Scope

- Behavior changes of any kind: CLI messages, exit codes (1 default; 2 for zero-match), and ordering semantics stay identical.
- The O(n²·log n) queue re-sort in Kahn's loop (compose.py:248) — separate low-priority item.
- A `compose_or_fail` helper in `_helpers.py`: there is exactly one call site; inline conversion is simpler and the helper can be extracted when a second caller appears.
- Other review-backlog items (validate unknown-type warning, CLAUDE.md refresh, CI matrix).


## Impact Analysis

- **Systems affected:** `core/compose.py` (exception type + docstring), `commands/plan_cmd.py` (one try/except at the boundary), `tests/test_compose.py` (4 assertion sites migrate from `click.ClickException` to `CompositionError`), new `tests/test_architecture.py`.
- **Behavioral impact:** None observable at the CLI. `af plan --task` error output and exit codes unchanged.
- **API impact:** `CompositionError` becomes the documented contract for library consumers of `core.compose`; `click.ClickException` no longer escapes core. Type-level only; no in-repo consumer other than plan_cmd.
- **Risk surface:** Low. Mechanical exception swap at 4 raise sites + 1 boundary; CLI tests must pass unchanged as the no-regression proof.
- **Rollback plan:** Single PR; revert the merge commit.


## Acceptance Criteria

- A1: `grep -rn "import click\|from click" src/fx_alfred/core/` returns 0 matches; enforced forever by `tests/test_architecture.py` (regex `^\s*(?:import|from)\s+click\b` over `core/*.py`).
- A2: `compose_order` raises `CompositionError` on a true cycle with the byte-identical message `Workflow cycle detected among: <nodes>`.
- A3: `resolve_sops_from_task` raises `CompositionError` for unknown positional ID (`SOP '<id>' not found`), ambiguous ID (scanner message), and zero-match (`--task "..." matched 0 tagged SOPs. ...`) with `exit_code == 2` on the zero-match case only.
- A4: `plan_cmd` converts `CompositionError` → `click.ClickException` preserving message and `exit_code`; all existing CLI-level tests (exit codes, stderr text) pass without modification.
- A5: Full gates: pytest, ruff check, ruff format --check, pyright, `af validate`.


## Implementation Plan

1. **RED:** New `tests/test_architecture.py` guard (fails: compose.py imports click). New `TestCompositionErrorContract` cases in `tests/test_compose.py` asserting `CompositionError` for cycle / not-found / zero-match-exit-2 (fail: ClickException raised today). Confirm RED.
2. **GREEN:** Add `CompositionError` to compose.py; swap the 4 raise sites; drop `import click`; fix module docstring + `resolve_sops_from_task` Raises section. Boundary try/except at plan_cmd.py:588. Migrate the 4 existing `click.ClickException` assertions in test_compose.py to `CompositionError`.
3. Verify A1–A5.
4. Trinity triad review (glm, deepseek, minimax), COR-1610 weights, all ≥ 9.0; fix convergent findings.
5. PR per COR-1505.

---

## Change History

| Date       | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | By               |
|------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------|
| 2026-06-11 | Initial version — de-Click core/compose.py per 2026-06-10 review finding (🔴 high) | Claude (Fable 5) |
| 2026-06-11 | RED (5 failing: architecture guard + 4 CompositionError contract) + GREEN (CompositionError; 4 raise sites; plan_cmd boundary; docstring lie fixed; 8 test assertions migrated). Exit codes verified by direct execution: zero-match=2, not-found=1, messages byte-identical. | Claude (Fable 5) |
| 2026-06-11 | R1 code-review panel [glm, deepseek, minimax] per COR-1602/COR-1610: glm 9.8 PASS, deepseek 9.8 PASS (extracted from session JSONL after worker returned early), minimax 9.8 PASS — gate met, blocking empty. Convergent advisory (glm+minimax): guard glob→rglob so future core/ subpackages cannot evade — applied. DeepSeek advisory: boundary conversion exit-1 path lacked CLI-level test (exit-2 was covered at test_plan_cmd.py:1505,1732) — added test_task_unknown_positional_exits_1_through_boundary. MiniMax single-voice advisory (exit_code type validation in CompositionError.__init__) recorded, not applied — current callers pass literals 1/2 only. Status → Approved | Claude (Fable 5) |
| 2026-06-12 | Released in v1.19.0 (PyPI, 2026-06-12) — status Approved → Completed per FXA-2102 Step 7 | Claude (Fable 5) |
