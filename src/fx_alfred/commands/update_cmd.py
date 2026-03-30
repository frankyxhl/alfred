"""af update command — structured metadata updates to existing documents."""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

import click
import yaml

from fx_alfred.commands._helpers import atomic_write, find_or_fail, render_section_content, scan_or_fail, validate_spec_status
from fx_alfred.context import root_option
from fx_alfred.core.normalize import slugify
from fx_alfred.core.document import FILENAME_PATTERN
from fx_alfred.core.parser import (
    MalformedDocumentError,
    MetadataField,
    parse_metadata,
    render_document,
)
from fx_alfred.core.schema import DocType


def _is_interactive() -> bool:
    """Check if stdin is a TTY (interactive terminal)."""
    return sys.stdin.isatty()


def _escape_pipe(value: str) -> str:
    """Escape pipe characters for use inside Markdown table cells."""
    return value.replace("|", "\\|")


def _get_doc_type(doc_type_code: str) -> DocType | None:
    """Get DocType enum from type_code string."""
    try:
        return DocType(doc_type_code)
    except ValueError:
        return None


def _replace_section_in_body(
    body: str, section_name: str, new_content: str
) -> tuple[str, bool]:
    """Replace a section in the body with new content.

    Returns tuple of (modified body, found flag). If section not found,
    returns (original body, False).
    """
    # Match the section heading and capture everything until next heading or end
    pattern = rf"^(##\s+{re.escape(section_name)}\s*\n)(.*?)(?=\n##\s|\n---\s*$|\Z)"
    match = re.search(pattern, body, re.MULTILINE | re.DOTALL)

    if match:
        # Replace the content after the heading
        before = body[: match.start()]
        heading = match.group(1)
        after = body[match.end() :]
        return before + heading + new_content + "\n" + after, True
    else:
        # Section not found
        return body, False


_EPILOG = """\
Examples:

  af update FXA-2107 --status "Active"

  af update 2107 --history "Fixed typo in scope" --by "Frank"

  af update FXA-2107 --title "New Title" -y

  af update FXA-2107 --field "Reviewed by" "Alice" --dry-run

  af update FXA-2107 --spec patch.yaml
"""


