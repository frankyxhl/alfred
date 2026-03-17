from itertools import groupby
from pathlib import Path

import click

from fx_alfred.core.document import Document
from fx_alfred.core.scanner import LayerValidationError, scan_documents


def _build_index(title: str, docs: list[Document]) -> str:
    lines = [f"# {title}\n"]
    lines.append("| ACID | Type | Title |")
    lines.append("|------|------|-------|")
    sorted_docs = sorted(docs, key=lambda d: d.acid)
    for doc in sorted_docs:
        lines.append(f"| {doc.acid} | {doc.type_code} | {doc.title} |")
    return "\n".join(lines) + "\n"


@click.command("index")
def index_cmd():
    """Regenerate document index files for PRJ layer only."""
    try:
        docs = scan_documents(Path.cwd())
    except LayerValidationError as e:
        raise click.ClickException(str(e)) from e

    # Only index PRJ layer documents
    prj_docs = [d for d in docs if d.source == "prj" and d.acid != "0000"]

    if not prj_docs:
        click.echo("No PRJ documents to index.")
        return

    prj_docs.sort(key=lambda d: d.prefix)
    rules_dir = Path.cwd() / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)

    for prefix, group in groupby(prj_docs, key=lambda d: d.prefix):
        group_list = list(group)
        index_content = _build_index("Document Index", group_list)
        index_path = rules_dir / f"{prefix}-0000-REF-Document-Index.md"
        index_path.write_text(index_content)
        click.echo(f"Updated {index_path}")
