from pathlib import Path

import click

from fx_alfred.core.scanner import LayerValidationError, scan_documents


@click.command("read")
@click.argument("acid")
def read_cmd(acid: str):
    """Read a document by ACID number."""
    try:
        docs = scan_documents(Path.cwd())
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
