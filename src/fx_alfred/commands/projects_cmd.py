"""FXA-2330: `af projects` — list/manage the Project SOP Registry."""

import click

from fx_alfred.commands._helpers import emit_json
from fx_alfred.core.registry import (
    load_registry,
    prune_missing_roots,
    registry_path,
    save_registry,
    today_str,
)


@click.command("projects")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON array.")
@click.option(
    "--prune",
    is_flag=True,
    help="Remove entries whose root directory no longer exists.",
)
def projects_cmd(output_json: bool, prune: bool):
    """List the machine-wide Project SOP Registry (USR-9000)."""
    path = registry_path()
    try:
        entries = load_registry(path)
    except (OSError, UnicodeDecodeError) as e:
        # load_registry intentionally propagates real read failures —
        # including invalid UTF-8 (a ValueError, not an OSError) — and the
        # CLI surface converts them instead of leaking a traceback;
        # never treat an unreadable registry as empty.
        raise click.ClickException(f"Cannot read project registry {path}: {e}") from e

    if prune:
        entries, removed = prune_missing_roots(entries)
        if removed:
            try:
                save_registry(path, entries, today=today_str())
            except Exception as e:
                raise click.ClickException(f"Project registry prune failed: {e}") from e
        if not output_json:
            for e in removed:
                click.echo(f"Pruned {e.prefix} {e.root} (root no longer exists)")

    if output_json:
        emit_json(
            [
                {
                    "prefix": e.prefix,
                    "root": e.root,
                    "doc_count": e.doc_count,
                    "last_seen": e.last_seen,
                }
                for e in entries
            ]
        )
        return

    if not entries:
        click.echo(
            "No projects registered yet — run `af register` in a project "
            "(or just `af list` there; the registry self-maintains)."
        )
        return

    prefix_w = max(len(e.prefix) for e in entries)
    root_w = max(len(e.root) for e in entries)
    click.echo(f"{'PRJ':<{prefix_w}}  {'Root':<{root_w}}  Docs  Last Seen")
    for e in entries:
        click.echo(
            f"{e.prefix:<{prefix_w}}  {e.root:<{root_w}}  {e.doc_count:>4}  {e.last_seen}"
        )
