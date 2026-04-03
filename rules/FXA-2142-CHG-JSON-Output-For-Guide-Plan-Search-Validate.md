# CHG-2142: JSON Output For Guide Plan Search Validate

**Applies to:** FXA project
**Last updated:** 2026-03-22
**Last reviewed:** 2026-03-22
**Status:** Completed
**Date:** 2026-03-22
**Requested by:** Frank
**Priority:** High
**Change Type:** Normal
**Related:** FXA-2140, FXA-2143

---

## What

Add a `--json` flag to `af guide`, `af plan`, `af search`, and `af validate`. Each command emits a stable, versioned JSON object that agents can parse reliably. This follows the existing pattern already established by `af list`, `af read`, and `af status`.

---

## Why

Alfred's README defines it as a tool for "AI agents and humans." Today, agents must parse human-readable text output from `guide`, `plan`, `search`, and `validate` — fragile and brittle when formatting changes. The four commands above are the highest-value targets because they are the primary decision-making interface for an agent running a task: routing → planning → searching context → validating output.

`af list`, `af read`, and `af status` already have JSON output. Adding `--json` to the remaining commands makes the full agent workflow programmable without text parsing.

---

## Impact Analysis

- **Systems affected:** `guide_cmd.py`, `plan_cmd.py`, `search_cmd.py`, `validate_cmd.py`
- **Channels affected:** none (CLI only)
- **Downtime required:** No
- **Rollback plan:** Remove `--json` flag from affected commands. No data migration needed; JSON is an additive output mode.
- **Breaking changes:** None — existing text output is unchanged when `--json` is not passed.

---

## Implementation Plan

### 1. `af guide --json`

```json
{
  "schema_version": "1",
  "routing_docs": [
    {
      "doc_id": "COR-1103",
      "title": "Workflow Routing",
      "source": "PKG",
      "status": "Active",
      "role": "routing"
    }
  ]
}
```

### 2. `af plan --json`

```json
{
  "schema_version": "1",
  "sop_ids": ["COR-1500", "COR-1600"],
  "phases": [
    {
      "phase": "RED",
      "source_sop": "COR-1500",
      "steps": [
        { "index": 1, "text": "Write a failing test", "gate": false },
        { "index": 2, "text": "Confirm test fails for the right reason", "gate": true }
      ]
    }
  ]
}
```

### 3. `af search --json`

```json
{
  "schema_version": "1",
  "query": "routing",
  "results": [
    {
      "doc_id": "COR-1103",
      "title": "Workflow Routing",
      "source": "PKG",
      "snippet": "...session-start routing SOP..."
    }
  ]
}
```

### 4. `af validate --json`

```json
{
  "schema_version": "1",
  "doc_id": "FXA-2140",
  "valid": false,
  "errors": [
    { "field": "Status", "message": "Value 'InProgress' not in allowed statuses for PRP" },
    { "section": "Open Questions", "message": "Required section missing" }
  ]
}
```

### 5. Tests

- Add `--json` output tests for each of the four commands
- Verify output is valid JSON and matches schema
- Verify text output is unchanged when `--json` is not passed

---

## Testing / Verification

- `af guide --json | python3 -m json.tool` exits 0
- `af plan COR-1500 --json | python3 -m json.tool` exits 0
- `af search routing --json | python3 -m json.tool` exits 0
- `af validate FXA-2140 --json | python3 -m json.tool` exits 0
- Existing text output unchanged: `af guide` (without --json) still produces human-readable text
- Unit tests pass for all four commands

---

## Approval

- [ ] Reviewed by: —
- [ ] Approved on: —

---

## Execution Log

| Date | Action | Result |
|------|--------|--------|

---

## Post-Change Review

_To be completed after implementation._

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-22 | Initial version | Frank + Claude Code |
