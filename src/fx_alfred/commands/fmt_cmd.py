"""af fmt command — format Alfred documents to canonical style (FXA-2141)."""

from __future__ import annotations

import difflib
import re
from pathlib import Path

import click

from fx_alfred.commands._helpers import atomic_write, find_or_fail, scan_or_fail
from fx_alfred.context import root_option
from fx_alfred.core.normalize import sort_metadata
from fx_alfred.core.parser import (
    MalformedDocumentError,
    MetadataField,
    ParsedDocument,
    parse_metadata,
    render_document,
)
from fx_alfred.core.schema import DocType


_EPILOG = """\
Examples:

  af fmt TST-2100                # Show diff for one document
  af fmt TST-2100 TST-2101       # Show diff for multiple documents
  af fmt                         # Format all PRJ-layer documents
  af fmt --write TST-2100        # Apply changes in-place
  af fmt --check                 # CI check: exit 1 if changes needed
"""


# ── Normalizers ──────────────────────────────────────────────────────────────


def normalize_metadata_order(parsed: ParsedDocument, doc_type: DocType | None) -> bool:
    """Reorder metadata fields to canonical order.

    Returns True if any changes were made (order changed).
    """
    if doc_type is None:
        return False

    current_keys = [mf.key for mf in parsed.metadata_fields]
    canonical_keys = sort_metadata(current_keys, doc_type)

    # List-based reorder — preserves all fields including duplicates
    ordered_fields: list[MetadataField] = []
    remaining = list(parsed.metadata_fields)
    for key in canonical_keys:
        for i, mf in enumerate(remaining):
            if mf.key == key:
                ordered_fields.append(remaining.pop(i))
                break
    ordered_fields.extend(remaining)

    # Same objects in same order = no change (dataclass __eq__ compares all fields)
    if ordered_fields == parsed.metadata_fields:
        return False

    parsed.metadata_fields = ordered_fields
    for mf in parsed.metadata_fields:
        mf.dirty = True
    return True


def normalize_tags(parsed: ParsedDocument) -> bool:
    """Normalize Tags metadata field: lowercase, sort, deduplicate.

    Returns True if any changes were made.
    """
    tag_field = next(
        (mf for mf in parsed.metadata_fields if mf.key == "Tags"), None
    )
    if tag_field is None:
        return False

    from fx_alfred.core.parser import parse_tags

    tags = parse_tags(tag_field.value)
    normalized = ", ".join(sorted(set(tags)))

    if normalized == tag_field.value:
        return False

    tag_field.value = normalized
    tag_field.dirty = True
    return True


def normalize_trailing_whitespace(parsed: ParsedDocument) -> bool:
    """Strip trailing whitespace from metadata values.

    Checks raw_line for trailing whitespace and marks field dirty if found.
    The value is already stripped by the parser, but raw_line preserves it.

    Returns True if any changes were made.
    """
    changed = False
    for mf in parsed.metadata_fields:
        # Check raw_line for trailing whitespace (value is already stripped by parser)
        if mf.raw_line.rstrip() != mf.raw_line:
            # Strip the value and mark dirty
            mf.value = mf.value.rstrip()
            mf.dirty = True
            changed = True
    return changed


def normalize_blank_lines_in_body(parsed: ParsedDocument) -> bool:
    """Normalize blank lines in the body section.

    Rules:
    - 1 blank line between --- separator and H2
    - 2 blank lines between content and H2
    - No runs of 2+ blank lines in non-heading content (collapse to 1)
    - Fence-aware: content inside ``` blocks is left unchanged

    Returns True if any changes were made.
    """
    if not parsed.body:
        return False

    lines = parsed.body.split("\n")
    result: list[str] = []
    in_fence = False

    for line in lines:
        # Track fence state (lines starting with ```)
        if line.strip().startswith("```"):
            in_fence = not in_fence
            result.append(line)
            continue

        # Inside fence: pass through unchanged
        if in_fence:
            result.append(line)
            continue

        # Outside fence: apply normalization
        # Check if this is an H2 heading (## heading, but not in fence)
        if line.strip().startswith("## "):
            # Determine how many blank lines should precede this H2
            # Find the last non-blank line
            last_content = ""
            if result:
                for j in range(len(result) - 1, -1, -1):
                    if result[j].strip():
                        last_content = result[j].strip()
                        break

            # Rule: if last content was ---, want 1 blank line
            # Otherwise, want 2 blank lines
            desired_blanks = 1 if last_content == "---" else 2

            # Remove excess blanks
            while result and result[-1].strip() == "":
                result.pop()

            # Add exactly the desired number of blank lines
            for _ in range(desired_blanks):
                result.append("")

            result.append(line)
        else:
            # Not an H2 heading
            # Collapse runs of blank lines to single blank line
            if line.strip() == "":
                # Only add a blank line if the previous line was non-blank
                if result and result[-1].strip() != "":
                    result.append(line)
                # Skip consecutive blank lines
            else:
                result.append(line)

    new_body = "\n".join(result)
    if new_body != parsed.body:
        parsed.body = new_body
        return True
    return False


