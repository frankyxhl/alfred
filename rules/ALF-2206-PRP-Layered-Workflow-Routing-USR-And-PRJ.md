# PRP-2206: Layered Workflow Routing USR And PRJ

**Applies to:** ALF project
**Last updated:** 2026-03-20
**Last reviewed:** 2026-03-20
**Status:** Implemented
**Related:** ALF-2205, COR-1103

---

## What Is It?

Extend the workflow routing system to support USR and PRJ layer routing documents. Each layer has a distinct responsibility — PKG routes to SOP types, USR provides user-level specifics, PRJ provides project-level specifics. Also enhance `af guide` to dynamically output merged routing info, and move current quick-start content to `af --help`.

---

## Problem

COR-1103 (PKG layer) defines universal routing rules but cannot reference project-specific SOPs without hardcoding them. This was flagged during ALF-2205 review — COR-1103 had to use generic placeholders like "INC (project-level SOP)" because referencing ALF-2300 directly violated the COR-level scope.

Each project has its own workflows:
- ALF: ALF-2300 (Record Incident), ALF-2000 (Create Channel)
- FXA: FXA-2102 (Release To PyPI), FXA-2100 (Leader Mediated Development)

Without layered routing, the agent must discover project-specific SOPs by reading all documents, or the user must remind it every time.

## Scope

**In scope:**
- Define the routing document format for USR and PRJ layers
- Define layer responsibilities (each layer has different content, not overlapping branches)
- Create ALF USR-layer routing document (`~/.alfred/`)
- Create FXA PRJ-layer routing document (`alfred_ops/rules/`)
- Enhance `af guide` to dynamically scan and output merged routing from all 3 layers
- Move current `af guide` quick-start content to `af --help` epilog
- Update memory entry to use `af guide` instead of `af read COR-1103`

**Out of scope:**
- Changing COR-1103 content (already handled by ALF-2205)
- `af validate` enforcement of routing documents
- New document type for routing (reuse SOP type)

## Proposed Solution

### Layer responsibilities (not overlapping branches)

Each layer has a distinct role. They don't share branch numbers or merge trees.

```
PKG (COR-1103):  WHAT type of work → which SOP category
                  "incident → INC", "new feature → PRP", "system change → CHG"

USR (~/.alfred/): WHO — user-level preferences and cross-project rules
                  "team dispatch → GLM codes, Codex/Gemini review"
                  "leader never writes code directly"

PRJ (./rules/):   WHERE — project-specific SOP mappings and workflows
                  "INC → ALF-2300", "release → FXA-2102", "development → FXA-2100"
```

Note: Project-specific SOP mappings (like `INC → ALF-2300`) belong in PRJ, not USR. USR is for cross-project user preferences only.

### Discovery mechanism

Routing documents use a **fixed naming convention**: `*-SOP-Workflow-Routing*.md`

`af guide` scans all three layers for documents matching this pattern:
1. PKG: scan bundled rules for `*-SOP-Workflow-Routing*.md`
2. USR: scan `~/.alfred/` for `*-SOP-Workflow-Routing*.md`
3. PRJ: scan `./rules/` for `*-SOP-Workflow-Routing*.md`

`af guide` uses `scan_documents()` from `scanner.py` to find all documents, then filters by filename pattern. This reuses the existing scanning infrastructure.

**Selection rules:**
- Only documents with `Status: Active` are used; `Status: Deprecated` documents are skipped
- If multiple Active matches in a layer, use the lowest ACID (tie-break)
- If a layer has no Active routing document, it's skipped
- Routing documents are ordinary SOP documents and must comply with COR-0002

### Routing document format

**PKG (COR-1103)** — existing, no changes:
```
═══ ALWAYS ═══
═══ PRIMARY ROUTE ═══
═══ OVERLAYS ═══
═══ GOLDEN RULES ═══
```

**USR routing document** (e.g., `ALF-2207-SOP-Workflow-Routing-USR.md`):

Cross-project user preferences only. No project-specific SOP mappings here.

