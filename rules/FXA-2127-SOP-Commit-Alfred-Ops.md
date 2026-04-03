# SOP-2127: Commit Alfred Ops

**Applies to:** FXA project
**Last updated:** 2026-03-20
**Last reviewed:** 2026-03-20
**Status:** Deprecated

---

## What Is It?

The process for committing document changes in `alfred_ops/`. This repo is local-only (no remote), so commit is the final persistence step.

---

## Why

Since `alfred_ops` has no remote, a local commit is the only persistence mechanism. Following a consistent commit process ensures document changes are saved, validated, and free of known side-effect artifacts (e.g., ALF-0000 duplicates).

---

## When to Use

- At the end of a session that created or modified documents in `alfred_ops/rules/`
- After PRP/CHG/ADR/PLN status changes
- After document migrations

## When NOT to Use

- Code changes in `fx_alfred/` — those have their own git workflow + push + release (FXA-2102)

---

## Steps

1. **Check status**
   ```bash
   cd /Users/frank/Projects/alfred/alfred_ops && git status
   ```

2. **Delete duplicate ALF-0000 if present** (known `af index` side effect)
   ```bash
   rm -f rules/ALF-0000-REF-Document-Index.md
   ```

3. **Stage and commit**
   ```bash
   git add rules/
   git commit -m "docs: <summary of changes>"
   ```

4. **Verify**
   ```bash
   af validate --root /Users/frank/Projects/alfred/alfred_ops
   ```
   Expected: 0 issues.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-20 | Initial version | Frank + Claude Code |
| 2026-03-20 | FXA-2133: Add Why section (5W1H migration) | Claude Code |
| 2026-04-03 | Deprecated: alfred_ops merged into fx_alfred (FXA-2186) | Claude Code |
