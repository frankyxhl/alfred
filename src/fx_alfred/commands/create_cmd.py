import re
from datetime import date
from importlib import resources
from pathlib import Path

import click

from fx_alfred.core.scanner import LayerValidationError, scan_documents

VALID_TYPES = {"sop", "adr", "prp"}


def validate_prefix(ctx, param, value):
    if not re.match(r"^[A-Z]{3}$", value):
        raise click.BadParameter("must be exactly 3 uppercase letters (e.g., ALF)")
    if value == "COR":
        raise click.BadParameter("COR prefix is reserved for PKG layer")
    return value


def validate_acid(ctx, param, value):
    if not re.match(r"^\d{4}$", value):
        raise click.BadParameter("must be exactly 4 digits (e.g., 2100)")
    return value


@click.command("create")
@click.argument("doc_type", type=click.Choice(sorted(VALID_TYPES)))
@click.option(
    "--prefix",
    required=True,
    callback=validate_prefix,
    help="Project prefix (e.g., ALF, NRV)",
)
@click.option(
    "--acid", required=True, callback=validate_acid, help="4-digit ACID number"
)
@click.option("--title", required=True, help="Document title")
def create_cmd(doc_type: str, prefix: str, acid: str, title: str):
    """Create a new document from template."""
    try:
        docs = scan_documents(Path.cwd())
    except LayerValidationError as e:
        raise click.ClickException(str(e)) from e

    for doc in docs:
        if doc.acid == acid:
            raise click.ClickException(f"ACID {acid} already exists: {doc.filename}")

    filename = f"{prefix}-{acid}-{doc_type.upper()}-{title.replace(' ', '-')}.md"
    output_path = Path.cwd() / "rules" / filename

    template_file = resources.files("fx_alfred.templates").joinpath(f"{doc_type}.md")
    template = template_file.read_text()

    content = (
        template.replace("{{ACID}}", acid)
        .replace("{{TITLE}}", title)
        .replace("{{DATE}}", date.today().isoformat())
        .replace("{{PREFIX}}", prefix)
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)
    click.echo(f"Created {output_path}")
