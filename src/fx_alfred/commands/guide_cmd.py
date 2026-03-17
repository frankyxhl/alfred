from importlib import resources

import click


@click.command("guide")
def guide_cmd():
    """Show quick start guide."""
    guide_content = resources.files("fx_alfred.templates").joinpath("guide.md")
    click.echo(guide_content.read_text())