def normalize_table_alignment(parsed: ParsedDocument) -> bool:
    """Align Change History table columns to equal width.

    Pads cells in header, separator, and data rows so all columns
    have the same width across all rows.

    Returns True if any changes were made.
    """
    if not parsed.history_header:
        return False

    # Parse the header to get column count
    header_lines = parsed.history_header.split("\n")
    if len(header_lines) < 2:
        return False

    header_line = None
    sep_line = None
    heading_line = ""

    for line in header_lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            heading_line = line
        elif stripped.startswith("|") and stripped.endswith("|"):
            if "---" in stripped:
                sep_line = stripped
            elif header_line is None:
                header_line = stripped

    if header_line is None or sep_line is None:
        return False

    # Parse all rows to get cells
    def parse_row(line: str) -> list[str]:
        inner = line.strip()[1:-1]  # Remove leading/trailing pipes
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", inner)]
        return cells

    def render_row(cells: list[str], widths: list[int]) -> str:
        padded = [c.ljust(w) if w > 0 else c for c, w in zip(cells, widths)]
        return "| " + " | ".join(padded) + " |"

    def render_sep(widths: list[int]) -> str:
        return "|" + "|".join("-" * (w + 2) for w in widths) + "|"

    header_cells = parse_row(header_line)
    num_cols = len(header_cells)

    # Collect all row DATA values (not the padded header text)
    # For header, we use the cell values without padding
    # For data rows, we use the HistoryRow values
    all_row_data: list[list[str]] = [header_cells]
    for row in parsed.history_rows:
        row_cells = [row.date, row.change, row.by]
        # Pad to num_cols
        while len(row_cells) < num_cols:
            row_cells.append("")
        all_row_data.append(row_cells[:num_cols])

    # Compute max width for each column based on DATA values
    widths = [0] * num_cols
    for row in all_row_data:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(cell))

    # Compute new rendered strings
    new_header_str = render_row(header_cells, widths)
    new_sep_str = render_sep(widths)
    new_rows = []
    for row in parsed.history_rows:
        row_cells = [row.date.strip(), row.change.strip(), row.by.strip()]
        while len(row_cells) < num_cols:
            row_cells.append("")
        new_rows.append(render_row(row_cells[:num_cols], widths))

    # Get original rendered rows for comparison
    original_rows = []
    for row in parsed.history_rows:
        row_cells = [row.date, row.change, row.by]
        while len(row_cells) < num_cols:
            row_cells.append("")
        original_rows.append("| " + " | ".join(c for c in row_cells[:num_cols]) + " |")

    if (
        header_line == new_header_str
        and sep_line == new_sep_str
        and all(a == b for a, b in zip(original_rows, new_rows))
        and len(original_rows) == len(new_rows)
    ):
        return False

    # Apply changes
    parsed.history_header = f"{heading_line}\n\n{new_header_str}\n{new_sep_str}"
    for row in parsed.history_rows:
        cells = [row.date.strip(), row.change.strip(), row.by.strip()]
        while len(cells) < num_cols:
            cells.append("")
        cells = cells[:num_cols]
        if num_cols > 0:
            row.date = cells[0].ljust(widths[0]) if widths[0] > 0 else cells[0]
        if num_cols > 1:
            row.change = cells[1].ljust(widths[1]) if widths[1] > 0 else cells[1]
        if num_cols > 2:
            row.by = cells[2].ljust(widths[2]) if widths[2] > 0 else cells[2]
    return True


