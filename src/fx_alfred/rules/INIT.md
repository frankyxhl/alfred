# Alfred Document System — Start Here

You are working in a project that uses the Alfred document system. Follow these steps to initialize.

## Step 1: Learn the language

Run `af read COR-0001` — defines all terms, type codes, and numbering conventions.

## Step 2: Know what exists

Run `af list` — shows all documents across PKG, USR, and PRJ layers.

Run `af read COR-0000` — index of all universal COR documents.

If a `*-0000-REF-*.md` file appears in the PRJ layer, read it too — that's the project-specific index.

## Step 3: Follow the rules

- **COR-1402**: Always declare which SOP you are following before starting a task.
- **COR-1400**: Every SOP does exactly one thing.
- **COR-1401**: All documents must be written in English.

## Step 4: Work on-demand

Do NOT read all SOPs upfront. Read them by ACID number only when needed.

Example: if you need to create a new SOP, run `af read COR-1000` and `af read COR-1001` at that point.

## Quick Reference

| Task | Read |
|------|------|
| Create a new SOP | COR-1000, COR-1001 |
| Create a decision record (ADR) | COR-1100, COR-1001 |
| Submit a change request | COR-1101, COR-1001 |
| Review and retrospective | COR-1200 |
| Update an existing document | COR-1300 |
| Deprecate a document | COR-1301 |
| Multi-agent direct review | COR-1600 |
| Multi-agent leader-mediated review | COR-1601 |
