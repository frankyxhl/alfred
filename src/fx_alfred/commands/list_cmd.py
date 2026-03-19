import json

import click

from fx_alfred.commands._helpers import scan_or_fail
from fx_alfred.context import root_option
from fx_alfred.core.source import SOURCE_LABELS


@click.command("list")
@root_option
@click.option("--type", "type_code", default=None, help="Filter by document type code.")
@click.option("--prefix", default=None, help="Filter by project prefix.")
@click.option(
    "--source", "source_filter", default=None, help="Filter by layer: pkg, usr, prj."
)
@click.option("--json", "json_output", is_flag=True, help="Output as JSON.")
@click.pass_context
def list_cmd(
    ctx: click.Context,
    type_code: str | None,
    prefix: str | None,
    source_filter: str | None,
    json_output: bool,
):
    """List all documents."""
    docs = scan_or_fail(ctx)

    # Apply filters (AND logic)
    if type_code is not None:
        docs = [d for d in docs if d.type_code.upper() == type_code.upper()]
    if prefix is not None:
        docs = [d for d in docs if d.prefix.upper() == prefix.upper()]
    if source_filter is not None:
        docs = [d for d in docs if d.source.lower() == source_filter.lower()]

    if not docs:
        if json_output:
            click.echo("[]")
        else:
            click.echo("No documents found.")
        return

    if json_output:
        output = [
            {
                "prefix": doc.prefix,
                "acid": doc.acid,
                "type_code": doc.type_code,
                "title": doc.title,
                "source": doc.source,
                "directory": doc.directory,
            }
            for doc in docs
        ]
        click.echo(json.dumps(output))
    else:
        for doc in docs:
            label = SOURCE_LABELS.get(doc.source, "???")
            click.echo(
                f"{label:<3}  {doc.prefix}-{doc.acid}  {doc.type_code:<3}  {doc.title}"
            )
