"""Tests for core/normalize.py — normalization utilities."""

from fx_alfred.core.normalize import (
    slugify,
    normalize_date,
    sort_metadata,
    strip_trailing_whitespace,
)
from fx_alfred.core.schema import DocType


def test_slugify_hello_world():
    assert slugify("Hello World") == "Hello-World"


def test_slugify_trims_whitespace():
    assert slugify("  trim  ") == "trim"


def test_slugify_removes_unsafe_chars():
    result = slugify("path/unsafe:chars?")
    assert result == "pathunsafechars"
    assert "/" not in result
    assert ":" not in result
    assert "?" not in result


def test_slugify_preserves_underscores():
    assert slugify("Hello_World") == "Hello_World"


def test_slugify_multiple_spaces():
    assert slugify("multiple   spaces") == "multiple-spaces"


def test_slugify_leading_trailing_hyphens():
    assert slugify("--leading-trailing--") == "leading-trailing"


def test_slugify_empty_string():
    assert slugify("") == ""


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


def test_strip_trailing_whitespace_removes_trailing():
    result = strip_trailing_whitespace(["hello   ", "world", "  "])
    assert result == ["hello", "world", ""]


def test_strip_trailing_whitespace_empty_list():
    assert strip_trailing_whitespace([]) == []


def test_normalize_date_passthrough():
    assert normalize_date("2026-03-22") == "2026-03-22"


def test_normalize_date_unparseable_returns_original():
    assert normalize_date("not-a-date") == "not-a-date"