def format_document(parsed: ParsedDocument, doc_type: DocType | None) -> bool:
    """Apply all normalizations to a parsed document.

    Returns True if any changes were made.
    """
    changed = False
    changed |= normalize_metadata_order(parsed, doc_type)
    changed |= normalize_tags(parsed)
    changed |= normalize_trailing_whitespace(parsed)
    changed |= normalize_blank_lines_in_body(parsed)
    changed |= normalize_table_alignment(parsed)
    return changed


# ─- Command Implementation ───────────────────────────────────────────────────


@click.command("fmt", epilog=_EPILOG)
@root_option
@click.argument("doc_ids", nargs=-1, required=False)
@click.option(
    "--write", "write_", is_flag=True, default=False, help="Apply changes in-place"
)
@click.option(
    "--check",
    is_flag=True,
    default=False,
    help="Print what would change, exit 1 if changes needed",
)
@click.pass_context
def fmt_cmd(
    ctx: click.Context, doc_ids: tuple[str, ...], write_: bool, check: bool
) -> None:
    """Format Alfred documents to canonical style.

    By default, shows a unified diff of what would change.
    With --write, applies changes in-place.
    With --check, prints doc IDs needing changes and exits 1 if any.
    """
    # Validate mutually exclusive options
    if write_ and check:
        raise click.ClickException("--check and --write cannot be used together")

    docs = scan_or_fail(ctx)

    # Track errors during doc_id lookup
    lookup_errors = False

    # If no doc_ids specified, format all PRJ-layer documents
    if not doc_ids:
        target_docs = [d for d in docs if d.source == "prj"]
        if not target_docs:
            click.echo("No PRJ-layer documents found.")
            return
    else:
        target_docs = []
        for doc_id in doc_ids:
            try:
                doc = find_or_fail(docs, doc_id)
                target_docs.append(doc)
            except click.ClickException as e:
                click.echo(str(e), err=True)
                lookup_errors = True
                continue

    # Track results
    docs_changed: list[str] = []
    docs_unchanged: list[str] = []
    docs_skipped: list[str] = []
    docs_error: list[
        str
    ] = []  # Documents with errors (parse error, file not found, etc.)

    for doc in target_docs:
        # Skip PKG-layer documents
        if doc.source == "pkg":
            click.echo(
                f"{doc.prefix}-{doc.acid} is in the read-only PKG layer, skipping."
            )
            docs_skipped.append(f"{doc.prefix}-{doc.acid}")
            continue

        # Resolve file path
        resource = doc.resolve_resource()
        file_path = Path(str(resource))

        if not file_path.exists():
            click.echo(f"Error: File not found for {doc.prefix}-{doc.acid}", err=True)
            docs_error.append(f"{doc.prefix}-{doc.acid}")
            continue

        # Read and parse
        try:
            content = file_path.read_text()
            parsed = parse_metadata(content)
        except MalformedDocumentError as e:
            click.echo(f"Error parsing {doc.prefix}-{doc.acid}: {e}", err=True)
            docs_error.append(f"{doc.prefix}-{doc.acid}")
            continue
        except Exception as e:
            click.echo(f"Error reading {doc.prefix}-{doc.acid}: {e}", err=True)
            docs_error.append(f"{doc.prefix}-{doc.acid}")
            continue

        # Determine document type
        try:
            doc_type = DocType(doc.type_code)
        except ValueError:
            doc_type = None

        # Apply normalizations — use rendered-output diff as truth (not normalizer return values)
        format_document(parsed, doc_type)
        new_content = render_document(parsed)
        if new_content == content:
            docs_unchanged.append(f"{doc.prefix}-{doc.acid}")
            continue

        docs_changed.append(f"{doc.prefix}-{doc.acid}")

        # Handle output modes
        if check:
            # Print what would change
            click.echo(f"{doc.prefix}-{doc.acid} needs formatting")
        elif write_:
            # Write changes in-place
            atomic_write(file_path, new_content)

            click.echo(f"Formatted {doc.prefix}-{doc.acid}")
        else:
            # Default mode: show unified diff
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

    # Final output
    if not docs_changed and not docs_skipped and not docs_error and not lookup_errors:
        click.echo("All documents already formatted.")
    elif check and docs_changed:
        ctx.exit(1)
    elif docs_error or lookup_errors:
        # Exit with error if any documents had errors
        ctx.exit(1)
