"""Routing-document detection — shared by `af guide` and `af export`.

Extracted from guide_cmd (FXA-2303) so the two commands cannot drift on
what counts as a routing document: either the ``Document role: routing``
metadata field, or the legacy ``SOP-Workflow-Routing`` filename pattern.
"""

from __future__ import annotations

from fx_alfred.core.document import Document
from fx_alfred.core.parser import ParsedDocument
from fx_alfred.core.schema import ROUTING_ROLE_METADATA_KEY, ROUTING_ROLE_VALUE

ROUTING_FILENAME_PATTERN = "SOP-Workflow-Routing"


def document_status(parsed: ParsedDocument) -> str | None:
    """Return the document's ``Status:`` metadata value, or None."""
    return next((mf.value for mf in parsed.metadata_fields if mf.key == "Status"), None)


def is_routing_document(doc: Document, parsed: ParsedDocument) -> bool:
    """True when the document is a routing document (role metadata first,
    filename pattern fallback — same precedence as `af guide`)."""
    role = next(
        (
            mf.value
            for mf in parsed.metadata_fields
            if mf.key == ROUTING_ROLE_METADATA_KEY
        ),
        None,
    )
    return role == ROUTING_ROLE_VALUE or ROUTING_FILENAME_PATTERN in doc.filename
