from fx_alfred.core.scanner import scan_documents


def test_scan_finds_all_documents(sample_project):
    docs = scan_documents(sample_project)
    assert len(docs) == 3


def test_scan_ignores_non_document_files(sample_project):
    docs = scan_documents(sample_project)
    filenames = [d.filename for d in docs]
    assert "INIT.md" not in filenames
    assert "README.md" not in filenames


def test_scan_sorted_by_acid(sample_project):
    docs = scan_documents(sample_project)
    acids = [d.acid for d in docs]
    assert acids == sorted(acids)