@click.command("update", epilog=_EPILOG)
@root_option
@click.argument("identifier")
@click.option(
    "--title",
    "new_title",
    default=None,
    help="Rename: update filename, H1, and auto-run index (PRJ only)",
)
@click.option(
    "--history", default=None, help="Append row to Change History table (date=today)"
)
@click.option(
    "--by", default="\u2014", help="Author name for history entry (default: \u2014)"
)
@click.option(
    "--status", default=None, help="Update Status field (only if field already exists)"
)
@click.option(
    "--field",
    nargs=2,
    multiple=True,
    metavar="KEY VALUE",
    help="Update any metadata field (only if field already exists)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Preview changes without writing to disk",
)
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    default=False,
    help="Skip interactive confirmation for destructive operations (rename)",
)
@click.option(
    "--spec",
    "spec_path",
    default=None,
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="YAML spec file with patches (metadata and/or sections)",
)
@click.pass_context
def update_cmd(
    ctx: click.Context,
    identifier: str,
    new_title: str | None,
    history: str | None,
    by: str,
    status: str | None,
    field: tuple[tuple[str, str], ...],
    dry_run: bool,
    yes: bool,
    spec_path: str | None,
) -> None:
    """Update metadata fields, append history, or rename a document."""
    # Validate: at least one update option must be provided (including --spec)
    has_spec = spec_path is not None
    if (
        new_title is None
        and history is None
        and status is None
        and not field
        and not has_spec
    ):
        raise click.ClickException(
            "Nothing to update. Provide at least one of: "
            "--title, --history, --status, --field"
        )

    docs = scan_or_fail(ctx)
    doc = find_or_fail(docs, identifier)

    # PKG layer is read-only
    if doc.source == "pkg":
        raise click.ClickException(
            "Cannot update PKG layer documents. They are read-only."
        )

    # Resolve file path
    resource = doc.resolve_resource()
    file_path = Path(str(resource))
    content = file_path.read_text()

    # Parse the document
    try:
        parsed = parse_metadata(content)
    except MalformedDocumentError as e:
        raise click.ClickException(str(e)) from e

    # ── Step 0.5: Semantic H1 validation (non-blocking) ────────────────────
    # The parser checks H1 syntax (# TYP-ACID: Title) but not whether TYP/ACID
    # match the document's type_code and acid from the filename.  Warn on mismatch.
    h1_match_sem = re.match(r"^# ([A-Z]{3})-(\d{4}): ", parsed.h1_line)
    if h1_match_sem:
        h1_typ, h1_acid = h1_match_sem.group(1), h1_match_sem.group(2)
        mismatches: list[str] = []
        if h1_typ != doc.type_code:
            mismatches.append(
                f"type '{h1_typ}' vs filename type_code '{doc.type_code}'"
            )
        if h1_acid != doc.acid:
            mismatches.append(f"ACID '{h1_acid}' vs filename ACID '{doc.acid}'")
        if mismatches:
            click.echo(
                f"Warning: H1 mismatch in {doc.filename}: {'; '.join(mismatches)}",
                err=True,
            )

    # ── Step 1: Validate all options ────────────────────────────────────────

    # Load spec file if provided
    spec_metadata_updates: dict[str, Any] = {}
    spec_section_updates: dict[str, Any] = {}
    if has_spec:
        try:
            with open(spec_path, "r") as f:
                spec = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise click.ClickException(f"Invalid YAML in spec file: {e}")

        if not isinstance(spec, dict):
            raise click.ClickException("Spec file must contain a YAML mapping")

        spec_metadata_updates = spec.get("metadata", {})
        spec_section_updates = spec.get("sections", {})

        if not isinstance(spec_metadata_updates, dict):
            raise click.ClickException(
                "Spec 'metadata' must be a mapping (key: value pairs)"
            )
        if not isinstance(spec_section_updates, dict):
            raise click.ClickException(
                "Spec 'sections' must be a mapping (key: value pairs)"
            )

        if not spec_metadata_updates and not spec_section_updates:
            raise click.ClickException(
                "Spec file must contain 'metadata' and/or 'sections'"
            )

    # Get document type for validation
    doc_type_enum = _get_doc_type(doc.type_code)

    # Collect CLI field updates (must already exist in document)
    cli_field_updates: dict[str, str] = {}
    if status is not None:
        cli_field_updates["Status"] = status
    for key, value in field:
        cli_field_updates[key] = value

    # Collect spec metadata updates (may add new fields)
    spec_field_updates: dict[str, str] = {}
    for key, value in spec_metadata_updates.items():
        spec_field_updates[key] = str(value)

    # Combined for apply step — CLI wins over spec (spec is the base, CLI overrides)
    field_updates: dict[str, str] = {**spec_field_updates, **cli_field_updates}

    # Validate effective Status (after CLI override) — only when a spec file is involved.
    # Plain --field/--status CLI updates are not status-validated here.
    if has_spec and "Status" in field_updates and doc_type_enum:
        validate_spec_status(doc_type_enum, field_updates["Status"])

    # Validate that CLI-requested fields exist (spec may add new ones)
    existing_keys = {mf.key for mf in parsed.metadata_fields}
    for key in cli_field_updates:
        if key not in existing_keys:
            raise click.ClickException(f"Field '{key}' not found in document")

    # Validate history section exists if --history is given
    if history is not None and not parsed.history_header:
        raise click.ClickException(
            "Change History section not found in document. "
            "Add a '## Change History' section with a table manually."
        )

    # Validate rename
    new_filename: str | None = None
    new_file_path: Path | None = None
    if new_title is not None:
        stripped_title = new_title.strip()
        if not stripped_title:
            raise click.ClickException("Title cannot be empty")
        if stripped_title != new_title:
            raise click.ClickException(
                "Title must not have leading/trailing whitespace"
            )
        if "/" in new_title or "\\" in new_title:
            raise click.ClickException(
                "Title must not contain path separators (/ or \\)"
            )

        # Build new filename
        new_filename = (
            f"{doc.prefix}-{doc.acid}-{doc.type_code}-{slugify(new_title)}.md"
        )
        if not FILENAME_PATTERN.match(new_filename):
            raise click.ClickException(
                f"Generated filename '{new_filename}' does not match required pattern "
                f"(^[A-Z]{{3}}-\\d{{4}}-[A-Z]{{3}}-.+\\.md$)"
            )

        new_file_path = file_path.parent / new_filename
        if new_file_path.exists() and new_file_path != file_path:
            raise click.ClickException(f"Target path already exists: {new_file_path}")

        # Interactive confirmation (skip for dry-run)
        if not yes and not dry_run:
            if not _is_interactive():
                raise click.ClickException(
                    "Cannot confirm rename in non-interactive mode. Use -y to skip confirmation."
                )
            old_name = file_path.name
            click.echo(f"Rename: {old_name} -> {new_filename}")
            if not click.confirm("Proceed?"):
                raise click.ClickException("Rename cancelled by user")

    # ── Step 2: Apply metadata updates ──────────────────────────────────────

    for mf in parsed.metadata_fields:
        if mf.key in field_updates:
            mf.value = field_updates[mf.key]
            mf.dirty = True

    # Append new spec fields (fields not currently in document)
    for key, value in spec_field_updates.items():
        if key not in existing_keys:
            inferred_style = (
                parsed.metadata_fields[0].prefix_style
                if parsed.metadata_fields
                else "bold"
            )
            parsed.metadata_fields.append(
                MetadataField(
                    key=key,
                    value=value,
                    prefix_style=inferred_style,
                    raw_line="",
                    dirty=True,
                )
            )

    # ── Step 3: Apply history append ────────────────────────────────────────

    if history is not None:
        from fx_alfred.core.parser import HistoryRow

        parsed.history_rows.append(
            HistoryRow(
                date=date.today().isoformat(),
                change=_escape_pipe(history),
                by=_escape_pipe(by),
            )
        )

    # ── Step 3.5: Apply section patches from spec ───────────────────────────

    if spec_section_updates:
        for section_name, section_content in spec_section_updates.items():
            rendered = render_section_content(section_content)
            new_body, found = _replace_section_in_body(
                parsed.body, section_name, rendered
            )
            if not found:
                raise click.ClickException(
                    f"Section '{section_name}' not found in document"
                )
            parsed.body = new_body

    # ── Step 4: Apply rename (H1 update) ────────────────────────────────────

    if new_title is not None:
        # Update H1 line: replace the title portion after ": "
        h1_match = re.match(r"^(# .+?:\s*)", parsed.h1_line)
        if h1_match:
            parsed.h1_line = h1_match.group(1) + new_title
        else:
            # Fallback: replace entire H1
            parsed.h1_line = f"# {doc.type_code}-{doc.acid}: {new_title}"

    # ── Step 5: Auto-touch Last updated ─────────────────────────────────────

    for mf in parsed.metadata_fields:
        if mf.key == "Last updated":
            mf.value = date.today().isoformat()
            mf.dirty = True
            break

    # ── Step 6: Render and write ────────────────────────────────────────────

    new_content = render_document(parsed)

    if dry_run:
        click.echo("Dry run — no changes written.\n")
        # Show diff-like output
        old_lines = content.split("\n")
        new_lines = new_content.split("\n")
        for i, (old, new) in enumerate(zip(old_lines, new_lines)):
            if old != new:
                click.echo(f"- {old}")
                click.echo(f"+ {new}")
        # Show extra lines
        if len(new_lines) > len(old_lines):
            for line in new_lines[len(old_lines) :]:
                click.echo(f"+ {line}")
        if new_title and new_filename:
            click.echo(f"\nRename: {file_path.name} -> {new_filename}")
        return

    # Atomic write
    atomic_write(file_path, new_content)

    # ── Step 7: Post-write — rename file and auto-index ─────────────────────

    if (
        new_title is not None
        and new_file_path is not None
        and new_file_path != file_path
    ):
        file_path.rename(new_file_path)
        click.echo(f"Renamed {file_path.name} -> {new_file_path.name}")

        if doc.source == "prj":
            try:
                from fx_alfred.commands.index_cmd import index_cmd

                ctx.invoke(index_cmd)
            except Exception as e:
                click.echo(f"Warning: Failed to update index: {e}", err=True)
    else:
        click.echo(f"Updated {file_path.name}")
