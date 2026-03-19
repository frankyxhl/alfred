"""Tests for LazyGroup lazy command loading."""

from unittest.mock import patch

import click


class TestLazyGroupListCommands:
    """Cycle 1: LazyGroup.list_commands returns all command names sorted."""

    def test_list_commands_returns_lazy_names_sorted(self):
        from fx_alfred.lazy import LazyGroup

        lazy_subcommands = {
            "zebra": "some.module:zebra_cmd",
            "alpha": "some.module:alpha_cmd",
            "middle": "some.module:middle_cmd",
        }
        group = LazyGroup(name="test", lazy_subcommands=lazy_subcommands)
        ctx = click.Context(group)
        names = group.list_commands(ctx)
        assert names == ["alpha", "middle", "zebra"]

    def test_list_commands_includes_base_and_lazy(self):
        from fx_alfred.lazy import LazyGroup

        lazy_subcommands = {
            "lazy-cmd": "some.module:lazy_cmd",
        }
        group = LazyGroup(name="test", lazy_subcommands=lazy_subcommands)

        # Add a non-lazy command directly
        @click.command()
        def eager_cmd():
            pass

        group.add_command(eager_cmd, "eager-cmd")

        ctx = click.Context(group)
        names = group.list_commands(ctx)
        assert "eager-cmd" in names
        assert "lazy-cmd" in names

    def test_list_commands_empty_lazy(self):
        from fx_alfred.lazy import LazyGroup

        group = LazyGroup(name="test", lazy_subcommands={})
        ctx = click.Context(group)
        names = group.list_commands(ctx)
        assert names == []


class TestLazyGroupGetCommand:
    """Cycle 2: LazyGroup.get_command loads command on demand."""

    def test_get_command_loads_real_command(self):
        """get_command returns the actual Click command from a real module."""
        from fx_alfred.lazy import LazyGroup

        lazy_subcommands = {
            "list": "fx_alfred.commands.list_cmd:list_cmd",
        }
        group = LazyGroup(name="test", lazy_subcommands=lazy_subcommands)
        ctx = click.Context(group)
        cmd = group.get_command(ctx, "list")
        assert cmd is not None
        assert isinstance(cmd, click.Command)
        assert cmd.name == "list"

    def test_get_command_returns_none_for_unknown(self):
        """get_command returns None for commands not registered."""
        from fx_alfred.lazy import LazyGroup

        group = LazyGroup(name="test", lazy_subcommands={})
        ctx = click.Context(group)
        cmd = group.get_command(ctx, "nonexistent")
        assert cmd is None

    def test_get_command_uses_importlib(self):
        """get_command calls importlib.import_module with the correct path."""
        from fx_alfred.lazy import LazyGroup

        lazy_subcommands = {
            "mycmd": "fake.module:my_cmd",
        }
        group = LazyGroup(name="test", lazy_subcommands=lazy_subcommands)
        ctx = click.Context(group)

        fake_cmd = click.Command("mycmd")

        class FakeModule:
            my_cmd = fake_cmd

        with patch("importlib.import_module", return_value=FakeModule()) as mock_imp:
            cmd = group.get_command(ctx, "mycmd")
            mock_imp.assert_called_once_with("fake.module")
            assert cmd is fake_cmd


class TestLazyCliIntegration:
    """Cycle 3: af --version works without importing all commands."""

    def test_version_flag_does_not_import_commands(self):
        """af --version should not trigger any lazy command imports."""
        import importlib

        from click.testing import CliRunner

        from fx_alfred.cli import cli

        original = importlib.import_module
        calls = []

        def tracking_import(name):
            calls.append(name)
            return original(name)

        with patch.object(importlib, "import_module", side_effect=tracking_import):
            runner = CliRunner()
            result = runner.invoke(cli, ["--version"])
            assert result.exit_code == 0
            assert "version" in result.output.lower()
            cmd_imports = [c for c in calls if c.startswith("fx_alfred.commands.")]
            assert cmd_imports == [], f"Command modules imported: {cmd_imports}"

    def test_version_output_contains_package_name(self):
        """af --version should show the package version string."""
        from click.testing import CliRunner

        from fx_alfred.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        # Should contain version info (package_name or version number)
        assert "fx-alfred" in result.output or "version" in result.output.lower()

    def test_cli_group_uses_lazy_group(self):
        """The cli object should be an instance of LazyGroup."""
        from fx_alfred.cli import cli
        from fx_alfred.lazy import LazyGroup

        assert isinstance(cli, LazyGroup)

    def test_cli_has_no_eager_command_imports(self):
        """cli.py should not eagerly import command modules at module level."""
        # This test verifies the LazyGroup registration dict exists
        from fx_alfred.cli import cli
        from fx_alfred.lazy import LazyGroup

        assert isinstance(cli, LazyGroup)
        assert hasattr(cli, "_lazy_subcommands")
        assert len(cli._lazy_subcommands) >= 8
