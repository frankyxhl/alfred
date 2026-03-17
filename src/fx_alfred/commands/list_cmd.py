import click

from fx_alfred.context import get_root
from fx_alfred.core.scanner import LayerValidationError, scan_documents

SOURCE_LABELS = {"pkg": "PKG", "usr": "USR", "prj": "PRJ"}


@click.command("list")
@click.pass_context
def list_cmd(ctx: click.Context):
    """List all documents."""
    root = get_root(ctx)
    try:
        docs = scan_documents(root)
    except LayerValidationError as e:
        raise click.ClickException(str(e)) from e

    if not docs:
        click.echo("No documents found.")
        return
    for doc in docs:
        label = SOURCE_LABELS.get(doc.source, "???")
        click.echo(
            f"{label:<3}  {doc.prefix}-{doc.acid}  {doc.type_code:<3}  {doc.title}"
        )
