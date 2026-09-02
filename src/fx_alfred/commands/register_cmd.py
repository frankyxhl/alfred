"""FXA-2330: `af register` — explicit Project SOP Registry upsert."""

from collections import Counter

import click

from fx_alfred.commands._helpers import (
    emit_json,
    registry_id_in_use,
    scan_or_fail,
)
from fx_alfred.context import get_root, root_option
from fx_alfred.core.registry import (
    load_registry,
    registry_path,
    save_registry,
    slot_conflict,
    today_str,
    upsert,
)


@click.command("register")
@root_option
@click.option("--json", "output_json", is_flag=True, help="Output as JSON array.")
@click.pass_context
def register_cmd(ctx: click.Context, output_json: bool):
    """Register this project in the user-level Project SOP Registry (USR-9000)."""
    docs = scan_or_fail(ctx)
    root = get_root(ctx)

    prj_docs = [d for d in docs if d.source == "prj"]
    if not prj_docs:
        raise click.ClickException(
            f"No Alfred project documents found at {root}; "
            "a project registers only when its PRJ layer carries documents."
        )
    if registry_id_in_use(docs):
        raise click.ClickException(
            "A USR-9000 document already exists in the scanned layers; "
            "registering here would create a duplicate id that fails layer "
            "validation. Move or renumber that document first."
        )

    prefix_counts = Counter(d.prefix for d in prj_docs)
    path = registry_path()
    try:
        entries = load_registry(path)
        # Ownership validation runs even when the upsert would be a no-op —
        # "already current" must never be reported for a foreign occupant.
        conflict = slot_conflict(path)
        if conflict is not None:
            raise click.ClickException(
                f"{conflict.name} already occupies the USR-9000 slot; "
                "move or renumber it before af can maintain the project "
                "registry"
            )
        new_entries, changed = upsert(
            entries,
            root=root,
            prefix_counts=dict(prefix_counts),
            today=today_str(),
        )
        if changed:
            save_registry(path, new_entries, today=today_str())
    except Exception as e:
        raise click.ClickException(f"Project registry update failed: {e}") from e

    resolved = str(root.resolve())
    rows = [
        {
            "prefix": e.prefix,
            "root": e.root,
            "doc_count": e.doc_count,
            "last_seen": e.last_seen,
        }
        for e in new_entries
        if e.root == resolved
    ]
    if output_json:
        emit_json(rows)
        return
    status = "updated" if changed else "already current"
    for row in rows:
        click.echo(
            f"Registered {row['prefix']} {row['root']} "
            f"({row['doc_count']} docs, last seen {row['last_seen']}) — {status}."
        )
