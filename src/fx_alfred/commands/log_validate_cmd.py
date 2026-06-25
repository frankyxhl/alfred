"""Click command for ``af log-validate``."""

from __future__ import annotations

import json
from pathlib import Path
from zipfile import BadZipFile

import click

from fx_alfred.commands._helpers import ExitCodeError
from fx_alfred.context import get_root, has_explicit_root, root_option
from fx_alfred.core.activity_log import (
    ActivityLogLineError,
    iter_records,
    log_file_for_dir,
    resolve_log_dir,
    validate_record,
)


def _default_targets(log_dir: Path) -> list[Path]:
    base = log_file_for_dir(log_dir)
    parts = sorted(log_dir.glob(f"{base.stem}.part*.jsonl")) if log_dir.exists() else []
    return [base, *parts]


@click.command("log-validate")
@root_option
@click.argument(
    "path",
    required=False,
    type=click.Path(exists=True, path_type=Path),
)
@click.pass_context
def log_validate_cmd(ctx: click.Context, path: Path | None) -> None:
    """Validate loose or archived activity-log rows."""

    log_dir = resolve_log_dir(get_root(ctx), explicit_root=has_explicit_root(ctx))
    targets = [path] if path is not None else _default_targets(log_dir)
    violation_count = 0
    try:
        for target in targets:
            for source, lineno, record in iter_records(target):
                for violation in validate_record(record):
                    violation_count += 1
                    click.echo(
                        f"{source}:{lineno}: {violation.field}: {violation.reason}"
                    )
    except ActivityLogLineError as exc:
        raise click.ClickException(
            f"{exc.source}:{exc.lineno}: record: {exc.reason}"
        ) from exc
    except BadZipFile as exc:
        raise ExitCodeError(f"corrupt archive.zip: {exc}", 5) from exc
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"invalid JSONL: {exc}") from exc

    if violation_count:
        raise click.ClickException(f"{violation_count} activity-log issue(s) found")
    click.echo("activity log ok")
