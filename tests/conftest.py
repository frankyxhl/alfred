import pytest


@pytest.fixture
def sample_project(tmp_path):
    """Create a minimal project with rules/ only (no .alfred/).

    COR documents come from PKG layer only.
    PRJ layer only allows non-COR prefixes.
    """
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "ALF-2201-PRP-AF-CLI-Tool.md").write_text("# AF CLI")
    (rules_dir / "ALF-2202-SOP-Another-Doc.md").write_text("# Another Doc")
    (rules_dir / "README.md").write_text("# Readme")  # should be ignored

    return tmp_path
