import click

from fx_alfred.commands._helpers import scan_or_fail
from fx_alfred.context import root_option
from fx_alfred.core.parser import MalformedDocumentError, parse_metadata
from fx_alfred.core.source import SOURCE_ORDER

ROUTING_PATTERN = "SOP-Workflow-Routing"


@click.command("guide")
@root_option
@click.pass_context
def guide_cmd(ctx: click.Context):
    """Show workflow routing guide for current session."""
    docs = scan_or_fail(ctx)

    # Filter for routing documents by filename pattern
    routing_docs = [d for d in docs if ROUTING_PATTERN in d.filename]

    for source in SOURCE_ORDER:
        layer_docs = [d for d in routing_docs if d.source == source]
        label = source.upper()

        if not layer_docs:
            click.echo(f"═══ {label}: (no active routing document found) ═══")
            click.echo()
            continue

        # Parse metadata, filter by Status: Active, handle malformed
        active_docs: list[tuple] = []
        for doc in layer_docs:
            try:
                content = doc.resolve_resource().read_text()
                parsed = parse_metadata(content)
                status = next(
                    (mf.value for mf in parsed.metadata_fields if mf.key == "Status"),
                    None,
                )
                if status == "Deprecated":
                    continue
                if status == "Active":
                    active_docs.append((doc, content))
            except MalformedDocumentError as e:
                click.echo(f"═══ {label}: {doc.prefix}-{doc.acid} (malformed: {e}) ═══")
                click.echo()
                continue

        if not active_docs:
            click.echo(f"═══ {label}: (no active routing document found) ═══")
            click.echo()
            continue

        if len(active_docs) > 1:
            click.echo(
                f"Warning: {len(active_docs)} active routing docs in"
                f" {label} layer, using lowest ACID"
            )

        # Sort by ACID, use first (lowest)
        active_docs.sort(key=lambda x: x[0].acid)
        doc, content = active_docs[0]

        click.echo(f"═══ {label}: {doc.prefix}-{doc.acid} {doc.title} ═══")
        click.echo()
        click.echo(content)
        click.echo()
