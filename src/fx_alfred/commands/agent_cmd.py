from __future__ import annotations


import click

from fx_alfred.commands._helpers import emit_json

from fx_alfred.context import get_root, root_option
from fx_alfred.core.agent_helpers import (
    AgentArgError,
    agent_tools_enabled,
    call_helper,
    gate_error_envelope,
    parse_arg_pairs,
    run_script,
)


@click.group("agent")
@root_option
def agent_cmd() -> None:
    """Run explicitly enabled agent helper tools."""


@agent_cmd.command("call")
@click.argument("helper_name")
@click.option(
    "--arg",
    "arg_pairs",
    multiple=True,
    help="Helper argument as key=value. May be repeated.",
)
@click.option("--json", "json_output", is_flag=True, help="Output as JSON envelope.")
@click.pass_context
def agent_call_cmd(
    ctx: click.Context,
    helper_name: str,
    arg_pairs: tuple[str, ...],
    json_output: bool,
) -> None:
    """Call a PRJ or USR helper function."""
    if not agent_tools_enabled():
        envelope = gate_error_envelope("helper", helper_name)
        if json_output:
            emit_json(envelope)
            ctx.exit(1)
        else:
            raise click.ClickException(envelope["error"]["message"])

    try:
        kwargs = parse_arg_pairs(arg_pairs)
    except AgentArgError as exc:
        raise click.UsageError(str(exc)) from exc

    envelope = call_helper(get_root(ctx), helper_name, kwargs)
    if json_output:
        emit_json(envelope)
        ctx.exit(0 if envelope["status"] == "ok" else 1)
    elif envelope["status"] == "ok":
        click.echo(str(envelope["result"]))
        return
    else:
        raise click.ClickException(envelope["error"]["message"])


@agent_cmd.command("run")
@click.argument("script_path")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON envelope.")
@click.pass_context
def agent_run_cmd(
    ctx: click.Context,
    script_path: str,
    json_output: bool,
) -> None:
    """Run a Python script through the current interpreter."""
    if not agent_tools_enabled():
        envelope = gate_error_envelope("script", script_path)
        if json_output:
            emit_json(envelope)
            ctx.exit(1)
        else:
            raise click.ClickException(envelope["error"]["message"])

    envelope = run_script(get_root(ctx), script_path)
    if json_output:
        emit_json(envelope)
        ctx.exit(0 if envelope["status"] == "ok" else 1)
    else:
        click.echo(envelope["stdout"], nl=False)
        click.echo(envelope["stderr"], nl=False, err=True)
        exit_code = envelope["exit_code"]
        ctx.exit(exit_code if isinstance(exit_code, int) else 1)
