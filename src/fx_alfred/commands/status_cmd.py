import json
from collections import Counter

import click

from fx_alfred.commands._helpers import scan_or_fail
from fx_alfred.context import root_option
from fx_alfred.core.source import SOURCE_LABELS, SOURCE_ORDER


@click.command("status")
@root_option
@click.option("--json", "json_output", is_flag=True, help="Output as JSON.")
@click.pass_context
def status_cmd(ctx: click.Context, json_output: bool):
    """Show document summary."""
    docs = scan_or_fail(ctx)

    if not docs:
        if json_output:
            click.echo(
                json.dumps(
                    {"total": 0, "by_source": {}, "by_type": {}, "by_prefix": {}}
                )
            )
        else:
            click.echo("No documents found.")
        return

    by_type = Counter(d.type_code for d in docs)
    by_prefix = Counter(d.prefix for d in docs)
    by_source = Counter(d.source for d in docs)

    if json_output:
        output = {
            "total": len(docs),
            "by_source": dict(by_source),
            "by_type": dict(by_type),
            "by_prefix": dict(by_prefix),
        }
        click.echo(json.dumps(output))
    else:
        click.echo(f"Total: {len(docs)} documents\n")
        click.echo("By source:")
        for source in SOURCE_ORDER:
            if source in by_source:
                label = SOURCE_LABELS.get(source, source.upper())
                click.echo(f"  {label}: {by_source[source]}")
        click.echo("\nBy type:")
        for type_code, count in sorted(by_type.items()):
            click.echo(f"  {type_code}: {count}")
        click.echo("\nBy prefix:")
        for prefix, count in sorted(by_prefix.items()):
            click.echo(f"  {prefix}: {count}")
