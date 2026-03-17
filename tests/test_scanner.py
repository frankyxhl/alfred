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


def test_duplicate_prefix_acid_is_error(tmp_path, monkeypatch):
    """Duplicate prefix+ACID across layers is a hard error."""
    # Create PRJ doc with same prefix+ACID as USR
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    user_alfred = fake_home / ".alfred"
    user_alfred.mkdir()
    (user_alfred / "TST-2100-SOP-UserDoc.md").write_text("# User")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

    project = tmp_path / "project"
    project.mkdir()
    rules = project / "rules"
    rules.mkdir()
    (rules / "TST-2100-SOP-ProjectDoc.md").write_text("# Project")
    try:
        scan_documents(project)
        assert False, "Expected LayerValidationError"
    except LayerValidationError as e:
        assert "Duplicate TST-2100" in str(e)


def test_different_prefix_same_acid_is_ok(tmp_path, monkeypatch):
    """Different prefixes with same ACID number should NOT conflict."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

    project = tmp_path / "project"
    project.mkdir()
    rules = project / "rules"
    rules.mkdir()
    (rules / "ALF-0000-REF-Document-Index.md").write_text("# ALF index")
    # PKG has COR-0000 - different prefix, same ACID - should be fine
    docs = scan_documents(project)
    acids_0000 = [d for d in docs if d.acid == "0000"]
    assert len(acids_0000) >= 2  # COR-0000 from PKG + ALF-0000 from PRJ


def test_scan_usr_recursive(tmp_path, monkeypatch):
    """USR layer scans subdirectories recursively."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    user_alfred = fake_home / ".alfred"
    user_alfred.mkdir()
    # Create subdirectory with document
    sub_dir = user_alfred / "sub_a"
    sub_dir.mkdir()
    (sub_dir / "TST-3000-SOP-Sub.md").write_text("# Sub doc")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

    project = tmp_path / "project"
    project.mkdir()
    docs = scan_documents(project)
    usr_docs = [d for d in docs if d.source == "usr"]
    assert len(usr_docs) == 1
    assert usr_docs[0].acid == "3000"
    assert usr_docs[0].prefix == "TST"
    # Verify resolve_resource works for nested USR docs
    resource = usr_docs[0].resolve_resource()
    content = resource.read_text()
    assert "# Sub doc" in content


def test_scan_prj_not_recursive(tmp_path):
    """PRJ layer does NOT scan subdirectories recursively."""
    project = tmp_path / "project"
    project.mkdir()
    rules = project / "rules"
    rules.mkdir()
    # Create subdirectory with document
    sub_dir = rules / "sub"
    sub_dir.mkdir()
    (sub_dir / "TST-4000-SOP-Sub.md").write_text("# Sub doc")
    # Create a valid doc in rules/ to ensure scanning works
    (rules / "ALF-5000-SOP-Top.md").write_text("# Top doc")

    docs = scan_documents(project)
    prj_docs = [d for d in docs if d.source == "prj"]
    # Should find ALF-5000 but NOT TST-4000 (in subdirectory)
    assert len(prj_docs) == 1
    assert prj_docs[0].acid == "5000"
    assert not any(d.acid == "4000" for d in prj_docs)
