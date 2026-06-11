# CHG-2301: JSON Output And Exit Code Unification

**Applies to:** FXA project
**Last updated:** 2026-06-11
**Last reviewed:** 2026-06-11
**Status:** Approved
**Date:** 2026-06-11
**Requested by:** Frank Xu (session review finding 2026-06-10; follow-up batch 2026-06-11)
**Priority:** Medium
**Change Type:** Normal
**Targets:** src/fx_alfred/commands/_helpers.py; src/fx_alfred/commands/* (14 json.dumps sites, 2 sys.exit sites, schema_version literals); tests/test_architecture.py; affected test assertions

---

## What

Unify the commands layer's three coexisting JSON emission styles and two exit idioms behind shared helpers, enforced by architecture guards:

1. **`_helpers.emit_json(data)`** — `click.echo(json.dumps(data, indent=2, ensure_ascii=False))`. All 14 `json.dumps` call sites across 13 command modules migrate. Three style families today: bare `json.dumps(output)` (list/read/status — `ensure_ascii=True`, so CJK titles render as `\uXXXX` escapes), `ensure_ascii=False` without indent (agent/where), and the full majority style (search/guide/plan/validate/skill/star; issue lacks `ensure_ascii=False`).
2. **`_helpers.SCHEMA_VERSION = "1"`** — the commands-layer envelope version. The 4 hardcoded `"schema_version": "1"` literals (search/guide/where/validate) and star_cmd's private duplicate constant migrate to it. `core/skills.SCHEMA_VERSION` (skills envelope) and `core/agent_helpers.SCHEMA_VERSION` (agent envelope) are separate schema families and keep their own constants; plan_cmd's computed `schema_ver` ("3"/"2"/"1" by payload shape) is real semantic versioning and stays.
3. **`ctx.exit` everywhere** — the 2 remaining `sys.exit` sites (validate_cmd, issue_cmd lint — the latter gains `@click.pass_context`) migrate; `import sys` removed where orphaned.
4. **Three architecture guards** (tests/test_architecture.py): in `commands/`, (a) no `json.dumps(` outside `_helpers.py`; (b) no `sys.exit(`; (c) no `"schema_version": "1"` string literal (named constants only).


## Why

2026-06-10 review, commands-layer findings #1/#2/#7: a tool whose primary consumers are agents parsing `--json` output had three formatting dialects — and the bare-dumps family actively degrades CJK content (`ensure_ascii=True` escapes the user's Chinese document titles). The literals and exit idioms are the same class of drift. Guards make the convention self-enforcing, matching the repo's established pattern (Click-free core, fence single-implementation, docs drift).


## Behavior Delta (deliberate, documented)

- list/read/status: output gains `indent=2` and raw UTF-8 (CJK unescaped) — JSON semantics identical; any `json.loads` consumer unaffected.
- agent/where: gain `indent=2`. issue: gains `ensure_ascii=False`.
- search/guide/plan/validate/skill/star: byte-identical.
- Exit codes: numerically identical (sys.exit→ctx.exit both raise SystemExit with the same codes).
- Tests asserting exact compact JSON strings migrate to parsed-JSON assertions (assertion migration, not behavior masking).


## Out of Scope

- Adding `schema_version` to envelopes that lack one (list/read/status) — schema additions are separate CHGs.
- plan_cmd's computed schema versioning (correct as-is).
- core-layer envelope constants (skills/agent_helpers — separate schema families).
- Machine-readable error envelopes for non-JSON failures.


## Acceptance Criteria

- A1: The three guards are RED on pre-change code and GREEN after; `grep -rn "json.dumps" src/fx_alfred/commands/ | grep -v _helpers.py` returns 0.
- A2: All `--json` outputs parse identically to before via `json.loads` (semantic equivalence); CJK content renders unescaped.
- A3: Exit codes byte-identical across all commands (existing CLI tests pass; only exact-format assertions migrate).
- A4: Full gates: pytest, ruff check, ruff format --check, pyright, `af validate`.


## Implementation Plan

1. **RED:** three guards in tests/test_architecture.py.
2. **GREEN:** `_helpers.emit_json` + `SCHEMA_VERSION`; sweep 13 modules; `@click.pass_context` on issue lint; migrate exact-format test assertions to parsed-JSON.
3. Verify A1–A4; spot-check CJK rendering live.
4. Trinity triad review (glm, deepseek, minimax), COR-1610, all ≥ 9.0; fix convergent findings.
5. PR per COR-1505.

---

## Change History

| Date       | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | By               |
|------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------|
| 2026-06-11 | Initial version — unify JSON emission, schema_version constants, exit idioms behind guarded helpers                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | Claude (Fable 5) |
| 2026-06-11 | RED (3 guards) + GREEN (14-site sweep, 13 modules; zero existing tests modified — json.loads equivalence proof; CJK live-verified raw).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | Claude (Fable 5) |
| 2026-06-11 | R1 code-review panel [glm, deepseek, minimax] per COR-1602/COR-1610: glm 9.2 PASS, deepseek 10.0 PASS (zero findings), minimax 9.8 PASS — gate met, blocking empty. All three endorsed the schema-constant boundary ("one schema family, one constant"; forced unification = false coupling) and verified pass_context has zero Click behavior change. GLM 1/3 advisories adopted on merit: agent_cmd dead _emit_json passthrough removed (4 sites direct-call); emit_json formatting unit test added (pins indent=2 + raw-CJK so an ensure_ascii regression cannot ship — the guard covers routing, this covers the helper). MiniMax guard-evasion notes (aliased import / from-import exit / quote-style) recorded as theoretical, self-marked out of scope, consistent with deepseek's "academic" and glm's "not worth generalizing" assessments. Status → Approved | Claude (Fable 5) |
