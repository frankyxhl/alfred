import re
from pathlib import Path

from click.testing import CliRunner
from fx_alfred.cli import cli


def test_status_shows_counts(sample_project, monkeypatch):
    """Status command shows document counts by type and prefix."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["status"], catch_exceptions=False)
    assert result.exit_code == 0
    # Check type codes are present
    assert "SOP" in result.output
    assert "REF" in result.output
    assert "PRP" in result.output
    # Check prefixes are present (COR from PKG, ALF from PRJ)
    assert "COR:" in result.output
    assert "ALF:" in result.output


def test_status_shows_by_source(sample_project, monkeypatch):
    """Status command shows 'By source' section with specific counts."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["status"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "By source:" in result.output

    # PKG should have many COR documents (all bundled rules)
    pkg_match = re.search(r"PKG:\s*(\d+)", result.output)
    assert pkg_match, "PKG count not found in output"
    pkg_count = int(pkg_match.group(1))
    assert pkg_count >= 20, f"Expected at least 20 PKG docs, got {pkg_count}"

    # PRJ should have exactly 2 documents (ALF-2201, ALF-2202)
    prj_match = re.search(r"PRJ:\s*(\d+)", result.output)
    assert prj_match, "PRJ count not found in output"
    prj_count = int(prj_match.group(1))
    assert prj_count == 3, f"Expected 3 PRJ docs, got {prj_count}"

    # USR may or may not be present; include it in the sum if shown
    usr_match = re.search(r"USR:\s*(\d+)", result.output)
    usr_count = int(usr_match.group(1)) if usr_match else 0

    # Total should be PKG + USR + PRJ
    total_match = re.search(r"Total:\s*(\d+)\s*documents", result.output)
    assert total_match, "Total count not found in output"
    total_count = int(total_match.group(1))
    assert total_count == pkg_count + usr_count + prj_count, (
        f"Total {total_count} != PKG {pkg_count} + USR {usr_count} + PRJ {prj_count}"
    )


def test_status_shows_usr_layer(tmp_path, monkeypatch):
    """Status command counts docs in the USR layer (~/.alfred/)."""
    # isolate_home autouse fixture already patched Path.home() to tmp_path/fake_home
    # We need to use that same fake home — reach it via Path.home()
    user_alfred = Path.home() / ".alfred"
    user_alfred.mkdir(parents=True)
    (user_alfred / "TST-3000-SOP-Test.md").write_text("# Test SOP")

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["status"], catch_exceptions=False)
    assert result.exit_code == 0

    usr_match = re.search(r"USR:\s*(\d+)", result.output)
    assert usr_match, "USR count not found in output"
    usr_count = int(usr_match.group(1))
    assert usr_count >= 1, f"Expected at least 1 USR doc, got {usr_count}"


def test_status_with_root_option(sample_project):
    runner = CliRunner()
    result = runner.invoke(
        cli, ["--root", str(sample_project), "status"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "PRJ" in result.output


def test_status_with_root_after_subcommand(sample_project):
    runner = CliRunner()
    result = runner.invoke(
        cli, ["status", "--root", str(sample_project)], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "PRJ" in result.output
