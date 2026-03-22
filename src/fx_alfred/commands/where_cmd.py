"""af where command — print the file path of a document."""

import json
from pathlib import Path

import click

from fx_alfred.commands._helpers import find_or_fail, scan_or_fail
from fx_alfred.context import root_option


@click.command("where")
@root_option
@click.argument("identifier")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def where_cmd(ctx, identifier: str, output_json: bool) -> None:
    """Print the file path of a document."""
    docs = scan_or_fail(ctx)
    doc = find_or_fail(docs, identifier)
    resource = doc.resolve_resource()
    if isinstance(resource, Path):
        file_path = resource.resolve()
    else:
        # PKG Traversable: works for directory installs (standard wheel)
        file_path = Path(str(resource)).resolve()

    if not file_path.exists():
        raise click.ClickException(
            f"Cannot resolve filesystem path for {doc.prefix}-{doc.acid}: "
            f"package may be installed as a zip archive"
        )

    if output_json:
        result = {
            "schema_version": "1",
            "doc_id": f"{doc.prefix}-{doc.acid}",
            "path": str(file_path),
            "source": doc.source,
            "filename": file_path.name,
        }
        click.echo(json.dumps(result, ensure_ascii=False))
    else:
        click.echo(str(file_path))
