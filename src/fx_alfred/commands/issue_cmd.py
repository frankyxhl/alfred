"""af issue — issue body utilities (FXA-2292)."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from fx_alfred.commands._helpers import emit_json
from fx_alfred.context import root_option
from fx_alfred.core.parser import extract_section, iter_lines_with_fence_state

# Phase 1: TBD-phrase rule (same list as COR-1506 §Hard Cap Trigger B).
# Order is significant — when two phrases appear on the same line, the one
# earlier in this list is reported first.
TBD_PHRASES = [
    "TBD after PR review",
    "TBD after option selection",
    "implementer chooses",
    "exact spec to be drafted after reviewer pick",
    "to be decided in review",
]

# Blueprint structural check (issue #219). The required-section contract is the
# repo's own Iterwheel Blueprint template — NOT hardcoded here, because af ships
# to many repos. COR-1501 names this file as the source of truth.
BLUEPRINT_REL = Path(".github") / "ISSUE_TEMPLATE" / "blueprint.md"
ACCEPTANCE_CRITERIA = "Acceptance Criteria"
COR_1501_POINTER = (
    "See COR-1501 (Create GitHub Issue) for the required blueprint structure."
)


def _check_tbd_phrases(text: str) -> list[dict]:
    """Return one violation dict per TBD-phrase occurrence.

    Case-insensitive substring match; line numbers are 1-based.
    Each (phrase, line) pair contributes at most one violation
    (duplicate occurrences of the same phrase on the same line are
    collapsed). Violations are sorted by line number ascending;
    ties preserve the order of TBD_PHRASES (stable sort).
    """
    violations: list[dict] = []
    lower_lines = [line.lower() for line in text.splitlines()]
    for phrase in TBD_PHRASES:
        needle = phrase.lower()
        for line_no, line in enumerate(lower_lines, start=1):
            if needle in line:
                violations.append(
                    {
                        "rule": "tbd-phrase",
                        "line": line_no,
                        "match": phrase,
                    }
                )
    # Stable sort by line; ties keep declaration order of TBD_PHRASES.
    violations.sort(key=lambda v: v["line"])
    return violations


def _h2_headings(text: str) -> list[str]:
    """Non-fenced, column-0 ``## `` heading titles, in order (fence-aware).

    The column-0 requirement matches ``extract_section``'s ``^##`` anchor, so a
    heading counted "present" here is always extractable there — an indented
    ``  ## Acceptance Criteria`` is treated as not-a-section by both.
    """
    out: list[str] = []
    for line, fenced in iter_lines_with_fence_state(text):
        if fenced:
            continue
        if line.startswith("## "):
            out.append(line[3:].strip())
    return out


def _find_blueprint(start: Path) -> Path | None:
    """Nearest ``.github/ISSUE_TEMPLATE/blueprint.md`` at ``start`` or an
    ancestor, bounded to the current repository.

    Walking up (rather than checking only ``start``) means the check works
    from a repo subdirectory and in repos that are not Alfred projects, where
    ``get_root`` falls back to the cwd and the template lives further up
    (PR #223 codex P2 #1). The walk stops at the repository boundary — the
    first ancestor holding ``.git`` (a dir for normal checkouts, a file for
    submodules/worktrees) — so a child repo without its own template never
    picks up a parent repo's blueprint (codex P2 #2). The repo root's own
    template is still considered before the walk stops there.
    """
    for directory in (start, *start.parents):
        candidate = directory / BLUEPRINT_REL
        if candidate.is_file():
            return candidate
        if (directory / ".git").exists():
            break  # repository boundary — do not cross into a parent repo
    return None


def _check_blueprint_structure(text: str, root: Path) -> list[dict]:
    """Check the body against the repo's blueprint template.

    Required sections are the template's ``## `` headings minus any ending in
    ``(optional)``. Reports a ``missing-section`` violation per absent required
    section, and a ``no-acceptance-criteria`` violation when the Acceptance
    Criteria section exists but has no ``- [ ]`` checkbox. When no template is
    found at ``root`` or any ancestor the check is skipped (no violations).
    """
    template_path = _find_blueprint(root)
    if template_path is None:
        return []

    required = [
        h
        for h in _h2_headings(template_path.read_text(encoding="utf-8"))
        if not h.lower().endswith("(optional)")
    ]
    present = set(_h2_headings(text))

    violations: list[dict] = []
    for heading in required:
        if heading not in present:
            violations.append({"rule": "missing-section", "line": 0, "match": heading})

    if ACCEPTANCE_CRITERIA in present:
        section = extract_section(text, ACCEPTANCE_CRITERIA) or ""
        # ponytail: only "- [ ]" counts as a checkbox; mirrors the blueprint
        # bot's own check. Widen to "* [ ]"/indented forms only if a real
        # issue body trips on it.
        has_checkbox = any(
            not fenced and line.strip().startswith("- [ ]")
            for line, fenced in iter_lines_with_fence_state(section)
        )
        if not has_checkbox:
            violations.append(
                {
                    "rule": "no-acceptance-criteria",
                    "line": 0,
                    "match": ACCEPTANCE_CRITERIA,
                }
            )
    return violations


def _render(v: dict) -> str:
    """One-line text rendering for a violation dict."""
    rule = v["rule"]
    if rule == "tbd-phrase":
        return f'✗ TBD-phrase detected at line {v["line"]}: "{v["match"]}"'
    if rule == "missing-section":
        return f"✗ Missing required section: ## {v['match']}"
    if rule == "no-acceptance-criteria":
        return f'✗ Section "## {v["match"]}" has no checkbox (- [ ]) item'
    raise AssertionError(f"unknown violation rule: {rule}")


@click.group(name="issue")
def issue_cmd() -> None:
    """Issue body utilities (lint, ...)."""


@issue_cmd.command(name="lint")
@click.argument(
    "body_file",
    type=click.Path(dir_okay=False, allow_dash=True),
)
@click.option("--json", "as_json", is_flag=True, help="Output violations as JSON.")
@root_option
@click.pass_context
def lint_cmd(ctx: click.Context, body_file: str, as_json: bool) -> None:
    """Lint a GitHub issue body for known anti-patterns.

    Checks (1) TBD-after-PR-review phrases and (2) the COR-1501 blueprint
    structure — required ``## `` sections and a checkbox under
    ``## Acceptance Criteria`` — derived from the repo's own
    ``.github/ISSUE_TEMPLATE/blueprint.md``. The template is searched from the
    invoking repo: explicit ``--root`` if given, else the body file's own
    directory (cwd for stdin), walking up to the repository boundary. The
    structural check is skipped when no such template is found.

    Reads from BODY_FILE or stdin if BODY_FILE is `-`.
    Exit 0 on PASS, 1 on FAIL.

    Violation ordering: blueprint-structure violations (``missing-section``,
    ``no-acceptance-criteria``; ``line: 0``) come first, then TBD-phrases by
    line. The COR-1501 pointer is printed only when a structural violation is
    present, so TBD-only output is identical to the pre-#219 behavior.
    """
    if body_file == "-":
        text = sys.stdin.read()
    else:
        path = Path(body_file)
        if not path.exists():
            raise click.FileError(body_file, hint="No such file")
        text = path.read_text(encoding="utf-8")

    # Anchor the template search to the INVOKING repo, not the Alfred-doc root:
    # discover_root walks past a child repo's .git to find a parent's rules/,
    # which would borrow the parent's blueprint (codex P2 #3). Explicit --root
    # wins; otherwise start at the body's own directory (cwd for stdin).
    explicit_root = (ctx.find_root().obj or {}).get("root")
    if explicit_root is not None:
        search_start = Path(explicit_root)
    elif body_file != "-":
        search_start = Path(body_file).resolve().parent
    else:
        search_start = Path.cwd()

    # Structural violations first (overall shape), then TBD by line.
    structural = _check_blueprint_structure(text, search_start)
    violations = structural + _check_tbd_phrases(text)

    if as_json:
        emit_json(
            {
                "result": "PASS" if not violations else "FAIL",
                "violation_count": len(violations),
                "violations": violations,
            }
        )
    else:
        for v in violations:
            click.echo(_render(v))
        click.echo()
        if violations:
            click.echo(f"Lint result: FAIL ({len(violations)} violations)")
            # Pointer only for structural fails — keeps TBD-only output
            # byte-for-byte identical to pre-#219 behavior (AC#4).
            if structural:
                click.echo(COR_1501_POINTER)
        else:
            click.echo("Lint result: PASS (0 violations)")

    ctx.exit(1 if violations else 0)
