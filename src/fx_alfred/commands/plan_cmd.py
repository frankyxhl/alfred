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
from fx_alfred.core.ascii_graph import render_ascii
from fx_alfred.core.dag_graph import render_dag
from fx_alfred.core.compose import resolve_sops_from_task
from fx_alfred.core.mermaid import render_mermaid
from fx_alfred.core.phases import PhaseDict
from fx_alfred.core.schema import TASK_TAGS
from fx_alfred.core.workflow import (
    LoopSignature,
    WorkflowSignature,
    _BRANCHES_RENDERER_READY,
    check_composition,
    has_workflow_branches_field,
    parse_workflow_loops,
    parse_workflow_signature,
    validate_workflow_signature,
)

# Heading search order for step extraction — authoritative list lives in
# ``core.steps._STEP_HEADINGS`` (shared with validate_cmd D3, PR #59 P2).
# Re-exported here for existing call sites inside this module.
from fx_alfred.core.steps import _STEP_HEADINGS  # noqa: E402, F401


def _gather_all_sops(
    docs: list[Document],
) -> list[tuple[Document, frozenset[str], bool]]:
    """Gather all SOPs with their task tags and always-included status.

    Returns list of (Document, task_tags_frozenset, always_included_bool).
    """
    result: list[tuple[Document, frozenset[str], bool]] = []

    for doc in docs:
        if doc.type_code != "SOP":
            continue

        try:
            content = doc.resolve_resource().read_text()
            parsed = parse_metadata(content)
        except (OSError, MalformedDocumentError):
            continue

        # Extract Task tags
        task_tags: frozenset[str] = frozenset()
        field_map = {mf.key: mf.value for mf in parsed.metadata_fields}
        raw_tags = field_map.get(TASK_TAGS)
        if raw_tags:
            # Parse tag list: "[tag1, tag2]" or "tag1, tag2"
            raw = raw_tags.strip()
            if raw.startswith("[") and raw.endswith("]"):
                raw = raw[1:-1]
            tags = [t.strip().lower() for t in raw.split(",") if t.strip()]
            task_tags = frozenset(tags)

        # Extract Always included
        always_included = False
        raw_always = field_map.get("Always included")
        if raw_always:
            always_included = raw_always.strip().lower() == "true"

        result.append((doc, task_tags, always_included))

    return result


def _format_composed_from_header(provenance: dict[str, list[str]]) -> str:
    """Format the 'Composed from:' header with provenance markers.

    Markers: (always), (auto), (explicit).
    """
    parts: list[str] = []

    for doc_id in provenance.get("always", []):
        parts.append(f"{doc_id}(always)")
    for doc_id in provenance.get("explicit", []):
        parts.append(f"{doc_id}(explicit)")
    for doc_id in provenance.get("auto", []):
        parts.append(f"{doc_id}(auto)")

    return "Composed from: " + " → ".join(parts)


_LLM_RULES = """\
## RULES
- Complete each checkbox before moving to the next phase
- Declare active SOP per COR-1402: before starting, at every phase transition, flag if none exist, and confirm at completion
- ⚠️ marks hard stops — do not proceed until condition is met
- If stuck, ask one clarifying question before proceeding
"""


def _extract_steps_section(body: str) -> str | None:
    """Try each heading in order, return first match.

    Delegates to ``core.steps.extract_steps_section`` so validate D3 and
    plan rendering agree on the heading set (PR #59 Codex review P2).
    """
    from fx_alfred.core.steps import extract_steps_section

    return extract_steps_section(body)


def _parse_numbered_items(section_text: str) -> list[str]:
    """Extract numbered items from section text.

    Matches both ``1. text`` and ``### 1. text`` formats.
    """
    items: list[str] = []
    for line in section_text.split("\n"):
        stripped = line.strip()
        # Match "### 1. text", "1. text", "3a. text" (FXA-2226 Path B sub-step)
        m = re.match(r"^(?:###\s+)?(\d+)([a-z])?\.\s+(.+)", stripped)
        if m:
            number = m.group(1)
            sub_branch = m.group(2) or ""
            items.append(f"{number}{sub_branch}. {m.group(3)}")
    return items


