"""Normalization utilities for Alfred document fields."""

import re
from datetime import datetime

from fx_alfred.core.schema import DocType, REQUIRED_METADATA


def slugify(title: str) -> str:
    """Convert a document title to a safe, cross-platform filename slug."""
    s = title.strip()
    if not s:
        return ""
    # Remove path-unsafe characters only (Windows + POSIX reserved chars)
    s = re.sub(r'[\\/:*?"<>|]', "", s)
    # Replace whitespace runs with single hyphen
    s = re.sub(r"\s+", "-", s)
    # Collapse multiple hyphens
    s = re.sub(r"-{2,}", "-", s)
    # Strip leading/trailing hyphens
    s = s.strip("-")
    return s


def normalize_date(s: str) -> str:
    """Normalize date string to YYYY-MM-DD. Returns original if unparseable."""
    # Already in YYYY-MM-DD format
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s
    # Try common formats
    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return s


KNOWN_OPTIONAL_ORDER = [
    "Related", "Reviewed by", "Last executed", "Severity",
    "Date", "Requested by", "Priority", "Change Type",
    "Document role", "Tags",
]


def sort_metadata(fields: list[str], doc_type: DocType) -> list[str]:
    """Return fields in canonical order. Required first, then known optional, then unknown."""
    canonical = REQUIRED_METADATA.get(doc_type, [])
    canonical_set = set(canonical)
    optional_set = set(KNOWN_OPTIONAL_ORDER)

    # Required fields in canonical order
    ordered = [f for f in canonical if f in fields]
    # Known optional fields in defined order
    ordered += [f for f in KNOWN_OPTIONAL_ORDER if f in fields and f not in canonical_set]
    # Truly unknown fields in original relative order
    ordered += [f for f in fields if f not in canonical_set and f not in optional_set]
    return ordered


def strip_trailing_whitespace(lines: list[str]) -> list[str]:
    """Strip trailing whitespace from each line. Returns new list."""
    return [line.rstrip() for line in lines]
