from itertools import groupby
from pathlib import Path

import click

from fx_alfred.core.document import Document
from fx_alfred.core.scanner import scan_documents


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
    """Regenerate document index files."""
    docs = scan_documents(Path.cwd())

    cor_docs = [d for d in docs if d.prefix == "COR" and d.acid != "0000"]
    if cor_docs:
        index_content = _build_index("Document Index (Meta Layer)", cor_docs)
        index_path = Path.cwd() / ".alfred" / "COR-0000-REF-Document-Index.md"
        index_path.write_text(index_content)
        click.echo(f"Updated {index_path}")

    biz_docs = [d for d in docs if d.prefix != "COR" and d.acid != "0000"]
    biz_docs.sort(key=lambda d: d.prefix)
    for prefix, group in groupby(biz_docs, key=lambda d: d.prefix):
        group_list = list(group)
        index_content = _build_index("Document Index (Business Layer)", group_list)
        index_path = Path.cwd() / "docs" / f"{prefix}-0000-REF-Document-Index.md"
        index_path.write_text(index_content)
        click.echo(f"Updated {index_path}")
