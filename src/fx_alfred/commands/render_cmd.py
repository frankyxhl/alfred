"""af render command — render a Markdown file to a standalone HTML document."""

from __future__ import annotations

from pathlib import Path

import click

from fx_alfred.core.markdown_render import first_h1, render_document


def _derive_title(md: str, file: Path) -> str:
    """Title = the first ATX H1 outside code fences (shared fence rules), else the file stem."""
    return first_h1(md) or file.stem


@click.command("render")
@click.argument("file")
@click.option(
    "-o",
    "--output",
    help="Write the HTML document to this file instead of stdout.",
)
@click.option(
    "--title", help="Document <title> (default: first H1, else the file stem)."
)
def render_cmd(file: str, output: str | None, title: str | None) -> None:
    """Render a Markdown FILE to a standalone HTML document.

    With no --output, the HTML is printed to stdout.
    """
    path = Path(file)
    if not path.exists():
        raise click.ClickException(f"File not found: {path}")
    if path.is_dir():
        raise click.ClickException(f"Not a file: {path}")
    md = path.read_text(encoding="utf-8")
    html_doc = render_document(md, title or _derive_title(md, path))
    if output is not None:
        Path(output).write_text(html_doc, encoding="utf-8")
        click.echo(f"Wrote {output}")
    else:
        click.echo(html_doc, nl=False)
