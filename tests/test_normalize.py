"""Tests for core/normalize.py — normalization utilities."""

import pytest


from fx_alfred.core.normalize import (
    slugify,
    normalize_date,
    sort_metadata,
    strip_trailing_whitespace,
)
from fx_alfred.core.schema import DocType


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
