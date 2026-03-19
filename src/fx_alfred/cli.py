import click

from fx_alfred.commands.changelog_cmd import changelog_cmd
from fx_alfred.commands.create_cmd import create_cmd
from fx_alfred.commands.guide_cmd import guide_cmd
from fx_alfred.commands.index_cmd import index_cmd
from fx_alfred.commands.list_cmd import list_cmd
from fx_alfred.commands.read_cmd import read_cmd
from fx_alfred.commands.status_cmd import status_cmd
from fx_alfred.commands.update_cmd import update_cmd
from fx_alfred.context import root_option


@click.group()
@root_option
@click.version_option(package_name="fx-alfred")  # type: ignore[call-overload]
@click.pass_context
def cli(ctx: click.Context):
    """Alfred document system CLI."""
    ctx.ensure_object(dict)


cli.add_command(changelog_cmd)
cli.add_command(create_cmd)
cli.add_command(guide_cmd)
cli.add_command(index_cmd)
cli.add_command(list_cmd)
cli.add_command(read_cmd)
cli.add_command(status_cmd)
cli.add_command(update_cmd)
