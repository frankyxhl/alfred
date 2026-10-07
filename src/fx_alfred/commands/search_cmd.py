"""Search command for af CLI -- searches document contents."""

import click

from fx_alfred.commands._helpers import (
    SCHEMA_VERSION,
    emit_json,
    scan_registered_project_documents,
    scan_or_fail,
)
from fx_alfred.context import get_root, root_option
from fx_alfred.core.document import Document
from fx_alfred.core.source import SOURCE_LABELS


_EPILOG = """\
Examples:

  af search TDD                    # find docs mentioning TDD
  af search "Change History"       # quote multi-word patterns
  af search workflow --root myproj # search in specific project
  af search workflow --all         # search every registered project

Shows up to 3 matching lines per document with line numbers.
"""


@click.command("search", epilog=_EPILOG)
@root_option
@click.argument("pattern")
@click.option(
    "--all",
    "search_all",
    is_flag=True,
    help="Also search PRJ documents in every registered project.",
)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def search_cmd(
    ctx: click.Context,
    pattern: str,
    search_all: bool,
    output_json: bool,
):
    """Search document contents for PATTERN (case-insensitive substring)."""
    docs = scan_or_fail(ctx)
    current_root = get_root(ctx)
    matched_documents: list[tuple[Document, str | None]] = [
        (doc, str(current_root) if search_all and doc.source == "prj" else None)
        for doc in docs
    ]

    if search_all:
        for project_root, project_docs in scan_registered_project_documents(
            current_root
        ):
            matched_documents.extend(
                (doc, str(project_root)) for doc in project_docs if doc.source == "prj"
            )

    pattern_lower = pattern.lower()

    matches_found = False
    results = []

    for doc, project_root in matched_documents:
        try:
            content = doc.resolve_resource().read_text(encoding="utf-8")
        except Exception:
            # Skip unreadable documents silently
            continue

        lines = content.split("\n")
        matching_lines = []

        for i, line in enumerate(lines, start=1):
            if pattern_lower in line.lower():
                matching_lines.append((i, line))

        if matching_lines:
            matches_found = True
            label = SOURCE_LABELS.get(doc.source, "???")

            if output_json:
                # First matching line as snippet, truncated to 120 chars
                snippet = matching_lines[0][1].strip()[:120]
                entry: dict[str, str | None] = {
                    "doc_id": f"{doc.prefix}-{doc.acid}",
                    "title": doc.title,
                    "source": doc.source,
                }
                if search_all:
                    entry["project_root"] = (
                        str(project_root) if project_root is not None else None
                    )
                entry["snippet"] = snippet
                results.append(entry)
            else:
                # Header line: PREFIX-ACID  SOURCE_LABEL  Title
                click.echo(f"{doc.prefix}-{doc.acid}  {label}  {doc.title}")
                if project_root is not None:
                    click.echo(f"  Project: {project_root}")

                # Show up to 3 matching lines with line numbers
                for line_num, line_content in matching_lines[:3]:
                    click.echo(f"  {line_num}: {line_content}")

                # Blank line after document group
                click.echo()

    if output_json:
        result = {
            "schema_version": SCHEMA_VERSION,
            "query": pattern,
            "results": results,
        }
        emit_json(result)
    elif not matches_found:
        click.echo("No matches found.")
