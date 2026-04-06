from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_home(tmp_path, monkeypatch):
    """Patch Path.home() to return a fresh tmp directory for every test.

    This ensures scanner.py:123 (Path.home() / ".alfred") hits an empty
    tmp dir rather than the real ~/.alfred/.
    """
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))


@pytest.fixture
def sample_project(tmp_path):
    """Create a minimal project with rules/ only (no .alfred/).

    COR documents come from PKG layer only.
    PRJ layer only allows non-COR prefixes.
    """
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "ALF-0000-REF-Document-Index.md").write_text("# ALF Index")
    (rules_dir / "ALF-2201-PRP-AF-CLI-Tool.md").write_text("# AF CLI")
    (rules_dir / "ALF-2202-SOP-Another-Doc.md").write_text("# Another Doc")
    (rules_dir / "README.md").write_text("# README")  # should be ignored

    return tmp_path
