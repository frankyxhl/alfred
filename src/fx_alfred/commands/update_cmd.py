"""af update command — structured metadata updates to existing documents."""

from __future__ import annotations

import difflib
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

import click
import yaml

from fx_alfred.commands._helpers import (
    PKG_READONLY_MSG,
    atomic_write,
    find_or_fail,
    invoke_index_update,
    render_section_content,
    scan_or_fail,
    validate_spec_status,
)
from fx_alfred.context import root_option
from fx_alfred.core.normalize import slugify
from fx_alfred.core.document import FILENAME_PATTERN
from fx_alfred.core.parser import (
    MalformedDocumentError,
    MetadataField,
    iter_lines_with_fence_state,
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


def _is_same_file(file_path: Path, new_file_path: Path) -> bool:
    try:
        # samefile checks same inode; keeps case-only renames on case-insensitive FS.
        return file_path.exists() and new_file_path.samefile(file_path)
    except OSError:
        return False


def _rename_case_only(file_path: Path, new_file_path: Path) -> None:
    tmp_path = file_path.with_name(f"{new_file_path.name}.{os.getpid()}.casefix.tmp")
    if tmp_path.exists():
        raise click.ClickException(f"Temporary rename path exists: {tmp_path}")
    file_path.rename(tmp_path)
    try:
        tmp_path.rename(new_file_path)
    except OSError as e:
        try:
            tmp_path.rename(file_path)
        except OSError as rollback_error:
            raise click.ClickException(
                f"Case-only rename failed; file remains at temporary path: {tmp_path}"
            ) from rollback_error
        raise click.ClickException(
            f"Case-only rename failed; restored original path: {file_path}"
        ) from e


def _replace_section_in_body(
    body: str, section_name: str, new_content: str
) -> tuple[str, bool]:
    """Replace a section in the body with new content.

    Returns tuple of (modified body, found flag). If section not found,
    returns (original body, False).
    """
    lines = body.split("\n")
    annotated = list(iter_lines_with_fence_state(body))
    heading_re = re.compile(rf"^##\s+{re.escape(section_name)}\s*$")

    start_idx = next(
        (
            i
            for i, (line, fenced) in enumerate(annotated)
            if not fenced and heading_re.match(line)
        ),
        None,
    )
    if start_idx is None:
        return body, False

    boundary_re = re.compile(r"^##\s+")
    end_idx = next(
        (
            i
            for i in range(start_idx + 1, len(annotated))
            if not annotated[i][1]
            and (boundary_re.match(annotated[i][0]) or annotated[i][0].strip() == "---")
        ),
        len(lines),
    )

    replacement_lines = lines[: start_idx + 1]
    replacement_lines.extend(new_content.split("\n"))
    replacement_lines.append("")
    replacement_lines.extend(lines[end_idx:])
    return "\n".join(replacement_lines), True


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
        raise click.ClickException(PKG_READONLY_MSG)

    # Resolve file path
    resource = doc.resolve_resource()
    file_path = Path(str(resource))
    content = file_path.read_text(encoding="utf-8")

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
            with open(spec_path, "r", encoding="utf-8") as f:
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
    status_changed = "Status" in field_updates

    # Validate effective Status against ALLOWED_STATUSES for the doc type.
    if status_changed and doc_type_enum:
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
        new_filename = (
            f"{doc.prefix}-{doc.acid}-{doc.type_code}-{slugify(new_title)}.md"
        )
        if not FILENAME_PATTERN.match(new_filename):
            raise click.ClickException(
                f"Generated filename '{new_filename}' does not match required pattern "
                f"(^[A-Z]{{3}}-\\d{{4}}-[A-Z]{{3}}-.+\\.md$)"
            )

        new_file_path = file_path.parent / new_filename
        is_same = _is_same_file(file_path, new_file_path)
        if new_file_path.exists() and not is_same:
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
        diff_lines = list(
            difflib.unified_diff(
                content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"{doc.filename}",
                tofile=f"{doc.filename}",
            )
        )
        for line in diff_lines:
            click.echo(line, nl=False)
        if new_title and new_filename:
            click.echo(f"\nRename: {file_path.name} -> {new_filename}")
        return

    # Atomic write
    atomic_write(file_path, new_content)

    # ── Step 7: Post-write — rename file and auto-index ─────────────────────
    renamed = (
        new_title is not None
        and new_file_path is not None
        and new_file_path != file_path
    )
    if renamed:
        assert new_file_path is not None
        case_only = file_path.name != new_file_path.name and _is_same_file(
            file_path, new_file_path
        )
        if case_only:
            _rename_case_only(file_path, new_file_path)
        else:
            file_path.rename(new_file_path)
        click.echo(f"Renamed {file_path.name} -> {new_file_path.name}")
    else:
        click.echo(f"Updated {file_path.name}")

    if doc.source == "prj" and (renamed or status_changed):
        invoke_index_update(ctx)
