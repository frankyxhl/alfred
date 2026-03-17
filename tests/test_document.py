from fx_alfred.core.document import Document


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


def test_filepath():
    doc = Document.from_filename("COR-1000-SOP-Create-SOP.md", directory=".alfred")
    assert doc.filepath == ".alfred/COR-1000-SOP-Create-SOP.md"
