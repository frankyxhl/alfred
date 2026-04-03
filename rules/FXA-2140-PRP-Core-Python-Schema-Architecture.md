# PRP-2140: Core Python Schema Architecture

**Applies to:** FXA project
**Last updated:** 2026-03-22
**Last reviewed:** 2026-03-22
**Status:** Implemented
**Related:** FXA-2141, FXA-2142, FXA-2143, COR-0002
**Reviewed by:** Codex (9.5/10), Gemini (10.0/10)

---

## What Is It?

Introduce a formal Python schema layer (`core/schema.py`, `core/normalize.py`) that centralizes all document type rules, metadata contracts, allowed statuses, and slug normalization. All commands (`create`, `update`, `validate`, `guide`, `plan`) import from this layer instead of defining rules inline. **v1 is a pure refactor: `schema.py` mirrors current `validate_cmd.py` rules exactly — no behavioral change to any command output.** Markdown remains the output format; Python schema is the authoritative source of truth for structure and constraints.

---

## Problem

Alfred's document rules are currently scattered across individual command implementations:

- `guide` identifies routing documents by checking if the filename contains `SOP-Workflow-Routing` — a fragile string match (`guide_cmd.py:8,18-19`)
- `plan` extracts steps by matching heading names (`What Is It?`, `Steps`, `Rules`, `Concepts`) and numbered-list regex inline in `plan_cmd.py`
- `create` generates file slugs with `title.replace(' ', '-')`, skipping sanitization for special characters, path separators, and cross-platform safety (`create_cmd.py:182`)
- `update --title` adds extra validation (leading/trailing whitespace, path separators) but this logic is not shared with `create`
- `validate` embeds per-type allowed statuses, required metadata fields, and required sections directly in `validate_cmd.py:26-44`

As commands evolve independently, these rules diverge. An agent or script calling multiple commands cannot trust they share a consistent contract. Adding a new document type (or changing a status name) requires edits in multiple places with no single point of truth.

---

## Scope

**In scope (v1) — refactor only, no behavioral changes:**
- `core/schema.py`: `DocType` enum, `DocRole` enum, allowed statuses per type, required metadata fields per type, required section headings per type — **all values mirror current `validate_cmd.py` exactly**
- `core/normalize.py`: shared `slugify(title) -> str`, `normalize_date(s) -> str`, `sort_metadata(fields) -> list`, `strip_trailing_whitespace(content) -> str`
- Refactor `validate_cmd.py` to import rules from `schema.py` — **same output, same behavior**
- Refactor `create_cmd.py` and `update_cmd.py` to use shared `slugify()` from `normalize.py` — **no behavioral change for well-formed titles**
- Refactor `guide_cmd.py` to also check `DocRole` metadata field as routing signal, with filename pattern as fallback — **guide fallback order: metadata role first, filename pattern second; both routes accepted**

**Out of scope (v1):**
- Any changes to allowed status values or required metadata fields beyond what exists today
- `core/api.py` (create_from_spec, patch_document) — covered by FXA-2143
- `core/render.py` (structured object → Markdown) — future work
- `core/lint.py` (semantic lint beyond validate) — future work
- Any changes to the Markdown format itself (COR-0002 remains authoritative)
- Migration of existing documents
- Changing contract values (adding/removing statuses, fields) — those require a separate PRP with migration plan

---

## Proposed Solution

### Module: `core/schema.py`

**Critical: mirrors `validate_cmd.py:26-44` exactly. No new values added, no values removed.**

```python
from enum import Enum

class DocType(str, Enum):
    SOP = "SOP"
    PRP = "PRP"
    CHG = "CHG"
    ADR = "ADR"
    REF = "REF"
    PLN = "PLN"
    INC = "INC"

class DocRole(str, Enum):
    ROUTING = "routing"
    SOP = "sop"
    INDEX = "index"
    GENERAL = "general"

# Mirrors validate_cmd.py ALLOWED_STATUS exactly
ALLOWED_STATUSES: dict[DocType, list[str]] = {
    DocType.SOP: ["Draft", "Active", "Deprecated"],
    DocType.PRP: ["Draft", "Approved", "Rejected", "Implemented"],
    DocType.CHG: ["Proposed", "Approved", "In Progress", "Completed", "Rolled Back"],
    DocType.ADR: ["Proposed", "Accepted", "Superseded", "Deprecated"],
    DocType.REF: ["Active", "Draft", "Deprecated"],
    DocType.PLN: ["Draft", "Active", "Completed", "Cancelled"],
    DocType.INC: ["Open", "Resolved", "Monitoring"],   # matches validate_cmd.py:44
}

# Mirrors validate_cmd.py REQUIRED_FIELDS_BY_TYPE exactly.
# Note: list ORDER defines canonical rendering order for formatters (e.g. af fmt).
REQUIRED_METADATA: dict[DocType, list[str]] = {
    DocType.SOP: ["Applies to", "Last updated", "Last reviewed", "Status"],
    DocType.PRP: ["Applies to", "Last updated", "Last reviewed", "Status"],   # 4 fields only
    DocType.CHG: ["Applies to", "Last updated", "Last reviewed", "Status"],
    DocType.ADR: ["Applies to", "Last updated", "Last reviewed", "Status"],
    DocType.REF: ["Applies to", "Last updated", "Last reviewed", "Status"],
    DocType.PLN: ["Applies to", "Last updated", "Last reviewed", "Status"],
    DocType.INC: ["Applies to", "Last updated", "Last reviewed", "Status"],
}

REQUIRED_SECTIONS: dict[DocType, list[str]] = {
    DocType.SOP: ["What Is It?", "Why", "When to Use", "When NOT to Use", "Steps"],
    DocType.PRP: ["What Is It?", "Problem", "Scope", "Proposed Solution", "Open Questions"],
    DocType.CHG: ["What", "Why", "Impact Analysis", "Implementation Plan"],
    DocType.ADR: ["Decision", "Context", "Consequences"],
    DocType.REF: ["What Is It?"],
    DocType.PLN: ["What Is It?", "Phases"],
    DocType.INC: ["What Happened", "Impact", "Root Cause", "Resolution"],
}

# Routing doc identification (supplements filename pattern)
ROUTING_ROLE_METADATA_KEY = "Document role"
ROUTING_ROLE_VALUE = "routing"
```

