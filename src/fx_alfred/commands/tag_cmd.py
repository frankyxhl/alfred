from collections import Counter

import click

from fx_alfred.commands._helpers import emit_json, format_doc_row, scan_or_fail
from fx_alfred.context import root_option


@click.command("tag")
@root_option
@click.argument("name", required=False, default=None)
@click.option("--json", "json_output", is_flag=True, help="Output as JSON.")
@click.pass_context
def tag_cmd(ctx: click.Context, name: str | None, json_output: bool):
    """List tags or documents matching a tag.

    With no argument: list every distinct tag across all documents with
    its usage count, sorted alphabetically.

    With NAME: list every document that carries that tag (case-insensitive
    exact match, same output format as `af list`).
    """
    docs = scan_or_fail(ctx)

    if name is None:
        # Aggregate all tags across all documents
        tag_counter: Counter[str] = Counter()
        for doc in docs:
            tag_counter.update(set(doc.tags))

        sorted_tags = sorted(tag_counter.items())

        if not sorted_tags:
            if json_output:
                emit_json([])
            else:
                click.echo("No tags found.")
            return

        if json_output:
            emit_json([{"tag": t, "count": c} for t, c in sorted_tags])
        else:
            width = max(len(t) for t, _ in sorted_tags)
            for t, c in sorted_tags:
                click.echo(f"{t:<{width}}  {c}")
    else:
        # Filter documents by the given tag name (case-insensitive exact match)
        matched = [d for d in docs if name.lower() in d.tags]

        if not matched:
            if json_output:
                emit_json([])
            else:
                click.echo("No documents found.")
            return

        if json_output:
            emit_json(
                [
                    {
                        "prefix": doc.prefix,
                        "acid": doc.acid,
                        "type_code": doc.type_code,
                        "title": doc.title,
                        "source": doc.source,
                        "directory": doc.directory,
                    }
                    for doc in matched
                ]
            )
        else:
            for doc in matched:
                click.echo(format_doc_row(doc))
