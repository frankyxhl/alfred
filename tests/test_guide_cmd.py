from click.testing import CliRunner
from fx_alfred.cli import cli


def test_guide_outputs_content():
    """Guide command outputs onboarding content."""
    runner = CliRunner()
    result = runner.invoke(cli, ["guide"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "Quick Start" in result.output
    assert "af create" in result.output
    assert "af list" in result.output
