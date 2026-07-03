"""Tests for core/normalize.py — normalization utilities."""

import pytest


from fx_alfred.core.normalize import (
    KNOWN_OPTIONAL_ORDER,
    slugify,
    normalize_date,
    sort_metadata,
    strip_trailing_whitespace,
)
from fx_alfred.core.schema import OPTIONAL_METADATA, DocType


pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Hello World", "Hello-World"),
        ("  trim  ", "trim"),
        ("path/unsafe:chars?", "pathunsafechars"),
        ("Hello_World", "Hello_World"),
        ("multiple   spaces", "multiple-spaces"),
        ("--leading-trailing--", "leading-trailing"),
        ("", ""),
    ],
    ids=[
        "spaces-to-dashes",
        "trim-whitespace",
        "remove-unsafe-chars",
        "preserve-underscores",
        "collapse-spaces",
        "strip-edge-dashes",
        "empty-string",
    ],
)
def test_slugify(value, expected):
    assert slugify(value) == expected


def test_slugify_removes_path_separators():
    result = slugify("path/unsafe:chars?")
    assert "/" not in result
    assert ":" not in result
    assert "?" not in result


def test_sort_metadata_canonical_order():
    fields = ["Status", "Applies to", "Last updated", "Last reviewed"]
    result = sort_metadata(fields, DocType.SOP)
    assert result == ["Applies to", "Last updated", "Last reviewed", "Status"]


def test_sort_metadata_unknown_field_appended():
    fields = ["Status", "Unknown field", "Applies to", "Last updated", "Last reviewed"]
    result = sort_metadata(fields, DocType.SOP)
    assert result == [
        "Applies to",
        "Last updated",
        "Last reviewed",
        "Status",
        "Unknown field",
    ]


def test_sort_metadata_empty():
    assert sort_metadata([], DocType.SOP) == []


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        (["hello   ", "world", "  "], ["hello", "world", ""]),
        ([], []),
    ],
    ids=["removes-trailing", "empty-list"],
)
def test_strip_trailing_whitespace(lines, expected):
    assert strip_trailing_whitespace(lines) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-03-22", "2026-03-22"),
        ("not-a-date", "not-a-date"),
    ],
    ids=["valid-date", "unparseable"],
)
def test_normalize_date(value, expected):
    assert normalize_date(value) == expected


# ---------------------------------------------------------------------------
# FXA-272: KNOWN_OPTIONAL_ORDER drift tests
# ---------------------------------------------------------------------------


def test_known_optional_order_covers_all_schema_optional_fields():
    """Every optional-metadata field name across all DocTypes must appear
    in KNOWN_OPTIONAL_ORDER, otherwise fmt sorts it into the unknown tail."""
    all_schema_fields: set[str] = set()
    for field_list in OPTIONAL_METADATA.values():
        all_schema_fields.update(field_list)

    known = set(KNOWN_OPTIONAL_ORDER)
    missing = sorted(all_schema_fields - known)
    assert missing == [], (
        f"OPTIONAL_METADATA fields missing from KNOWN_OPTIONAL_ORDER: {missing}"
    )


def test_sort_metadata_keeps_workflow_branches_adjacent():
    """Workflow branches must sort adjacent to Workflow loops, not after Tags.
    Disposition must sort before truly-unknown fields. X-Custom stays last."""
    fields = [
        "Tags",
        "Workflow loops",
        "Workflow branches",
        "Disposition",
        "X-Custom",
    ]
    result = sort_metadata(fields, DocType.SOP)

    # Workflow branches must appear before Tags (i.e. adjacent to Workflow
    # group, not dumped into the unknown tail after Tags).
    wb_idx = result.index("Workflow branches")
    tags_idx = result.index("Tags")
    assert wb_idx < tags_idx, (
        f"Workflow branches ({wb_idx}) must sort before Tags ({tags_idx}); got {result}"
    )

    # Disposition must sort before the truly-unknown X-Custom.
    disp_idx = result.index("Disposition")
    x_idx = result.index("X-Custom")
    assert disp_idx < x_idx, (
        f"Disposition ({disp_idx}) must sort before X-Custom ({x_idx}); got {result}"
    )

    # X-Custom must be last.
    assert result[-1] == "X-Custom", f"X-Custom must be last; got {result}"


def test_sort_metadata_idempotent():
    """Sorting twice must equal sorting once."""
    fields = [
        "Tags",
        "Workflow loops",
        "Workflow branches",
        "Disposition",
        "X-Custom",
    ]
    once = sort_metadata(fields, DocType.SOP)
    twice = sort_metadata(once, DocType.SOP)
    assert twice == once, f"sort_metadata not idempotent: {once} -> {twice}"
