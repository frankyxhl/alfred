"""Show suggested prompts for agent configuration."""

import click

_SETUP_TEXT = """\
# Alfred Workflow Setup

Add ONE of the following to your agent's instruction file
(CLAUDE.md, agent.md, system prompt, etc.):

## Option A: Minimal

At session start, run COR-1208 (Session Startup Sanity Check: pwd, git status --short --branch, git log -5, project smoke test, load tracker per COR-1201, surface anomalies).
Then run `af guide` to see routing.
Before every task, run `af plan <SOP_IDs>` and follow the output.
Declare the active SOP per COR-1402 as the first line of EVERY reply (use the no-formal-SOP form `📋 COR-1402 Declare Active Process → no formal task SOP` when none applies).

## Option B: With routing

At session start:
1. Run COR-1208 (Session Startup Sanity Check: pwd, git status --short --branch, git log -5, smoke test, load tracker, surface anomalies — stop until operator acknowledges any anomalies)
2. Run `af guide --root <project-root>` to see routing (PKG → USR → PRJ)

Before every task:
3. From the decision tree, identify which SOPs apply
4. Run `af plan <SOP_IDs>` to generate workflow instructions
5. Declare the active SOP per COR-1402 as the first line of every reply (use the no-formal-SOP form when none applies)
6. Follow each step. At every SOP transition, declare the new active SOP.
7. Do not skip review gates.

## Option C: Full (recommended)

At session start:
1. Run COR-1208 (Session Startup Sanity Check: pwd, git status --short --branch, git log -5, smoke test, load tracker per COR-1201, surface anomalies — stop until operator acknowledges any anomalies)
2. Run `af guide --root <project-root>` to see routing (PKG → USR → PRJ)

Before every task:
3. From the decision tree, identify which SOPs apply to this task
4. Run `af plan <SOP_IDs>` to generate step-by-step workflow
5. Declare the active SOP per COR-1402 as the first line of every reply (use the no-formal-SOP form when none applies)
6. Follow each step. At every SOP transition, declare the new active SOP.
7. Do not commit code without completing review steps
8. When task is done, confirm which SOPs were used and use the plan output as completion checklist

COR-1208 = first action of every active session (state-recovery ritual; wraps COR-1201 as step 4).
af guide = once per session (routing context).
af plan  = before EVERY task (checklist from SOPs).
COR-1402 = open EVERY reply with the active-process line (use `📋 COR-1402 Declare Active Process → no formal task SOP` when none applies); re-declare at every transition; confirm at completion.
"""


@click.command("setup")
def setup_cmd() -> None:
    """Show suggested prompts for agent configuration."""
    click.echo(_SETUP_TEXT)
