# Alfred Quick Start Guide

Welcome to Alfred - your document management system!

## Getting Started

1. **Create a document**
   ```bash
   af create sop --prefix ALF --acid 1001 --title "My First SOP"
   ```

   To auto-assign the next available ACID in an area:
   ```bash
   af create sop --prefix ALF --area 21 --title "My SOP"
   ```

   To write to your personal user layer (`~/.alfred/`):
   ```bash
   af create sop --prefix USR --acid 3000 --title "My Rule" --layer user
   ```

   To write to a subdirectory of the user layer:
   ```bash
   af create sop --prefix USR --acid 3000 --title "My Rule" --layer user --subdir my-project
   ```

2. **List all documents**
   ```bash
   af list
   ```

3. **Read a document**
   ```bash
   af read COR-1001
   ```

4. **Show status**
   ```bash
   af status
   ```

5. **Regenerate indexes** (project layer only)
   ```bash
   af index
   ```

## Document Naming Convention

Documents follow the pattern: `PREFIX-ACID-TYPE-TITLE.md`

- **PREFIX**: 3-letter project code (e.g., `ALF`, `TST`, `USR`)
- **ACID**: 4-digit unique identifier (e.g., 1001)
- **TYPE**: Document type (SOP, ADR, CHG, INC, PLN, PRP, REF)
- **TITLE**: Human-readable title with dashes

### Supported create types

`sop`, `adr`, `prp`, `ref`, `chg`, `pln`, `inc`

**Note:** Index files (`*-0000-REF-*`) are generated via `af index`, not `af create`.

## Layer System

- **PKG**: Bundled COR documents (read-only, included with fx-alfred)
- **USR**: Your personal documents in `~/.alfred/`
- **PRJ**: Project documents in `./rules/`

## Need Help?

Run `af --help` to see all available commands.
