from click.testing import CliRunner
from fx_alfred.cli import cli


def test_changelog_outputs_content():
    """Changelog command outputs changelog content."""
    runner = CliRunner()
    result = runner.invoke(cli, ["changelog"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "# Changelog" in result.output
    assert "v0.5.0" in result.output
