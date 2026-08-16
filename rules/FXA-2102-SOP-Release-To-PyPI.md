# SOP-2102: Release To PyPI

**Applies to:** FXA project
**Last updated:** 2026-08-16
**Last reviewed:** 2026-08-16
**Status:** Active
**Task tags:** release, pypi
**Tags:** release, ship

---

## What Is It?

The process for releasing a new version of fx-alfred to PyPI via GitHub Actions and Trusted Publisher.

Since FXA-2328 the primary path is **automated**: merging a conventional-commit PR to `main` triggers `cd-release.yml` (semantic-release decides the version, tags, and creates the GitHub Release), which fires `publish.yml` (test → build → Trusted Publishing). The manual §Steps below are the fallback for when the automation is unavailable or a hand-crafted release is needed.

---

## Why

A defined release process ensures consistent, verifiable deployments. Using GitHub Actions with Trusted Publisher eliminates manual credential handling and guarantees that only CI-tested code reaches PyPI.

---

## When to Use

- A new version of fx-alfred is ready for public release
- All tests pass, lint is clean, and dual code review is complete
- The change has landed (or is about to land) on `main` — the automated path
  bumps the version itself; only the manual fallback pre-bumps (§Prerequisites)

---

## When NOT to Use

- Code is not yet reviewed -- complete FXA-2100 (Leader Mediated Development) first
- Tests or lint are failing

Note: bundled SOP document changes ship in the wheel, so `docs(...)` commits DO release (as a patch bump) under the automated path; commit as `chore`/`test`/`ci` when a change genuinely should not release.

---

## Prerequisites

Common to both paths:

- All tests pass (`.venv/bin/pytest -v`)
- Ruff lint clean (`.venv/bin/ruff check .`)
- Ruff format clean (`.venv/bin/ruff format --check .`) — if files need formatting, format + commit first
- Pyright clean (`.venv/bin/pyright src/`) — catches type errors that the publish CI also runs
- Dual code review passed (Codex + Gemini both ≥ 9/10)
- README updated per **Step 2** below (FXA-2136 Update README SOP)

Manual fallback only — do **NOT** do these under the automated path (a
pre-bumped version makes `cd-release.yml` compute `CURRENT == NEXT`, clear
the release, and skip the CHANGELOG promotion):

- Version bumped in `pyproject.toml`
- All changes committed and pushed to `main`

---

## Automated Path (Primary, FXA-2328)

1. Land the change on `main` through the normal PR flow with conventional
   commits (`feat` → minor, `fix`/`perf`/`docs` → patch; `chore`/`test`/`ci`
   → no release). Update CHANGELOG's `## Unreleased` section and the README
   "NEW in vX" line (FXA-2136) inside the PR — semantic-release does not
   write prose.
2. On merge, `cd-release.yml` first promotes CHANGELOG's `## Unreleased`
   notes to a `## v{version} (date)` section (skipped when Unreleased is
   empty), then runs semantic-release: bumps
   `pyproject.toml:project.version`, commits `chore(release): ...`, tags
   `v{version}`, creates the GitHub Release (via `SEMANTIC_RELEASE_PAT`).
   The promotion lands before the tag, so the built wheel ships correct
   version boundaries for `af changelog`.
3. The Release event triggers `publish.yml`: test gate → build → Trusted
   Publishing to PyPI.
4. Verify: `gh run list --workflow=publish.yml --limit 1` shows success and
   `pip index versions fx-alfred` (or the PyPI JSON API) lists the new
   version.

Requirements: the `SEMANTIC_RELEASE_PAT` repository secret must exist (repo
scope; the default `GITHUB_TOKEN` cannot fire `publish.yml`), and the PAT
owner must be able to push the release commit to `main`.

---

## Steps

Manual fallback — use when the automation is unavailable, a release needs
hand-crafted notes, or `cd-release.yml` is being bypassed deliberately.

1. **Verify readiness**
   ```bash
   .venv/bin/pytest -v
   .venv/bin/ruff check .
   .venv/bin/ruff format --check .    # if files need formatting, format + commit first
   .venv/bin/pyright src/             # must be equivalent to the CI gate (`pyright src/` in .github/workflows/publish.yml)
   .venv/bin/af --version             # confirm version matches
   ```

2. **Update README per FXA-2136** (skip only when the release contains zero user-facing changes)
   Run the FXA-2136 Update README SOP. At minimum:
   - Bump or add the "NEW in v\<VERSION\>" highlight line for any new feature/command
   - Add new commands to the Commands Reference / Document Management section
   - Confirm Quick Start commands still work
   - Update the Key SOPs table if a new COR SOP shipped
   - Commit the README change with the version bump (or as a separate commit on the release branch) **before** running Step 3
   - Verification: `grep -F "v<NEW_VERSION>" README.md` returns at least one match (confirms the new version is referenced) AND a manual scan finds no stale references to the prior version. This works regardless of whether the release commit lives on a branch or on `main`.

3. **Create GitHub Release** using the release notes template below
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

4. **Wait for CI** — GitHub Actions runs test → build → publish automatically

5. **Verify CI passed**
   ```bash
   gh run list --repo frankyxhl/alfred --limit 1
   ```

6. **Verify on PyPI**
   ```bash
   pipx install fx-alfred --force
   af --version  # should show new version
   ```

7. **Update CHG document** — mark status as Completed in the related CHG doc

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

| Date       | Change                                                                                                                                                                                                                                                                                            | By                  |
|------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------|
| 2026-03-17 | Initial version                                                                                                                                                                                                                                                                                   | Claude Code         |
| 2026-03-20 | FXA-2133: Add Why, When to Use, When NOT to Use sections (5W1H migration)                                                                                                                                                                                                                         | Claude Code         |
| 2026-03-21 | Added Examples section + release notes template                                                                                                                                                                                                                                                   | Claude Code         |
| 2026-04-18 | Add pyright to Prerequisites + Step 1 per CHG-FXA-2208 (post v1.6.0 publish incident).                                                                                                                                                                                                            | Frank + Claude Code |
| 2026-05-07 | FXA-2275: promote README check from Prerequisites to a numbered Step (new Step 2). Renumbered subsequent steps 3-7. Reason: README updates were silently skipped twice during v1.12.0 and v1.13.0 release work because the check sat in Prerequisites and was easy to miss when reading top-down. | Claude Code         |
| 2026-06-26 | Add task tags so COR-1202 can compose release plans from natural-language tasks.                                                                                                                                                                                                                  | Claude Code         |
| 2026-06-26 | Drop bare `publish` task tag — too generic; `publish docs` etc. wrongly routed to PyPI release (Codex review).                                                                                                                                                                                    | Claude Code         |
| 2026-08-16 | FXA-2328: automated path (cd-release.yml semantic-release → publish.yml) documented as primary; manual §Steps demoted to fallback; docs-commits-release note added (bundled SOPs ship in the wheel).                                                                                              | Claude Code         |
