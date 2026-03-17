import pytest


@pytest.fixture
def sample_project(tmp_path):
    """Create a minimal project with .alfred/ and docs/."""
    alfred_dir = tmp_path / ".alfred"
    alfred_dir.mkdir()
    (alfred_dir / "COR-0001-REF-Glossary.md").write_text("# Glossary")
    (alfred_dir / "COR-1000-SOP-Create-SOP.md").write_text("# Create SOP")
    (alfred_dir / "INIT.md").write_text("# Init")  # should be ignored

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "ALF-2201-PRP-AF-CLI-Tool.md").write_text("# AF CLI")
    (docs_dir / "README.md").write_text("# Readme")  # should be ignored

    return tmp_path
