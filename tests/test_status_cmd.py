from click.testing import CliRunner
from fx_alfred.cli import cli


def test_status_shows_counts(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["status"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "3" in result.output  # total docs
    assert "SOP" in result.output
    assert "REF" in result.output
    assert "PRP" in result.output
