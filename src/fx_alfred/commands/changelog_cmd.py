from importlib import resources

import click


@click.command("changelog")
def changelog_cmd():
    """Show version changelog."""
    changelog = resources.files("fx_alfred").joinpath("CHANGELOG.md")
    click.echo(changelog.read_text())
