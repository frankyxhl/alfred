"""Document metadata parser and renderer.

Parses Alfred documents into structured components (H1, metadata fields,
body, Change History) and reconstructs them preserving original formatting.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field


class MalformedDocumentError(Exception):
    """Raised when a document does not match the expected structure."""


@dataclass
class MetadataField:
    """A single metadata field from the document header."""

    key: str
    value: str
    prefix_style: str  # "bold" for "**Key:** value", "list" for "- **Key:** value"
    raw_line: str  # original line for round-trip fidelity
    dirty: bool = False  # True when value has been modified (forces re-render)


@dataclass
class HistoryRow:
    """A single row in the Change History table."""

    date: str
    change: str
    by: str


@dataclass
class ParsedDocument:
    """Structured representation of a parsed Alfred document."""

    h1_line: str  # full H1 line, e.g. "# SOP-1300: Update Document"
    metadata_fields: list[MetadataField] = field(default_factory=list)
    blank_after_h1: int = 0  # number of blank lines between H1 and first metadata field
    blank_after_metadata: int = (
        0  # number of blank lines between last field and first ---
    )
    body: str = (
        ""  # everything between first --- and Change History (inclusive of separators)
    )
    history_header: str = ""  # the "## Change History" line + table header rows
    history_rows: list[HistoryRow] = field(default_factory=list)
    trailing: str = ""  # anything after the last history row
    has_trailing_newline: bool = False  # whether original document ended with \n


# Patterns for metadata field lines
_BOLD_FIELD = re.compile(r"^\*\*(.+?):\*\*\s*(.*)")
_LIST_FIELD = re.compile(r"^- \*\*(.+?):\*\*\s*(.*)")

# H1 must follow the Document Structure Contract: # <TYP>-<ACID>: <Title>
H1_PATTERN = re.compile(r"^# (?P<type_code>[A-Z]{3})-(?P<acid>\d{4}): .+$")


def parse_metadata(content: str) -> ParsedDocument:
    """Parse an Alfred document into structured components.

    Raises:
        MalformedDocumentError: if document structure is invalid.
    """
    lines = content.split("\n")

    if not lines or not lines[0].startswith("# "):
        raise MalformedDocumentError(
            "Malformed document: first line is not a valid H1 header"
        )

    if not H1_PATTERN.match(lines[0]):
        raise MalformedDocumentError(
            "Malformed document: H1 does not match expected format '# <TYP>-<ACID>: <Title>'"
        )

    has_trailing_newline = content.endswith("\n")
    h1_line = lines[0]

    # Find the first --- separator
    sep_index = None
    for i in range(1, len(lines)):
        stripped = lines[i].strip()
        if stripped == "---":
            sep_index = i
            break

    if sep_index is None:
        raise MalformedDocumentError(
            "Malformed document: missing metadata separator '---'"
        )

    # Collect blank lines immediately after H1
    blank_after_h1_count = 0
    first_non_blank = 1
    for i in range(1, sep_index):
        if not lines[i].strip():
            blank_after_h1_count += 1
            first_non_blank = i + 1
        else:
            break

    # Parse metadata fields between H1 and first ---
    metadata_fields: list[MetadataField] = []
    blank_lines_before_sep: list[str] = []

    for i in range(first_non_blank, sep_index):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            blank_lines_before_sep.append(line)
            continue

        list_match = _LIST_FIELD.match(stripped)
        bold_match = _BOLD_FIELD.match(stripped)

        if list_match:
            # Drain any accumulated blank lines (they were between fields)
            blank_lines_before_sep.clear()
            metadata_fields.append(
                MetadataField(
                    key=list_match.group(1),
                    value=list_match.group(2),
                    prefix_style="list",
                    raw_line=line,
                )
            )
        elif bold_match:
            blank_lines_before_sep.clear()
            metadata_fields.append(
                MetadataField(
                    key=bold_match.group(1),
                    value=bold_match.group(2),
                    prefix_style="bold",
                    raw_line=line,
                )
            )
        else:
            # Non-blank, non-field line in metadata block — skip
            blank_lines_before_sep.clear()

    if not metadata_fields:
        raise MalformedDocumentError("No metadata fields found in document")

    blank_after_metadata_count = len(blank_lines_before_sep)

    # Everything from first --- onward is body + change history
    rest_lines = lines[sep_index:]
    rest_text = "\n".join(rest_lines)

    # Try to find "## Change History" section
    history_section_idx = None
    for i, line in enumerate(rest_lines):
        if line.strip() == "## Change History":
            history_section_idx = i
            break

    if history_section_idx is None:
        # No change history section
        return ParsedDocument(
            h1_line=h1_line,
            metadata_fields=metadata_fields,
            blank_after_h1=blank_after_h1_count,
            blank_after_metadata=blank_after_metadata_count,
            body=rest_text,
            history_header="",
            history_rows=[],
            trailing="",
            has_trailing_newline=has_trailing_newline,
        )

    # Body is everything before the Change History heading
    body_lines = rest_lines[:history_section_idx]
    body = "\n".join(body_lines)

    # Parse history section
    history_lines = rest_lines[history_section_idx:]

    # Find the table header (| Date | Change | By |) and separator (|---|---|---|)
    table_header_end = None
    for i in range(1, len(history_lines)):
        stripped = history_lines[i].strip()
        if stripped.startswith("|") and "---" in stripped:
            table_header_end = i
            break

    if table_header_end is None:
        # Change History heading exists but no table — treat entire section as body
        return ParsedDocument(
            h1_line=h1_line,
            metadata_fields=metadata_fields,
            blank_after_h1=blank_after_h1_count,
            blank_after_metadata=blank_after_metadata_count,
            body=rest_text,
            history_header="",
            history_rows=[],
            trailing="",
            has_trailing_newline=has_trailing_newline,
        )

    history_header = "\n".join(history_lines[: table_header_end + 1])

    # Parse data rows
    rows: list[HistoryRow] = []
    trailing_lines: list[str] = []
    data_done = False
    for i in range(table_header_end + 1, len(history_lines)):
        line = history_lines[i]
        stripped = line.strip()
        if not data_done and stripped.startswith("|") and stripped.endswith("|"):
            # Strip leading/trailing pipes, then split on unescaped pipes
            inner = stripped[1:-1]
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", inner)]
            rows.append(
                HistoryRow(
                    date=cells[0] if cells else "",
                    change=cells[1] if len(cells) > 1 else "",
                    by=cells[2] if len(cells) > 2 else "",
                )
            )
        else:
            data_done = True
            trailing_lines.append(line)

    trailing = "\n".join(trailing_lines)

    return ParsedDocument(
        h1_line=h1_line,
        metadata_fields=metadata_fields,
        blank_after_h1=blank_after_h1_count,
        blank_after_metadata=blank_after_metadata_count,
        body=body,
        history_header=history_header,
        history_rows=rows,
        trailing=trailing,
        has_trailing_newline=has_trailing_newline,
    )


def render_document(parsed: ParsedDocument) -> str:
    """Reconstruct a document from parsed components.

    Preserves original body, whitespace, separators, and metadata field prefix style.
    Uses raw_line for fields that weren't modified (preserves exact original formatting).
    """
    lines: list[str] = []

    # H1
    lines.append(parsed.h1_line)

    # Blank line(s) between H1 and first metadata field
    for _ in range(parsed.blank_after_h1):
        lines.append("")

    # Metadata fields — use raw_line for unmodified fields, regenerate for dirty ones
    for mf in parsed.metadata_fields:
        if mf.dirty:
            if mf.prefix_style == "list":
                lines.append(f"- **{mf.key}:** {mf.value}")
            else:
                lines.append(f"**{mf.key}:** {mf.value}")
        else:
            lines.append(mf.raw_line)

    # Blank lines between metadata and separator
    for _ in range(parsed.blank_after_metadata):
        lines.append("")

    # Body (starts with first --- separator)
    if parsed.body:
        lines.append(parsed.body)

    # Change History section
    if parsed.history_header:
        lines.append(parsed.history_header)
        for row in parsed.history_rows:
            lines.append(f"| {row.date} | {row.change} | {row.by} |")
        if parsed.trailing:
            lines.append(parsed.trailing)

    result = "\n".join(lines)
    if parsed.has_trailing_newline and not result.endswith("\n"):
        result += "\n"
    return result


def parse_tags(value: str) -> list[str]:
    """Split comma-separated tags, strip whitespace, filter empty, lowercase."""
    return [t.strip().lower() for t in value.split(",") if t.strip()]


def _fence_run_length(stripped: str, ch: str) -> int:
    """Return the length of the leading run of ``ch`` in ``stripped`` (0 if none)."""
    run = 0
    while run < len(stripped) and stripped[run] == ch:
        run += 1
    return run


def iter_lines_with_fence_state(text: str) -> Iterator[tuple[str, bool]]:
    """Yield ``(line, fenced)`` for each line of ``text``.

    ``fenced`` is True for fence opener lines, fence closer lines, and every
    line in between — i.e. lines that markdown structure matching (headings,
    step numbers) must ignore.

    Fence matching follows CommonMark rules (same discipline as the step
    parsers in ``core/steps.py``, PR #59 reviews P2 #4/#7/#8):

    - Opener is a run of 3 or more backtick or tilde characters.
    - Closer must use the **same character** AND be a run of **at least
      as many** characters as the opener.
    """
    fence_char: str | None = None  # '`' or '~' or None
    fence_len = 0
    for line in text.split("\n"):
        stripped = line.lstrip()
        if fence_char is not None:
            # Inside a fence — closer must be the same char with len >= opener.
            if stripped and stripped[0] == fence_char:
                run = _fence_run_length(stripped, fence_char)
                if run >= fence_len:
                    fence_char = None
                    fence_len = 0
            yield line, True
            continue
        # Outside any fence — check for an opener (≥3 run of ` or ~).
        if stripped and stripped[0] in ("`", "~"):
            ch = stripped[0]
            run = _fence_run_length(stripped, ch)
            if run >= 3:
                fence_char = ch
                fence_len = run
                yield line, True
                continue
        yield line, False


def extract_section(body: str, heading: str) -> str | None:
    """Extract a section from document body by heading name.

    Searches for ``## {heading}`` or ``### {heading}`` (line-start anchored).
    Returns text from after the heading until the next heading of same or higher
    level, or end of body.  Returns ``None`` if no matching heading is found.

    Lines inside fenced code blocks are ignored for both the heading match
    and the boundary search, so column-0 ``#`` lines in code samples (e.g.
    bash comments) neither start nor terminate a section (CHG-2294).
    """
    annotated = list(iter_lines_with_fence_state(body))
    # Try ## first, then ###
    for prefix in ("##", "###"):
        heading_re = re.compile(rf"^{re.escape(prefix)}\s+{re.escape(heading)}\s*$")
        start_idx = next(
            (
                i
                for i, (line, fenced) in enumerate(annotated)
                if not fenced and heading_re.match(line)
            ),
            None,
        )
        if start_idx is None:
            continue
        # Find next heading of same or higher level (number of '#')
        level = len(prefix)
        boundary_re = re.compile(rf"^#{{1,{level}}}\s+")
        end_idx = next(
            (
                j
                for j in range(start_idx + 1, len(annotated))
                if not annotated[j][1] and boundary_re.match(annotated[j][0])
            ),
            len(annotated),
        )
        section = "\n".join(line for line, _ in annotated[start_idx + 1 : end_idx])
        return section.strip()
    return None
