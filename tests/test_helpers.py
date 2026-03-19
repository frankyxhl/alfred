from unittest.mock import patch

import click
import pytest

from fx_alfred.commands._helpers import find_or_fail, scan_or_fail
from fx_alfred.core.document import Document
from fx_alfred.core.scanner import LayerValidationError


def test_scan_or_fail_returns_documents(sample_project):
    """scan_or_fail returns a non-empty list of Documents for a valid project."""
    ctx = click.Context(click.Command("test"), obj={"root": sample_project})
    docs = scan_or_fail(ctx)
    assert isinstance(docs, list)
    assert len(docs) > 0


def test_scan_or_fail_raises_click_exception_on_validation_error(tmp_path):
    """scan_or_fail converts LayerValidationError to ClickException."""
    ctx = click.Context(click.Command("test"), obj={"root": tmp_path})
    with patch(
        "fx_alfred.commands._helpers.scan_documents",
        side_effect=LayerValidationError(["bad layer"]),
    ):
        with pytest.raises(click.ClickException, match="bad layer"):
            scan_or_fail(ctx)


def test_find_or_fail_returns_document(sample_project):
    """find_or_fail returns the matching Document for a valid identifier."""
    ctx = click.Context(click.Command("test"), obj={"root": sample_project})
    docs = scan_or_fail(ctx)
    doc = find_or_fail(docs, "ALF-2201")
    assert doc.acid == "2201"


def test_find_or_fail_raises_on_not_found(sample_project):
    """find_or_fail raises ClickException when document is not found."""
    ctx = click.Context(click.Command("test"), obj={"root": sample_project})
    docs = scan_or_fail(ctx)
    with pytest.raises(click.ClickException, match="No document found"):
        find_or_fail(docs, "XXX-9999")


def test_find_or_fail_raises_on_ambiguous():
    """find_or_fail raises ClickException when identifier is ambiguous."""
    doc1 = Document(
        prefix="AAA",
        acid="1000",
        type_code="SOP",
        title="A",
        source="pkg",
        directory="rules",
        base_path=None,
    )
    doc2 = Document(
        prefix="BBB",
        acid="1000",
        type_code="SOP",
        title="B",
        source="prj",
        directory="rules",
        base_path=None,
    )
    with pytest.raises(click.ClickException, match="Ambiguous"):
        find_or_fail([doc1, doc2], "1000")
