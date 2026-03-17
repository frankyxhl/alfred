from pathlib import Path

import click


def get_root(ctx: click.Context) -> Path:
    """Get root directory from click context."""
    return ctx.obj.get("root", Path.cwd()) if ctx.obj else Path.cwd()
