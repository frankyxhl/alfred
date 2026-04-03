# SOP-2136: Update README

**Applies to:** FXA project
**Last updated:** 2026-03-21
**Last reviewed:** 2026-03-21
**Status:** Active

---

## What Is It?

The process for keeping README.md in sync with the current state of fx-alfred before each release.

## Why

README is the first thing users and AI agents see. An outdated README with missing commands, wrong version numbers, or stale examples creates confusion and wastes onboarding time.

---

## When to Use

- Before each release (called from FXA-2102 Release SOP)
- After adding new commands or features
- After changing existing command behavior

## When NOT to Use

- Patch releases with only bugfixes and no user-facing changes
- Internal document-only changes (no code release)

---

## Steps

1. **Check version** — Ensure version in README matches `pyproject.toml`

2. **Check Commands Reference** — Run `af --help` and compare against README's Commands Reference section. Add any missing commands, remove any deprecated ones.

3. **Check Features section** — Each major feature should have a subsection with a command example. Verify:
   - `af guide` — current behavior described?
   - `af plan` — all 3 modes documented?
   - `af validate` — current checks listed?
   - `af create` / `af update` — examples current?

4. **Check Quick Start** — Run the Quick Start commands on a clean project. Do they work?

5. **Check For AI Agents section** — Key SOPs table up to date? Any new COR SOPs to add?

6. **Check badges** — PyPI version badge shows latest? Tests badge green?

7. **Check Document Types table** — Any new types added?

8. **Commit** — If changes were made, commit README.md before proceeding with release.

## Examples

```bash
# Check version matches
grep "version" pyproject.toml          # should show current version
head -10 README.md                     # should reference same version

# Check commands
af --help                              # compare against README Commands Reference
```

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-21 | Initial version | Frank + Claude Code |
| 2026-03-21 | Added Examples section | Claude Code |
