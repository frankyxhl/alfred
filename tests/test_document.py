from pathlib import Path

from fx_alfred.core.document import Document


def test_resolve_resource_for_prj():
    """resolve_resource() returns Path for PRJ layer."""
    doc = Document.from_filename(
        "TST-1000-SOP-Test.md",
        directory="rules",
        source="prj",
        base_path=Path("/tmp/project"),
    )
    res = doc.resolve_resource()
    assert isinstance(res, Path)
    assert str(res).endswith("TST-1000-SOP-Test.md")


def test_resolve_resource_for_pkg():
    """resolve_resource() returns Traversable for PKG layer."""
    doc = Document.from_filename(
        "COR-1000-SOP-Create-SOP.md",
        directory="rules",
        source="pkg",
        base_path=None,
    )
    res = doc.resolve_resource()
    # Traversable has read_text method
    assert hasattr(res, "read_text")
    content = res.read_text()
    assert "SOP" in content


def test_resolve_resource_without_base_path_raises():
    """resolve_resource() raises for non-PKG without base_path."""
    doc = Document.from_filename(
        "TST-1000-SOP-Test.md",
        directory="rules",
        source="prj",
        base_path=None,
    )
    try:
        doc.resolve_resource()
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "Cannot resolve resource" in str(e)


def test_document_source_field():
    doc = Document.from_filename(
        "COR-1000-SOP-Create-SOP.md",
        directory=".alfred",
        source="prj",
        base_path=Path("/tmp/project"),
    )
    assert doc.source == "prj"
    assert doc.base_path == Path("/tmp/project")


def test_document_source_defaults():
    doc = Document.from_filename(
        "COR-1000-SOP-Create-SOP.md",
        directory=".alfred",
    )
    assert doc.source == "prj"
    assert doc.base_path is None


def test_parse_cor_filename():
    doc = Document.from_filename("COR-1000-SOP-Create-SOP.md", directory=".alfred")
    assert doc.prefix == "COR"
    assert doc.acid == "1000"
    assert doc.type_code == "SOP"
    assert doc.title == "Create SOP"
    assert doc.directory == ".alfred"


def test_parse_business_filename():
    doc = Document.from_filename("ALF-2201-PRP-AF-CLI-Tool.md", directory="docs")
    assert doc.prefix == "ALF"
    assert doc.acid == "2201"
    assert doc.type_code == "PRP"
    assert doc.title == "AF CLI Tool"
    assert doc.directory == "docs"


def test_parse_invalid_filename_returns_none():
    doc = Document.from_filename("README.md", directory=".")
    assert doc is None
