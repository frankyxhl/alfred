import click

from fx_alfred.commands._helpers import scan_or_fail
from fx_alfred.context import root_option
from fx_alfred.core.source import SOURCE_LABELS


@click.command("list")
@root_option
@click.pass_context
def list_cmd(ctx: click.Context):
    """List all documents."""
    docs = scan_or_fail(ctx)

    if not docs:
        click.echo("No documents found.")
        return
    for doc in docs:
        label = SOURCE_LABELS.get(doc.source, "???")
        click.echo(
            f"{label:<3}  {doc.prefix}-{doc.acid}  {doc.type_code:<3}  {doc.title}"
        )
