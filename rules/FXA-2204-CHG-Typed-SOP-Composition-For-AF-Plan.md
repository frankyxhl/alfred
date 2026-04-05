# CHG-2204: Typed SOP Composition For AF Plan

**Applies to:** FXA project
**Last updated:** 2026-04-05
**Last reviewed:** 2026-04-05
**Status:** Proposed
**Date:** 2026-04-05
**Requested by:** Frank
**Priority:** High
**Change Type:** Normal
**Related:** FXA-2135, FXA-2140, FXA-2125, COR-1103

---

## What

Add typed workflow composition to `af plan` so a SOP can declare its workflow signature and `af plan` can verify whether adjacent SOPs compose.

New optional SOP metadata fields:

**Workflow input:** `<single state token>`
**Workflow output:** `<single state token>`
**Workflow requires:** `<comma-separated capability tokens>`
**Workflow provides:** `<comma-separated capability tokens>`

Example:

**Workflow input:** `proposal:none`
**Workflow output:** `proposal:draft`
**Workflow requires:** `repo:clean`
**Workflow provides:** `proposal:draft, proposal:editable`

v1 behavior:

1. `af plan` parses workflow metadata from each SOP in the requested chain.
2. If two adjacent SOPs both declare `Workflow output` / `Workflow input`, they must match exactly.
3. If either side is untyped, the edge is allowed and treated as untyped.
4. `Workflow requires` and `Workflow provides` are parsed, validated, and surfaced in JSON output, but do not block execution in v1.
5. On mismatch, `af plan` fails fast with a clear error and prints no partial workflow.
6. Text output may optionally show `State: <input> -> <output>` for typed phases.
7. `--json` output adds additive workflow fields per phase plus edge compatibility results.

Non-goals (v1):

- automatic SOP discovery or synthesis
- branching or parallel graph planning
- theorem-prover-style inference
- hard-gate checking of `Workflow requires` / `Workflow provides`
- mass migration of all existing SOPs

## Why

Current `af plan` can turn an ordered SOP list into a checklist, but it treats the chain as syntax, not semantics. A typed workflow signature lets Alfred model a SOP as a transformation from one task state to another.

This gives Alfred a practical version of the category-theory idea:

- object = workflow state
- morphism = SOP
- composition is valid only when previous output matches next input

The payoff is operational, not academic:

- catch wrong SOP ordering earlier
- make workflow chains self-describing
- expose machine-readable state transitions in JSON
- create a clean foundation for future semantic linting and routing

## Impact Analysis

- **Systems affected:** `src/fx_alfred/core/schema.py`, `src/fx_alfred/core/normalize.py`, new `src/fx_alfred/core/workflow.py`, `src/fx_alfred/commands/validate_cmd.py`, `src/fx_alfred/commands/plan_cmd.py`, README, bundled format-contract/reference docs, selected SOPs used as typed examples
- **User-facing behavior:** additive, backward-compatible for untyped SOPs; typed mismatch becomes a hard error in `af plan`
- **Data migration:** none required; existing SOPs remain valid without workflow metadata
- **Risk:** Medium — touches JSON output and validation logic, but scope is limited to optional SOP metadata and plan-time checks
- **Rollback plan:** revert the workflow metadata parser/validator and restore `af plan` to sequence-only behavior; typed metadata can remain inert text in documents

## Workflow Signature Contract

### Metadata keys

SOP-only, optional:

- `Workflow input`
- `Workflow output`
- `Workflow requires`
- `Workflow provides`

### Token format

Single tokens (`Workflow input` / `Workflow output`) and list tokens (`Workflow requires` / `Workflow provides`) must match:

`^[a-z0-9][a-z0-9:_/-]*$`

Examples:

- `proposal:draft`
- `proposal:reviewed`
- `review:passed`
- `tests:green`
- `repo:clean`

### Validation rules

1. If any of `Workflow input` or `Workflow output` is present, both must be present.
2. `Workflow input` and `Workflow output` each contain exactly one token.
3. `Workflow requires` and `Workflow provides` are comma-separated token lists.
4. Empty tokens are invalid.
5. Duplicate tokens are invalid.
6. Validation is case-sensitive in storage, but canonical examples and docs must use lowercase.
7. Routing SOPs and other SOPs without workflow metadata remain valid and untyped.

## Design Decisions

### 1. Enforce composition in `af plan`, not `af guide`

`af guide` is routing and discovery. `af plan` is where an explicit ordered chain is turned into an executable checklist, so composition checks belong there.

### 2. Backward compatibility first

Existing SOPs must continue to work unchanged. Missing workflow metadata means "untyped", not "invalid".

### 3. v1 hard-gates only adjacent state equality

Only this rule blocks planning:

`previous.Workflow output == next.Workflow input`

`Workflow requires` / `Workflow provides` are intentionally non-blocking in v1 to keep the first implementation small, reliable, and easy to test.

### 4. Keep workflow typing in metadata, not body sections

