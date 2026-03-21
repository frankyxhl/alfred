"""Show suggested prompts for agent configuration."""

import click

_SETUP_TEXT = """\
# Alfred Workflow Setup

Add ONE of the following to your agent's instruction file
(CLAUDE.md, agent.md, system prompt, etc.):

## Option A: Minimal

Before any work, run `af plan <SOP_IDs>` and follow the output.

## Option B: With routing

Before any work:
1. Run `af guide --root <project-root>` to determine which SOPs apply
2. Run `af plan <SOP_IDs>` to generate workflow instructions
3. Follow each step. Do not skip review gates.

## Option C: Full

Before any work:
1. Run `af guide --root <project-root>` to see routing (PKG → USR → PRJ)
2. From the decision tree, identify which SOPs apply to this task
3. Run `af plan <SOP_IDs>` to generate step-by-step workflow
4. Follow each step, declaring active SOP at transitions
5. Do not commit code without completing review steps
6. At session end, use the plan output as completion checklist
"""


@click.command("setup")
def setup_cmd() -> None:
    """Show suggested prompts for agent configuration."""
    click.echo(_SETUP_TEXT)
