import re
from datetime import date
from importlib import resources
from pathlib import Path
from typing import Any

import click
import yaml

from fx_alfred.commands._helpers import scan_or_fail
from fx_alfred.context import get_root, root_option
from fx_alfred.core.normalize import slugify
from fx_alfred.core.schema import (
    DocType,
    ALLOWED_STATUSES,
    REQUIRED_METADATA,
    REQUIRED_SECTIONS,
)

VALID_TYPES = {"sop", "adr", "prp", "ref", "chg", "pln", "inc"}
VALID_TYPE_NAMES = sorted(dt.value for dt in DocType)


def validate_prefix(ctx, param, value):
    if value is None:
        return value
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


def _validate_spec_doc_type(type_str: str) -> DocType:
    """Validate document type string and return DocType enum."""
    type_upper = type_str.upper()
    try:
        return DocType(type_upper)
    except ValueError:
        valid_types = ", ".join(VALID_TYPE_NAMES)
        raise click.ClickException(
            f"Unknown document type '{type_str}'; valid: {valid_types}"
        )


def _validate_spec_status(doc_type: DocType, status: str) -> None:
    """Validate status for the given document type."""
    allowed = ALLOWED_STATUSES.get(doc_type, [])
    if status not in allowed:
        allowed_str = ", ".join(allowed)
        raise click.ClickException(
            f"Status '{status}' not allowed for {doc_type.value}; allowed: {allowed_str}"
        )


def _validate_spec_required_metadata(
    doc_type: DocType, metadata: dict[str, Any]
) -> None:
    """Validate that all required metadata fields are present."""
    required = REQUIRED_METADATA.get(doc_type, [])
    for field in required:
        if field not in metadata:
            raise click.ClickException(
                f"Required metadata field '{field}' missing for {doc_type.value}"
            )


def _validate_spec_required_sections(
    doc_type: DocType, sections: dict[str, Any]
) -> None:
    """Validate that all required sections are present."""
    required = REQUIRED_SECTIONS.get(doc_type, [])
    for section in required:
        if section not in sections:
            raise click.ClickException(
                f"Required section '{section}' missing for {doc_type.value}"
            )


def _render_section_content(content: Any) -> str:
    """Render section content to markdown text."""
    if isinstance(content, list):
        lines = []
        for item in content:
            lines.append(f"- {item}")
        return "\n".join(lines)
    elif isinstance(content, str):
        return content
    else:
        return str(content)


def _generate_spec_document(
    doc_type: DocType,
    prefix: str,
    acid: str,
    title: str,
    metadata: dict[str, Any],
    sections: dict[str, Any],
) -> str:
    """Generate full markdown document content from spec."""
    today = date.today().isoformat()
    lines: list[str] = []

    # H1 header
    lines.append(f"# {doc_type.value}-{acid}: {title}")
    lines.append("")

    # Metadata fields in canonical order
    canonical_order = REQUIRED_METADATA.get(doc_type, [])
    # Add any extra metadata fields
    all_fields = list(metadata.keys())
    for field in canonical_order:
        if field in metadata:
            lines.append(f"**{field}:** {metadata[field]}")
    # Add any extra fields not in canonical order
    for field in all_fields:
        if field not in canonical_order:
            lines.append(f"**{field}:** {metadata[field]}")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Sections
    for section_name, section_content in sections.items():
        lines.append(f"## {section_name}")
        lines.append("")
        rendered = _render_section_content(section_content)
        lines.append(rendered)
        lines.append("")

    # Change History
    lines.append("---")
    lines.append("")
    lines.append("## Change History")
    lines.append("")
    lines.append("| Date | Change | By |")
    lines.append("|------|--------|----|")
    lines.append(f"| {today} | Initial version | — |")
    lines.append("")

    return "\n".join(lines)


_EPILOG = """\
Examples:

  af create sop --prefix ALF --acid 2100 --title "My SOP"

  af create adr --prefix ALF --area 21 --title "Use PostgreSQL"

  af create ref --prefix ALF --acid 2200 --title "API Reference"

  af create sop --prefix USR --acid 3000 --title "My Rule" --layer user

  af create sop --prefix USR --acid 3000 --title "My Rule" --layer user --subdir my-project

  af create --spec spec.yaml
"""