# _parse_steps_for_json relocated to fx_alfred.core.steps (FXA-2218 Commit 1);
# re-exported below for backward-compatible call sites in this module.
from fx_alfred.core.steps import _parse_steps_for_json  # noqa: E402, F401


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


def _classify_step(
    step_idx: int,
    gate: bool,
    loop_to_steps: dict[int, LoopSignature],
    loop_from_steps: dict[int, LoopSignature],
) -> tuple[bool, LoopSignature | None, LoopSignature | None]:
    """Classify a step for gate and loop markers.

    Returns (is_gate, loop_to_signature_or_None, loop_from_signature_or_None).

    Gate and loop markers are INDEPENDENTLY COMPOSABLE — a step can be both
    a gate and a loop endpoint without losing either marker.

    When a step is both loop_to and loop_from (multi-loop edge case where
    the same step is the target of one loop and the source of another),
    loop_from takes precedence as it carries more information (the condition
    and back-reference).
    """
    loop_to_sig = loop_to_steps.get(step_idx)
    loop_from_sig = loop_from_steps.get(step_idx)
    return (gate, loop_to_sig, loop_from_sig)


def _apply_text_markers(
    text: str,
    gate: bool,
    loop_to_sig: LoopSignature | None,
    loop_from_sig: LoopSignature | None,
    phase_num: int,
) -> str:
    """Apply gate and loop markers to TODO item text.

    Markers are applied in this EXACT order (documented contract):
    1. If loop_to_sig: prepend "🔁 loop-start: " to text.
    2. If gate: prepend "⚠️ gate: " to text (after loop-start, so leftmost
       token is ⚠️ when both apply).
    3. If loop_from_sig: append " — 🔁 if {cond} → back to {phase}.{to} (max {N})"
       to text.

    A step that is gate AND loop-to AND loop-from renders:
    "⚠️ gate: 🔁 loop-start: <original> — 🔁 if cond → back to N.K (max 3)"
    """
    # 1. Loop-start prefix (loop target)
    if loop_to_sig:
        text = f"🔁 loop-start: {text}"

    # 2. Gate prefix
    if gate:
        text = f"⚠️ gate: {text}"

    # 3. Loop-back suffix (loop source)
    if loop_from_sig:
        # For cross-SOP loops, `to_step` is already "PREFIX-ACID.step"; intra-SOP
        # stays `{phase}.{step}` (FXA-2218 Commit 4 output contract).
        if isinstance(loop_from_sig.to_step, int):
            target_ref = f"{phase_num}.{loop_from_sig.to_step}"
        else:
            target_ref = loop_from_sig.to_step
        text = f"{text} — 🔁 if {loop_from_sig.condition} → back to {target_ref} (max {loop_from_sig.max_iterations})"

    return text


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
    loop_to_steps = {
        loop.to_step: loop for loop in loops if isinstance(loop.to_step, int)
    }
    loop_from_steps = {loop.from_step: loop for loop in loops}

    for step in steps:
        step_idx = step["index"]
        text = step["text"]
        gate = step["gate"]
        # FXA-2226 Path B: append optional sub_branch suffix for sibling
        # sub-steps so dotted index goes from "1.3" → "1.3a".
        dotted = f"{phase_num}.{step_idx}{step.get('sub_branch', '')}"

        # Classify step (gate and loop markers are independent)
        is_gate, loop_to_sig, loop_from_sig = _classify_step(
            step_idx, gate, loop_to_steps, loop_from_steps
        )

        # Apply markers to text
        text = _apply_text_markers(text, is_gate, loop_to_sig, loop_from_sig, phase_num)

        items.append(f"{checkbox_prefix}{dotted} [{sop_id}] {text}")

    return items


