from itertools import groupby

import click

from fx_alfred.commands._helpers import scan_or_fail
from fx_alfred.context import get_root, root_option
from fx_alfred.core.document import Document


def _build_index(title: str, docs: list[Document]) -> str:
    lines = [f"# {title}\n"]
    lines.append("| ACID | Type | Title |")
    lines.append("|------|------|-------|")
    sorted_docs = sorted(docs, key=lambda d: d.acid)
    for doc in sorted_docs:
        lines.append(f"| {doc.acid} | {doc.type_code} | {doc.title} |")
    return "\n".join(lines) + "\n"


@click.command("index")
@root_option
@click.pass_context
def index_cmd(ctx: click.Context):
    """Regenerate document index files for PRJ layer only."""
    docs = scan_or_fail(ctx)

    prj_docs = [d for d in docs if d.source == "prj" and d.acid != "0000"]

    if not prj_docs:
        click.echo("No PRJ documents to index.")
        return

    prj_docs.sort(key=lambda d: d.prefix)
    root = get_root(ctx)
    rules_dir = root / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)

    for prefix, group in groupby(prj_docs, key=lambda d: d.prefix):
        group_list = list(group)
        index_content = _build_index("Document Index", group_list)
        index_path = rules_dir / f"{prefix}-0000-REF-Document-Index.md"
        index_path.write_text(index_content)
        click.echo(f"Updated {index_path}")
