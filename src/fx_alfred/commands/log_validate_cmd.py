"""Click command for ``af log-validate``."""

from __future__ import annotations

import json
from pathlib import Path
from zipfile import BadZipFile

import click

from fx_alfred.context import get_root, root_option
from fx_alfred.core.activity_log import (
    ActivityLogLineError,
    iter_records,
    resolve_log_dir,
    validate_record,
)


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

    target = path or resolve_log_dir(get_root(ctx))
    violation_count = 0
    try:
        for source, lineno, record in iter_records(target):
            for violation in validate_record(record):
                violation_count += 1
                click.echo(f"{source}:{lineno}: {violation.field}: {violation.reason}")
    except ActivityLogLineError as exc:
        raise click.ClickException(
            f"{exc.source}:{exc.lineno}: record: {exc.reason}"
        ) from exc
    except BadZipFile as exc:
        err = click.ClickException(f"corrupt archive.zip: {exc}")
        err.exit_code = 5
        raise err from exc
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"invalid JSONL: {exc}") from exc

    if violation_count:
        raise click.ClickException(f"{violation_count} activity-log issue(s) found")
    click.echo("activity log ok")
