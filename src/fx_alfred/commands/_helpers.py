"""Shared helpers for CLI commands — wraps core functions with Click error handling."""

import os
import tempfile
from pathlib import Path
from typing import Any

import click

from fx_alfred.context import get_root
from fx_alfred.core.document import Document
from fx_alfred.core.scanner import (
    AmbiguousDocumentError,
    DocumentNotFoundError,
    LayerValidationError,
    find_document,
    scan_documents,
)
from fx_alfred.core.schema import ALLOWED_STATUSES, DocType


def scan_or_fail(ctx: click.Context) -> list[Document]:
    """Scan documents, converting LayerValidationError to ClickException."""
    root = get_root(ctx)
    try:
        return scan_documents(root)
    except LayerValidationError as e:
        raise click.ClickException(str(e)) from e


def find_or_fail(docs: list[Document], identifier: str) -> Document:
    """Find document by identifier, converting lookup errors to ClickException."""
    try:
        return find_document(docs, identifier)
    except (DocumentNotFoundError, AmbiguousDocumentError) as e:
        raise click.ClickException(str(e)) from e


def validate_spec_status(doc_type: DocType, status: str) -> None:
    """Validate status for the given document type."""
    allowed = ALLOWED_STATUSES.get(doc_type, [])
    if status not in allowed:
        allowed_str = ", ".join(allowed)
        raise click.ClickException(
            f"Status '{status}' not allowed for {doc_type.value}; allowed: {allowed_str}"
        )


def render_section_content(content: Any) -> str:
    """Render section content to markdown text."""
    if isinstance(content, list):
        lines = []
        for item in content:
            lines.append(f"- {item}")
        return "\n".join(lines)
    elif isinstance(content, str):
        return content
    else:
        return str(content)


def atomic_write(path: Path, content: str) -> None:
    """Write content to a file atomically using temp file + os.replace.

    Creates a temporary file in the same directory, writes content to it,
    then atomically replaces the target file. On failure, cleans up the
    temporary file without modifying the original.

    Args:
        path: Target file path to write to.
        content: String content to write.

    Raises:
        OSError: If file operations fail (propagated after cleanup).
    """
    fd, tmp_path_str = tempfile.mkstemp(dir=str(path.parent), suffix=".md.tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.replace(tmp_path_str, str(path))
    except Exception:
        # Clean up temp file on any failure
        try:
            os.unlink(tmp_path_str)
        except OSError:
            pass
        raise
