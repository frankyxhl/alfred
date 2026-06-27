import json
import pytest


import tempfile
from pathlib import Path

from fx_alfred.core.scanner import LayerValidationError, scan_documents


pytestmark = pytest.mark.integration


def test_scan_finds_all_documents(sample_project):
    docs = scan_documents(sample_project)
    # PKG docs + 3 from rules/ (ALF-0000, ALF-2201, ALF-2202)
    prj_docs = [d for d in docs if d.source == "prj"]
    assert len(prj_docs) == 3


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
    assert len(prj_docs) == 3  # ALF-0000, ALF-2201, ALF-2202 from rules/


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


# ── FXA-2314: USR sub-project layer via projects.json mapping ─────────────────


def _make_projects_json(alfred_dir: Path, mapping: dict) -> None:
    """Write ~/.alfred/projects.json with the given mapping."""
    (alfred_dir / "projects.json").write_text(
        json.dumps({"projects": mapping}), encoding="utf-8"
    )


def _write_routing_doc(path: Path, prefix: str, acid: str) -> None:
    """Write a minimal but parse-able routing document."""
    path.write_text(
        f"# SOP-{acid}: Workflow Routing\n\n"
        f"**Applies to:** {prefix}\n"
        "**Status:** Active\n\n"
        "---\n\n"
        f"{prefix}-{acid} routing content.\n",
        encoding="utf-8",
    )


# ── Happy-path: mapped root loads subproject as PRJ ──────────────────────────


def test_scan_mapped_root_loads_subproject_as_prj(tmp_path):
    """Mapped root: ~/.alfred/<NAME>/ docs load with source='prj'."""
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True)
    ext_repo = tmp_path / "ext_repo"
    ext_repo.mkdir()

    nrv_dir = alfred / "NRV"
    nrv_dir.mkdir()
    (nrv_dir / "NRV-2500-SOP-Workflow-Routing-PRJ.md").write_text("# NRV doc")

    _make_projects_json(alfred, {str(ext_repo.resolve()): "NRV"})

    docs = scan_documents(ext_repo)
    prj_docs = [d for d in docs if d.source == "prj"]

    assert any(d.prefix == "NRV" and d.acid == "2500" for d in prj_docs), (
        "NRV-2500 must appear as source='prj' in a mapped context"
    )


def test_scan_mapped_root_excludes_subdir_from_usr(tmp_path):
    """Registered subproject dir is excluded from the flat USR layer scan."""
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True)
    ext_repo = tmp_path / "ext_repo"
    ext_repo.mkdir()

    nrv_dir = alfred / "NRV"
    nrv_dir.mkdir()
    (nrv_dir / "NRV-2500-SOP-Workflow-Routing-PRJ.md").write_text("# NRV doc")
    # A genuine USR doc (not in NRV subdir)
    (alfred / "ALF-2207-SOP-Workflow-Routing-USR.md").write_text("# USR doc")

    _make_projects_json(alfred, {str(ext_repo.resolve()): "NRV"})

    docs = scan_documents(ext_repo)
    usr_docs = [d for d in docs if d.source == "usr"]

    assert not any(d.prefix == "NRV" for d in usr_docs), (
        "NRV-* docs must NOT appear in USR layer when NRV is a registered subproject"
    )


def test_scan_mapped_root_no_layer_validation_error(tmp_path):
    """Mapped root scan must complete without LayerValidationError (no duplicates)."""
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True)
    ext_repo = tmp_path / "ext_repo"
    ext_repo.mkdir()

    nrv_dir = alfred / "NRV"
    nrv_dir.mkdir()
    (nrv_dir / "NRV-2500-SOP-Workflow-Routing-PRJ.md").write_text("# NRV doc")
    (alfred / "ALF-2207-SOP-Workflow-Routing-USR.md").write_text("# USR doc")

    _make_projects_json(alfred, {str(ext_repo.resolve()): "NRV"})

    # Must not raise LayerValidationError
    docs = scan_documents(ext_repo)
    assert docs  # scan completes


# ── Recursion: nested doc inside the subproject dir is found under PRJ ────────


def test_scan_nested_doc_in_subproject_found_as_prj(tmp_path):
    """Doc at ~/.alfred/<NAME>/<subdir>/X.md is found as PRJ (recursive scan)."""
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True)
    ext_repo = tmp_path / "ext_repo"
    ext_repo.mkdir()

    nrv_dir = alfred / "NRV"
    nrv_deep = nrv_dir / "sub_category"
    nrv_deep.mkdir(parents=True)
    (nrv_deep / "NRV-2600-SOP-Nested-Doc.md").write_text("# Nested NRV doc")

    _make_projects_json(alfred, {str(ext_repo.resolve()): "NRV"})

    docs = scan_documents(ext_repo)
    prj_docs = [d for d in docs if d.source == "prj"]

    assert any(d.prefix == "NRV" and d.acid == "2600" for d in prj_docs), (
        "Doc nested inside ~/.alfred/NRV/sub_category/ must be found as PRJ"
    )


