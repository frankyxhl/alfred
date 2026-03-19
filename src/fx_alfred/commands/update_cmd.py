"""af update command — structured metadata updates to existing documents."""

from __future__ import annotations

import os
import re
import sys
import tempfile
from datetime import date
from pathlib import Path

import click

from fx_alfred.context import get_root, root_option
from fx_alfred.core.document import FILENAME_PATTERN, Document
from fx_alfred.core.parser import MalformedDocumentError, parse_metadata, render_document
from fx_alfred.core.scanner import (
    AmbiguousDocumentError,
    DocumentNotFoundError,
    LayerValidationError,
    find_document,
    scan_documents,
)


def _is_interactive() -> bool:
    """Check if stdin is a TTY (interactive terminal)."""
    return sys.stdin.isatty()


def _escape_pipe(value: str) -> str:
    """Escape pipe characters for use inside Markdown table cells."""
    return value.replace("|", "\\|")


_EPILOG = """\
Examples:

  af update FXA-2107 --status "Active"

  af update 2107 --history "Fixed typo in scope" --by "Frank"

  af update FXA-2107 --title "New Title" -y

  af update FXA-2107 --field "Reviewed by" "Alice" --dry-run
"""


@click.command("update", epilog=_EPILOG)
@root_option
@click.argument("identifier")
@click.option("--title", "new_title", default=None, help="Rename: update filename, H1, and auto-run index (PRJ only)")
@click.option("--history", default=None, help="Append row to Change History table (date=today)")
@click.option("--by", default="\u2014", help="Author name for history entry (default: \u2014)")
@click.option("--status", default=None, help="Update Status field (only if field already exists)")
@click.option("--field", nargs=2, multiple=True, metavar="KEY VALUE", help="Update any metadata field (only if field already exists)")
@click.option("--dry-run", is_flag=True, default=False, help="Preview changes without writing to disk")
@click.option("-y", "--yes", is_flag=True, default=False, help="Skip interactive confirmation for destructive operations (rename)")
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
) -> None:
    """Update metadata fields, append history, or rename a document."""
    # Validate: at least one update option must be provided
    if new_title is None and history is None and status is None and not field:
        raise click.ClickException(
            "Nothing to update. Provide at least one of: "
            "--title, --history, --status, --field"
        )

    root = get_root(ctx)
    try:
        docs = scan_documents(root)
    except LayerValidationError as e:
        raise click.ClickException(str(e)) from e

    try:
        doc = find_document(docs, identifier)
    except DocumentNotFoundError as e:
        raise click.ClickException(str(e)) from e
    except AmbiguousDocumentError as e:
        raise click.ClickException(str(e)) from e

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
            mismatches.append(f"type '{h1_typ}' vs filename type_code '{doc.type_code}'")
        if h1_acid != doc.acid:
            mismatches.append(f"ACID '{h1_acid}' vs filename ACID '{doc.acid}'")
        if mismatches:
            click.echo(
                f"Warning: H1 mismatch in {doc.filename}: {'; '.join(mismatches)}",
                err=True,
            )

    # ── Step 1: Validate all options ────────────────────────────────────────

    # Collect all field updates to validate
    field_updates: dict[str, str] = {}
    if status is not None:
        field_updates["Status"] = status
    for key, value in field:
        field_updates[key] = value

    # Validate that all requested fields exist
    existing_keys = {mf.key for mf in parsed.metadata_fields}
    for key in field_updates:
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
            raise click.ClickException("Title must not have leading/trailing whitespace")
        if "/" in new_title or "\\" in new_title:
            raise click.ClickException("Title must not contain path separators (/ or \\)")

        # Build new filename
        new_filename = f"{doc.prefix}-{doc.acid}-{doc.type_code}-{new_title.replace(' ', '-')}.md"
        if not FILENAME_PATTERN.match(new_filename):
            raise click.ClickException(
                f"Generated filename '{new_filename}' does not match required pattern "
                f"(^[A-Z]{{3}}-\\d{{4}}-[A-Z]{{3}}-.+\\.md$)"
            )

        new_file_path = file_path.parent / new_filename
        if new_file_path.exists() and new_file_path != file_path:
            raise click.ClickException(
                f"Target path already exists: {new_file_path}"
            )

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

    # Atomic write: temp file -> rename
    fd, tmp_path_str = tempfile.mkstemp(
        dir=str(file_path.parent), suffix=".md.tmp"
    )
    try:
        with os.fdopen(fd, "w") as f:
            f.write(new_content)
        os.replace(tmp_path_str, str(file_path))
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path_str)
        except OSError:
            pass
        raise

    # ── Step 7: Post-write — rename file and auto-index ─────────────────────

    if new_title is not None and new_file_path is not None and new_file_path != file_path:
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
