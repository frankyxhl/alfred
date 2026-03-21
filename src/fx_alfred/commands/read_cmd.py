import json

import click

from fx_alfred.commands._helpers import find_or_fail, scan_or_fail
from fx_alfred.context import root_option


@click.command("read")
@root_option
@click.argument("identifier")
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output as JSON object with document metadata and content.",
)
@click.pass_context
def read_cmd(ctx: click.Context, identifier: str, json_output: bool):
    """Read a document by PREFIX-ACID (e.g., COR-1000) or ACID only (e.g., 1000)."""
    docs = scan_or_fail(ctx)
    doc = find_or_fail(docs, identifier)

    try:
        content = doc.resolve_resource().read_text()
    except Exception as e:
        raise click.ClickException(f"Failed to read {doc.filename}: {e}") from e

    if json_output:
        output = {
            "prefix": doc.prefix,
            "acid": doc.acid,
            "type_code": doc.type_code,
            "title": doc.title,
            "source": doc.source,
            "content": content,
        }
        click.echo(json.dumps(output))
    else:
        click.echo(content)
