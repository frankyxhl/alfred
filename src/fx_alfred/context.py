from pathlib import Path

import click


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
        help="Project root directory",
    )(f)


def get_root(ctx: click.Context) -> Path:
    """Get root directory from click context."""
    root_ctx = ctx.find_root()
    if root_ctx.obj and "root" in root_ctx.obj:
        return root_ctx.obj["root"]
    return Path.cwd()
