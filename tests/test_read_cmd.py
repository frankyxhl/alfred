from click.testing import CliRunner
from fx_alfred.cli import cli


def test_read_by_acid_from_pkg(tmp_path, monkeypatch):
    """Read a PKG layer document by ACID."""
    # Can read PKG docs from any directory
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["read", "1000"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "SOP" in result.output  # Content from PKG COR-1000


def test_read_by_acid_from_prj(sample_project, monkeypatch):
    """Read a PRJ layer document by ACID."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["read", "2201"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "# AF CLI" in result.output


def test_read_not_found(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["read", "9999"], catch_exceptions=False)
    assert result.exit_code != 0
    assert "9999" in result.output


def test_read_with_root_option(sample_project):
    """Read command respects --root option."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--root", str(sample_project), "read", "2201"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "# AF CLI" in result.output
