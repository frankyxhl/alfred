from pathlib import Path

import click

from fx_alfred.core.scanner import LayerValidationError, scan_documents

SOURCE_LABELS = {"pkg": "PKG", "usr": "USR", "prj": "PRJ"}


@click.command("list")
def list_cmd():
    """List all documents."""
    try:
        docs = scan_documents(Path.cwd())
    except LayerValidationError as e:
        raise click.ClickException(str(e)) from e

    if not docs:
        click.echo("No documents found.")
        return
    for doc in docs:
        label = SOURCE_LABELS.get(doc.source, "???")
        click.echo(f"{label}\t{doc.prefix}-{doc.acid}\t{doc.type_code}\t{doc.title}")
