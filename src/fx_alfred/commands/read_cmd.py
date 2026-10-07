import click

from fx_alfred.commands._helpers import (
    emit_json,
    scan_registered_project_documents,
    scan_or_fail,
)
from fx_alfred.context import get_root, root_option
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
@click.option(
    "--all",
    "read_all",
    is_flag=True,
    help="Also match PRJ documents in every registered project.",
)
@click.pass_context
def read_cmd(
    ctx: click.Context,
    identifier: str,
    json_output: bool,
    read_all: bool,
):
    """Read a document by PREFIX-ACID (e.g., COR-1000) or ACID only (e.g., 1000)."""
    docs = scan_or_fail(ctx)
    current_root = get_root(ctx)
    document_roots: dict[int, str] = {}
    if read_all:
        document_roots.update(
            {id(doc): str(current_root) for doc in docs if doc.source == "prj"}
        )
        all_docs = list(docs)
        for project_root, project_docs in scan_registered_project_documents(
            current_root
        ):
            for doc in project_docs:
                if doc.source == "prj":
                    document_roots[id(doc)] = str(project_root)
                    all_docs.append(doc)
        docs = all_docs

    try:
        doc = find_document(docs, identifier)
    except DocumentNotFoundError:
        raise click.ClickException(f"No document found: {identifier}") from None
    except AmbiguousDocumentError as e:
        if not read_all:
            raise click.ClickException(str(e)) from e
        candidate_lines = "\n".join(
            f"  {item.prefix}-{item.acid}"
            + (f" at {document_roots[id(item)]}" if id(item) in document_roots else "")
            for item in e.matches
        )
        raise click.ClickException(
            f"Ambiguous document {identifier}. Use --root <project>:\n{candidate_lines}"
        ) from e

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
