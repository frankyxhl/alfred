import click

from fx_alfred.context import get_root
from fx_alfred.core.scanner import LayerValidationError, scan_documents


@click.command("read")
@click.argument("acid")
@click.pass_context
def read_cmd(ctx: click.Context, acid: str):
    """Read a document by ACID number."""
    root = get_root(ctx)
    try:
        docs = scan_documents(root)
    except LayerValidationError as e:
        raise click.ClickException(str(e)) from e

    for doc in docs:
        if doc.acid == acid:
            try:
                content = doc.resolve_resource().read_text()
                click.echo(content)
                return
            except Exception as e:
                raise click.ClickException(f"Failed to read {doc.filename}: {e}") from e
    raise click.ClickException(f"No document found with ACID {acid}")
