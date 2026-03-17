from collections import Counter
from pathlib import Path

import click

from fx_alfred.core.scanner import scan_documents


@click.command("status")
def status_cmd():
    """Show document summary."""
    docs = scan_documents(Path.cwd())
    if not docs:
        click.echo("No documents found.")
        return

    by_type = Counter(d.type_code for d in docs)
    by_prefix = Counter(d.prefix for d in docs)

    click.echo(f"Total: {len(docs)} documents\n")
    click.echo("By type:")
    for type_code, count in sorted(by_type.items()):
        click.echo(f"  {type_code}: {count}")
    click.echo("\nBy prefix:")
    for prefix, count in sorted(by_prefix.items()):
        click.echo(f"  {prefix}: {count}")
