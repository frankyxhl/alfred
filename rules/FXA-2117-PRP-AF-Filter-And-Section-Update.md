# PRP-2117: AF Filter And Section Update

**Applies to:** FXA project
**Last updated:** 2026-03-20
**Last reviewed:** 2026-03-20
**Status:** Draft
**Related:** FXA-2116 (Document Format Contract, prerequisite)
**Reviewed by:** —

---

## What Is It?

Two new capabilities for the af CLI: (1) `af filter` command for content-based document queries, and (2) `af update --section` for block-level content updates. Both depend on FXA-2116 (Document Format Contract) being implemented first.

---

## Problem

1. `af list` can only filter by filename metadata (type, prefix, source) — no way to query by Status, Reviewed by, or any document content
2. Finding all Draft PRPs requires reading every document manually or using `af search "Status"` and parsing the output
3. `af update` can modify individual metadata fields and append history, but cannot replace an entire section (e.g., Description, Open Questions)
4. AI agents waste tokens reading full documents when they only need one field or one section

---

## Scope

**In scope:**
- New `af filter` command — content-aware document filtering
- `af update --section` — replace entire section content
- `af read --field` / `af read --section` — selective reading (token-efficient)

**Out of scope:**
- Changes to `af list` — it stays as filename-level filtering
- Full-text search — `af search` already handles that
- markdown-it-py / AST parsing — not needed; line scanning is sufficient

**Prerequisite:** FXA-2116 (Document Format Contract) must be implemented first so document format is guaranteed.

---

## Proposed Solution

### af filter — Content-Based Queries

```bash
af filter --status Draft                          # all Draft documents
af filter --status Draft --type PRP               # Draft PRPs only
af filter --field "Reviewed by" "Codex*"          # wildcard match
af filter --field "Reviewed by" --empty           # field exists but value is empty/—
af filter --has-section "Open Questions"           # docs that have this section
af filter --status Draft --json                   # JSON output
```

Implementation: For each document from `scan_documents()`, read first 15 lines, regex match metadata fields, apply filter. Combine with existing filename filters (--type, --prefix, --source).

Output format: Same as `af list` (or --json).

### af update --section — Block-Level Updates

```bash
af update FXA-2106 --section "Description" "New description content here"
af update FXA-2106 --section "Open Questions" "1. First question\n2. Second"
af update FXA-2106 --section "Description" --from-file desc.md
```

Implementation: Find `## <Section Name>` heading, find next `## ` or `---` or EOF, replace everything between.

### af read --field / --section — Selective Reading

```bash
af read FXA-2106 --field Status                   # → "Draft"
af read FXA-2106 --field --all                     # → all metadata as key: value
af read FXA-2106 --field --all --json              # → JSON object of metadata
af read FXA-2106 --section "Problem"               # → just the Problem section
af read FXA-2106 --section "Open Questions" --json  # → section content as JSON string
```

Implementation:
- `--field`: Read first 15 lines, regex match, return value
- `--section`: Line scan for H2 heading, return content until next H2/separator

### Token Savings

| Operation | Current tokens | With new commands |
|-----------|---------------|-------------------|
| Check Status | ~150 (full af read) | ~5 (af read --field Status) |
| Read Description | ~150 (full af read) | ~20 (af read --section Description) |
| Find Draft PRPs | ~150 × N documents | ~10 per match (af filter --status Draft) |
| Update Description | ~300 (read + parse + write all) | ~25 (af update --section) |

---

## Implementation Order

1. **CHG-1: af read --field** — selective metadata reading (simplest, most impactful for token savings)
2. **CHG-2: af read --section** — selective section reading
3. **CHG-3: af filter** — content-based filtering
4. **CHG-4: af update --section** — block-level updates

---

## Open Questions

1. Should `af filter` support regex matching on field values, or just exact + wildcard?
2. Should `af read --field --all` include the H1 components (type_code, acid, title) in addition to metadata fields?
3. Should `af update --section` create a new section if it doesn't exist, or error?
4. How to handle `af filter` performance if document count grows to 100+? (Cache metadata on scan?)

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version from session discussion | Claude Code |
