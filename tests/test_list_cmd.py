from click.testing import CliRunner
from fx_alfred.cli import cli


def test_list_shows_documents(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["list"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "COR-0001" in result.output
    assert "COR-1000" in result.output
    assert "ALF-2201" in result.output


def test_list_shows_type_codes(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["list"], catch_exceptions=False)
    assert "REF" in result.output
    assert "SOP" in result.output
    assert "PRP" in result.output
