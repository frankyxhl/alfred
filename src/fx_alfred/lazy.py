"""LazyGroup: Click group that imports command modules on demand."""

from __future__ import annotations

import click


class LazyGroup(click.Group):
    """Click group that lazily loads subcommands on first access."""

    def __init__(
        self,
        *args,
        lazy_subcommands: dict[str, str] | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._lazy_subcommands = lazy_subcommands or {}

    def list_commands(self, ctx: click.Context) -> list[str]:
        base = super().list_commands(ctx)
        lazy = sorted(self._lazy_subcommands.keys())
        return base + lazy

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        if cmd_name in self._lazy_subcommands:
            return self._load_lazy(cmd_name)
        return super().get_command(ctx, cmd_name)

    def _load_lazy(self, cmd_name: str) -> click.Command:
        import importlib

        module_path, attr = self._lazy_subcommands[cmd_name].rsplit(":", 1)
        mod = importlib.import_module(module_path)
        return getattr(mod, attr)