@click.command("create", epilog=_EPILOG)
@root_option
@click.argument(
    "doc_type",
    type=click.Choice(sorted(VALID_TYPES), case_sensitive=False),
    required=False,
)
@click.option(
    "--prefix",
    default=None,
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
@click.option("--title", default=None, help="Document title")
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
@click.option(
    "--spec",
    "spec_path",
    default=None,
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="YAML spec file for document creation (alternative to CLI args).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Preview generated content without writing to disk.",
)
@click.pass_context
def create_cmd(
    ctx: click.Context,
    doc_type: str | None,
    prefix: str | None,
    acid: str | None,
    area: str | None,
    title: str | None,
    layer: str | None,
    subdir: str | None,
    spec_path: str | None,
    dry_run: bool,
):
    """Create a new document from template or spec file."""
    # ── Mode 1: Spec file mode ───────────────────────────────────────────────
    if spec_path:
        try:
            with open(spec_path, "r") as f:
                spec = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise click.ClickException(f"Invalid YAML in spec file: {e}")

        if not isinstance(spec, dict):
            raise click.ClickException("Spec file must contain a YAML mapping")

        # Extract and validate type
        type_str = spec.get("type")
        if type_str is None:
            raise click.ClickException("Spec file missing 'type' field")
        doc_type_enum = _validate_spec_doc_type(type_str)

        # Extract prefix, acid, title from spec if not given via CLI
        spec_prefix = spec.get("prefix")
        spec_acid = spec.get("acid")
        spec_title = spec.get("title")
        spec_area = spec.get("area")

        # CLI args override spec
        final_prefix = prefix if prefix is not None else spec_prefix
        final_acid = acid if acid is not None else spec_acid
        final_title = title if title is not None else spec_title
        final_area = area if area is not None else spec_area

        # Enforce acid/area mutual exclusivity from spec
        if spec_acid is not None and spec_area is not None:
            raise click.ClickException("Spec cannot contain both 'acid' and 'area'")

        # Enforce acid/area mutual exclusivity across all sources (CLI + spec)
        if final_acid is not None and final_area is not None:
            raise click.ClickException("Cannot specify both acid and area")

        # Validate required fields
        if final_prefix is None:
            raise click.ClickException("Prefix required (via --prefix or spec file)")
        if final_title is None:
            raise click.ClickException("Title required (via --title or spec file)")
        if final_acid is None and final_area is None:
            raise click.ClickException(
                "ACID or area required (via --acid/--area or spec file)"
            )

        # Validate prefix format (reuse callback logic)
        if not re.match(r"^[A-Z]{3}$", final_prefix):
            raise click.ClickException("Prefix must be exactly 3 uppercase letters")
        if final_prefix == "COR":
            raise click.ClickException("COR prefix is reserved for PKG layer")

        # Validate ACID format if provided
        if final_acid is not None:
            if not re.match(r"^\d{4}$", str(final_acid)):
                raise click.ClickException("ACID must be exactly 4 digits")
            final_acid = str(final_acid)
            if final_acid == "0000":
                raise click.ClickException(
                    "ACID 0000 is reserved for generated index files"
                )

        # Validate area format if provided
        if final_area is not None:
            if not re.match(r"^\d{2}$", str(final_area)):
                raise click.ClickException("Area must be exactly 2 digits")

        # Extract and validate metadata
        spec_metadata = spec.get("metadata", {})
        spec_sections = spec.get("sections", {})

        if not isinstance(spec_metadata, dict):
            raise click.ClickException(
                "Spec 'metadata' must be a mapping (key: value pairs)"
            )
        if not isinstance(spec_sections, dict):
            raise click.ClickException(
                "Spec 'sections' must be a mapping (key: value pairs)"
            )

        # Auto-fill Last updated if not provided (before validation)
        if "Last updated" not in spec_metadata:
            spec_metadata["Last updated"] = date.today().isoformat()

        # Validate required metadata
        _validate_spec_required_metadata(doc_type_enum, spec_metadata)

        # Validate required sections
        _validate_spec_required_sections(doc_type_enum, spec_sections)

        # Validate status if provided
        if "Status" in spec_metadata:
            _validate_spec_status(doc_type_enum, spec_metadata["Status"])

        # Resolve write base
        write_base = _resolve_write_base(ctx, layer, subdir)

        # Scan for existing docs to check collisions and auto-assign ACID
        docs = scan_or_fail(ctx)

        # Auto-assign ACID from area if needed
        if final_acid is None and final_area is not None:
            final_acid = _next_acid_in_area(docs, final_prefix, str(final_area))

        assert final_acid is not None

        # Check for duplicate
        for existing_doc in docs:
            if existing_doc.prefix == final_prefix and existing_doc.acid == final_acid:
                raise click.ClickException(
                    f"{final_prefix}-{final_acid} already exists in {existing_doc.source.upper()} layer: "
                    f"{existing_doc.filename}. "
                    "Try --area to auto-assign the next available ACID."
                )

        # Generate document content
        content = _generate_spec_document(
            doc_type_enum,
            final_prefix,
            str(final_acid),
            final_title,
            spec_metadata,
            spec_sections,
        )

        filename = f"{final_prefix}-{final_acid}-{doc_type_enum.value}-{slugify(final_title)}.md"
        output_path = write_base / filename

        if dry_run:
            click.echo("Dry run — no file written.\n")
            click.echo(content)
            return

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)
        click.echo(f"Created {output_path}")

        if layer != "user":
            try:
                from fx_alfred.commands.index_cmd import index_cmd

                ctx.invoke(index_cmd)
            except Exception as e:
                click.echo(f"Warning: Failed to update index: {e}", err=True)
        return

    # ── Mode 2: CLI args mode (original behavior) ──────────────────────────────
    if doc_type is None:
        raise click.ClickException(
            "Document type argument required when not using --spec"
        )

    if acid and area:
        raise click.ClickException("Cannot specify both --acid and --area")
    if not acid and not area:
        raise click.ClickException("Must specify either --acid or --area")

    # prefix and title are required in CLI mode (validate_prefix returns original value if None passed)
    if prefix is None:
        raise click.ClickException("Missing option '--prefix'.")
    if title is None:
        raise click.ClickException("Missing option '--title'.")

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
    filename = f"{prefix}-{acid}-{doc_type_lower.upper()}-{slugify(title)}.md"
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

    if dry_run:
        click.echo("Dry run — no file written.\n")
        click.echo(content)
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)
    click.echo(f"Created {output_path}")

    if layer != "user":
        try:
            from fx_alfred.commands.index_cmd import index_cmd

            ctx.invoke(index_cmd)
        except Exception as e:
            click.echo(f"Warning: Failed to update index: {e}", err=True)
