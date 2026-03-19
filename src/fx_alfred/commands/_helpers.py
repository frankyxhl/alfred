"""Shared helpers for CLI commands — wraps core functions with Click error handling."""

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
