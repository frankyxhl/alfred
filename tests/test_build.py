"""Build and packaging tests."""

import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest


def _has_build_module():
    try:
        import build  # noqa: F401

        return True
    except ImportError:
        return False


needs_build = pytest.mark.skipif(
    not _has_build_module(), reason="build module not installed"
)


@needs_build
def test_wheel_contains_rules(tmp_path):
    """Verify wheel contains rules/*.md files."""
    project_root = Path(__file__).parent.parent

    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(tmp_path)],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Build failed: {result.stderr}"

    wheels = list(tmp_path.glob("fx_alfred-*.whl"))
    assert len(wheels) == 1, f"Expected 1 wheel, found {len(wheels)}"

    with zipfile.ZipFile(wheels[0], "r") as whl:
        names = whl.namelist()
        rules_files = [
            n for n in names if "fx_alfred/rules/" in n and n.endswith(".md")
        ]
        assert len(rules_files) > 0, "No rules/*.md files found in wheel"
        assert any("COR-" in n for n in rules_files), "No COR documents in wheel"


@needs_build
def test_sdist_contains_rules(tmp_path):
    """Verify sdist contains rules/*.md files."""
    project_root = Path(__file__).parent.parent

    result = subprocess.run(
        [sys.executable, "-m", "build", "--sdist", "--outdir", str(tmp_path)],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Build failed: {result.stderr}"

    sdist_files = list(tmp_path.glob("fx_alfred-*.tar.gz"))
    assert len(sdist_files) == 1, f"Expected 1 sdist, found {len(sdist_files)}"

    with tarfile.open(sdist_files[0], "r:gz") as tar:
        names = tar.getnames()
        rules_files = [n for n in names if "/rules/" in n and n.endswith(".md")]
        assert len(rules_files) > 0, "No rules/*.md files found in sdist"
        assert any("COR-" in n for n in rules_files), "No COR documents in sdist"
