import click

from fx_alfred.context import get_root, root_option
from fx_alfred.core.scanner import LayerValidationError, scan_documents


def _find_document(docs, identifier):
    """Find document by PREFIX-ACID or ACID only. Returns (doc, error_msg)."""
    if "-" in identifier:
        prefix, acid = identifier.split("-", 1)
        matches = [d for d in docs if d.prefix == prefix and d.acid == acid]
    else:
        matches = [d for d in docs if d.acid == identifier]

    if not matches:
        return None, f"No document found: {identifier}"
    if len(matches) > 1:
        options = ", ".join(f"{d.prefix}-{d.acid}" for d in matches)
        return (
            None,
            f"Ambiguous ACID {identifier}. Multiple matches: {options}. Use PREFIX-ACID to be precise.",
        )
    return matches[0], None


@click.command("read")
@root_option
@click.argument("identifier")
@click.pass_context
def read_cmd(ctx: click.Context, identifier: str):
    """Read a document by PREFIX-ACID (e.g., COR-1000) or ACID only (e.g., 1000)."""
    root = get_root(ctx)
    try:
        docs = scan_documents(root)
    except LayerValidationError as e:
        raise click.ClickException(str(e)) from e

    doc, error = _find_document(docs, identifier)
    if error:
        raise click.ClickException(error)

    try:
        content = doc.resolve_resource().read_text()  # type: ignore[union-attr]
    except Exception as e:
        raise click.ClickException(f"Failed to read {doc.filename}: {e}") from e  # type: ignore[union-attr]
    click.echo(content)
