"""Tag commands — list/show/add/rm tags on Alfred documents."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import click

from fx_alfred.commands._helpers import (
    atomic_write,
    emit_json,
    find_or_fail,
    format_doc_row,
    scan_or_fail,
)
from fx_alfred.context import root_option
from fx_alfred.core.parser import (
    MalformedDocumentError,
    MetadataField,
    parse_metadata,
    parse_tags,
    render_document,
)


@click.group("tag")
def tag_cmd() -> None:
    """Manage document tags.

    Subcommands:
      ls   — list every distinct tag with usage counts
      show — list documents carrying a given tag
      add  — add tags to a document
      rm   — remove tags from a document
    """


@tag_cmd.command("ls")
@root_option
@click.option("--json", "json_output", is_flag=True, help="Output as JSON.")
@click.pass_context
def ls_cmd(ctx: click.Context, json_output: bool) -> None:
    """List every distinct tag with usage count, sorted alphabetically."""
    docs = scan_or_fail(ctx)

    tag_counter: Counter[str] = Counter()
    for doc in docs:
        tag_counter.update(set(doc.tags))

    sorted_tags = sorted(tag_counter.items())

    if not sorted_tags:
        if json_output:
            emit_json([])
        else:
            click.echo("No tags found.")
        return

    if json_output:
        emit_json([{"tag": t, "count": c} for t, c in sorted_tags])
    else:
        width = max(len(t) for t, _ in sorted_tags)
        for t, c in sorted_tags:
            click.echo(f"{t:<{width}}  {c}")


@tag_cmd.command("show")
@root_option
@click.argument("name")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON.")
@click.pass_context
def show_cmd(ctx: click.Context, name: str, json_output: bool) -> None:
    """List all documents carrying NAME (case-insensitive exact match)."""
    docs = scan_or_fail(ctx)
    matched = [d for d in docs if name.lower() in d.tags]

    if not matched:
        if json_output:
            emit_json([])
        else:
            click.echo("No documents found.")
        return

    if json_output:
        emit_json(
            [
                {
                    "prefix": doc.prefix,
                    "acid": doc.acid,
                    "type_code": doc.type_code,
                    "title": doc.title,
                    "source": doc.source,
                    "directory": doc.directory,
                }
                for doc in matched
            ]
        )
    else:
        for doc in matched:
            click.echo(format_doc_row(doc))


@tag_cmd.command("add")
@root_option
@click.argument("identifier")
@click.argument("tags", nargs=-1, required=True)
@click.pass_context
def add_cmd(ctx: click.Context, identifier: str, tags: tuple[str, ...]) -> None:
    """Add one or more TAGS to document IDENTIFIER.

    TAGS may be multiple positional arguments, comma-separated values, or a
    mix: `af tag add FXA-2315 routing,plan session`
    PKG/COR documents are read-only; submit a PR to change their tags.
    """
    docs = scan_or_fail(ctx)
    doc = find_or_fail(docs, identifier)

    if doc.source == "pkg":
        raise click.ClickException(
            "Cannot update PKG layer documents. They are read-only."
        )

    # Flatten comma-separated args to a deduplicated ordered list
    new_tags: list[str] = []
    for tag_arg in tags:
        new_tags.extend(parse_tags(tag_arg))

    resource = doc.resolve_resource()
    file_path = Path(str(resource))
    content = file_path.read_text(encoding="utf-8")

    try:
        parsed = parse_metadata(content)
    except MalformedDocumentError as e:
        raise click.ClickException(str(e)) from e

    tag_field = next((mf for mf in parsed.metadata_fields if mf.key == "Tags"), None)
    existing_tags = parse_tags(tag_field.value) if tag_field is not None else []

    # Union: preserve existing order, append new (deduped)
    seen: set[str] = set(existing_tags)
    merged = list(existing_tags)
    for t in new_tags:
        if t not in seen:
            merged.append(t)
            seen.add(t)

    tags_value = ", ".join(merged)

    if tag_field is None:
        inferred_style = (
            parsed.metadata_fields[0].prefix_style if parsed.metadata_fields else "bold"
        )
        parsed.metadata_fields.append(
            MetadataField(
                key="Tags",
                value=tags_value,
                prefix_style=inferred_style,
                raw_line="",
                dirty=True,
            )
        )
    else:
        tag_field.value = tags_value
        tag_field.dirty = True

    atomic_write(file_path, render_document(parsed))
    click.echo(f"{doc.prefix}-{doc.acid} tags: {tags_value}")


@tag_cmd.command("rm")
@root_option
@click.argument("identifier")
@click.argument("tags", nargs=-1, required=True)
@click.pass_context
def rm_cmd(ctx: click.Context, identifier: str, tags: tuple[str, ...]) -> None:
    """Remove one or more TAGS from document IDENTIFIER.

    TAGS may be multiple positional arguments, comma-separated values, or a
    mix. Removing a tag not present is idempotent (exit 0). Removing the last
    tag drops the Tags: field entirely.
    PKG/COR documents are read-only; submit a PR to change their tags.
    """
    docs = scan_or_fail(ctx)
    doc = find_or_fail(docs, identifier)

    if doc.source == "pkg":
        raise click.ClickException(
            "Cannot update PKG layer documents. They are read-only."
        )

    # Flatten comma-separated args
    tags_to_remove: set[str] = set()
    for tag_arg in tags:
        tags_to_remove.update(parse_tags(tag_arg))

    resource = doc.resolve_resource()
    file_path = Path(str(resource))
    content = file_path.read_text(encoding="utf-8")

    try:
        parsed = parse_metadata(content)
    except MalformedDocumentError as e:
        raise click.ClickException(str(e)) from e

    tag_field = next((mf for mf in parsed.metadata_fields if mf.key == "Tags"), None)

    if tag_field is None:
        click.echo(f"No Tags field on {doc.prefix}-{doc.acid}; nothing to remove.")
        return

    existing_tags = parse_tags(tag_field.value)
    existing_set = set(existing_tags)
    absent = sorted(tags_to_remove - existing_set)

    for t in absent:
        click.echo(f"Tag '{t}' not present on {doc.prefix}-{doc.acid}; skipping.")

    actually_removed = tags_to_remove & existing_set
    if not actually_removed:
        return

    kept = [t for t in existing_tags if t not in tags_to_remove]

    if kept:
        tag_field.value = ", ".join(kept)
        tag_field.dirty = True
    else:
        parsed.metadata_fields = [
            mf for mf in parsed.metadata_fields if mf.key != "Tags"
        ]

    atomic_write(file_path, render_document(parsed))
    remaining = ", ".join(kept) if kept else "(none — field removed)"
    click.echo(f"{doc.prefix}-{doc.acid} tags: {remaining}")
