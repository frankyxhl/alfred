import click

from fx_alfred.commands._helpers import (
    emit_json,
    format_doc_row,
    scan_registered_project_documents,
    scan_or_fail,
)
from fx_alfred.context import get_root, root_option
from fx_alfred.core.document import Document


_EPILOG = """\
Examples:

  af list                          # all documents
  af list --type SOP               # only SOPs
  af list --prefix FXA --type PRP  # FXA proposals only
  af list --source prj             # project-layer only
  af list --json                   # JSON array output
  af list --type SOP --json        # filtered JSON
  af list --all                    # every registered project's PRJ docs

Types: SOP, ADR, PRP, REF, CHG, PLN, INC
Sources: pkg (bundled), usr (~/.alfred/), prj (./rules/)
Filters use exact case-insensitive matching (AND logic).
"""


@click.command("list", epilog=_EPILOG)
@root_option
@click.option(
    "--type",
    "type_code",
    default=None,
    help="Filter by type (SOP, PRP, CHG, ADR, REF, PLN, INC).",
)
@click.option("--prefix", default=None, help="Filter by prefix (e.g. FXA, COR, ALF).")
@click.option(
    "--source", "source_filter", default=None, help="Filter by layer (pkg, usr, prj)."
)
@click.option("--json", "json_output", is_flag=True, help="Output as JSON array.")
@click.option(
    "--tag", default=None, help="Filter by tag (case-insensitive exact match)."
)
@click.option(
    "--all",
    "list_all",
    is_flag=True,
    help="Also list PRJ documents in every registered project.",
)
@click.pass_context
def list_cmd(
    ctx: click.Context,
    type_code: str | None,
    prefix: str | None,
    source_filter: str | None,
    json_output: bool,
    tag: str | None,
    list_all: bool,
):
    """List all documents across PKG, USR, and PRJ layers."""
    docs = scan_or_fail(ctx)
    current_root = get_root(ctx)
    documents: list[tuple[Document, str | None]] = [
        (doc, str(current_root) if list_all and doc.source == "prj" else None)
        for doc in docs
    ]

    if list_all:
        for project_root, project_docs in scan_registered_project_documents(
            current_root
        ):
            documents.extend(
                (doc, str(project_root)) for doc in project_docs if doc.source == "prj"
            )
    # Apply filters (AND logic)
    if type_code is not None:
        documents = [
            item for item in documents if item[0].type_code.upper() == type_code.upper()
        ]
    if prefix is not None:
        documents = [
            item for item in documents if item[0].prefix.upper() == prefix.upper()
        ]
    if source_filter is not None:
        documents = [
            item
            for item in documents
            if item[0].source.lower() == source_filter.lower()
        ]
    if tag is not None:
        documents = [item for item in documents if tag.lower() in item[0].tags]
    docs = [doc for doc, _ in documents]

    if not docs:
        if json_output:
            click.echo("[]")
        else:
            click.echo("No documents found.")
        return

    if json_output:
        output = [
            {
                "prefix": doc.prefix,
                "acid": doc.acid,
                "type_code": doc.type_code,
                "title": doc.title,
                "source": doc.source,
                "directory": doc.directory,
                **({"project_root": project_root} if list_all else {}),
            }
            for doc, project_root in documents
        ]
        emit_json(output)
    else:
        for doc, project_root in documents:
            click.echo(format_doc_row(doc))
            if project_root is not None:
                click.echo(f"  Project: {project_root}")
