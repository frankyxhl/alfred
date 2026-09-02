"""Shared helpers for CLI commands — wraps core functions with Click error handling."""

import importlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import click

from fx_alfred.context import get_root
from fx_alfred.core.document import Document
from fx_alfred.core.fsmode import resolve_write_mode
from fx_alfred.core.registry import (
    REGISTRY_FILENAME,
    load_registry,
    registry_path,
    save_registry,
    slot_conflict,
    today_str,
    upsert,
)
from fx_alfred.core.scanner import (
    AmbiguousDocumentError,
    DocumentNotFoundError,
    LayerValidationError,
    find_document,
    scan_documents,
)
from fx_alfred.core.schema import ALLOWED_STATUSES, DocType
from fx_alfred.core.source import SOURCE_LABELS

# Commands-layer JSON envelope version (CHG-2301). Schema families owned
# by core keep their own constants (core.skills / core.agent_helpers);
# plan_cmd versions its payload shape independently.
SCHEMA_VERSION = "1"

# Shared read-only guard message — used by update_cmd, tag_cmd (add/rm).
PKG_READONLY_MSG = "Cannot update PKG layer documents. They are read-only."


class ExitCodeError(click.ClickException):
    """ClickException with a caller-specified exit code.

    Click 8.4 types ``ClickException.exit_code`` as a ClassVar, so assigning it
    on an instance fails type checking. Re-declaring it as an instance attribute
    restores the per-instance exit code without changing runtime behavior.
    """

    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code  # type: ignore[misc]


def emit_json(data: Any) -> None:
    """Emit ``data`` as the canonical CLI JSON form (CHG-2301).

    indent=2 for human inspection, ensure_ascii=False so CJK content
    renders as written. All command --json output goes through here
    (enforced by tests/test_architecture.py).
    """
    click.echo(json.dumps(data, indent=2, ensure_ascii=False))


def format_doc_row(doc: Document) -> str:
    """Format a document as a single-line list row (same as `af list` output)."""
    label = SOURCE_LABELS.get(doc.source, "???")
    return f"{label:<3}  {doc.prefix}-{doc.acid}  {doc.type_code:<3}  {doc.title}"


def scan_or_fail(ctx: click.Context) -> list[Document]:
    """Scan documents, converting LayerValidationError to ClickException."""
    root = get_root(ctx)
    try:
        return scan_documents(root)
    except LayerValidationError as e:
        raise click.ClickException(str(e)) from e


def registry_id_in_use(docs: list) -> bool:
    """True when any scanned document already carries the USR-9000 id.

    A PRJ (or any non-registry) document named USR-9000-*.md makes the
    registry write create a duplicate prefix+ACID across layers — every
    subsequent scan would fail LayerValidationError. The ONLY exemption is
    the canonical registry document itself: usr source, canonical filename,
    top-level ``~/.alfred`` location — a PRJ doc that merely carries the
    canonical filename is NOT exempt (PR #338 R5/R7 P1). The trigger must
    warn+skip and ``af register`` must refuse.
    """
    usr_home = (Path.home() / ".alfred").resolve()
    for d in docs:
        if d.prefix != "USR" or d.acid != "9000":
            continue
        if d.source == "usr" and d.filename == REGISTRY_FILENAME:
            try:
                if Path(d.base_path).resolve() == usr_home:
                    continue  # the registry itself
            except (TypeError, OSError):
                pass
        return True
    return False


def touch_project_registry(ctx: click.Context, docs: list[Document]) -> bool:
    """FXA-2330: background Project SOP Registry upsert for read commands.

    Called right after ``scan_or_fail`` by guide/list/read/status. When the
    PRJ layer contributed documents, upsert one row per (prefix, root) into
    ``~/.alfred/USR-9000-REF-Project-SOP-Registry.md``. Best-effort by
    contract: any failure — including registry write failure — is a
    one-line stderr warning and NEVER blocks the primary command. Silent
    on success so ``--json`` output stays pure.

    Returns True when the registry document was actually (re)written —
    ``read_cmd`` re-scans in that case so a first-ever ``af read USR-9000``
    finds the document the trigger itself just created (PR #338 R1).
    """
    prj_docs = [d for d in docs if d.source == "prj"]
    if not prj_docs:
        return False
    if registry_id_in_use(docs):
        click.echo(
            "Warning: a USR-9000 document already exists outside the project "
            "registry; skipping registry update to avoid a duplicate id.",
            err=True,
        )
        return False
    try:
        prefix_counts: dict[str, int] = {}
        for doc in prj_docs:
            prefix_counts[doc.prefix] = prefix_counts.get(doc.prefix, 0) + 1
        path = registry_path()
        entries = load_registry(path)
        # Ownership validation runs BEFORE the no-change short-circuit: a
        # foreign table-bearing doc that happens to parse with matching
        # rows must still warn+skip, not silently count as "ours" (PR #338
        # R11).
        conflict = slot_conflict(path)
        if conflict is not None:
            click.echo(
                f"Warning: {conflict.name} already occupies the USR-9000 "
                "slot; skipping registry update.",
                err=True,
            )
            return False
        new_entries, changed = upsert(
            entries,
            root=get_root(ctx),
            prefix_counts=prefix_counts,
            today=today_str(),
        )
        if changed:
            save_registry(path, new_entries, today=today_str())
            return True
        return False
    except Exception as e:  # noqa: BLE001 — catalog maintenance must never kill the command
        click.echo(f"Warning: project registry update failed: {e}", err=True)
        return False


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
    mode = resolve_write_mode(path)

    fd, tmp_path_str = tempfile.mkstemp(dir=str(path.parent), suffix=".md.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.chmod(tmp_path_str, mode)
        os.replace(tmp_path_str, str(path))
    except Exception:
        # Clean up temp file on any failure
        try:
            os.unlink(tmp_path_str)
        except OSError:
            pass
        raise


def invoke_index_update(ctx: click.Context) -> None:
    """Invoke index_cmd to regenerate document index.

    Lazy-imports index_cmd to avoid circular imports, then invokes it
    with the given context. On failure, emits a warning to stderr.

    Args:
        ctx: Click context to invoke the command with.
    """
    try:
        index_cmd_module = importlib.import_module("fx_alfred.commands.index_cmd")
        ctx.invoke(index_cmd_module.index_cmd)
    except Exception as e:
        click.echo(f"Warning: Failed to update index: {e}", err=True)
