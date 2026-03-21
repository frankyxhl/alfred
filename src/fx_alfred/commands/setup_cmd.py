"""Show suggested prompts for agent configuration."""

import click

_SETUP_TEXT = """\
# Alfred Workflow Setup

Add ONE of the following to your agent's instruction file
(CLAUDE.md, agent.md, system prompt, etc.):

## Option A: Minimal

Every time you are about to do a task, run `af guide` first to route,
then `af plan <SOP_IDs>` and follow the output.

## Option B: With routing

Every time you are about to do a task:
1. Run `af guide --root <project-root>` to determine which SOPs apply
2. Run `af plan <SOP_IDs>` to generate workflow instructions
3. Follow each step. Do not skip review gates.

This is not a one-time setup — run it before EVERY task that involves
creating, changing, reviewing, or releasing anything.

## Option C: Full (recommended)

Every time you are about to do a task:
1. Run `af guide --root <project-root>` to see routing (PKG → USR → PRJ)
2. From the decision tree, identify which SOPs apply to this task
3. Run `af plan <SOP_IDs>` to generate step-by-step workflow
4. Follow each step, declaring active SOP at transitions (COR-1402)
5. Do not commit code without completing review steps
6. When task is done, use the plan output as completion checklist

This is MANDATORY before every task — not just at session start.
If you skip routing, you risk following the wrong workflow.
"""


@click.command("setup")
def setup_cmd() -> None:
    """Show suggested prompts for agent configuration."""
    click.echo(_SETUP_TEXT)
