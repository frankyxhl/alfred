# REF-1204: CTX Format

**Applies to:** All projects using the COR document system
**Last updated:** 2026-05-03
**Last reviewed:** 2026-05-03
**Status:** Active
**Depends on:** COR-0002 (Document Format Contract)
**Related:** COR-1203 (Pre-Task Alignment — references CTX documents for glossary challenge)
**Authored from:** FXA-2121 PRP (companion REF to COR-1203, defines the glossary template)

---

## What Is It?

The document format specification for project glossary (CTX) documents. A CTX document is a shared lexicon of project-specific terms — the "ubiquitous language" that agents and humans use to communicate concisely about the project.

---

## Why

Without a shared glossary, agents explain terms on every invocation, inflating token usage. A CTX document gives canonical definitions that COR-1203 (Pre-Task Alignment) can challenge against, and that future sessions can reference directly without re-explaining "Review Unit", "mechanism", "gate", etc.

---

## Document Format

A CTX document is a Markdown table with four columns:

```
| Term | Definition | Source | Updated |
|------|------------|--------|----------|
```

- **Term:** the canonical name (capitalised if domain-specific, lowercase if generic)
- **Definition:** one or two sentences; precise but concise
- **Source:** the ACID that first defined the term (e.g., `COR-1613`), or "session" if resolved in-conversation
- **Updated:** ISO date of last change (YYYY-MM-DD)

### CTX document location

- **PRJ-layer:** `rules/<prefix>-XXXX-CTX-<topic>.md` (e.g., `FXA-2123-CTX-Alfred-Glossary.md`). Uses existing Alfred document filename convention — the 3-letter code `CTX` parses correctly under current `FILENAME_PATTERN`.
- **Project root:** `CONTEXT.md` for single-context projects following the same table format, without Alfred document headers.
- **Multi-context:** `CONTEXT-MAP.md` at project root pointing to per-module CONTEXT.md files.

### Metadata

PRJ-layer CTX documents use base Alfred metadata format (COR-0002 frontmatter). Since no `DocType.CTX` enum exists, CTX documents declare `**Status:** Active` and use REF-compatible metadata. `af validate` handles unknown type codes gracefully (falls back to base required fields). `af fmt` formats the metadata block regardless of type code.

---

## CTX Maintenance

- Create a CTX document when a project accumulates 5+ domain terms that benefit from canonical definition
- Update a term's row when the definition is sharpened or clarified (change `Updated` date, preserve `Source`)
- Add a new row when a new term is resolved during a COR-1203 interview or any other session
- Terms that become obsolete should be marked with a deprecated entry rather than deleted (per COR-1301)

---

## Pilot Instance

The first CTX instance is `FXA-2271-CTX-Alfred-Glossary.md` in the Alfred project's top-level `rules/` directory, covering ~15 core Alfred terms. This pilot validates the format and informs future promotion decisions. After 90 days and ≥3 CTX instances in real use, a future PRP may propose adding `DocType.CTX` to `schema.py` and `af create ctx` tooling.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-03 | Initial version per FXA-2121 PRP. Defines CTX format spec; companion to COR-1203. | Frank Xu |
