# PRP-2193: Simplify-Fmt-Metadata-Order-Comparison

**Applies to:** FXA project
**Last updated:** 2026-04-04
**Last reviewed:** 2026-04-04
**Status:** Draft

---

## What Is It?

Replace fragile `id()`-based list comparison with direct list equality in `fmt_cmd.normalize_metadata_order()`.

---

## Problem

`normalize_metadata_order()` in `src/fx_alfred/commands/fmt_cmd.py` (line 60) uses `[id(mf) for mf in ordered_fields] == [id(mf) for mf in parsed.metadata_fields]` to detect whether metadata field order changed. This relies on CPython's `id()` (memory address) which is:

1. **Harder to understand** — readers must reason about object identity rather than value semantics
2. **Non-idiomatic** — standard Python comparison for dataclasses uses `==`
3. **Unnecessary** — both lists contain the exact same `MetadataField` instances (popped from a copy), and `MetadataField` is a `@dataclass` with auto-generated `__eq__`

## Proposed Solution

Replace lines 59-60:
```python
# Before
    # Compare by object identity: same objects in same order = no change
    if [id(mf) for mf in ordered_fields] == [id(mf) for mf in parsed.metadata_fields]:
        return False

# After
    # Same objects in same order = no change (dataclass __eq__ compares all fields)
    if ordered_fields == parsed.metadata_fields:
        return False
```

This is semantically equivalent because:
- The reorder algorithm (lines 50-57) pops objects from `remaining` (a shallow copy of `parsed.metadata_fields`) and appends them to `ordered_fields` — same instances, not copies
- The stable reorder preserves relative order of duplicate keys, so even with duplicates the same objects end up at the same positions
- Dataclass `__eq__` compares all fields (key, value, prefix_style, raw_line, dirty)

**Scope:**

| In scope | Out of scope |
|----------|-------------|
| `src/fx_alfred/commands/fmt_cmd.py` lines 59-60 | All other files |
| Comment text on line 59 | No SOP changes |
| No test changes needed (existing `test_fmt_cmd.py` covers this path) | No CLI interface changes |

## Risk Awareness

1. **Duplicate metadata fields with identical values:** If two `MetadataField` instances have identical field values (same key, value, prefix_style, raw_line, dirty) and their positions swap, `==` would report no change while `id()` would detect the swap. This cannot happen in this code path because objects are popped from `remaining` (not copied), so identity and value equality are equivalent. Even hypothetically, swapping value-identical fields produces an identical document — not detecting this is correct behavior.

2. **Future `__eq__` override:** If `MetadataField` later adds a custom `__eq__` that deviates from the default dataclass behavior, this comparison could break. This is mitigated by the fact that `MetadataField` is a simple data holder with no reason to override `__eq__`, and any such change would be caught by existing fmt tests.

3. **No runtime risk:** The change is a mechanical refactor; the function's return value and side effects are unchanged for all inputs that can occur in practice.

## Open Questions

None — this is a mechanical refactor.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-04 | Initial version | — |
| 2026-04-04 | R2: Add scope table, risk awareness section, specify comment text (Codex 8.7 blocking issues) | Claude Code |
