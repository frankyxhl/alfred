from pathlib import Path

import click

from fx_alfred.core.document import FILENAME_PATTERN


def discover_root(start: Path) -> Path:
    """Return the nearest ancestor of ``start`` (inclusive) that is an
    Alfred project root, else ``start`` itself.

    A directory qualifies when its ``rules/`` subdirectory contains at
    least one non-COR document matching ``FILENAME_PATTERN`` — bare
    ``rules/`` folders from unrelated projects do not count, and neither
    does the bundled PKG rules directory (COR-only by the scanner's layer
    invariant; treating it as a PRJ root would raise LayerValidationError,
    e.g. when running from inside ``src/fx_alfred/``). The fallback
    preserves the pre-CHG-2300 behavior (cwd) for invocations outside any
    Alfred project.
    """
    for candidate in (start, *start.parents):
        rules_dir = candidate / "rules"
        if not rules_dir.is_dir():
            continue
        try:
            entries = rules_dir.iterdir()
        except OSError:
            continue
        if any(
            e.is_file()
            and FILENAME_PATTERN.match(e.name)
            and not e.name.startswith("COR-")
            for e in entries
        ):
            return candidate
    return start


def _store_root(
    ctx: click.Context, param: click.Parameter, value: Path | None
) -> Path | None:  # type: ignore[type-arg]
    if value is not None:
        root_ctx = ctx.find_root()
        root_ctx.ensure_object(dict)
        root_ctx.obj["root"] = value.resolve()
    return value


def root_option(f):  # type: ignore[type-arg]
    return click.option(
        "--root",
        type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),  # type: ignore[type-var]
        expose_value=False,
        callback=_store_root,
        help=(
            "Project root directory (default: nearest ancestor whose rules/ "
            "contains Alfred documents, else the working directory)"
        ),
    )(f)


def get_root(ctx: click.Context) -> Path:
    """Get root directory from click context.

    Explicit ``--root`` wins; otherwise the nearest Alfred project root
    above the working directory is used (CHG-2300), falling back to the
    working directory itself.
    """
    root_ctx = ctx.find_root()
    if root_ctx.obj and "root" in root_ctx.obj:
        return root_ctx.obj["root"]
    return discover_root(Path.cwd())