Metadata is easier for `validate`, `fmt`, `create --spec`, `update --spec`, and `plan --json` to consume consistently.

### 5. Add canonical metadata ordering

Extend `KNOWN_OPTIONAL_ORDER` so `af fmt` keeps these fields stable:

1. `Workflow input`
2. `Workflow output`
3. `Workflow requires`
4. `Workflow provides`

Place them after `Document role` and before `Tags`.

## CLI Behavior Contract

### `af plan` text output

- Existing output format stays intact.
- For typed phases, insert one extra line after the summary:
  - `State: proposal:draft -> proposal:reviewed`
- On typed mismatch, raise `click.ClickException` with an error like:
  - `Workflow type mismatch: COR-1102 outputs 'proposal:draft' but COR-1602 expects 'change:approved'`

### `af plan --json`

Keep output backward-compatible and additive.

Per phase add:

- `workflow_input`
- `workflow_output`
- `workflow_requires`
- `workflow_provides`
- `workflow_typed`

Add top-level:

- `composition_valid`
- `edges`

Example `edges` item:

```json
{
  "from": "COR-1102",
  "to": "COR-1602",
  "typed": true,
  "compatible": true,
  "from_output": "proposal:draft",
  "to_input": "proposal:draft"
}
```

### `af validate`

Add optional workflow-metadata linting for SOP documents:

- invalid token format
- one of input or output missing
- duplicate tokens in requires or provides
- empty token after comma splitting

Do not require these metadata fields on all SOPs.

## Implementation Plan

1. **Schema** — Add workflow metadata key constants to `core/schema.py`. Mark them as SOP-only optional workflow fields. Keep the module pure data only.
2. **Formatting contract** — Extend `core/normalize.py` `KNOWN_OPTIONAL_ORDER` with the 4 workflow fields.
3. **Pure workflow helper** — Add new `core/workflow.py` with `WorkflowSignature` dataclass, `WorkflowEdge` dataclass, `parse_workflow_signature()`, `validate_workflow_signature()`, `check_composition()`. No filesystem access.
4. **Validation** — Extend `validate_cmd.py` to lint workflow metadata for SOP docs. Leave non-SOP docs untouched.
5. **Plan command** — Refactor `plan_cmd.py`: parse all SOPs first, build workflow signatures, check adjacent composition, abort on typed mismatch, add additive JSON fields and `edges`, add `State:` line in text output.
6. **Documentation** — Update README `af plan` section, update bundled format/reference doc, add example chain.
7. **Seed example SOPs** — Add workflow metadata to a minimal chain (proposal creation → review, approved change → implementation, implementation → release). Do not mass-migrate every SOP.
8. **Hard gate** — pytest, ruff, af validate all pass. Manual smoke tests for typed pass / typed fail / untyped compatibility.

## Testing / Verification

### Unit tests

- parse valid single-token input/output
- reject invalid token characters
- reject missing `Workflow output` when `Workflow input` exists
- reject duplicate entries in `Workflow requires`
- compatible typed edge returns `compatible=True`
- mismatched typed edge returns explicit error payload

### `plan_cmd` tests

- untyped SOP chain preserves current output
- typed compatible chain renders successfully
- typed mismatch raises `ClickException`
- `--json` contains workflow fields and `composition_valid`
- mixed typed/untyped chain is allowed and marks corresponding edge `typed=false`

### `validate_cmd` tests

- valid workflow metadata passes
- bad token format is reported
- partial signature is reported
- duplicate `Workflow provides` token is reported

### `fmt` tests

- workflow metadata fields are reordered canonically
- existing metadata ordering remains unchanged for docs without workflow metadata

## Out of Scope / Follow-ups

- hard enforcement of `Workflow requires` / `Workflow provides`
- automatic path search for a valid SOP chain
- support for branching, parallel phases, or conditional edges
- routing-time compatibility checks inside `af guide`
- automatic migration of all legacy SOPs

## Approval

* [ ] Reviewed by: —
* [ ] Approved on: —

## Execution Log

| Date | Action | Result |
|------|--------|--------|
| 2026-04-05 | Initial proposal drafted | Not started |
| 2026-04-05 | Scope reduced to v1 adjacent typing | Planned |
| 2026-04-05 | Implementation ready for TDD execution | Planned |

## Post-Change Review

- **Success criteria:**
  - `af plan` catches at least one intentionally broken typed chain in tests
  - existing untyped workflows remain unchanged
  - JSON output becomes more semantically useful without breaking current text UX
- **Reviewer notes:** (to be filled after implementation)
- **Follow-up changes:** (to be filled after implementation)

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-05 | Initial version | Frank + GPT-5.4 Pro |
| 2026-04-05 | Scoped v1 to adjacent state composition; requires/provides advisory | Frank + GPT-5.4 Pro |
| 2026-04-05 | Added validation, JSON, fmt, and migration details | Frank + GPT-5.4 Pro |
| 2026-04-05 | Created as FXA-2204 (2193 occupied by PRP) | Saeba |
