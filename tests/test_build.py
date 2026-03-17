"""Build and packaging tests."""

import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path


def test_wheel_contains_rules(tmp_path):
    """Verify wheel contains rules/*.md files."""
    project_root = Path(__file__).parent.parent

    # Find uv in PATH
    uv_path = shutil.which("uv")
    assert uv_path is not None, "uv command not found in PATH"

    # Build the wheel to temp directory
    result = subprocess.run(
        [uv_path, "build", "--wheel", "--out-dir", str(tmp_path)],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Build failed: {result.stderr}"

    # Find the wheel file
    wheels = list(tmp_path.glob("fx_alfred-*.whl"))
    assert len(wheels) == 1, f"Expected 1 wheel, found {len(wheels)}"
    wheel_path = wheels[0]

    # Check wheel contents for rules/*.md
    with zipfile.ZipFile(wheel_path, "r") as whl:
        names = whl.namelist()
        rules_files = [
            n for n in names if "fx_alfred/rules/" in n and n.endswith(".md")
        ]
        assert len(rules_files) > 0, "No rules/*.md files found in wheel"
        # Should have at least the COR documents
        assert any("COR-" in n for n in rules_files), "No COR documents in wheel"


def test_sdist_contains_rules(tmp_path):
    """Verify sdist contains rules/*.md files."""
    project_root = Path(__file__).parent.parent

    # Find uv in PATH
    uv_path = shutil.which("uv")
    assert uv_path is not None, "uv command not found in PATH"

    # Build the sdist to temp directory
    result = subprocess.run(
        [uv_path, "build", "--sdist", "--out-dir", str(tmp_path)],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Build failed: {result.stderr}"

    # Find the sdist file
    sdist_files = list(tmp_path.glob("fx_alfred-*.tar.gz"))
    assert len(sdist_files) == 1, f"Expected 1 sdist, found {len(sdist_files)}"
    sdist_path = sdist_files[0]

    # Check sdist contents for rules/*.md
    with tarfile.open(sdist_path, "r:gz") as tar:
        names = tar.getnames()
        rules_files = [n for n in names if "/rules/" in n and n.endswith(".md")]
        assert len(rules_files) > 0, "No rules/*.md files found in sdist"
        # Should have at least the COR documents
        assert any("COR-" in n for n in rules_files), "No COR documents in sdist"