def _build_todo_json(
    phase_num: int,
    sop_id: str,
    body: str,
    loops: list[LoopSignature],
) -> list[dict]:
    """Build JSON todo items for a single SOP phase.

    JSON contract:
    - gate: bool — gate semantic (independent of loop_marker).
    - loop_marker: "loop-start" | "loop-back" | null — NEVER carries "gate".
    - gate AND loop-from → gate=True, loop_marker="loop-back".
    - gate AND loop-to → gate=True, loop_marker="loop-start".
    - loop-to AND loop-from same step → loop_marker="loop-back" (tiebreak).
    """
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
    loop_to_steps = {
        loop.to_step: loop for loop in loops if isinstance(loop.to_step, int)
    }
    loop_from_steps = {loop.from_step: loop for loop in loops}

    for step in steps:
        step_idx = step["index"]
        text = step["text"]
        gate = step["gate"]
        # FXA-2226 Path B: append optional sub_branch suffix.
        dotted = f"{phase_num}.{step_idx}{step.get('sub_branch', '')}"

        # Classify step (gate and loop markers are independent)
        is_gate, loop_to_sig, loop_from_sig = _classify_step(
            step_idx, gate, loop_to_steps, loop_from_steps
        )

        # Determine loop_marker for JSON (never "gate")
        # Tiebreak: loop_from takes precedence over loop_to
        loop_marker = None
        if loop_from_sig:
            loop_marker = "loop-back"
        elif loop_to_sig:
            loop_marker = "loop-start"

        items.append(
            {
                "index": dotted,
                "sop": sop_id,
                "text": text,
                "gate": is_gate,
                "loop_marker": loop_marker,
            }
        )

    return items


def _build_mermaid_phases(
    phase_info: list[
        tuple[
            str, Document, ParsedDocument, WorkflowSignature | None, list[LoopSignature]
        ]
    ],
    provenance_map: dict[str, str] | None = None,
) -> list[PhaseDict]:
    """Build the phases list consumed by ``render_mermaid()`` / ``render_ascii()``.

    Each entry is ``{"sop_id": str, "steps": list[dict], "loops": list}``.
    When ``provenance_map`` is provided, each entry also gets
    ``"provenance"`` set to the matching marker ("always" / "auto" / "explicit").
    """
    mermaid_phases: list[PhaseDict] = []
    for sop_id, doc, parsed, sig, loops in phase_info:
        body = parsed.body
        doc_id = f"{doc.prefix}-{doc.acid}"
        steps_section = _extract_steps_section(body)
        steps = _parse_steps_for_json(steps_section) if steps_section else []
        entry: PhaseDict = {
            "sop_id": doc_id,
            "steps": steps,
            "loops": loops,
        }
        if provenance_map is not None:
            prov = provenance_map.get(doc_id)
            if prov:
                entry["provenance"] = prov
        mermaid_phases.append(entry)
    return mermaid_phases


def _build_provenance_map(
    composed_from_provenance: dict[str, list[str]] | None,
) -> dict[str, str]:
    """Invert a {marker: [doc_ids]} dict into {doc_id: marker}."""
    result: dict[str, str] = {}
    if not composed_from_provenance:
        return result
    for marker, doc_ids in composed_from_provenance.items():
        for doc_id in doc_ids:
            result[doc_id] = marker
    return result


def _render_layout(
    mermaid_phases: list[PhaseDict],
    provenance_map: dict[str, str],
    graph_layout: str,
) -> str:
    """Dispatch between ``render_ascii`` (flat, legacy) and ``render_dag``
    (nested, default) based on ``graph_layout`` (FXA-2218 Commit 7).
    """
    if graph_layout == "nested":
        return render_dag(mermaid_phases, provenance_map)
    return render_ascii(mermaid_phases)


