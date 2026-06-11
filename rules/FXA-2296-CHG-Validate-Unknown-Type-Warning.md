# CHG-2296: Validate Unknown Type Warning

**Applies to:** FXA project
**Last updated:** 2026-06-12
**Last reviewed:** 2026-06-11
**Status:** Completed
**Date:** 2026-06-11
**Requested by:** Frank Xu (session review finding 2026-06-10; follow-up batch 2026-06-11)
**Priority:** Medium
**Change Type:** Normal
**Targets:** src/fx_alfred/commands/validate_cmd.py; tests/test_validate_cmd.py

---

## What

`af validate` emits a per-document **warning** when a document's filename TYPE code is not in the `DocType` enum, instead of silently skipping type-specific validation. One warning per document: `Unknown document type '<TYP>' — type-specific validation skipped (known types: SOP, PRP, CHG, ADR, REF, PLN, INC)`.

- Text mode: warning lines printed per doc (prefix `~`), summary line gains `, N warning(s)` **only when N > 0** (existing `"0 issues found"` substring assertions unaffected).
- JSON mode: each result object gains an additive `"warnings": [...]` key (always present, empty when none); `"valid"` remains governed by errors only; `schema_version` stays `"1"` (additive field).
- Exit code unchanged: warnings never cause exit 1 (CI-safe — the current corpus contains one CTX document).

The two `except ValueError` fallbacks at the `DocType(doc.type_code)` lookup sites collapse into a single membership check per document, which is also the warning trigger.


## Why

`validate_cmd.py:195,211` silently tolerates unknown TYPE codes: `DocType('XYZ')` raises `ValueError`, the handler falls back to base-field checks and **skips Status-value validation entirely**. A typo'd type (`SPO` for `SOP`) therefore bypasses the type contract with zero feedback — found in the 2026-06-10 project review. Live evidence: `FXA-2271-CTX-Alfred-Glossary.md` (CTX is not in the DocType enum, not in COR-0002, not in the CLI epilog type list) validates with no signal at all.

Warning (not error) because: (a) the corpus legitimately contains one CTX doc today — an error would break `af validate` exit 0 and every CI/smoke flow; (b) legitimizing CTX as a real type requires a COR-0002 (PKG, read-only) upstream change — out of scope here. The warning creates visibility and pressure to resolve CTX properly without breaking anything.


## Out of Scope

- Adding CTX (or any new type) to `DocType` — requires upstream COR-0002 contract change with REQUIRED_METADATA/SECTIONS/STATUSES decisions.
- Making unknown types an error / exit-code change.
- `af create` / `af fmt` behavior for unknown types (create already restricts type choices; fmt is format-only).
- Warning suppression/allowlist mechanisms (no evidence of need; one known case).


## Acceptance Criteria

- A1: A structurally-valid document with TYPE `XYZ` produces exit 0, a warning naming `XYZ` and listing known types, and no new issues.
- A2: The warning fires once per document even though two lookup sites previously degraded independently; Status validation remains skipped for unknown types (no false Status issues).
- A3: JSON mode: the doc's result has `"warnings": ["Unknown document type 'XYZ' ..."]` and `"valid": true`; known-type docs have `"warnings": []`.
- A4: Zero-warning corpora produce byte-identical text output to today (summary clause appears only when warnings exist).
- A5: Real corpus: `af validate --root .` reports exactly 1 warning (FXA-2271 CTX), 0 issues, exit 0.
- A6: Full gates: pytest, ruff check, ruff format --check, pyright, `af validate`.


## Implementation Plan

1. **RED:** tests in `tests/test_validate_cmd.py`: unknown-type warning text + exit 0 (A1), single-warning + status-skip semantics (A2), JSON `warnings` key both populated and empty (A3), no-warnings summary unchanged (A4). Confirm RED.
2. **GREEN:** single `DocType` membership check per doc in `validate_cmd.py`; `warnings_by_doc` channel; text + JSON output wiring; epilog Checks list gains the warning line.
3. Verify A1–A6.
4. Trinity triad review (glm, deepseek, minimax), COR-1610, all ≥ 9.0; fix convergent findings.
5. PR per COR-1505.

---

## Change History

| Date       | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | By               |
|------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------|
| 2026-06-11 | Initial version — surface unknown TYPE codes as validate warnings (2026-06-10 review finding; CTX evidence) | Claude (Fable 5) |
| 2026-06-11 | RED (3 failing + 1 baseline lock) + GREEN (single membership check; warnings channel; text `~` lines; JSON additive `warnings` key; exit code untouched). Real corpus: 286 docs, 0 issues, 1 warning (FXA-2271 CTX), exit 0. | Claude (Fable 5) |
| 2026-06-11 | R1 code-review panel [glm, deepseek, minimax] per COR-1602/COR-1610: glm 9.1 PASS, deepseek 9.3 PASS, minimax 9.7 PASS — gate met, blocking empty. Convergent advisories applied: (3/3) text-mode doc_id double heading for docs with both issues+warnings → merged to one heading per doc in scan order; (2/3 glm+deepseek) combined issues+warnings path untested → added test (text single-heading + exit 1 + both counts in summary + JSON valid:false with both arrays). MiniMax style advisory (summary string surgery) → f-string conditional suffix. MiniMax pre-existing note ("1 issues found" always-plural grammar, asserted by existing tests) recorded, not changed. Status → Approved | Claude (Fable 5) |
| 2026-06-12 | Released in v1.19.0 (PyPI, 2026-06-12) — status Approved → Completed per FXA-2102 Step 7 | Claude (Fable 5) |
