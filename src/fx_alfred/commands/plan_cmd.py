"""Generate workflow checklist from SOPs (FXA-2134)."""

from __future__ import annotations

import json
import re

import click

from fx_alfred.commands._helpers import find_or_fail, scan_or_fail
from fx_alfred.context import root_option
from fx_alfred.core.document import Document
from fx_alfred.core.parser import (
    MalformedDocumentError,
    ParsedDocument,
    extract_section,
    parse_metadata,
)
from fx_alfred.core.workflow import (
    LoopSignature,
    WorkflowSignature,
    check_composition,
    parse_workflow_loops,
    parse_workflow_signature,
    validate_workflow_signature,
)

# Heading search order for step extraction
_STEP_HEADINGS = ("Steps", "Rule", "Rules", "Concepts")

_LLM_RULES = """\
## RULES
- Complete each checkbox before moving to the next phase
- Declare active SOP per COR-1402: before starting, at every phase transition, flag if none exist, and confirm at completion
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


def _parse_steps_for_json(section_text: str) -> list[dict]:
    """Extract steps as structured data for JSON output.

    Returns list of {"index": int, "text": str, "gate": bool}.
    Gate is true if step ends with "✓" or contains "[GATE]".
    """
    steps = []
    for line in section_text.split("\n"):
        stripped = line.strip()
        m = re.match(r"^(?:###\s+)?(\d+)\.\s+(.+)", stripped)
        if m:
            index = int(m.group(1))
            text = m.group(2)
            gate = text.endswith("✓") or "[GATE]" in text
            steps.append({"index": index, "text": text, "gate": gate})
    return steps


def _format_phase(
    heading: str,
    summary: str | None,
    body: str,
    summary_prefix: str,
    checkbox: str,
    state_line: str | None = None,
) -> str:
    """Format a single SOP phase.

    Parameters
    ----------
    heading:
        Pre-built heading line (e.g. ``## Phase 1: COR-1500 (TDD)``).
    summary:
        Raw "What Is It?" section text, or *None*.
    body:
        Full document body (used to extract Steps).
    summary_prefix:
        Prefix before first paragraph of summary (e.g. ``"What: "`` or ``""``).
    checkbox:
        Per-item checkbox prefix (e.g. ``"- [ ] "`` or ``"□ "``).
    state_line:
        Optional workflow state line (e.g. ``"State: x -> y"``).
    """
    lines: list[str] = [heading]

    if summary:
        first_para = summary.split("\n\n")[0].strip()
        lines.append(f"{summary_prefix}{first_para}")

    if state_line:
        lines.append(state_line)

    lines.append("")

    steps_section = _extract_steps_section(body)
    if steps_section is None:
        lines.append("(no Steps section found)")
    else:
        items = _parse_numbered_items(steps_section)
        if items:
            for item in items:
                lines.append(f"{checkbox}{item}")
        else:
            # Raw section text fallback
            lines.append(steps_section)

    return "\n".join(lines)


def _build_todo_items(
    phase_num: int,
    sop_id: str,
    body: str,
    loops: list[LoopSignature],
    checkbox_prefix: str,
) -> list[str]:
    """Build flat TODO items for a single SOP phase.

    Returns list of formatted TODO lines with dotted numbering,
    SOP provenance tags, gate markers, and loop markers.
    """
    items: list[str] = []
    steps_section = _extract_steps_section(body)

    if steps_section is None:
        return [f"{checkbox_prefix}{phase_num}.1 [{sop_id}] (no Steps section found)"]

    steps = _parse_steps_for_json(steps_section)
    if not steps:
        # Raw section text fallback
        return [f"{checkbox_prefix}{phase_num}.1 [{sop_id}] {steps_section.strip()}"]

    # Build loop marker maps
    loop_to_steps = {loop.to_step: loop for loop in loops}
    loop_from_steps = {loop.from_step: loop for loop in loops}

    for step in steps:
        step_idx = step["index"]
        text = step["text"]
        gate = step["gate"]
        dotted = f"{phase_num}.{step_idx}"

        # Determine loop marker
        loop_marker = None
        if gate:
            loop_marker = "gate"
        elif step_idx in loop_to_steps:
            loop_marker = "loop-start"
        elif step_idx in loop_from_steps:
            loop_marker = "loop-back"

        # Apply markers to text
        if loop_marker == "loop-start":
            text = f"🔁 loop-start: {text}"
        elif loop_marker == "loop-back":
            loop = loop_from_steps[step_idx]
            text = f"{text} — 🔁 if {loop.condition} → back to {phase_num}.{loop.to_step} (max {loop.max_iterations})"
        elif gate:
            text = f"⚠️ gate: {text}"

        items.append(f"{checkbox_prefix}{dotted} [{sop_id}] {text}")

    return items


def _build_todo_json(
    phase_num: int,
    sop_id: str,
    body: str,
    loops: list[LoopSignature],
) -> list[dict]:
    """Build JSON todo items for a single SOP phase."""
    items: list[dict] = []
    steps_section = _extract_steps_section(body)

    if steps_section is None:
        return [
            {
                "index": f"{phase_num}.1",
                "sop": sop_id,
                "text": "(no Steps section found)",
                "gate": False,
                "loop_marker": None,
            }
        ]

    steps = _parse_steps_for_json(steps_section)
    if not steps:
        return [
            {
                "index": f"{phase_num}.1",
                "sop": sop_id,
                "text": steps_section.strip(),
                "gate": False,
                "loop_marker": None,
            }
        ]

    # Build loop marker maps
    loop_to_steps = {loop.to_step: loop for loop in loops}
    loop_from_steps = {loop.from_step: loop for loop in loops}

    for step in steps:
        step_idx = step["index"]
        text = step["text"]
        gate = step["gate"]
        dotted = f"{phase_num}.{step_idx}"

        # Determine loop marker
        loop_marker = None
        if gate:
            loop_marker = "gate"
        elif step_idx in loop_to_steps:
            loop_marker = "loop-start"
        elif step_idx in loop_from_steps:
            loop_marker = "loop-back"

        items.append(
            {
                "index": dotted,
                "sop": sop_id,
                "text": text,
                "gate": gate,
                "loop_marker": loop_marker,
            }
        )

    return items


@click.command("plan")
@root_option
@click.argument("sop_ids", nargs=-1)
@click.option("--human", is_flag=True, help="Human-readable output")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option(
    "--todo",
    "output_todo",
    is_flag=True,
    help="Flat unified TODO list across selected SOPs",
)
@click.pass_context
def plan_cmd(
    ctx: click.Context,
    sop_ids: tuple[str, ...],
    human: bool,
    output_json: bool,
    output_todo: bool,
) -> None:
    """Generate workflow checklist from SOPs."""
    if not sop_ids:
        raise click.UsageError("Usage: af plan SOP_ID [SOP_ID ...]")

    if output_json and human:
        raise click.UsageError("--json and --human are mutually exclusive")

    docs = scan_or_fail(ctx)

    # ── First pass: parse all SOPs and collect workflow signatures ──
    phase_info: list[
        tuple[
            str, Document, ParsedDocument, WorkflowSignature | None, list[LoopSignature]
        ]
    ] = []

    for sop_id in sop_ids:
        doc = find_or_fail(docs, sop_id)

        # Verify document is SOP type
        if doc.type_code != "SOP":
            if not output_json:
                click.echo(
                    f"Warning: {doc.prefix}-{doc.acid} is {doc.type_code}, not SOP. Skipping."
                )
            continue

        # Parse document content
        try:
            content = doc.resolve_resource().read_text()
            parsed = parse_metadata(content)
        except MalformedDocumentError as e:
            if not output_json:
                click.echo(
                    f"Warning: {doc.prefix}-{doc.acid} (malformed: {e}). Skipping."
                )
            continue

        sig = parse_workflow_signature(parsed)
        loops = parse_workflow_loops(parsed)
        phase_info.append((sop_id, doc, parsed, sig, loops))

    # ── Validate workflow signatures before composition ──
    for sop_id, doc, parsed, sig, loops in phase_info:
        if sig is not None:
            wf_errors = validate_workflow_signature(sig)
            if wf_errors:
                doc_id = f"{doc.prefix}-{doc.acid}"
                raise click.ClickException(
                    f"Invalid workflow metadata in {doc_id}: " + "; ".join(wf_errors)
                )

    # ── Workflow composition check ──
    chain: list[tuple[str, WorkflowSignature]] = [
        (
            f"{doc.prefix}-{doc.acid}",
            sig if sig is not None else WorkflowSignature(input="", output=""),
        )
        for _, doc, _, sig, _ in phase_info
    ]
    edges = check_composition(chain)

    for edge in edges:
        if edge.typed and not edge.compatible:
            raise click.ClickException(
                f"Workflow type mismatch: {edge.from_doc} outputs "
                f"'{edge.from_output}' but {edge.to_doc} expects '{edge.to_input}'"
            )

    composition_valid = all(e.compatible for e in edges) if edges else True

    # ── Flat TODO output mode ──
    if output_todo and not output_json:
        todo_items: list[str] = []
        phase_num = 0
        checkbox = "□ " if human else "- [ ] "

        for sop_id, doc, parsed, sig, loops in phase_info:
            phase_num += 1
            body = parsed.body
            doc_id = f"{doc.prefix}-{doc.acid}"
            items = _build_todo_items(phase_num, doc_id, body, loops, checkbox)
            todo_items.extend(items)

        if not todo_items:
            return

        # Header
        if human:
            click.echo("# Flat TODO — Follow each item in order")
        else:
            click.echo("# Flat TODO — Follow each item in order")
        click.echo()
        click.echo("\n".join(todo_items))
        return

    # ── JSON output mode ──
    if output_json:
        phases_json: list[dict] = []
        todo_json: list[dict] = []
        loops_json: list[dict] = []
        phase_num = 0

        for sop_id, doc, parsed, sig, loops in phase_info:
            phase_num += 1
            body = parsed.body
            doc_id = f"{doc.prefix}-{doc.acid}"

            steps_section = _extract_steps_section(body)
            steps = _parse_steps_for_json(steps_section) if steps_section else []
            phases_json.append(
                {
                    "phase": sop_id,
                    "source_sop": sop_id,
                    "steps": steps,
                    "workflow_input": sig.input if sig else "",
                    "workflow_output": sig.output if sig else "",
                    "workflow_requires": sig.requires if sig else [],
                    "workflow_provides": sig.provides if sig else [],
                    "workflow_typed": sig is not None
                    and bool(sig.input and sig.output),
                }
            )

            # Build todo items if --todo is set
            if output_todo:
                todo_items = _build_todo_json(phase_num, doc_id, body, loops)
                todo_json.extend(todo_items)

                # Build loops array with dotted step references
                for loop in loops:
                    loops_json.append(
                        {
                            "id": loop.id,
                            "from": f"{phase_num}.{loop.from_step}",
                            "to": f"{phase_num}.{loop.to_step}",
                            "max_iterations": loop.max_iterations,
                            "sop": doc_id,
                        }
                    )

        result = {
            "schema_version": "2" if output_todo else "1",
            "sop_ids": list(sop_ids),
            "phases": phases_json,
            "composition_valid": composition_valid,
            "edges": [
                {
                    "from": e.from_doc,
                    "to": e.to_doc,
                    "typed": e.typed,
                    "compatible": e.compatible,
                    "from_output": e.from_output,
                    "to_input": e.to_input,
                }
                for e in edges
            ],
        }

        if output_todo:
            result["todo"] = todo_json
            result["loops"] = loops_json

        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # ── Second pass: render phased output (default behavior) ──
    phases_text: list[str] = []
    phase_num = 0

    for sop_id, doc, parsed, sig, loops in phase_info:
        body = parsed.body
        summary = extract_section(body, "What Is It?")
        title = doc.title
        phase_num += 1

        # Build state line for typed phases
        state_line: str | None = None
        if sig is not None and sig.input and sig.output:
            state_line = f"State: {sig.input} -> {sig.output}"

        if human:
            heading = f"═══ Phase {phase_num}: {sop_id} ({title}) ═══"
            phases_text.append(
                _format_phase(heading, summary, body, "", "□ ", state_line)
            )
        else:
            heading = f"## Phase {phase_num}: {sop_id} ({title})"
            phases_text.append(
                _format_phase(heading, summary, body, "What: ", "- [ ] ", state_line)
            )

    if not phases_text:
        return

    # Header
    if human:
        click.echo("\n".join(phases_text))
    else:
        click.echo(
            "# Session Workflow — Follow each phase in order. Do not skip any step."
        )
        click.echo()
        click.echo("\n\n".join(phases_text))
        click.echo()
        click.echo(_LLM_RULES)
