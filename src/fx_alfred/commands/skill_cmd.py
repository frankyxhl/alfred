from __future__ import annotations

import json

import click

from fx_alfred.commands._helpers import scan_or_fail
from fx_alfred.context import root_option
from fx_alfred.core.skills import (
    SCHEMA_VERSION,
    SkillLookupError,
    list_skills,
    read_skill,
    skill_metadata,
)


@click.group("skill")
@root_option
def skill_cmd() -> None:
    """Discover and read explicit skill documents."""


@skill_cmd.command("list")
@click.option("--task", default=None, help="Score skills for a task description.")
@click.option(
    "--layer",
    type=click.Choice(["PKG", "USR", "PRJ", "all"], case_sensitive=False),
    default="all",
    help="Filter by document layer.",
)
@click.option("--json", "json_output", is_flag=True, help="Output as JSON object.")
@click.pass_context
def skill_list_cmd(
    ctx: click.Context,
    task: str | None,
    layer: str,
    json_output: bool,
) -> None:
    """List skill documents."""
    docs = scan_or_fail(ctx)
    results = list_skills(docs, task=task, layer=layer)

    if json_output:
        click.echo(
            json.dumps(
                {"schema_version": SCHEMA_VERSION, "results": results},
                ensure_ascii=False,
            )
        )
        return

    if not results:
        click.echo("No matching skills found." if task else "No skills found.")
        return

    for item in results:
        layer_label = item["source"]["layer"]
        score = "" if item["score"] is None else f"  score={item['score']}"
        click.echo(
            f"{layer_label:<3}  {item['id']}  {item['type_code']:<3}  "
            f"{item['title']}{score}"
        )


@skill_cmd.command("read")
@click.argument("identifier")
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output as JSON object with metadata and content.",
)
@click.pass_context
def skill_read_cmd(
    ctx: click.Context,
    identifier: str,
    json_output: bool,
) -> None:
    """Read a skill by ID, ACID, exact title, or slug."""
    docs = scan_or_fail(ctx)
    try:
        doc, content = read_skill(docs, identifier)
    except SkillLookupError as exc:
        raise click.ClickException(str(exc)) from exc

    if json_output:
        click.echo(
            json.dumps(
                {
                    "schema_version": SCHEMA_VERSION,
                    "document": skill_metadata(doc),
                    "content": content,
                },
                ensure_ascii=False,
            )
        )
        return

    click.echo(content)
