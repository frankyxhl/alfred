import contextlib
import getpass
import os
import re
import tempfile
import time
from datetime import date
from importlib import resources
from pathlib import Path
from typing import Any

import click
import yaml

try:
    import fcntl
except ModuleNotFoundError:  # pragma: no cover - non-POSIX platforms (Windows)
    fcntl = None  # type: ignore[assignment]

from fx_alfred.commands._helpers import (
    invoke_index_update,
    render_section_content,
    scan_or_fail,
    validate_spec_status,
)
from fx_alfred.context import get_root, root_option
from fx_alfred.core.document import FILENAME_PATTERN
from fx_alfred.core.normalize import slugify
from fx_alfred.core.projects import project_layer_dir
from fx_alfred.core.schema import (
    DocType,
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


def _validate_generated_filename(filename: str, title: str) -> str:
    if not FILENAME_PATTERN.match(filename):
        raise click.ClickException(
            f"Title {title!r} generated invalid filename {filename!r}. "
            "Choose a title with at least one alphanumeric character so the slug is not empty."
        )
    return filename


def lock_path_for(write_base: Path) -> Path:  # noqa: ARG001 - one lock for every target
    """The single per-user `af create` lock: `~/.alfred/.af-create.lock`.

    Allocation scopes overlap (a global user write numbers against every
    registered unit AND the caller's rules/; a unit write against the global
    USR area), so per-scope locks cannot be made disjoint. `~/.alfred` is
    the one location every process touching the document namespace shares
    (unlike TMPDIR, which varies per environment) and is per-user by
    construction. When `~/.alfred` cannot be written (read-only HOME in a
    container or service account) the lock degrades to the temp dir so a
    project-layer create still works. Creates are rare and hold the lock
    for milliseconds.
    """
    user_root = Path.home() / ".alfred"
    try:
        user_root.mkdir(parents=True, exist_ok=True)
        if os.access(user_root, os.W_OK):
            return user_root / ".af-create.lock"
    except OSError:
        pass
    ident = str(os.getuid()) if hasattr(os, "getuid") else getpass.getuser()
    return Path(tempfile.gettempdir()) / f"af-create-{ident}.lock"


def _reclaim_stale_marker(marker: Path) -> bool:
    """Remove a fallback marker older than AF_CREATE_LOCK_STALE seconds
    (default 60): a killed process never reaches its `finally`."""
    stale_after = float(os.environ.get("AF_CREATE_LOCK_STALE", "60"))
    try:
        age = time.time() - marker.stat().st_mtime
    except FileNotFoundError:
        return True
    if age < stale_after:
        return False
    with contextlib.suppress(FileNotFoundError):
        marker.unlink()
    return True


@contextlib.contextmanager
def _creation_lock(write_base: Path, dry_run: bool = False):
    """Serialise allocation + write, so two concurrent `af create` runs cannot
    pick the same next ACID. POSIX: flock on the lock file (released by the
    OS on any exit). Elsewhere: an exclusive-create `.excl` marker holding
    `pid mtime`, reclaimed when stale. Waits up to AF_CREATE_LOCK_TIMEOUT
    seconds (default 10)."""
    if dry_run:  # a preview writes nothing — not even a lock file
        yield
        return
    timeout = float(os.environ.get("AF_CREATE_LOCK_TIMEOUT", "10"))
    deadline = time.monotonic() + timeout
    lock_path = lock_path_for(write_base)
    busy = click.ClickException("another af create is running; retry in a moment")
    if fcntl is None:
        marker = lock_path.with_suffix(".excl")
        while True:
            try:
                fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                break
            except FileExistsError:
                if _reclaim_stale_marker(marker):
                    continue
                if time.monotonic() >= deadline:
                    raise busy from None
                time.sleep(0.05)
        try:
            os.write(fd, f"{os.getpid()} {int(time.time())}".encode())
            os.close(fd)
            yield
        finally:
            with contextlib.suppress(FileNotFoundError):
                marker.unlink()
        return
    with open(lock_path, "a+") as handle:
        while True:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise busy from None
                time.sleep(0.05)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _reject_scanner_invisible(write_base: Path, units: dict[str, Path]) -> None:
    """A user-layer destination the scanner skips (`logs/` at the top of
    ~/.alfred or of a registered unit, or a rules/.../logs path) would hold
    documents no later scan can see: refuse to create there."""
    user_root = Path.home() / ".alfred"
    roots = [user_root, user_root.resolve()]
    unit_root = _registered_unit_root(write_base, units)
    if unit_root is not None:
        roots += [unit_root, unit_root.resolve()]
    # Judge the lexical path AND the resolved one: `~/.alfred/safe` may be a
    # symlink into the excluded logs tree.
    for base in (write_base, write_base.resolve()):
        for root in roots:
            try:
                parts = base.relative_to(root).parts
            except ValueError:
                continue
            if (parts and parts[0] == "logs") or ("rules" in parts and "logs" in parts):
                raise click.ClickException(
                    f"{write_base} is excluded from document scanning (logs path); "
                    "choose another --subdir"
                )


def _registered_units() -> dict[str, Path]:
    """NAME -> `~/.alfred/NAME` for every subproject registered in projects.json."""
    from fx_alfred.core.projects import load_projects

    user_root = Path.home() / ".alfred"
    return {name: user_root / name for name in set(load_projects().values())}


def _registered_unit_root(write_base: Path, units: dict[str, Path]) -> Path | None:
    """`~/.alfred/<NAME>` when `write_base` lies inside a registered unit (any
    depth). Lexical first — `<NAME>` may be a symlink to external storage, so
    resolving before the containment check would move the path outside the
    user root; the resolved comparison is only a fallback."""
    user_root = Path.home() / ".alfred"
    for base in (write_base, write_base.resolve()):
        for root in (user_root, user_root.resolve()):
            try:
                rel = base.relative_to(root)
            except ValueError:
                continue
            if rel.parts and rel.parts[0] in units:
                return units[rel.parts[0]]
    return None


def _scan_units_into(merged: list, dirs) -> list:
    from fx_alfred.core.scanner import _scan_path_dir

    seen = {(d.prefix, d.acid, str(d.directory)) for d in merged}
    for directory in dirs:
        if not directory.is_dir():
            continue
        for doc in _scan_path_dir(directory, source="usr", recursive=True):
            key = (doc.prefix, doc.acid, str(doc.directory))
            if key not in seen:
                seen.add(key)
                merged.append(doc)
    return merged


def _allocation_docs(docs: list, write_base: Path, layer: str | None) -> list:
    """The documents ACID allocation and the collision check must see.

    Project layer: `scan_documents` already scanned the target (non-recursively,
    on purpose — `rules/archive/` is invisible), so the scan is used as is.

    User layer, target inside a registered unit `~/.alfred/<NAME>/…` (any
    depth): that whole unit is one PRJ layer, so the scope is PKG + USR + a
    recursive scan of `<NAME>`; the caller's own PRJ documents (a different
    unit, or the same one — rescanned anyway) are dropped, and the unit is
    scanned directly because the USR scan hides registered directories.

    User layer, target in the global `~/.alfred` area: the document becomes
    visible to EVERY later scan, so the scope is the scan as is (PKG + USR +
    the caller's PRJ) plus a recursive scan of every registered unit — a USR
    document duplicating any unit's ACID would fail `_validate_layers()`
    the next time that unit is scanned.
    """
    if layer != "user":
        return docs
    units = _registered_units()
    _reject_scanner_invisible(write_base, units)
    unit_root = _registered_unit_root(write_base, units)
    if unit_root is not None:
        return _scan_units_into([d for d in docs if d.source != "prj"], [unit_root])
    return _scan_units_into(list(docs), units.values())


def _next_acid_sequential(docs: list, prefix: str) -> str:
    """The simplest numbering: the highest ACID already used by ``prefix`` + 1.

    ``0000`` (the document index) counts as used, so an empty project starts at
    ``0001``; area-numbered documents raise the high-water mark (after
    ``2100`` comes ``2101``) — no gap-filling, so a number is never reused.
    """
    highest = 0
    for doc in docs:
        if doc.prefix == prefix:
            try:
                highest = max(highest, int(doc.acid))
            except (TypeError, ValueError):
                continue
    if highest >= 9999:
        raise click.ClickException(f"No ACID left for prefix {prefix} (9999 reached)")
    return f"{highest + 1:04d}"


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
        return project_layer_dir(root)

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


def _resolve_spec_fields(
    spec: dict[str, Any],
    prefix: str | None,
    acid: str | None,
    area: str | None,
    title: str | None,
) -> tuple[DocType, str, str | None, str | None, str, dict[str, Any], dict[str, Any]]:
    """Extract, override with CLI args, and validate spec fields for --spec mode."""
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
    # Neither --acid nor --area: sequential numbering (highest used + 1), assigned below.

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
        validate_spec_status(doc_type_enum, spec_metadata["Status"])

    return (
        doc_type_enum,
        final_prefix,
        final_acid,
        final_area,
        final_title,
        spec_metadata,
        spec_sections,
    )


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
        rendered = render_section_content(section_content)
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
    help="4-digit ACID number (mutually exclusive with --area). Omit both --acid and --area to number sequentially: highest existing ACID for the prefix + 1, starting at 0001",
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
            with open(spec_path, "r", encoding="utf-8") as f:
                spec = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise click.ClickException(f"Invalid YAML in spec file: {e}")

        (
            doc_type_enum,
            final_prefix,
            final_acid,
            final_area,
            final_title,
            spec_metadata,
            spec_sections,
        ) = _resolve_spec_fields(spec, prefix, acid, area, title)

        # Resolve write base
        write_base = _resolve_write_base(ctx, layer, subdir)

        # Scan for existing docs to check collisions and auto-assign ACID
        with _creation_lock(write_base, dry_run=dry_run):
            docs = _allocation_docs(scan_or_fail(ctx), write_base, layer)

            # Auto-assign ACID from area if needed
            if final_acid is None and final_area is not None:
                final_acid = _next_acid_in_area(docs, final_prefix, str(final_area))
            elif final_acid is None:
                final_acid = _next_acid_sequential(docs, final_prefix)

            if final_acid is None:
                raise click.ClickException(
                    "ACID resolution failed for spec-file mode "
                    "(neither acid nor area resolved to a valid ACID)"
                )

            # Check for duplicate
            for existing_doc in docs:
                if (
                    existing_doc.prefix == final_prefix
                    and existing_doc.acid == final_acid
                ):
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

            filename = _validate_generated_filename(
                f"{final_prefix}-{final_acid}-{doc_type_enum.value}-{slugify(final_title)}.md",
                final_title,
            )
            output_path = write_base / filename

            if dry_run:
                click.echo("Dry run — no file written.\n")
                click.echo(content)
                return

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")
            click.echo(f"Created {output_path}")

            if layer != "user":
                invoke_index_update(ctx)
        return

    # ── Mode 2: CLI args mode (original behavior) ──────────────────────────────
    if doc_type is None:
        raise click.ClickException(
            "Document type argument required when not using --spec"
        )

    if acid and area:
        raise click.ClickException("Cannot specify both --acid and --area")

    # prefix and title are required in CLI mode (validate_prefix returns original value if None passed)
    if prefix is None:
        raise click.ClickException("Missing option '--prefix'.")
    if title is None:
        raise click.ClickException("Missing option '--title'.")

    if acid == "0000":
        raise click.ClickException("ACID 0000 is reserved for generated index files")

    # Resolve write base early so --root + --layer user conflict is caught first
    write_base = _resolve_write_base(ctx, layer, subdir)

    with _creation_lock(write_base, dry_run=dry_run):
        docs = _allocation_docs(scan_or_fail(ctx), write_base, layer)

        if area is not None:
            if not re.match(r"^\d{2}$", area):
                raise click.ClickException("--area must be exactly 2 digits (e.g., 21)")
            acid = _next_acid_in_area(docs, prefix, area)
        elif acid is None:
            acid = _next_acid_sequential(docs, prefix)

        if acid is None:
            raise click.ClickException(
                "ACID resolution failed for CLI mode "
                "(neither --acid nor --area resolved to a valid ACID)"
            )

        doc_type_lower = doc_type.lower()

        for doc in docs:
            if doc.prefix == prefix and doc.acid == acid:
                raise click.ClickException(
                    f"{prefix}-{acid} already exists in {doc.source.upper()} layer: "
                    f"{doc.filename}. "
                    "Try --area to auto-assign the next available ACID."
                )
        filename = _validate_generated_filename(
            f"{prefix}-{acid}-{doc_type_lower.upper()}-{slugify(title)}.md", title
        )
        output_path = write_base / filename

        template_file = resources.files("fx_alfred.templates").joinpath(
            f"{doc_type_lower}.md"
        )
        template = template_file.read_text(encoding="utf-8")

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
        output_path.write_text(content, encoding="utf-8")
        click.echo(f"Created {output_path}")

        if layer != "user":
            invoke_index_update(ctx)