```
# SOP-2207: Workflow Routing USR

═══ USER CONTEXT ═══

• Implementation dispatch → GLM for coding, Codex/Gemini for review
• Code changes → always go through /team, leader never writes code directly
• All code changes must go through review before commit

═══ USER GOLDEN RULES ═══

• GLM = Worker (writes code), Codex/Gemini = Reviewer (reviews code)
• Never create documents outside af system, always use af create
```

**PRJ routing document** (e.g., `FXA-2124-SOP-Workflow-Routing-PRJ.md`):

Project-specific SOP mappings and workflows.

```
# SOP-2124: Workflow Routing PRJ

═══ PROJECT CONTEXT ═══

• INC (incident) → ALF-2300 (Record Incident)
• Release to PyPI → FXA-2102
• Leader mediated development → FXA-2100
• All documents use af create (never manual), prefix FXA, area 21

═══ PROJECT GOLDEN RULES ═══

ALF-2300: Record what happened, impact, resolution, follow-up
FXA-2102: Tag release on GitHub, CI publishes to PyPI; verify with af --version
FXA-2100: Leader dispatches GLM, reviews with Codex+Gemini, synthesizes
```

### `af guide` behavior change

**Current:** Static quick-start guide from `templates/guide.md`

**New:** Dynamic routing output. Add `@root_option` decorator to `guide_cmd` to enable PRJ layer scanning.

**Implementation:**
1. Use `scan_documents(root)` from `scanner.py` to get all documents
2. Filter documents by filename containing `SOP-Workflow-Routing`
3. Filter by `Status: Active` only (parse metadata, skip Deprecated)
4. Group by source layer (pkg, usr, prj)
5. Within each layer, select lowest ACID if multiple matches
6. Output full document content via `doc.resolve_resource().read_text()` (same as `af read`)
7. Between layers, output a separator with layer name and document ID

**Rendering contract:** Full document text output (including metadata header), consistent with `af read` behavior. No section extraction. If `parse_metadata()` raises `MalformedDocumentError`, output filename + error message and continue with next layer.

Example output:
```
═══ PKG: COR-1103 Workflow Routing ═══

# SOP-1103: Workflow Routing

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-20
...
[full document content]

═══ USR: ALF-2207 Workflow Routing USR ═══

# SOP-2207: Workflow Routing USR
...
[full document content]

═══ PRJ: FXA-2124 Workflow Routing PRJ ═══

# SOP-2124: Workflow Routing PRJ
...
[full document content]
```

If no routing doc found for a layer:
```
═══ USR: (no active routing document found) ═══
```

### Quick-start content migration

Move current `templates/guide.md` content (document naming, layer system, create examples) into the `af` CLI epilog, shown via `af --help`. Update existing `test_guide_*` tests to match the new dynamic output.

### Agent session-start behavior

Memory entry updated from:
```
af read COR-1103
```
to:
```
af guide --root <project-root>
```

This single command gives the agent the full merged routing context from all 3 layers.

### Selection rules

| Rule | Details |
|------|---------|
| Naming convention | Filename must contain `SOP-Workflow-Routing` |
| Status filter | Only `Status: Active` documents are used |
| Deprecated skip | `Status: Deprecated` documents are silently skipped |
| Tie-break | Lowest ACID wins within same layer |
| Layer priority | Output order: PKG → USR → PRJ (additive, not overriding) |

### Failure modes

| Scenario | Behavior |
|----------|----------|
| No USR routing doc | Skip USR section, output note |
| No PRJ routing doc | Skip PRJ section, output note |
| Multiple Active routing docs in one layer | Warning, use lowest ACID |
| Deprecated routing doc exists | Silently skipped |
| Malformed routing doc | Show filename + parse error, continue with other layers |
| `scan_documents()` fails | Fall back to error message, exit 1 |

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version | Frank + Claude Code |
| 2026-03-20 | Round 1 revision: separate layer responsibilities (not branch merging), fixed discovery via naming convention, af guide as delivery mechanism, resolved all open questions, failure modes | Claude Code |
| 2026-03-20 | Round 2 revision: USR=cross-project only, PRJ=project-specific SOPs, lifecycle-aware selection (Active only), rendering contract (full text via scan_documents), @root_option for guide_cmd, test migration noted | Claude Code |
