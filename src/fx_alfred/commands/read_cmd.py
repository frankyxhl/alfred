from pathlib import Path

import click

from fx_alfred.core.scanner import scan_documents


@click.command("read")
@click.argument("acid")
def read_cmd(acid: str):
    """Read a document by ACID number."""
    docs = scan_documents(Path.cwd())
    for doc in docs:
        if doc.acid == acid:
            content = (Path.cwd() / doc.filepath).read_text()
            click.echo(content)
            return
    raise click.ClickException(f"No document found with ACID {acid}")