# ── Mapping-wins / shadow: local rules/ is shadowed when mapping fires ────────


def test_scan_mapping_wins_subproject_loads_as_prj(tmp_path):
    """Mapped root + local rules/: subproject docs still load as PRJ (mapping wins)."""
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True)
    ext_repo = tmp_path / "ext_repo"
    ext_repo.mkdir()

    # Local rules/ in the repo (will be shadowed)
    local_rules = ext_repo / "rules"
    local_rules.mkdir()
    (local_rules / "ALF-9001-SOP-Local-Doc.md").write_text("# Local doc")

    # Subproject
    nrv_dir = alfred / "NRV"
    nrv_dir.mkdir()
    (nrv_dir / "NRV-2500-SOP-Workflow-Routing-PRJ.md").write_text("# NRV doc")

    _make_projects_json(alfred, {str(ext_repo.resolve()): "NRV"})

    docs = scan_documents(ext_repo)
    prj_docs = [d for d in docs if d.source == "prj"]

    assert any(d.prefix == "NRV" and d.acid == "2500" for d in prj_docs), (
        "NRV subproject docs must appear as PRJ even when local rules/ exists"
    )


def test_scan_mapping_wins_local_rules_shadowed(tmp_path):
    """Mapped root + local rules/: local rules docs must NOT appear in PRJ (orphan-unreachable)."""
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True)
    ext_repo = tmp_path / "ext_repo"
    ext_repo.mkdir()

    local_rules = ext_repo / "rules"
    local_rules.mkdir()
    (local_rules / "ALF-9001-SOP-Local-Doc.md").write_text("# Local doc")

    nrv_dir = alfred / "NRV"
    nrv_dir.mkdir()
    (nrv_dir / "NRV-2500-SOP-Workflow-Routing-PRJ.md").write_text("# NRV doc")

    _make_projects_json(alfred, {str(ext_repo.resolve()): "NRV"})

    docs = scan_documents(ext_repo)

    assert not any(d.acid == "9001" and d.source == "prj" for d in docs), (
        "ALF-9001 from local rules/ must NOT appear in PRJ when mapping wins (shadow)"
    )


def test_scan_mapping_wins_no_layer_validation_error(tmp_path):
    """Mapped root with local rules/: _validate_layers passes (no duplicates)."""
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True)
    ext_repo = tmp_path / "ext_repo"
    ext_repo.mkdir()

    local_rules = ext_repo / "rules"
    local_rules.mkdir()
    (local_rules / "ALF-9001-SOP-Local-Doc.md").write_text("# Local doc")

    nrv_dir = alfred / "NRV"
    nrv_dir.mkdir()
    (nrv_dir / "NRV-2500-SOP-Workflow-Routing-PRJ.md").write_text("# NRV doc")

    _make_projects_json(alfred, {str(ext_repo.resolve()): "NRV"})

    # Must not raise LayerValidationError
    docs = scan_documents(ext_repo)
    assert docs


def test_scan_mapping_wins_shadow_warning_emitted(tmp_path, capsys):
    """Mapped root with local rules/ emits a shadow warning to stderr."""
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True)
    ext_repo = tmp_path / "ext_repo"
    ext_repo.mkdir()

    local_rules = ext_repo / "rules"
    local_rules.mkdir()
    (local_rules / "ALF-9001-SOP-Local-Doc.md").write_text("# Local doc")

    nrv_dir = alfred / "NRV"
    nrv_dir.mkdir()
    (nrv_dir / "NRV-2500-SOP-Workflow-Routing-PRJ.md").write_text("# NRV doc")

    _make_projects_json(alfred, {str(ext_repo.resolve()): "NRV"})

    scan_documents(ext_repo)
    captured = capsys.readouterr()
    assert captured.err or captured.out, (
        "A shadow warning must be emitted when mapping wins over a populated local rules/"
    )


# ── Path normalisation: symlink on the candidate still matches ────────────────


def test_scan_symlink_path_matches_after_resolve(tmp_path):
    """Key and candidate differing only by a symlink match after resolve() on both sides."""
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True)
    real_repo = tmp_path / "real_repo"
    real_repo.mkdir()
    link_repo = tmp_path / "link_repo"
    link_repo.symlink_to(real_repo)

    nrv_dir = alfred / "NRV"
    nrv_dir.mkdir()
    (nrv_dir / "NRV-2500-SOP-Workflow-Routing-PRJ.md").write_text("# NRV doc")

    # Register with the canonical real path
    _make_projects_json(alfred, {str(real_repo.resolve()): "NRV"})

    # Scan via the symlinked path
    docs = scan_documents(link_repo)
    prj_docs = [d for d in docs if d.source == "prj"]

    assert any(d.prefix == "NRV" and d.acid == "2500" for d in prj_docs), (
        "Symlinked repo path must resolve to the registered key and load subproject as PRJ"
    )


# ── Missing target dir: ~/.alfred/<NAME>/ doesn't exist ──────────────────────


