# SOP-2102: Release To PyPI

**Applies to:** FXA project
**Last updated:** 2026-03-17
**Last reviewed:** 2026-03-17
**Status:** Active

---

## What Is It?

The process for releasing a new version of fx-alfred to PyPI via GitHub Actions and Trusted Publisher.

---

## Why

A defined release process ensures consistent, verifiable deployments. Using GitHub Actions with Trusted Publisher eliminates manual credential handling and guarantees that only CI-tested code reaches PyPI.

---

## When to Use

- A new version of fx-alfred is ready for public release
- All tests pass, lint is clean, and dual code review is complete
- Version has been bumped and changes are pushed to `main`

---

## When NOT to Use

- Code is not yet reviewed -- complete FXA-2100 (Leader Mediated Development) first
- Tests or lint are failing
- Only document changes were made (no code release needed)

---

## Prerequisites

- All tests pass (`.venv/bin/pytest -v`)
- Ruff lint clean (`.venv/bin/ruff check .`)
- Ruff format clean (`.venv/bin/ruff format --check .`) — if files need formatting, format + commit first
- Dual code review passed (Codex + Gemini both ≥ 9/10)
- README up to date (FXA-2136 Update README SOP)
- Version bumped in `pyproject.toml`
- All changes committed and pushed to `main`

---

## Steps

1. **Verify readiness**
   ```bash
   .venv/bin/pytest -v
   .venv/bin/ruff check .
   .venv/bin/ruff format --check .    # if files need formatting, format + commit first
   .venv/bin/af --version             # confirm version matches
   ```

2. **Create GitHub Release** using the release notes template below
   ```bash
   gh release create v<VERSION> --title "v<VERSION>" --notes "$(cat <<'NOTES'
   <release notes from template>
   NOTES
   )"
   ```

### Release Notes Template

```markdown
## Release Notes

Released on YYYY-MM-DD.

### New Features

- `command` — Description ([ACID](link))

### Improvements

- `command` — What changed

### Bug Fixes

- Fixed X — Description

### Stats

- NNN tests (N new), all passing
- 0 breaking changes

### Install / Upgrade

\`\`\`bash
pip install fx-alfred==X.Y.Z       # install specific version
pipx install fx-alfred              # first install
pipx upgrade fx-alfred              # upgrade existing
\`\`\`
```

Categories (use only what applies):
- **New Features** — new commands, new capabilities
- **Improvements** — enhancements to existing features
- **Bug Fixes** — corrections
- **Docs** — documentation-only changes
- **Stats** — test count, breaking changes

3. **Wait for CI** — GitHub Actions runs test → build → publish automatically

4. **Verify CI passed**
   ```bash
   gh run list --repo frankyxhl/alfred --limit 1
   ```

5. **Verify on PyPI**
   ```bash
   pipx install fx-alfred --force
   af --version  # should show new version
   ```

6. **Update CHG document** — mark status as Completed in the related CHG doc

---

## Rollback

If the release is broken:
1. Yank the version on PyPI: `https://pypi.org/manage/project/fx-alfred/release/<VERSION>/`
2. Fix the issue, bump to next patch version, re-release

## Examples

```bash
# Release v1.0.0
.venv/bin/pytest -v                           # verify tests
.venv/bin/ruff check .                        # verify lint
# bump version in pyproject.toml
git add pyproject.toml src/fx_alfred/CHANGELOG.md
git commit -m "chore: bump version to 1.0.0"
git push
gh release create v1.0.0 --title "v1.0.0" --notes "..."
gh run watch <run-id> --compact               # watch CI
pipx upgrade fx-alfred                        # verify on PyPI
```

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-17 | Initial version | Claude Code |
| 2026-03-20 | FXA-2133: Add Why, When to Use, When NOT to Use sections (5W1H migration) | Claude Code |
| 2026-03-21 | Added Examples section + release notes template | Claude Code |
