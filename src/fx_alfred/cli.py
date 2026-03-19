import click

from fx_alfred.context import root_option
from fx_alfred.lazy import LazyGroup


@click.group(
    cls=LazyGroup,
    lazy_subcommands={
        "changelog": "fx_alfred.commands.changelog_cmd:changelog_cmd",
        "create": "fx_alfred.commands.create_cmd:create_cmd",
        "guide": "fx_alfred.commands.guide_cmd:guide_cmd",
        "index": "fx_alfred.commands.index_cmd:index_cmd",
        "list": "fx_alfred.commands.list_cmd:list_cmd",
        "read": "fx_alfred.commands.read_cmd:read_cmd",
        "search": "fx_alfred.commands.search_cmd:search_cmd",
        "status": "fx_alfred.commands.status_cmd:status_cmd",
        "update": "fx_alfred.commands.update_cmd:update_cmd",
        "validate": "fx_alfred.commands.validate_cmd:validate_cmd",
    },
)
@root_option
@click.version_option(package_name="fx-alfred")  # type: ignore[call-overload]
@click.pass_context
def cli(ctx: click.Context):
    """Alfred document system CLI."""
    ctx.ensure_object(dict)
