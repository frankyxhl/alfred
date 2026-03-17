from pathlib import Path

from click.testing import CliRunner
from fx_alfred.cli import cli


def test_list_shows_documents(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["list"], catch_exceptions=False)
    assert result.exit_code == 0
    # PKG docs
    assert "COR-0001" in result.output
    assert "COR-1000" in result.output
    # PRJ docs
    assert "ALF-2201" in result.output
    assert "ALF-2202" in result.output


def test_list_shows_type_codes(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["list"], catch_exceptions=False)
    assert "REF" in result.output
    assert "SOP" in result.output
    assert "PRP" in result.output


def test_list_shows_source_labels(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["list"], catch_exceptions=False)
    assert "PKG" in result.output
    assert "PRJ" in result.output


def test_list_uses_spaces_not_tabs(sample_project, monkeypatch):
    """List output uses space alignment, not tabs."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["list"], catch_exceptions=False)
    assert result.exit_code == 0
    lines = result.output.strip().split("\n")
    # Each line should have double spaces between columns
    for line in lines:
        if "COR-" in line or "ALF-" in line:
            assert "\t" not in line, f"Found tab in: {line}"
            assert "  " in line, f"No double space in: {line}"


def test_list_with_root_before_subcommand(sample_project):
    """af --root <path> list works."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["--root", str(sample_project), "list"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "ALF-2201" in result.output


def test_list_with_root_after_subcommand(sample_project):
    """af list --root <path> works."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["list", "--root", str(sample_project)], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "ALF-2201" in result.output


def test_list_shows_usr_documents(tmp_path, monkeypatch):
    """af list shows documents from the USR layer (~/.alfred/)."""
    # isolate_home autouse fixture already patched Path.home() to tmp_path/fake_home
    user_alfred = Path.home() / ".alfred"
    user_alfred.mkdir(parents=True)
    (user_alfred / "TST-3000-SOP-Test.md").write_text("# Test SOP")

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["list"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "TST-3000" in result.output
    assert "USR" in result.output
