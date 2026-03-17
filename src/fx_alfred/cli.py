from pathlib import Path

import click

from fx_alfred.commands.create_cmd import create_cmd
from fx_alfred.commands.guide_cmd import guide_cmd
from fx_alfred.commands.index_cmd import index_cmd
from fx_alfred.commands.list_cmd import list_cmd
from fx_alfred.commands.read_cmd import read_cmd
from fx_alfred.commands.status_cmd import status_cmd


@click.group()
@click.option(
    "--root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),  # type: ignore[type-var]
    default=".",
    help="Project root directory (default: current directory)",
)
@click.version_option(package_name="fx-alfred")  # type: ignore[call-overload]
@click.pass_context
def cli(ctx: click.Context, root: Path):
    """Alfred document system CLI."""
    ctx.ensure_object(dict)
    ctx.obj["root"] = root.resolve()


cli.add_command(create_cmd)
cli.add_command(guide_cmd)
cli.add_command(index_cmd)
cli.add_command(list_cmd)
cli.add_command(read_cmd)
cli.add_command(status_cmd)
