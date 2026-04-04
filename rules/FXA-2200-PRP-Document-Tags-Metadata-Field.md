# PRP-2200: Document Tags Metadata Field

**Applies to:** FXA project
**Last updated:** 2026-04-04
**Last reviewed:** 2026-04-04
**Status:** Approved

---

## What Is It?

Add an optional `Tags` metadata field to all document types. Tags are comma-separated, free-form labels (e.g., `Tags: tdd, review, release`) that enable filtering via `af list --tag <value>`.

---

## Problem

Currently there is no way to categorize or cross-cut documents beyond type, prefix, and source layer. For example, finding all documents related to "review" requires `af search review`, which returns full-text matches including irrelevant hits in Change History or body text. A dedicated Tags field enables precise, intent-based categorization that full-text search cannot provide.

## Scope

**In scope (v1):**

1. **Metadata field:** Add `Tags` as an optional metadata field for all document types in `schema.py`.
2. **Parser helper:** Add `parse_tags()` in `parser.py` to split comma-separated tag strings.
3. **Document property:** Add `tags` property to `Document` dataclass in `document.py`.
4. **CLI filter:** Add `--tag` option to `af list` in `list_cmd.py` (single value, case-insensitive exact match).
5. **Validation:** `af validate` reports Tags format errors (empty tags, duplicates) as issues (non-zero exit) in `validate_cmd.py`.
6. **Formatting:** `af fmt` normalizes Tags in `fmt_cmd.py`.
7. **Metadata ordering:** Update `sort_metadata()` in `normalize.py` to place Tags after required fields.
8. **Document contract:** Update COR-0002 (Document Format Contract) Optional Fields table to register Tags for all types.

**Out of scope (v1):**

- Tag auto-complete or suggestion
- Tag taxonomy enforcement or controlled vocabulary
- Tag-based routing in `af guide`
- Multiple `--tag` flags (AND/OR logic) — v1 supports single `--tag` only
- `af create` template pre-population of Tags — users add Tags manually after creation

## Proposed Solution

### 1. Schema (`schema.py`)

Add a new `OPTIONAL_METADATA` dict. Tags is available for all document types:

```python
OPTIONAL_METADATA: dict[DocType, list[str]] = {
    dt: ["Tags"] for dt in DocType
}
```

This dict is additive — existing optional fields (Related, Reviewed by, etc.) defined in COR-0002 remain valid. `OPTIONAL_METADATA` only lists fields that have special CLI handling (validation, formatting).

### 2. Parser (`parser.py`)

Add a pure function. Note: `parse_metadata()` returns `ParsedDocument` (not a dict) — the `parse_tags()` helper operates on the raw string value extracted from a `MetadataField`, not on the `ParsedDocument` directly.

```python
def parse_tags(value: str) -> list[str]:
    """Split comma-separated tags, strip whitespace, filter empty, lowercase."""
    return [t.strip().lower() for t in value.split(",") if t.strip()]
```

No changes to `parse_metadata()` signature or return type.

### 3. Document dataclass (`document.py`)

Add a `tags` property that reads the file content on demand. Access the Tags value by iterating `ParsedDocument.metadata_fields` (a list of `MetadataField` objects):

```python
from fx_alfred.core.parser import parse_metadata, parse_tags, MalformedDocumentError

@property
def tags(self) -> list[str]:
    """Parse Tags metadata field. Returns [] if absent or unreadable."""
    try:
        content = self.resolve_resource().read_text()
        parsed = parse_metadata(content)
        tag_field = next(
            (mf for mf in parsed.metadata_fields if mf.key == "Tags"), None
        )
        return parse_tags(tag_field.value) if tag_field else []
    except (ValueError, OSError, MalformedDocumentError):
        return []
```

**Performance note:** `tags` reads the file each time it is called. For `af list --tag`, this means reading every document file. This is acceptable because: (a) document count is typically <200, (b) `af list` without `--tag` remains fast (filename-only), (c) file reads are only triggered when `--tag` is specified.

**Backward compatibility:** Existing documents without a Tags field return `[]` — they are unaffected. `af validate` does NOT flag documents missing Tags (since it is optional).

### 4. List command (`list_cmd.py`)

Add `--tag` option with AND logic against existing filters:

```python
@click.option("--tag", default=None, help="Filter by tag (case-insensitive exact match).")
```

Filter logic (after existing type/prefix/source filters):
```python
if tag is not None:
    docs = [d for d in docs if tag.lower() in d.tags]
```

If no documents match, output "No documents found." (consistent with existing behavior). Documents that are unreadable or have no Tags are silently excluded from matches (consistent with how `af validate` handles read failures — it reports "Could not read document" and continues).

### 5. Validate command (`validate_cmd.py`)

Add Tags-specific validation inside the existing `try` block, after the Status validation and before the SOP section checks (around line 210 in current code). This hooks into the same `issues` list and follows the same pattern:

