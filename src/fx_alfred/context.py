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
    usr_alfred = Path.home() / ".alfred"
    for candidate in (start, *start.parents):
        if candidate == usr_alfred:
            # The USR layer home can never be a PRJ root: discovering it
            # would alias the same files into both the USR (recursive)
            # and PRJ (rules/) scans → duplicate-ID LayerValidationError
            # (FXA-2300 R1 glm finding).
            continue
        rules_dir = candidate / "rules"
        if not rules_dir.is_dir():
            continue
        # iterdir() is lazy — entry-level OSErrors (stale NFS handles,
        # per-entry permission failures) surface during iteration, so the
        # whole scan sits inside the try (FXA-2300 R1 convergent finding).
        try:
            if any(
                e.is_file()
                and FILENAME_PATTERN.match(e.name)
                and not e.name.startswith("COR-")
                for e in rules_dir.iterdir()
            ):
                return candidate
        except OSError:
            continue
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
