"""af render command — render a Markdown file to a standalone HTML document."""

from __future__ import annotations

from pathlib import Path

import click

from fx_alfred.core.markdown_render import render_document


def _derive_title(md: str, file: Path) -> str:
    """Title = the first ATX H1 if present, else the file stem."""
    for line in md.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return file.stem


@click.command("render")
@click.argument("file", type=click.Path(path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    help="Write the HTML document to this file instead of stdout.",
)
@click.option(
    "--title", help="Document <title> (default: first H1, else the file stem)."
)
def render_cmd(file: Path, output: Path | None, title: str | None) -> None:
    """Render a Markdown FILE to a standalone HTML document.

    With no --output, the HTML is printed to stdout.
    """
    if not file.exists():
        raise click.ClickException(f"File not found: {file}")
    md = file.read_text(encoding="utf-8")
    html_doc = render_document(md, title or _derive_title(md, file))
    if output is not None:
        output.write_text(html_doc, encoding="utf-8")
        click.echo(f"Wrote {output}")
    else:
        click.echo(html_doc, nl=False)
