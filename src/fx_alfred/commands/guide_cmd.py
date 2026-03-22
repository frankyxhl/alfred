import json

import click

from fx_alfred.commands._helpers import scan_or_fail
from fx_alfred.context import root_option
from fx_alfred.core.parser import MalformedDocumentError, parse_metadata
from fx_alfred.core.schema import ROUTING_ROLE_METADATA_KEY, ROUTING_ROLE_VALUE
from fx_alfred.core.source import SOURCE_ORDER

ROUTING_PATTERN = "SOP-Workflow-Routing"


@click.command("guide")
@root_option
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def guide_cmd(ctx: click.Context, output_json: bool):
    """Show workflow routing guide for current session."""
    docs = scan_or_fail(ctx)

    # Collect routing docs for JSON output
    routing_docs = []

    for source in SOURCE_ORDER:
        layer_docs = [d for d in docs if d.source == source]
        label = source.upper()

        active_docs: list[tuple] = []
        for doc in layer_docs:
            try:
                content = doc.resolve_resource().read_text()
                parsed = parse_metadata(content)

                # Check routing: metadata role first, filename pattern fallback
                role = next(
                    (
                        mf.value
                        for mf in parsed.metadata_fields
                        if mf.key == ROUTING_ROLE_METADATA_KEY
                    ),
                    None,
                )
                is_routing = (role == ROUTING_ROLE_VALUE) or (
                    ROUTING_PATTERN in doc.filename
                )
                if not is_routing:
                    continue

                status = next(
                    (mf.value for mf in parsed.metadata_fields if mf.key == "Status"),
                    None,
                )
                if status == "Deprecated":
                    continue
                if status == "Active":
                    active_docs.append((doc, content, role))
            except MalformedDocumentError as e:
                # Only report malformed errors for filename-pattern-matched docs
                # (backward-compatible: non-routing docs were never parsed before this refactor)
                if ROUTING_PATTERN in doc.filename:
                    if not output_json:
                        click.echo(
                            f"═══ {label}: {doc.prefix}-{doc.acid} (malformed: {e}) ═══"
                        )
                        click.echo()
                continue

        if not active_docs:
            if not output_json:
                click.echo(f"═══ {label}: (no active routing document found) ═══")
                click.echo()
            continue

        if len(active_docs) > 1:
            if not output_json:
                click.echo(
                    f"Warning: {len(active_docs)} active routing docs in"
                    f" {label} layer, using lowest ACID"
                )

        active_docs.sort(key=lambda x: x[0].acid)
        doc, content, role = active_docs[0]

        # Collect for JSON output
        routing_docs.append(
            {
                "doc_id": f"{doc.prefix}-{doc.acid}",
                "title": doc.title,
                "source": doc.source.upper(),
                "status": "Active",
                "role": ROUTING_ROLE_VALUE if role == ROUTING_ROLE_VALUE else "routing",
            }
        )

        if not output_json:
            click.echo(f"═══ {label}: {doc.prefix}-{doc.acid} {doc.title} ═══")
            click.echo()
            click.echo(content)
            click.echo()

    if output_json:
        result = {
            "schema_version": "1",
            "routing_docs": routing_docs,
        }
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        click.echo(
            "Run this at session start for routing context."
            " Then run `af plan <SOP_IDs>` before each task."
            " First time? Run `af setup` to configure your agent."
        )
