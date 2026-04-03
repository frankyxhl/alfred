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
Declare active SOP per COR-1402 before starting work (or flag if none exist).

## Option B: With routing

At session start:
1. Load today's Discussion Tracker per COR-1201 (auto-increments D items)
2. Run `af guide --root <project-root>` to see routing (PKG → USR → PRJ)

Before every task:
3. From the decision tree, identify which SOPs apply
4. Run `af plan <SOP_IDs>` to generate workflow instructions
5. Declare active SOP per COR-1402 before starting work (or flag if none exist)
6. Follow each step. At every SOP transition, declare the new active SOP.
7. Do not skip review gates.

## Option C: Full (recommended)

At session start:
1. Load today's Discussion Tracker per COR-1201 (auto-increments D items)
2. Run `af guide --root <project-root>` to see routing (PKG → USR → PRJ)

Before every task:
3. From the decision tree, identify which SOPs apply to this task
4. Run `af plan <SOP_IDs>` to generate step-by-step workflow
5. Declare active SOP per COR-1402 before starting work (or flag if none exist)
6. Follow each step. At every SOP transition, declare the new active SOP.
7. Do not commit code without completing review steps
8. When task is done, confirm which SOPs were used and use the plan output as completion checklist

af guide = once per session (routing context).
af plan  = before EVERY task (checklist from SOPs).
COR-1201 = once per session (Discussion Tracker, auto-increment D items).
COR-1402 = declare active SOP before work, at every transition, flag if none exist, confirm at completion.
"""


@click.command("setup")
def setup_cmd() -> None:
    """Show suggested prompts for agent configuration."""
    click.echo(_SETUP_TEXT)
