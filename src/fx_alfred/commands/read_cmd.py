import click

from fx_alfred.commands._helpers import (
    emit_json,
    scan_or_fail,
    touch_project_registry,
)
from fx_alfred.context import root_option
from fx_alfred.core.scanner import (
    AmbiguousDocumentError,
    DocumentNotFoundError,
    find_document,
)


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
    wrote = touch_project_registry(ctx, docs)
    # Resolve against the PRE-bootstrap snapshot first, so background
    # registry maintenance cannot change this read's semantics: an
    # unambiguous ACID-only lookup (project has its own 9000 doc) stays
    # unambiguous instead of turning ambiguous once USR-9000 exists.
    # Only a not-found retry may consult the rescan — that is
    # the fresh-machine `af read USR-9000` bootstrap path.
    try:
        doc = find_document(docs, identifier)
    except DocumentNotFoundError:
        if not wrote:
            raise click.ClickException(f"No document found: {identifier}") from None
        try:
            docs = scan_or_fail(ctx)
            doc = find_document(docs, identifier)
        except (DocumentNotFoundError, AmbiguousDocumentError) as e:
            raise click.ClickException(str(e)) from e
    except AmbiguousDocumentError as e:
        raise click.ClickException(str(e)) from e

    try:
        content = doc.resolve_resource().read_text(encoding="utf-8")
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
        emit_json(output)
    else:
        click.echo(content)
