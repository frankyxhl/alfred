"""Generate workflow checklist from SOPs (FXA-2134)."""

from __future__ import annotations

import re

import click

from fx_alfred.commands._helpers import find_or_fail, scan_or_fail
from fx_alfred.context import root_option
from fx_alfred.core.parser import (
    MalformedDocumentError,
    extract_section,
    parse_metadata,
)

# Heading search order for step extraction
_STEP_HEADINGS = ("Steps", "Rule", "Rules", "Concepts")

_LLM_RULES = """\
## RULES
- Complete each checkbox before moving to the next phase
- Declare active SOP at every phase transition (COR-1402)
- ⚠️ marks hard stops — do not proceed until condition is met
- If stuck, ask one clarifying question before proceeding
"""


def _extract_steps_section(body: str) -> str | None:
    """Try each heading in order, return first match."""
    for heading in _STEP_HEADINGS:
        section = extract_section(body, heading)
        if section is not None:
            return section
    return None


def _parse_numbered_items(section_text: str) -> list[str]:
    """Extract numbered items from section text.

    Matches both ``1. text`` and ``### 1. text`` formats.
    """
    items: list[str] = []
    for line in section_text.split("\n"):
        stripped = line.strip()
        # Match "### 1. text" or "1. text"
        m = re.match(r"^(?:###\s+)?(\d+)\.\s+(.+)", stripped)
        if m:
            items.append(f"{m.group(1)}. {m.group(2)}")
    return items


def _format_phase_llm(
    phase_num: int, sop_id: str, title: str, summary: str | None, body: str
) -> str:
    """Format a single SOP phase for LLM-optimized output."""
    lines: list[str] = []
    lines.append(f"## Phase {phase_num}: {sop_id} ({title})")

    if summary:
        # Take first paragraph of "What Is It?" section
        first_para = summary.split("\n\n")[0].strip()
        lines.append(f"What: {first_para}")

    lines.append("")

    steps_section = _extract_steps_section(body)
    if steps_section is None:
        lines.append("(no Steps section found)")
    else:
        items = _parse_numbered_items(steps_section)
        if items:
            for item in items:
                lines.append(f"- [ ] {item}")
        else:
            # Raw section text fallback
            lines.append(steps_section)

    return "\n".join(lines)


def _format_phase_human(
    phase_num: int, sop_id: str, title: str, summary: str | None, body: str
) -> str:
    """Format a single SOP phase for human-readable output."""
    lines: list[str] = []
    lines.append(f"═══ Phase {phase_num}: {sop_id} ({title}) ═══")

    if summary:
        first_para = summary.split("\n\n")[0].strip()
        lines.append(first_para)

    lines.append("")

    steps_section = _extract_steps_section(body)
    if steps_section is None:
        lines.append("(no Steps section found)")
    else:
        items = _parse_numbered_items(steps_section)
        if items:
            for item in items:
                lines.append(f"□ {item}")
        else:
            lines.append(steps_section)

    return "\n".join(lines)


@click.command("plan")
@root_option
@click.argument("sop_ids", nargs=-1)
@click.option("--human", is_flag=True, help="Human-readable output")
@click.pass_context
def plan_cmd(ctx: click.Context, sop_ids: tuple[str, ...], human: bool) -> None:
    """Generate workflow checklist from SOPs."""
    if not sop_ids:
        raise click.UsageError("Usage: af plan SOP_ID [SOP_ID ...]")

    docs = scan_or_fail(ctx)
    phases: list[str] = []
    phase_num = 0

    for sop_id in sop_ids:
        doc = find_or_fail(docs, sop_id)

        # Verify document is SOP type
        if doc.type_code != "SOP":
            click.echo(
                f"Warning: {doc.prefix}-{doc.acid} is {doc.type_code}, not SOP. Skipping."
            )
            continue

        # Parse document content
        try:
            content = doc.resolve_resource().read_text()
            parsed = parse_metadata(content)
        except MalformedDocumentError as e:
            click.echo(f"Warning: {doc.prefix}-{doc.acid} (malformed: {e}). Skipping.")
            continue

        body = parsed.body
        summary = extract_section(body, "What Is It?")
        title = doc.title
        phase_num += 1

        if human:
            phases.append(_format_phase_human(phase_num, sop_id, title, summary, body))
        else:
            phases.append(_format_phase_llm(phase_num, sop_id, title, summary, body))

    if not phases:
        return

    # Header
    if human:
        click.echo("\n".join(phases))
    else:
        click.echo(
            "# Session Workflow — Follow each phase in order. Do not skip any step."
        )
        click.echo()
        click.echo("\n\n".join(phases))
        click.echo()
        click.echo(_LLM_RULES)
