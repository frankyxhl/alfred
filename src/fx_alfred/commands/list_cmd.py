from pathlib import Path

import click

from fx_alfred.core.scanner import scan_documents


@click.command("list")
def list_cmd():
    """List all documents."""
    docs = scan_documents(Path.cwd())
    if not docs:
        click.echo("No documents found.")
        return
    for doc in docs:
        click.echo(f"  {doc.prefix}-{doc.acid}  {doc.type_code}  {doc.title}")
