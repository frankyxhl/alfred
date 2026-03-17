from click.testing import CliRunner
from fx_alfred.cli import cli


def test_read_by_acid(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["read", "1000"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "# Create SOP" in result.output


def test_read_not_found(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["read", "9999"], catch_exceptions=False)
    assert result.exit_code != 0
    assert "9999" in result.output
