"""Click command for ``af log-archive``."""

from __future__ import annotations

from pathlib import Path

import click

from fx_alfred.context import get_root, has_explicit_root, root_option
from fx_alfred.core.activity_log import ArchiveError, archive_directory, resolve_log_dir


@click.command("log-archive")
@root_option
@click.option("--force", is_flag=True, help="Overwrite corrupt archive.zip")
@click.argument(
    "path",
    required=False,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.pass_context
def log_archive_cmd(ctx: click.Context, force: bool, path: Path | None) -> None:
    """Archive closed-day activity logs into archive.zip."""

    try:
        log_dir = path or resolve_log_dir(
            get_root(ctx), explicit_root=has_explicit_root(ctx)
        )
        result = archive_directory(
            log_dir,
            force=force,
        )
    except ArchiveError as exc:
        err = click.ClickException(str(exc))
        err.exit_code = 5
        raise err from exc
    click.echo(result.message or f"archived {len(result.archived_files)} file(s)")