def test_scan_missing_subproject_dir_empty_prj_with_warning(tmp_path, capsys):
    """If the mapped ~/.alfred/<NAME>/ dir doesn't exist: empty PRJ + warning, no crash."""
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True)
    ext_repo = tmp_path / "ext_repo"
    ext_repo.mkdir()

    # Map to "NRV" but DON'T create ~/.alfred/NRV/
    _make_projects_json(alfred, {str(ext_repo.resolve()): "NRV"})

    docs = scan_documents(ext_repo)  # must not raise
    prj_docs = [d for d in docs if d.source == "prj"]
    assert prj_docs == [], "PRJ must be empty when target dir does not exist"

    captured = capsys.readouterr()
    assert captured.err or captured.out, (
        "A warning must be emitted when the mapped ~/.alfred/<NAME>/ dir is absent"
    )


# ── Backward compatibility ────────────────────────────────────────────────────


def test_scan_absent_projects_json_backward_compat(tmp_path):
    """No projects.json => existing behavior (regular PRJ scan from rules/)."""
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True)
    project = tmp_path / "project"
    project.mkdir()
    rules = project / "rules"
    rules.mkdir()
    (rules / "ALF-5001-SOP-Normal.md").write_text("# Normal doc")

    # No projects.json
    docs = scan_documents(project)
    prj_docs = [d for d in docs if d.source == "prj"]
    assert any(d.acid == "5001" and d.source == "prj" for d in prj_docs), (
        "Absent projects.json must not change behavior for an ordinary project"
    )


def test_scan_malformed_projects_json_backward_compat(tmp_path, capsys):
    """Malformed projects.json => fallback to normal behavior (regular PRJ scan)."""
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True)
    (alfred / "projects.json").write_text("{broken{{", encoding="utf-8")

    project = tmp_path / "project"
    project.mkdir()
    rules = project / "rules"
    rules.mkdir()
    (rules / "ALF-5002-SOP-Normal.md").write_text("# Normal doc")

    docs = scan_documents(project)
    prj_docs = [d for d in docs if d.source == "prj"]
    assert any(d.acid == "5002" and d.source == "prj" for d in prj_docs), (
        "Malformed projects.json must fall back to normal behavior"
    )


def test_scan_unregistered_subdir_still_recurses_into_usr(tmp_path):
    """An UNREGISTERED ~/.alfred/ subdir retains recursive-USR behavior (locked)."""
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True)
    # Unregistered subdir
    unregistered = alfred / "unregistered_sub"
    unregistered.mkdir()
    (unregistered / "TST-8001-SOP-Unregistered.md").write_text("# Unregistered")

    # A mapping that does NOT include 'unregistered_sub'
    ext_repo = tmp_path / "ext_repo"
    ext_repo.mkdir()
    _make_projects_json(alfred, {str(ext_repo.resolve()): "NRV"})

    # Scanning a different project — unregistered docs should still be in USR
    other_project = tmp_path / "other_project"
    other_project.mkdir()
    docs = scan_documents(other_project)
    usr_docs = [d for d in docs if d.source == "usr"]
    assert any(d.acid == "8001" for d in usr_docs), (
        "Unregistered subdirs must still recurse into USR"
    )


# ── Document.directory field for redirected PRJ docs ─────────────────────────


def test_scan_redirected_prj_doc_directory_field(tmp_path):
    """Redirected PRJ doc must have directory == '<NAME>' (e.g. 'NRV'), not '.alfred'."""
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True)
    ext_repo = tmp_path / "ext_repo"
    ext_repo.mkdir()

    nrv_dir = alfred / "NRV"
    nrv_dir.mkdir()
    (nrv_dir / "NRV-2500-SOP-Workflow-Routing-PRJ.md").write_text("# NRV doc")

    _make_projects_json(alfred, {str(ext_repo.resolve()): "NRV"})

    docs = scan_documents(ext_repo)
    prj_docs = [d for d in docs if d.source == "prj"]
    nrv_doc = next(
        (d for d in prj_docs if d.prefix == "NRV" and d.acid == "2500"), None
    )
    assert nrv_doc is not None, "NRV-2500 must be found as a PRJ doc"
    assert nrv_doc.directory == "NRV", (
        f"Expected directory='NRV', got '{nrv_doc.directory}'"
    )


def test_scan_usr_doc_directory_field(tmp_path, monkeypatch):
    """USR-layer doc must have directory == '.alfred' (not the subproject name)."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    alfred = fake_home / ".alfred"
    alfred.mkdir()
    # Plain USR doc living directly in ~/.alfred/
    (alfred / "USR-9002-SOP-Plain-USR.md").write_text("# USR doc")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

    project = tmp_path / "project"
    project.mkdir()
    docs = scan_documents(project)
    usr_docs = [d for d in docs if d.source == "usr"]
    usr_doc = next((d for d in usr_docs if d.acid == "9002"), None)
    assert usr_doc is not None, "USR-9002 must be found as a USR doc"
    assert usr_doc.directory == ".alfred", (
        f"Expected directory='.alfred', got '{usr_doc.directory}'"
    )
