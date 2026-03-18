import click

from fx_alfred.context import get_root, root_option
from fx_alfred.core.scanner import (
    AmbiguousDocumentError,
    DocumentNotFoundError,
    LayerValidationError,
    find_document,
    scan_documents,
)


@click.command("read")
@root_option
@click.argument("identifier")
@click.pass_context
def read_cmd(ctx: click.Context, identifier: str):
    """Read a document by PREFIX-ACID (e.g., COR-1000) or ACID only (e.g., 1000)."""
    root = get_root(ctx)
    try:
        docs = scan_documents(root)
    except LayerValidationError as e:
        raise click.ClickException(str(e)) from e

    try:
        doc = find_document(docs, identifier)
    except (DocumentNotFoundError, AmbiguousDocumentError) as e:
        raise click.ClickException(str(e)) from e

    try:
        content = doc.resolve_resource().read_text()
    except Exception as e:
        raise click.ClickException(f"Failed to read {doc.filename}: {e}") from e
    click.echo(content)