def _emit_graph(
    phase_info: list,
    provenance_map: dict[str, str],
    graph_format: str,
    graph_layout: str = "nested",
) -> None:
    """Emit graph output for text modes (default, --todo).

    ``graph_format`` must be one of ``ascii``, ``mermaid``, ``both``.
    ``graph_layout`` must be one of ``nested`` (FXA-2218 default) or ``flat``
    (legacy ascii_graph layout).
    """
    mermaid_phases = _build_mermaid_phases(phase_info, provenance_map)
    if graph_format in ("ascii", "both"):
        ascii_str = _render_layout(mermaid_phases, provenance_map, graph_layout)
        click.echo(ascii_str, nl=False)
    if graph_format == "both":
        click.echo()
    if graph_format in ("mermaid", "both"):
        mermaid_str = render_mermaid(mermaid_phases)
        click.echo("```mermaid")
        click.echo(mermaid_str)
        click.echo("```")


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
@click.option(
    "--graph",
    "output_graph",
    is_flag=True,
    help="Append graph of composed plan (ASCII + fenced Mermaid by default)",
)
@click.option(
    "--graph-format",
    "graph_format",
    type=click.Choice(["ascii", "mermaid", "both"]),
    default="both",
    help="Graph rendering format (requires --graph). Default: both.",
)
@click.option(
    "--graph-layout",
    "graph_layout",
    type=click.Choice(["nested", "flat"]),
    default="nested",
    help=(
        "ASCII graph layout (requires --graph, ASCII-only): 'nested' "
        "(default, FXA-2218 — step-boxes inside phase-boxes with cross-SOP "
        "tracks) or 'flat' (legacy, one phase-box per SOP)."
    ),
)
@click.option(
    "--task",
    "task_description",
    default=None,
    help="Auto-compose SOPs by matching Task tags against task description",
)
@click.pass_context
def plan_cmd(
    ctx: click.Context,
    sop_ids: tuple[str, ...],
    human: bool,
    output_json: bool,
    output_todo: bool,
    output_graph: bool,
    graph_format: str,
    graph_layout: str,
    task_description: str | None,
) -> None:
    """Generate workflow checklist from SOPs."""
    # ── Validate --graph-format / --graph coupling ──
    # --graph-format is only meaningful with --graph.  Detect when the user
    # passed a non-default graph_format without --graph and raise UsageError.
    if not output_graph:
        # click.Choice default is "both"; distinguish explicit vs default by
        # consulting the parameter source. Explicit without --graph is an error.
        param_source = ctx.get_parameter_source("graph_format")  # type: ignore[attr-defined]
        if param_source is not None and param_source.name != "DEFAULT":
            raise click.UsageError("--graph-format requires --graph")
        # Same coupling rule for --graph-layout.
        layout_source = ctx.get_parameter_source("graph_layout")  # type: ignore[attr-defined]
        if layout_source is not None and layout_source.name != "DEFAULT":
            raise click.UsageError("--graph-layout requires --graph")

    # Scan documents first (needed for --task resolution)
    docs = scan_or_fail(ctx)

    # Handle --task flag for auto-composition
    composed_from_provenance: dict[str, list[str]] | None = None

    if task_description is not None:
        # Auto-compose SOPs via tag matching
        all_sops = _gather_all_sops(docs)
        positional_list = list(sop_ids)
        try:
            resolved_ids, composed_from_provenance = resolve_sops_from_task(
                task_description, all_sops, positional_list
            )
        except click.ClickException:
            # Re-raise with proper exit code
            raise
        # Convert resolved IDs back to tuple for processing
        sop_ids = tuple(resolved_ids)

    if not sop_ids:
        raise click.UsageError("Usage: af plan SOP_ID [SOP_ID ...]")

    if output_json and human:
        raise click.UsageError("--json and --human are mutually exclusive")

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
            sig = parse_workflow_signature(parsed)
            loops = parse_workflow_loops(parsed)
            # FXA-2226 Path B: enforce renderer-readiness gate at plan time too
            # (per Gemini PR #68 review F2). Until CHG-2227 Phase 8a flips
            # `_BRANCHES_RENDERER_READY` to True, any SOP authoring
            # `Workflow branches:` is rejected here so `af plan` never emits
            # sub-stepped surface (`"1.3a"` indices, ASCII collisions, etc.)
            # before the renderer ships.
            # Per Codex PR #68 R2 review: gate on FIELD PRESENCE (including
            # `Workflow branches: []` / `null`), not on parsed-list non-emptiness.
            # The spec is "MUST NOT author this field" — authoring empty still
            # authors the field.
            if not _BRANCHES_RENDERER_READY and has_workflow_branches_field(parsed):
                raise click.ClickException(
                    f"{doc.prefix}-{doc.acid}: Workflow branches: schema "
                    "is parsed but renderer support is not yet shipped "
                    "(CHG-2227 pending). Production SOPs MUST NOT author "
                    "this field until CHG-2227 lands."
                )
        except MalformedDocumentError as e:
            if not output_json:
                click.echo(
                    f"Warning: {doc.prefix}-{doc.acid} (malformed: {e}). Skipping."
                )
            continue

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

    # ── Cross-SOP loop runtime checks (FXA-2218 D4) ──
    # After composition order is fixed, every cross-SOP loop must:
    #   (a) reference a target SOP that is part of this composed plan
    #   (b) reference a target that comes BEFORE the source in plan order
    #       (back-edge semantic — "on failure, retry from earlier step")
    #
    # Repeated SOP IDs are supported (e.g. plan "A B A"): all positions
    # preserved; D4 accepts if ANY target occurrence precedes the source
    # occurrence being evaluated (PR #59 Codex review P2 #5).
    composed_positions: dict[str, list[int]] = {}
    for idx, (_sid, doc, _p, _sig, _lps) in enumerate(phase_info):
        composed_positions.setdefault(f"{doc.prefix}-{doc.acid}", []).append(idx)
    for source_idx, (_sid, doc, _parsed, _sig, loops) in enumerate(phase_info):
        source_id = f"{doc.prefix}-{doc.acid}"
        for i, loop in enumerate(loops):
            target = loop.cross_sop_target()
            if target is None:
                continue
            t_prefix, t_acid, _t_step = target
            target_id = f"{t_prefix}-{t_acid}"
            target_positions = composed_positions.get(target_id)
            if not target_positions:
                raise click.ClickException(
                    f"{source_id} Workflow loops[{i}].to = {loop.to_step!r} "
                    f"— {target_id} not in composed plan "
                    f"(add positionally: af plan {source_id} {target_id} ...)"
                )
            # Back-edge if ANY target occurrence precedes this source
            # occurrence. Rejected only when ALL target positions are >=
            # source_idx.
            if not any(tp < source_idx for tp in target_positions):
                raise click.ClickException(
                    f"{source_id} Workflow loops[{i}].to = {loop.to_step!r} "
                    f"— target SOP precedes source; back-edges only"
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

        # Header (with Composed from if task was used)
        if composed_from_provenance:
            header = _format_composed_from_header(composed_from_provenance)
            click.echo(f"# {header}")
            click.echo()
        click.echo("# Flat TODO — Follow each item in order")
        click.echo()
        click.echo("\n".join(todo_items))

        if output_graph:
            provenance_map = _build_provenance_map(composed_from_provenance)
            click.echo()
            _emit_graph(phase_info, provenance_map, graph_format, graph_layout)
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
                todo_items_json = _build_todo_json(phase_num, doc_id, body, loops)
                todo_json.extend(todo_items_json)

                # Build loops array with dotted step references. Cross-SOP
                # loops emit `to` as the raw "PREFIX-ACID.step" string — same
                # lexical form as the authored metadata (FXA-2218 Commit 4).
                for loop in loops:
                    if isinstance(loop.to_step, int):
                        loop_to_ref = f"{phase_num}.{loop.to_step}"
                    else:
                        loop_to_ref = loop.to_step
                    loops_json.append(
                        {
                            "id": loop.id,
                            "from": f"{phase_num}.{loop.from_step}",
                            "to": loop_to_ref,
                            "max_iterations": loop.max_iterations,
                            "sop": doc_id,
                        }
                    )

        has_new_keys = (
            output_todo or output_graph or (composed_from_provenance is not None)
        )
        schema_ver = "2" if has_new_keys else "1"

        result = {
            "schema_version": schema_ver,
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

        if composed_from_provenance:
            result["composed_from"] = composed_from_provenance

        if output_todo:
            result["todo"] = todo_json
            result["loops"] = loops_json

        if output_graph:
            provenance_map = _build_provenance_map(composed_from_provenance)
            mermaid_phases = _build_mermaid_phases(phase_info, provenance_map)
            if graph_format in ("ascii", "both"):
                result["ascii_graph"] = _render_layout(
                    mermaid_phases, provenance_map, graph_layout
                )
            if graph_format in ("mermaid", "both"):
                result["graph_mermaid"] = render_mermaid(mermaid_phases)

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

    # Header (with Composed from if task was used)
    if composed_from_provenance:
        header = _format_composed_from_header(composed_from_provenance)
        click.echo(f"# {header}")
        click.echo()
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

    if output_graph:
        provenance_map = _build_provenance_map(composed_from_provenance)
        _emit_graph(phase_info, provenance_map, graph_format, graph_layout)
