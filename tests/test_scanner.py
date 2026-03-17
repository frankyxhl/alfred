import tempfile
from pathlib import Path

from fx_alfred.core.scanner import LayerValidationError, scan_documents


def test_scan_finds_all_documents(sample_project):
    docs = scan_documents(sample_project)
    # PKG docs + 2 from rules/
    prj_docs = [d for d in docs if d.source == "prj"]
    assert len(prj_docs) == 2


def test_scan_ignores_non_document_files(sample_project):
    docs = scan_documents(sample_project)
    filenames = [d.filename for d in docs]
    assert "README.md" not in filenames


def test_scan_sorted_by_source_then_acid(sample_project):
    """PKG first, then USR, then PRJ; each group sorted by acid."""
    docs = scan_documents(sample_project)
    # Within each source group, acids should be sorted
    for source in ("pkg", "usr", "prj"):
        group = [d for d in docs if d.source == source]
        acids = [d.acid for d in group]
        assert acids == sorted(acids), f"{source} group not sorted by acid"
    # Source groups appear in order: pkg before usr before prj
    sources = [d.source for d in docs]
    pkg_indices = [i for i, s in enumerate(sources) if s == "pkg"]
    prj_indices = [i for i, s in enumerate(sources) if s == "prj"]
    if pkg_indices and prj_indices:
        assert max(pkg_indices) < min(prj_indices)


def test_scan_pkg_documents():
    """PKG layer: bundled rules inside the package."""
    with tempfile.TemporaryDirectory() as td:
        docs = scan_documents(Path(td))
        pkg_docs = [d for d in docs if d.source == "pkg"]
        assert len(pkg_docs) > 0
        assert any(d.prefix == "COR" for d in pkg_docs)


def test_scan_usr_documents(tmp_path, monkeypatch):
    """USR layer: ~/.alfred/ documents."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    user_alfred = fake_home / ".alfred"
    user_alfred.mkdir()
    (user_alfred / "USR-9001-SOP-My-Custom.md").write_text(
        "# Custom"
    )  # Use non-conflicting ACID
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

    project = tmp_path / "project"
    project.mkdir()
    docs = scan_documents(project)
    usr_docs = [d for d in docs if d.source == "usr"]
    assert len(usr_docs) == 1
    assert usr_docs[0].prefix == "USR"


def test_scan_prj_documents(sample_project):
    """PRJ layer: rules/ in project only."""
    docs = scan_documents(sample_project)
    prj_docs = [d for d in docs if d.source == "prj"]
    assert len(prj_docs) == 2  # 2 from rules/


def test_scan_source_labels(sample_project):
    """Each document has correct source label."""
    docs = scan_documents(sample_project)
    sources = set(d.source for d in docs)
    assert "pkg" in sources
    assert "prj" in sources


def test_cor_in_usr_is_error(tmp_path, monkeypatch):
    """COR prefix in USR layer is a hard error."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    user_alfred = fake_home / ".alfred"
    user_alfred.mkdir()
    (user_alfred / "COR-9999-SOP-Invalid.md").write_text("# Invalid")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

    project = tmp_path / "project"
    project.mkdir()
    try:
        scan_documents(project)
        assert False, "Expected LayerValidationError"
    except LayerValidationError as e:
        assert "COR document found in USR layer" in str(e)


def test_cor_in_prj_is_error(tmp_path):
    """COR prefix in PRJ layer is a hard error."""
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "COR-9999-SOP-Invalid.md").write_text("# Invalid")
    try:
        scan_documents(tmp_path)
        assert False, "Expected LayerValidationError"
    except LayerValidationError as e:
        assert "COR document found in PRJ layer" in str(e)


def test_duplicate_acid_is_error(tmp_path, monkeypatch):
    """Duplicate ACID across layers is a hard error."""
    # Create USR doc with ACID 1000 (PKG has COR-1000)
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    user_alfred = fake_home / ".alfred"
    user_alfred.mkdir()
    (user_alfred / "USR-1000-SOP-Duplicate.md").write_text("# Duplicate")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

    project = tmp_path / "project"
    project.mkdir()
    try:
        scan_documents(project)
        assert False, "Expected LayerValidationError"
    except LayerValidationError as e:
        assert "Duplicate ACID 1000" in str(e)
