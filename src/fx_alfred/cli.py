import click

from fx_alfred.context import root_option
from fx_alfred.lazy import LazyGroup

_EPILOG = """\
Document Naming Convention:

  PREFIX-ACID-TYPE-TITLE.md
  PREFIX: 3-letter project code (ALF, FXA, COR, USR)
  ACID:   4-digit unique identifier (e.g. 1001)
  TYPE:   SOP, ADR, PRP, REF, CHG, PLN, INC
  TITLE:  Human-readable title with dashes

Layer System:

  PKG: Bundled COR documents (read-only, included with fx-alfred)
  USR: Your personal documents in ~/.alfred/
  PRJ: Project documents in ./rules/

Quick Start:

  af create sop --prefix ALF --area 21 --title "My SOP"
  af list
  af read COR-1000
  af guide          Show workflow routing for current session
  af fmt            Format documents to canonical style
"""


@click.group(
    cls=LazyGroup,
    lazy_subcommands={
        "changelog": "fx_alfred.commands.changelog_cmd:changelog_cmd",
        "create": "fx_alfred.commands.create_cmd:create_cmd",
        "fmt": "fx_alfred.commands.fmt_cmd:fmt_cmd",
        "guide": "fx_alfred.commands.guide_cmd:guide_cmd",
        "index": "fx_alfred.commands.index_cmd:index_cmd",
        "list": "fx_alfred.commands.list_cmd:list_cmd",
        "plan": "fx_alfred.commands.plan_cmd:plan_cmd",
        "read": "fx_alfred.commands.read_cmd:read_cmd",
        "setup": "fx_alfred.commands.setup_cmd:setup_cmd",
        "search": "fx_alfred.commands.search_cmd:search_cmd",
        "status": "fx_alfred.commands.status_cmd:status_cmd",
        "update": "fx_alfred.commands.update_cmd:update_cmd",
        "validate": "fx_alfred.commands.validate_cmd:validate_cmd",
        "where": "fx_alfred.commands.where_cmd:where_cmd",
    },
    epilog=_EPILOG,
    context_settings={"max_content_width": 120},
)
@root_option
@click.version_option(package_name="fx-alfred")  # type: ignore[call-overload]
@click.pass_context
def cli(ctx: click.Context):
    """Alfred — Agent Runbook CLI."""
    ctx.ensure_object(dict)
