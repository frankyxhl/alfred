"""Show suggested prompts for agent configuration."""

import click

_SETUP_TEXT = """\
# Alfred Workflow Setup

Add ONE of the following to your agent's instruction file
(CLAUDE.md, agent.md, system prompt, etc.):

## Option A: Minimal

Load today's Discussion Tracker per COR-1201 (auto-increments D items).
At session start, run `af guide` to see routing.
Before every task, run `af plan <SOP_IDs>` and follow the output.

## Option B: With routing

At session start:
1. Load today's Discussion Tracker per COR-1201 (auto-increments D items)
2. Run `af guide --root <project-root>` to see routing (PKG → USR → PRJ)

Before every task:
3. From the decision tree, identify which SOPs apply
4. Run `af plan <SOP_IDs>` to generate workflow instructions
5. Follow each step. Do not skip review gates.

## Option C: Full (recommended)

At session start:
1. Load today's Discussion Tracker per COR-1201 (auto-increments D items)
2. Run `af guide --root <project-root>` to see routing (PKG → USR → PRJ)

Before every task:
3. From the decision tree, identify which SOPs apply to this task
4. Run `af plan <SOP_IDs>` to generate step-by-step workflow
5. Follow each step, declaring active SOP at transitions (COR-1402)
6. Do not commit code without completing review steps
7. When task is done, use the plan output as completion checklist

af guide = once per session (routing context).
af plan  = before EVERY task (checklist from SOPs).
COR-1201 = once per session (Discussion Tracker, auto-increment D items).
"""


@click.command("setup")
def setup_cmd() -> None:
    """Show suggested prompts for agent configuration."""
    click.echo(_SETUP_TEXT)