```python
# Validate Tags field format (if present)
tag_field = next(
    (mf for mf in parsed.metadata_fields if mf.key == "Tags"), None
)
if tag_field is not None:
    raw_parts = [t.strip() for t in tag_field.value.split(",")]
    # Check for empty tags (e.g., "tdd,,review" or trailing comma)
    if any(not part for part in raw_parts):
        issues.append("Tags field contains empty tag values")
    # Check for duplicates (case-insensitive)
    lowered = [t.lower() for t in raw_parts if t]
    if len(lowered) != len(set(lowered)):
        issues.append("Tags field contains duplicate tags")
```

These are reported as validation issues (same severity as existing checks) and cause non-zero exit code, consistent with current `af validate` behavior.

### 6. Fmt command (`fmt_cmd.py`)

Add a `normalize_tags` function and insert it into the `format_document()` pipeline after `normalize_metadata_order` and before `normalize_trailing_whitespace`:

```python
def normalize_tags(parsed: ParsedDocument) -> bool:
    """Normalize Tags metadata field: lowercase, sort, deduplicate.

    Returns True if any changes were made.
    """
    tag_field = next(
        (mf for mf in parsed.metadata_fields if mf.key == "Tags"), None
    )
    if tag_field is None:
        return False

    from fx_alfred.core.parser import parse_tags
    tags = parse_tags(tag_field.value)
    normalized = ", ".join(sorted(set(tags)))

    if normalized == tag_field.value:
        return False

    tag_field.value = normalized
    tag_field.dirty = True
    return True
```

Pipeline order in `format_document()`:
```python
def format_document(parsed: ParsedDocument, doc_type: DocType | None) -> bool:
    changed = False
    changed |= normalize_metadata_order(parsed, doc_type)
    changed |= normalize_tags(parsed)           # NEW — after order, before whitespace
    changed |= normalize_trailing_whitespace(parsed)
    changed |= normalize_blank_lines_in_body(parsed)
    changed |= normalize_table_alignment(parsed)
    return changed
```

### 7. Metadata ordering (`normalize.py`)

Update `sort_metadata()` to recognize Tags and other known optional fields. Tags is placed after all required fields, before truly unknown fields:

```python
KNOWN_OPTIONAL_ORDER = [
    "Related", "Reviewed by", "Last executed", "Severity",
    "Date", "Requested by", "Priority", "Change Type",
    "Document role", "Tags",
]

def sort_metadata(fields: list[str], doc_type: DocType) -> list[str]:
    """Return fields in canonical order. Required first, then known optional, then unknown."""
    canonical = REQUIRED_METADATA.get(doc_type, [])
    canonical_set = set(canonical)
    optional_set = set(KNOWN_OPTIONAL_ORDER)

    # Required fields in canonical order
    ordered = [f for f in canonical if f in fields]
    # Known optional fields in defined order
    ordered += [f for f in KNOWN_OPTIONAL_ORDER if f in fields and f not in canonical_set]
    # Truly unknown fields in original relative order
    ordered += [f for f in fields if f not in canonical_set and f not in optional_set]
    return ordered
```

### 8. Document Format Contract (COR-0002)

Add Tags to the Optional Fields table under the "## Optional Fields" section:

| Field | Used by | Source |
|-------|---------|--------|
| Tags | All types | FXA-2200 PRP |

## Risks and Trade-offs

1. **Tag fragmentation / typos:** Free-form tags may diverge (e.g., "test" vs "testing" vs "tests"). Mitigation: `af fmt` lowercases, sorts, and deduplicates. Taxonomy enforcement is explicitly out of scope for v1 but can be added later as a validate rule.
2. **Performance on large document sets:** `af list --tag` reads every document file to parse metadata. For the current scale (<200 docs) this is negligible (<1s). If document count grows significantly, a tag index cache could be added in a future version.
3. **Unreadable documents:** `Document.tags` catches `ValueError`/`OSError`/`MalformedDocumentError` and returns `[]`, so malformed or missing files do not crash `af list --tag` — they are silently excluded from tag matches, consistent with how `af validate` handles read failures.

## Open Questions

None.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-04 | Initial version | Frank |
| 2026-04-04 | R1 fix: clarified data model, added COR-0002/normalize.py scope, added risks, defined validate severity, specified single --tag only, added performance notes | Claude Code |
| 2026-04-04 | R2 fix: fixed parse_metadata return type (ParsedDocument not dict), fixed Document.tags code to use MetadataField iteration, specified sort_metadata modification with KNOWN_OPTIONAL_ORDER, specified validate_cmd integration point, specified fmt pipeline ordering | Claude Code |
| 2026-04-04 | R3 review passed: Codex 10.0, Gemini 9.7. Approved. | Claude Code |
