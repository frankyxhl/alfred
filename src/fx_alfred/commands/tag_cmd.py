"""af tag command group — manage starred tags (FXA-2273)."""

from __future__ import annotations

import json

import click

from fx_alfred.core.preferences import (
    PreferencesError,
    add_starred_tag,
    get_starred_tags,
    remove_starred_tag,
)


SCHEMA_VERSION = "1"


def _normalise(name: str) -> str:
    cleaned = name.strip().lower()
    if not cleaned:
        raise click.ClickException("tag name cannot be empty")
    return cleaned


@click.group("tag")
def tag_cmd() -> None:
    """Manage starred tags (per-user, persisted in ~/.alfred/preferences.yaml)."""


@tag_cmd.command("star")
@click.argument("name")
def tag_star_cmd(name: str) -> None:
    """Mark <name> as a starred tag."""
    norm = _normalise(name)
    try:
        added, _ = add_starred_tag(norm)
    except PreferencesError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"{'starred' if added else 'already starred'}: {norm}")


@tag_cmd.command("unstar")
@click.argument("name")
def tag_unstar_cmd(name: str) -> None:
    """Remove <name> from starred tags."""
    norm = _normalise(name)
    try:
        removed, _ = remove_starred_tag(norm)
    except PreferencesError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"{'unstarred' if removed else 'not starred'}: {norm}")


@tag_cmd.command("list")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON object.")
def tag_list_cmd(json_output: bool) -> None:
    """List the user's starred tags (sorted)."""
    try:
        starred = get_starred_tags()
    except PreferencesError as exc:
        raise click.ClickException(str(exc)) from exc

    if json_output:
        click.echo(
            json.dumps({"schema_version": SCHEMA_VERSION, "starred_tags": starred})
        )
        return

    for tag in starred:
        click.echo(tag)
