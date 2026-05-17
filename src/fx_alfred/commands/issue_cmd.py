"""af issue — issue body utilities (FXA-2292)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

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


@click.group(name="issue")
def issue_cmd() -> None:
    """Issue body utilities (lint, ...)."""


@issue_cmd.command(name="lint")
@click.argument(
    "body_file",
    type=click.Path(dir_okay=False, allow_dash=True),
)
@click.option("--json", "as_json", is_flag=True, help="Output violations as JSON.")
def lint_cmd(body_file: str, as_json: bool) -> None:
    """Lint a GitHub issue body for known anti-patterns.

    Phase 1: detects TBD-after-PR-review phrases (see #168 §Hard Cap Trigger B).
    Reads from BODY_FILE or stdin if BODY_FILE is `-`.
    Exit 0 on PASS, 1 on FAIL.
    """
    if body_file == "-":
        text = sys.stdin.read()
    else:
        path = Path(body_file)
        if not path.exists():
            raise click.FileError(body_file, hint="No such file")
        text = path.read_text(encoding="utf-8")

    violations = _check_tbd_phrases(text)

    if as_json:
        click.echo(
            json.dumps(
                {
                    "result": "PASS" if not violations else "FAIL",
                    "violation_count": len(violations),
                    "violations": violations,
                },
                indent=2,
            )
        )
    else:
        for v in violations:
            click.echo(f'✗ TBD-phrase detected at line {v["line"]}: "{v["match"]}"')
        click.echo()
        if violations:
            click.echo(f"Lint result: FAIL ({len(violations)} violations)")
        else:
            click.echo("Lint result: PASS (0 violations)")

    sys.exit(1 if violations else 0)
