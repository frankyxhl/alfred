"""Show suggested prompts for agent configuration."""

import click

_SETUP_TEXT = """\
# Alfred Workflow Setup

Add ONE of the following to your agent's instruction file
(CLAUDE.md, agent.md, system prompt, etc.):

## Option A: Minimal

At session start, run `af guide` to see routing.
Before every task, run `af plan <SOP_IDs>` and follow the output.

## Option B: With routing

At session start:
1. Run `af guide --root <project-root>` to see routing (PKG → USR → PRJ)

Before every task:
2. From the decision tree, identify which SOPs apply
3. Run `af plan <SOP_IDs>` to generate workflow instructions
4. Follow each step. Do not skip review gates.

## Option C: Full (recommended)

At session start:
1. Run `af guide --root <project-root>` to see routing (PKG → USR → PRJ)

Before every task:
2. From the decision tree, identify which SOPs apply to this task
3. Run `af plan <SOP_IDs>` to generate step-by-step workflow
4. Follow each step, declaring active SOP at transitions (COR-1402)
5. Do not commit code without completing review steps
6. When task is done, use the plan output as completion checklist

af guide = once per session (routing context).
af plan  = before EVERY task (checklist from SOPs).
"""


@click.command("setup")
def setup_cmd() -> None:
    """Show suggested prompts for agent configuration."""
    click.echo(_SETUP_TEXT)
