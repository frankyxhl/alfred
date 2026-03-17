from collections import Counter
from pathlib import Path

import click

from fx_alfred.core.scanner import LayerValidationError, scan_documents

SOURCE_LABELS = {"pkg": "PKG", "usr": "USR", "prj": "PRJ"}


@click.command("status")
def status_cmd():
    """Show document summary."""
    try:
        docs = scan_documents(Path.cwd())
    except LayerValidationError as e:
        raise click.ClickException(str(e)) from e

    if not docs:
        click.echo("No documents found.")
        return

    by_type = Counter(d.type_code for d in docs)
    by_prefix = Counter(d.prefix for d in docs)
    by_source = Counter(d.source for d in docs)

    click.echo(f"Total: {len(docs)} documents\n")
    click.echo("By source:")
    for source in ("pkg", "usr", "prj"):
        if source in by_source:
            label = SOURCE_LABELS.get(source, source.upper())
            click.echo(f"  {label}: {by_source[source]}")
    click.echo("\nBy type:")
    for type_code, count in sorted(by_type.items()):
        click.echo(f"  {type_code}: {count}")
    click.echo("\nBy prefix:")
    for prefix, count in sorted(by_prefix.items()):
        click.echo(f"  {prefix}: {count}")
