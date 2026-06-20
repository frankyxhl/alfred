"""Click command for ``af log``."""

from __future__ import annotations

from json.encoder import encode_basestring_ascii

import click

from fx_alfred.context import get_root, has_explicit_root, root_option
from fx_alfred.core.activity_log import (
    ArchiveError,
    append_record,
    archive_directory,
    compose_record,
    resolve_log_dir,
    validate_record,
)


@click.command("log")
@root_option
@click.argument("summary")
@click.option("--event", default="note", help="Activity event type")
@click.option("--agent", default="other", help="Agent family")
@click.option("--agent-name", default=None, help="Concrete agent name")
@click.option("--agent-version", default=None, help="Concrete agent version")
@click.option("--session-id", default=None, help="Agent session identifier")
@click.option("--ref", "refs", multiple=True, help="Related SOP/PRP/CHG id")
@click.option("--file", "files", multiple=True, help="Related file path")
@click.pass_context
def log_cmd(
    ctx: click.Context,
    summary: str,
    event: str,
    agent: str,
    agent_name: str,
    agent_version: str | None,
    session_id: str | None,
    refs: tuple[str, ...],
    files: tuple[str, ...],
) -> None:
    """Append a manual activity-log row."""

    record = compose_record(
        summary=summary,
        event=event,
        agent=agent,
        agent_name=agent_name,
        agent_version=agent_version,
        session_id=session_id,
        refs=refs,
        files=files,
        command="log",
        usage_kind="manual_log",
    )
    violations = validate_record(record)
    if violations:
        message = "; ".join(f"{v.field}: {v.reason}" for v in violations)
        raise click.ClickException(message)
    log_dir = resolve_log_dir(get_root(ctx), explicit_root=has_explicit_root(ctx))
    try:
        archive_directory(log_dir)
    except (ArchiveError, OSError) as exc:
        detail = encode_basestring_ascii(str(exc))
        click.echo(
            f"af log: lazy archival failed {detail}; Recover: af log-archive --force",
            err=True,
        )
    path = append_record(record, log_dir=log_dir)
    click.echo(str(path))
