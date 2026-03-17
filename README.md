# alfred

A minimal, self-consistent document management system built on PDCA + Johnny Decimal.

## Quick Start

```bash
git clone git@github.com:frankyxhl/alfred.git
cd alfred
```

## Structure

```
.alfred/          ← COR (Core) meta-layer documents (universal, apply to all projects)
docs/             ← ALF (Alfred) business-layer documents (project-specific)
```

## For LLMs: How This System Works

### 1. Read these files first

- `.alfred/COR-0001-REF-Glossary.md` — all terms and abbreviations
- `.alfred/COR-0000-REF-Document-Index.md` — index of all meta-layer documents
- `docs/ALF-0000-REF-Document-Index.md` — index of all business-layer documents

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

Supported types: `adr`, `chg`, `inc`, `pln`, `prp`, `ref`, `sop`

```bash
# Specify an exact ACID
af create sop --prefix ALF --acid 2100 --title "My SOP"

# Auto-assign the next available ACID in an area
af create adr --prefix ALF --area 21 --title "Use PostgreSQL"
```

The index is updated automatically after each create. To update it manually, run `af index`.

## Installing into another project

Copy `.alfred/` into the target project:

```bash
cp -r .alfred/ /path/to/other-project/.alfred/
```

The target project keeps its own `docs/` for business-layer documents.

## Version control

This project uses [jj](https://martinvonz.github.io/jj/) (Jujutsu) colocated with git.

```bash
jj log              # view history
jj status           # current changes
jj git push         # push to GitHub
```
