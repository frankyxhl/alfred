import re
from datetime import date
from importlib import resources
from pathlib import Path

import click

from fx_alfred.commands._helpers import scan_or_fail
from fx_alfred.context import get_root, root_option

VALID_TYPES = {"sop", "adr", "prp", "ref", "chg", "pln", "inc"}


def validate_prefix(ctx, param, value):
    if not re.match(r"^[A-Z]{3}$", value):
        raise click.BadParameter("must be exactly 3 uppercase letters (e.g., ALF)")
    if value == "COR":
        raise click.BadParameter("COR prefix is reserved for PKG layer")
    return value


def validate_acid(ctx, param, value):
    if value is None:
        return value
    if not re.match(r"^\d{4}$", value):
        raise click.BadParameter("must be exactly 4 digits (e.g., 2100)")
    return value


def _next_acid_in_area(docs: list, prefix: str, area: str) -> str:
    area_int = int(area)
    start = area_int * 100 + (1 if area == "00" else 0)
    end = area_int * 100 + 99

    used = set()
    for doc in docs:
        if doc.prefix == prefix:
            acid_int = int(doc.acid)
            if start <= acid_int <= end:
                used.add(acid_int)

    for candidate in range(start, end + 1):
        if candidate not in used:
            return f"{candidate:04d}"

    raise click.ClickException(
        f"Area {area} is full for prefix {prefix} ({end - start + 1} slots)"
    )


def _resolve_write_base(
    ctx: click.Context, layer: str | None, subdir: str | None
) -> Path:
    root = get_root(ctx)
    user_root = Path.home() / ".alfred"

    # Safety: reject project-layer writes when root is ~/.alfred
    if root.resolve() == user_root.resolve() and layer != "user":
        raise click.ClickException(
            "Refusing to write to project layer inside ~/.alfred. "
            "Use --layer user or set --root to a project directory."
        )

    # Default layer
    if layer is None:
        layer = "project"

    # Validate option combinations
    root_ctx = ctx.find_root()
    root_was_explicit = bool(root_ctx.obj and "root" in root_ctx.obj)
    if layer == "user" and root_was_explicit:
        raise click.ClickException("Cannot use --root with --layer user")
    if layer == "project" and subdir is not None:
        raise click.ClickException("--subdir is only valid with --layer user")

    if layer == "project":
        return root / "rules"

    # User layer
    if subdir is None or subdir == ".":
        return user_root

    rel = Path(subdir)
    if rel.is_absolute() or ".." in rel.parts:
        raise click.ClickException(
            "--subdir must be a safe relative path (no absolute paths or '..')"
        )
    return user_root / rel


_EPILOG = """\
Examples:

  af create sop --prefix ALF --acid 2100 --title "My SOP"

  af create adr --prefix ALF --area 21 --title "Use PostgreSQL"

  af create ref --prefix ALF --acid 2200 --title "API Reference"

  af create sop --prefix USR --acid 3000 --title "My Rule" --layer user

  af create sop --prefix USR --acid 3000 --title "My Rule" --layer user --subdir my-project
"""


@click.command("create", epilog=_EPILOG)
@root_option
@click.argument(
    "doc_type", type=click.Choice(sorted(VALID_TYPES), case_sensitive=False)
)
@click.option(
    "--prefix",
    required=True,
    callback=validate_prefix,
    help="Project prefix (e.g., ALF, NRV)",
)
@click.option(
    "--acid",
    default=None,
    callback=validate_acid,
    help="4-digit ACID number (mutually exclusive with --area)",
)
@click.option(
    "--area",
    default=None,
    help="2-digit area code; auto-assigns next available ACID (mutually exclusive with --acid)",
)
@click.option("--title", required=True, help="Document title")
@click.option(
    "--layer",
    type=click.Choice(["project", "user"], case_sensitive=False),
    default=None,
    help="Write layer: project (./rules/) or user (~/.alfred/).",
)
@click.option(
    "--subdir",
    default=None,
    help="Subdirectory under ~/.alfred/ (only with --layer user).",
)
@click.pass_context
def create_cmd(
    ctx: click.Context,
    doc_type: str,
    prefix: str,
    acid: str | None,
    area: str | None,
    title: str,
    layer: str | None,
    subdir: str | None,
):
    """Create a new document from template."""
    if acid and area:
        raise click.ClickException("Cannot specify both --acid and --area")
    if not acid and not area:
        raise click.ClickException("Must specify either --acid or --area")

    if acid == "0000":
        raise click.ClickException("ACID 0000 is reserved for generated index files")

    # Resolve write base early so --root + --layer user conflict is caught first
    write_base = _resolve_write_base(ctx, layer, subdir)

    docs = scan_or_fail(ctx)

    if area:
        if not re.match(r"^\d{2}$", area):
            raise click.ClickException("--area must be exactly 2 digits (e.g., 21)")
        acid = _next_acid_in_area(docs, prefix, area)

    # acid is guaranteed non-None here
    assert acid is not None

    doc_type_lower = doc_type.lower()

    for doc in docs:
        if doc.prefix == prefix and doc.acid == acid:
            raise click.ClickException(
                f"{prefix}-{acid} already exists in {doc.source.upper()} layer: "
                f"{doc.filename}. "
                "Try --area to auto-assign the next available ACID."
            )
    filename = f"{prefix}-{acid}-{doc_type_lower.upper()}-{title.replace(' ', '-')}.md"
    output_path = write_base / filename

    template_file = resources.files("fx_alfred.templates").joinpath(
        f"{doc_type_lower}.md"
    )
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

    if layer != "user":
        try:
            from fx_alfred.commands.index_cmd import index_cmd

            ctx.invoke(index_cmd)
        except Exception as e:
            click.echo(f"Warning: Failed to update index: {e}", err=True)
