# alfred

A minimal, self-consistent document management system built on PDCA + Johnny Decimal.

## Quick Start

```bash
pip install fx-alfred
cd my-project
af guide
```

## Layer System

Alfred uses a 3-layer document model:

| Layer | Location | Description |
|-------|----------|-------------|
| **PKG** | Bundled with fx-alfred | COR reference documents — read-only, always available |
| **USR** | `~/.alfred/` | Your personal documents, shared across all projects |
| **PRJ** | `./rules/` | Project-specific documents |

## For LLMs: How This System Works

### 1. Read these files first

```bash
af read COR-0001    # glossary — all terms and abbreviations
af list             # index of all available documents across all layers
```

### 2. File naming format

```
<PREFIX>-<ACID>-<TYP>-<Title>.md
```

- **PREFIX**: `COR` (universal) or 3-letter project code (`ALF`, `BLA`, `CLR`)
- **ACID**: 4-digit Johnny Decimal number (Area + Category + Item)
- **TYP**: 3-letter type code (SOP, ADR, CHG, INC, PLN, PRP, REF)

### 3. PDCA areas (meta layer)

| Area | Phase | What it covers |
|------|-------|----------------|
| 10xx | Do | Create and read documents |
| 11xx | Plan | Decision records and change requests |
| 12xx | Check | Session retrospective |
| 13xx | Act | Update, deprecate, maintain index |
| 14xx | Constraint | Universal rules (atomicity, language policy) |
| 15xx | Development | TDD, GitHub issues, git branch naming |

### 4. Key rules

- **COR-1400**: Every SOP does exactly one thing (atomic)
- **COR-1401**: All documents in English
- **COR-1402**: Always declare which SOP is being followed before starting a task

### 5. To create a new document

Follow `COR-1001` (Create Document) for naming and numbering, then the type-specific SOP.

Supported types: `sop`, `adr`, `chg`, `inc`, `pln`, `prp`, `ref`

```bash
# Specify an exact ACID
af create sop --prefix ALF --acid 2100 --title "My SOP"

# Auto-assign the next available ACID in an area
af create adr --prefix ALF --area 21 --title "Use PostgreSQL"

# Write to user layer (~/.alfred/)
af create sop --prefix USR --acid 3000 --title "My Rule" --layer user

# Write to a subdirectory of the user layer
af create sop --prefix USR --acid 3000 --title "My Rule" --layer user --subdir my-project
```

The index is updated automatically after each create (project layer only). To update it manually, run `af index`.

## Installing into another project

```bash
pip install fx-alfred
af guide
```

Then create project documents with `af create` and view them with `af list`.

## Version control

This project uses git.

```bash
git log             # view history
git status          # current changes
git push            # push to GitHub
```
