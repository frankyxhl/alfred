# Alfred Quick Start Guide

Welcome to Alfred - your document management system!

## Getting Started

1. **Create a document**
   ```bash
   af create sop --prefix MYPRJ --acid 1001 --title "My First SOP"
   ```

2. **List all documents**
   ```bash
   af list
   ```

3. **Read a document**
   ```bash
   af read 1001
   ```

4. **Show status**
   ```bash
   af status
   ```

5. **Regenerate indexes**
   ```bash
   af index
   ```

## Document Naming Convention

Documents follow the pattern: `PREFIX-ACID-TYPE-TITLE.md`

- **PREFIX**: 3-letter project code (e.g., MYPRJ → MYP)
- **ACID**: 4-digit unique identifier (e.g., 1001)
- **TYPE**: Document type (SOP, ADR, PRP)
- **TITLE**: Human-readable title with dashes

## Layer System

- **PKG**: Bundled COR documents (read-only)
- **USR**: Your personal documents in `~/.alfred/`
- **PRJ**: Project documents in `./rules/`

## Need Help?

Run `af --help` to see all available commands.