### Module: `core/normalize.py`

```python
import re

def slugify(title: str) -> str:
    """Convert a document title to a safe, cross-platform filename slug."""
    slug = title.strip()
    slug = re.sub(r'[\\/:*?"<>|]', '', slug)   # strip path-unsafe chars
    slug = re.sub(r'\s+', '-', slug)             # spaces → dashes
    slug = re.sub(r'-{2,}', '-', slug)           # collapse multiple dashes
    slug = slug.strip('-')
    return slug

def normalize_date(s: str) -> str:
    """Normalize date strings to YYYY-MM-DD."""
    ...

def sort_metadata(fields: list[str], doc_type: DocType) -> list[str]:
    """Return metadata field names in canonical order for the given doc type.
    Unknown fields are appended after known fields in original order."""
    known = REQUIRED_METADATA.get(doc_type, [])
    known_set = set(known)
    result = [f for f in known if f in set(fields)]
    result += [f for f in fields if f not in known_set]
    return result
```

### Routing fallback order for `guide_cmd.py`

```python
# 1. Prefer metadata-declared role (new, forward-compatible)
if doc.metadata.get(ROUTING_ROLE_METADATA_KEY) == ROUTING_ROLE_VALUE:
    routing_docs.append(doc)
# 2. Fall back to filename pattern (backwards-compatible for existing docs)
elif ROUTING_PATTERN in doc.filename:
    routing_docs.append(doc)
```

### Refactoring plan

| File | Current behavior | After refactor | Behavioral change? |
|------|-----------------|----------------|-------------------|
| `validate_cmd.py` | Defines allowed statuses, required fields inline | Import from `schema.py` | **None** |
| `create_cmd.py` | `title.replace(' ', '-')` | `normalize.slugify(title)` | None for valid titles |
| `update_cmd.py` | Ad-hoc title validation | `normalize.slugify(title)` | None for valid titles |
| `guide_cmd.py` | Filename pattern only | Metadata role first, filename fallback | **None** (additive detection) |

---

## Open Questions

_All resolved._

1. ~~Should `DocRole` be stored as a metadata field in addition to the filename pattern, or replace it?~~
   **Resolved:** Add `Document role: routing` as an additional metadata signal; keep filename pattern as fallback for existing docs. Guide fallback order: metadata role first, filename pattern second. No migration required.

2. ~~Should `REQUIRED_SECTIONS` be enforced strictly (exact heading name) or as a case-insensitive contains check?~~
   **Resolved:** Case-insensitive contains check, matching current `validate` behavior.

3. ~~Should `core/schema.py` be importable without triggering any file I/O?~~
   **Resolved:** Yes. `schema.py` is pure data definitions only — no filesystem access, no imports from `core/scanner.py` or `core/parser.py`.

---

## Implementation Plan

1. Read `validate_cmd.py:26-44` to capture current exact status and field values
2. Create `core/schema.py` mirroring those values exactly (no additions, no removals)
3. Create `core/normalize.py` with `slugify()`, `normalize_date()`, `sort_metadata()`
4. Refactor `validate_cmd.py` to import from `schema.py` — run existing tests to confirm no behavioral change
5. Refactor `create_cmd.py` and `update_cmd.py` to use `normalize.slugify()` — run existing tests
6. Refactor `guide_cmd.py` to check `DocRole` metadata first, filename pattern as fallback
7. Add unit tests: `schema.py` constants, `normalize.slugify()` edge cases, `sort_metadata()` with unknown fields

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-22 | Initial version | Frank + Claude Code |
| 2026-03-22 | Round 1 revision: clarify v1 is refactor-only, mirror validate_cmd.py values exactly (INC statuses, REQUIRED_METADATA), add guide fallback order, add behavioral change column to refactoring table | Frank + Claude Code |
| 2026-03-22 | Round 2 approved (Codex 9.5, Gemini 10.0). Advisory: add order comment to REQUIRED_METADATA | Frank + Claude Code |
| 2026-03-22 | Round 3 approved (Codex 9.23, Gemini 10.0). Fixes: slugify() rewritten to strip path-unsafe chars only per PRP spec; guide_cmd.py malformed error scope restricted to filename-pattern-matched docs. Status → Implemented | — |
