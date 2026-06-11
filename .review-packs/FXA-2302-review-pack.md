# FXA-2302 Review Pack — plan_cmd Decomposition (final backlog item)

## Review request

Review this pure-refactor diff with the COR-1610 rubric pinned below. Unit = branch diff vs main (plan_cmd.py restructure + one ratchet guard + CHG doc). Cross-reference plan_cmd.py at HEAD.

## What & why

The 2026-06-10 review's last open finding: plan_cmd.py's main function had absorbed every plan feature since FXA-2134 into 376 lines of 3-4-level nested mode branching, plus two near-duplicate todo builders sharing extraction/fallback/loop-map/classification verbatim.

Change (two commits + ratchet fix):
1. **Todo merge**: frozen `_TodoEntry` dataclass + `_classify_todo_entries` = single classification source; `_build_todo_items`/`_build_todo_json` become thin renderers (public names/signatures unchanged). Fallback entries take the uniform path (`_apply_text_markers` no-ops on unmarked entries).
2. **Decomposition**: plan_cmd() 376 → 76 lines of orchestration over 8 named module-level functions with explicit params (no closures): _validate_option_coupling, _resolve_sop_ids (CompositionError boundary), _collect_phase_info + _enforce_branches_gate (the 35-line FXA-2226 gate moved VERBATIM incl. all PR #68 review comments), _validate_composition, _validate_cross_sop_loops (FXA-2218 D4 verbatim), _emit_todo_text, _emit_json_output (108 lines — now the largest), _emit_phased_text. `_PhaseInfo` type alias for the shared tuple.
3. **Ratchet guard**: AST check — no commands/ function > 150 lines; three PRE-EXISTING oversized functions grandfathered at current sizes (create_cmd 230 / update_cmd 283 / validate_cmd 325 — shrink-only caps; decomposing them = recorded follow-up, NOT this CHG).

## Refactor contract — zero behavior change (verified)

- 1000 tests pass (999 + guard) with ZERO existing-test modifications — 100+ plan-surface tests (text/json/todo/graph/human, loops, branches, provenance, skills) are the characterization contract.
- **7 golden CLI outputs captured pre-change and diffed byte-identical after EACH commit**: text, todo, json, json+todo, graph (2 SOPs), human, --task zero-match (exit 2 preserved).
- ruff / format / pyright / af validate clean.

File length grew 918 → ~1020 (docstrings + explicit params — the CHG's metrics are function length and duplication, both met; noted honestly).

NOT in scope (no deductions per COR-1610 rule 4): moving anything to core/ (D4 loop validation stays; FXA-2295 precedent — core moves get focused CHGs); decomposing the three grandfathered functions; package split; any behavior change.

## Pinned rubric — COR-1610

| Dimension | Weight |
|-----------|--------|
| Correctness | 25% |
| Test Coverage | 25% |
| Code Style | 15% |
| Security | 15% |
| Simplicity | 20% |

Rules: deductions cite file:line; BLOCKING vs ADVISORY; no out-of-scope deductions; verify tests before scoring; weighted average rounded to one decimal; >= 9.0 PASS. Recompute arithmetic before printing. Required output: Decision Matrix + weighted average + verdict + findings.

Special attention: (a) hunt for extraction-induced behavior drift the goldens might miss — warning-output ordering, early-return paths (empty phase_info), parameter-threading mistakes (human/checkbox/graph flags), the sop_ids reassignment in --task mode; (b) is the grandfathered ratchet sound design or should the panel push for decomposing the other three now; (c) verify _enforce_branches_gate and _validate_cross_sop_loops are verbatim moves (no logic drift) against pre-change main (git show main:src/fx_alfred/commands/plan_cmd.py).

## The diff (vs main)

diff --git a/src/fx_alfred/commands/plan_cmd.py b/src/fx_alfred/commands/plan_cmd.py
index 593572d..df2bfe7 100644
--- a/src/fx_alfred/commands/plan_cmd.py
+++ b/src/fx_alfred/commands/plan_cmd.py
@@ -2,6 +2,7 @@
 
 from __future__ import annotations
 
+from dataclasses import dataclass
 
 import click
 
@@ -24,6 +25,7 @@ from fx_alfred.core.skills import list_skills
 from fx_alfred.core.workflow import (
     BranchSignature,
     LoopSignature,
+    WorkflowEdge,
     WorkflowSignature,
     _BRANCHES_RENDERER_READY,
     check_composition,
@@ -254,53 +256,83 @@ def _apply_text_markers(
     return text
 
 
-def _build_todo_items(
+@dataclass(frozen=True)
+class _TodoEntry:
+    """One classified TODO step — the single source both todo renderers
+    (text lines and JSON dicts) derive from (CHG-2302)."""
+
+    dotted: str  # "2.3" / "2.3a" (FXA-2226 Path B sub-step suffix) / "2.1" fallback
+    text: str  # step text without markers; fallback message for fallback entries
+    gate: bool
+    loop_to_sig: LoopSignature | None
+    loop_from_sig: LoopSignature | None
+
+
+def _classify_todo_entries(
     phase_num: int,
-    sop_id: str,
     body: str,
     loops: list[LoopSignature],
-    checkbox_prefix: str,
-) -> list[str]:
-    """Build flat TODO items for a single SOP phase.
+) -> list[_TodoEntry]:
+    """Extract and classify a phase's TODO entries.
 
-    Returns list of formatted TODO lines with dotted numbering,
-    SOP provenance tags, gate markers, and loop markers.
+    Shared by `_build_todo_items` (text) and `_build_todo_json` (JSON) —
+    section extraction, fallback handling, loop-map building, and per-step
+    classification previously lived verbatim in both (CHG-2302).
+
+    Fallback entries (no Steps section / no parsed steps) take the uniform
+    path: gate=False and no loop signatures, so marker application is a
+    no-op on them.
     """
-    items: list[str] = []
     steps_section = _extract_steps_section(body)
-
     if steps_section is None:
-        return [f"{checkbox_prefix}{phase_num}.1 [{sop_id}] (no Steps section found)"]
+        return [
+            _TodoEntry(f"{phase_num}.1", "(no Steps section found)", False, None, None)
+        ]
 
     steps = _parse_steps_for_json(steps_section)
     if not steps:
         # Raw section text fallback
-        return [f"{checkbox_prefix}{phase_num}.1 [{sop_id}] {steps_section.strip()}"]
+        return [_TodoEntry(f"{phase_num}.1", steps_section.strip(), False, None, None)]
 
-    # Build loop marker maps
     loop_to_steps = {
         loop.to_step: loop for loop in loops if isinstance(loop.to_step, int)
     }
     loop_from_steps = {loop.from_step: loop for loop in loops}
 
+    entries: list[_TodoEntry] = []
     for step in steps:
         step_idx = step["index"]
-        text = step["text"]
-        gate = step["gate"]
         # FXA-2226 Path B: append optional sub_branch suffix for sibling
         # sub-steps so dotted index goes from "1.3" → "1.3a".
         dotted = f"{phase_num}.{step_idx}{step.get('sub_branch', '')}"
-
         # Classify step (gate and loop markers are independent)
         is_gate, loop_to_sig, loop_from_sig = _classify_step(
-            step_idx, gate, loop_to_steps, loop_from_steps
+            step_idx, step["gate"], loop_to_steps, loop_from_steps
         )
+        entries.append(
+            _TodoEntry(dotted, step["text"], is_gate, loop_to_sig, loop_from_sig)
+        )
+    return entries
 
-        # Apply markers to text
-        text = _apply_text_markers(text, is_gate, loop_to_sig, loop_from_sig, phase_num)
 
-        items.append(f"{checkbox_prefix}{dotted} [{sop_id}] {text}")
+def _build_todo_items(
+    phase_num: int,
+    sop_id: str,
+    body: str,
+    loops: list[LoopSignature],
+    checkbox_prefix: str,
+) -> list[str]:
+    """Build flat TODO items for a single SOP phase.
 
+    Returns list of formatted TODO lines with dotted numbering,
+    SOP provenance tags, gate markers, and loop markers.
+    """
+    items: list[str] = []
+    for entry in _classify_todo_entries(phase_num, body, loops):
+        text = _apply_text_markers(
+            entry.text, entry.gate, entry.loop_to_sig, entry.loop_from_sig, phase_num
+        )
+        items.append(f"{checkbox_prefix}{entry.dotted} [{sop_id}] {text}")
     return items
 
 
@@ -320,67 +352,23 @@ def _build_todo_json(
     - loop-to AND loop-from same step → loop_marker="loop-back" (tiebreak).
     """
     items: list[dict] = []
-    steps_section = _extract_steps_section(body)
-
-    if steps_section is None:
-        return [
-            {
-                "index": f"{phase_num}.1",
-                "sop": sop_id,
-                "text": "(no Steps section found)",
-                "gate": False,
-                "loop_marker": None,
-            }
-        ]
-
-    steps = _parse_steps_for_json(steps_section)
-    if not steps:
-        return [
-            {
-                "index": f"{phase_num}.1",
-                "sop": sop_id,
-                "text": steps_section.strip(),
-                "gate": False,
-                "loop_marker": None,
-            }
-        ]
-
-    # Build loop marker maps
-    loop_to_steps = {
-        loop.to_step: loop for loop in loops if isinstance(loop.to_step, int)
-    }
-    loop_from_steps = {loop.from_step: loop for loop in loops}
-
-    for step in steps:
-        step_idx = step["index"]
-        text = step["text"]
-        gate = step["gate"]
-        # FXA-2226 Path B: append optional sub_branch suffix.
-        dotted = f"{phase_num}.{step_idx}{step.get('sub_branch', '')}"
-
-        # Classify step (gate and loop markers are independent)
-        is_gate, loop_to_sig, loop_from_sig = _classify_step(
-            step_idx, gate, loop_to_steps, loop_from_steps
-        )
-
+    for entry in _classify_todo_entries(phase_num, body, loops):
         # Determine loop_marker for JSON (never "gate")
         # Tiebreak: loop_from takes precedence over loop_to
         loop_marker = None
-        if loop_from_sig:
+        if entry.loop_from_sig:
             loop_marker = "loop-back"
-        elif loop_to_sig:
+        elif entry.loop_to_sig:
             loop_marker = "loop-start"
-
         items.append(
             {
-                "index": dotted,
+                "index": entry.dotted,
                 "sop": sop_id,
-                "text": text,
-                "gate": is_gate,
+                "text": entry.text,
+                "gate": entry.gate,
                 "loop_marker": loop_marker,
             }
         )
-
     return items
 
 
@@ -493,69 +481,23 @@ def _emit_recommended_skills(recommended_skills: list[dict] | None) -> None:
         )
 
 
-@click.command("plan")
-@root_option
-@click.argument("sop_ids", nargs=-1)
-@click.option("--human", is_flag=True, help="Human-readable output")
-@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
-@click.option(
-    "--todo",
-    "output_todo",
-    is_flag=True,
-    help="Flat unified TODO list across selected SOPs",
-)
-@click.option(
-    "--graph",
-    "output_graph",
-    is_flag=True,
-    help="Append graph of composed plan (ASCII + fenced Mermaid by default)",
-)
-@click.option(
-    "--graph-format",
-    "graph_format",
-    type=click.Choice(["ascii", "mermaid", "both"]),
-    default="both",
-    help="Graph rendering format (requires --graph). Default: both.",
-)
-@click.option(
-    "--graph-layout",
-    "graph_layout",
-    type=click.Choice(["nested", "flat"]),
-    default="nested",
-    help=(
-        "ASCII graph layout (requires --graph, ASCII-only): 'nested' "
-        "(default, FXA-2218 — step-boxes inside phase-boxes with cross-SOP "
-        "tracks) or 'flat' (legacy, one phase-box per SOP)."
-    ),
-)
-@click.option(
-    "--task",
-    "task_description",
-    default=None,
-    help="Auto-compose SOPs by matching Task tags against task description",
-)
-@click.option(
-    "--with-skills",
-    is_flag=True,
-    help="Recommend matching skill documents for the task.",
-)
-@click.pass_context
-def plan_cmd(
+_PhaseInfo = tuple[
+    str, Document, ParsedDocument, "WorkflowSignature | None", list[LoopSignature]
+]
+
+
+def _validate_option_coupling(
     ctx: click.Context,
-    sop_ids: tuple[str, ...],
-    human: bool,
-    output_json: bool,
-    output_todo: bool,
     output_graph: bool,
-    graph_format: str,
-    graph_layout: str,
-    task_description: str | None,
     with_skills: bool,
+    task_description: str | None,
 ) -> None:
-    """Generate workflow checklist from SOPs."""
-    # ── Validate --graph-format / --graph coupling ──
-    # --graph-format is only meaningful with --graph.  Detect when the user
-    # passed a non-default graph_format without --graph and raise UsageError.
+    """Reject option combinations that are only meaningful together.
+
+    --graph-format / --graph-layout require --graph (explicit non-default
+    values are detected via the Click parameter source); --with-skills
+    requires --task.
+    """
     if not output_graph:
         # click.Choice default is "both"; distinguish explicit vs default by
         # consulting the parameter source. Explicit without --graph is an error.
@@ -570,49 +512,86 @@ def plan_cmd(
     if with_skills and task_description is None:
         raise click.UsageError("--with-skills requires --task")
 
-    # Scan documents first (needed for --task resolution)
-    docs = scan_or_fail(ctx)
-    recommended_skills = (
-        list_skills(docs, task=task_description) if with_skills else None
-    )
-
-    # Handle --task flag for auto-composition
-    composed_from_provenance: dict[str, list[str]] | None = None
 
-    if task_description is not None:
-        # Auto-compose SOPs via tag matching
-        all_sops = _gather_all_sops(docs)
-        positional_list = list(sop_ids)
-        try:
-            resolved_ids, composed_from_provenance = resolve_sops_from_task(
-                task_description, all_sops, positional_list
-            )
-        except CompositionError as e:
-            # CLI boundary (CHG-2295): core raises the domain exception;
-            # convert here, preserving message and exit code (2 = zero-match).
-            exc = click.ClickException(str(e))
-            exc.exit_code = e.exit_code
-            raise exc from e
-        # Convert resolved IDs back to tuple for processing
-        sop_ids = tuple(resolved_ids)
+def _resolve_sop_ids(
+    docs: list[Document],
+    sop_ids: tuple[str, ...],
+    task_description: str,
+) -> tuple[tuple[str, ...], dict[str, list[str]]]:
+    """Resolve --task auto-composition into an ordered SOP-ID tuple.
 
-    if not sop_ids:
-        raise click.UsageError("Usage: af plan SOP_ID [SOP_ID ...]")
+    Returns (resolved_sop_ids, provenance). CLI boundary for
+    CompositionError (CHG-2295): core raises the domain exception;
+    converted here preserving message and exit code (2 = zero-match).
+    """
+    all_sops = _gather_all_sops(docs)
+    try:
+        resolved_ids, provenance = resolve_sops_from_task(
+            task_description, all_sops, list(sop_ids)
+        )
+    except CompositionError as e:
+        exc = click.ClickException(str(e))
+        exc.exit_code = e.exit_code
+        raise exc from e
+    return tuple(resolved_ids), provenance
+
+
+def _enforce_branches_gate(doc: Document, parsed: ParsedDocument) -> None:
+    """FXA-2226 Path B renderer-readiness gate, applied at plan time.
+
+    (Per Gemini PR #68 review F2.) Until CHG-2227 Phase 8a flips
+    `_BRANCHES_RENDERER_READY` to True, any SOP authoring
+    `Workflow branches:` is rejected here so `af plan` never emits
+    sub-stepped surface (`"1.3a"` indices, ASCII collisions, etc.)
+    before the renderer ships.
+
+    Per Codex PR #68 R2 review: gate on FIELD PRESENCE (including
+    `Workflow branches: []` / `null`), not on parsed-list non-emptiness.
+    Per Codex PR #68 R3 review: also gate on undeclared sub-step lines
+    (`3a./3b.` written directly in `## Steps` without the metadata
+    field). The Phase 1 parser surfaces those into StepDict.sub_branch
+    and Phase 3's `dotted` format emits `"1.3a"` — so even without
+    the metadata field, an author can produce Path B surface.
+    Detection: any parsed step has a `sub_branch` key set.
+    """
+    if _BRANCHES_RENDERER_READY:
+        return
+    gate_trip = has_workflow_branches_field(parsed)
+    if not gate_trip:
+        # Per Codex PR #68 R4 inline review: use a flush-left,
+        # fence-aware scan (mirrors validate_branches discipline).
+        # `_parse_steps_for_json` strips indentation and skips
+        # fence tracking, so it would falsely trip the gate on
+        # indented or fenced `3a.` lines.
+        from fx_alfred.core.steps import has_top_level_substep_lines
+
+        steps_section = _extract_steps_section(parsed.body)
+        if steps_section is not None:
+            gate_trip = has_top_level_substep_lines(steps_section)
+    if gate_trip:
+        raise click.ClickException(
+            f"{doc.prefix}-{doc.acid}: Workflow branches: schema "
+            "(or sub-step lines like `3a./3b.`) parsed but renderer "
+            "support is not yet shipped (CHG-2227 pending). "
+            "Production SOPs MUST NOT author this field or use "
+            "sub-step syntax until CHG-2227 lands."
+        )
 
-    if output_json and human:
-        raise click.UsageError("--json and --human are mutually exclusive")
 
-    # ── First pass: parse all SOPs and collect workflow signatures ──
-    phase_info: list[
-        tuple[
-            str, Document, ParsedDocument, WorkflowSignature | None, list[LoopSignature]
-        ]
-    ] = []
+def _collect_phase_info(
+    docs: list[Document],
+    sop_ids: tuple[str, ...],
+    output_json: bool,
+) -> list[_PhaseInfo]:
+    """First pass: parse each SOP and collect workflow metadata.
 
+    Non-SOP and malformed documents are skipped with a warning (text
+    modes only — JSON output stays parseable).
+    """
+    phase_info: list[_PhaseInfo] = []
     for sop_id in sop_ids:
         doc = find_or_fail(docs, sop_id)
 
-        # Verify document is SOP type
         if doc.type_code != "SOP":
             if not output_json:
                 click.echo(
@@ -620,47 +599,12 @@ def plan_cmd(
                 )
             continue
 
-        # Parse document content
         try:
             content = doc.resolve_resource().read_text(encoding="utf-8")
             parsed = parse_metadata(content)
             sig = parse_workflow_signature(parsed)
             loops = parse_workflow_loops(parsed)
-            # FXA-2226 Path B: enforce renderer-readiness gate at plan time too
-            # (per Gemini PR #68 review F2). Until CHG-2227 Phase 8a flips
-            # `_BRANCHES_RENDERER_READY` to True, any SOP authoring
-            # `Workflow branches:` is rejected here so `af plan` never emits
-            # sub-stepped surface (`"1.3a"` indices, ASCII collisions, etc.)
-            # before the renderer ships.
-            # Per Codex PR #68 R2 review: gate on FIELD PRESENCE (including
-            # `Workflow branches: []` / `null`), not on parsed-list non-emptiness.
-            # Per Codex PR #68 R3 review: also gate on undeclared sub-step lines
-            # (`3a./3b.` written directly in `## Steps` without the metadata
-            # field). The Phase 1 parser surfaces those into StepDict.sub_branch
-            # and Phase 3's `dotted` format emits `"1.3a"` — so even without
-            # the metadata field, an author can produce Path B surface.
-            # Detection: any parsed step has a `sub_branch` key set.
-            if not _BRANCHES_RENDERER_READY:
-                _gate_trip = has_workflow_branches_field(parsed)
-                if not _gate_trip:
-                    # Per Codex PR #68 R4 inline review: use a flush-left,
-                    # fence-aware scan (mirrors validate_branches discipline).
-                    # `_parse_steps_for_json` strips indentation and skips
-                    # fence tracking, so it would falsely trip the gate on
-                    # indented or fenced `3a.` lines.
-                    from fx_alfred.core.steps import has_top_level_substep_lines
-
-                    _steps_section = _extract_steps_section(parsed.body)
-                    if _steps_section is not None:
-                        _gate_trip = has_top_level_substep_lines(_steps_section)
-                if _gate_trip:
-                    raise click.ClickException(
-                        f"{doc.prefix}-{doc.acid}: Workflow branches: schema "
-                        "(or sub-step lines like `3a./3b.`) parsed but renderer "
-                        "support is not yet shipped (CHG-2227 pending). "
-                        "Production SOPs MUST NOT author this field or use "
-                        "sub-step syntax until CHG-2227 lands."
-                    )
+            _enforce_branches_gate(doc, parsed)
         except MalformedDocumentError as e:
             if not output_json:
                 click.echo(
@@ -669,9 +613,12 @@ def plan_cmd(
             continue
 
         phase_info.append((sop_id, doc, parsed, sig, loops))
+    return phase_info
 
-    # ── Validate workflow signatures before composition ──
-    for sop_id, doc, parsed, sig, loops in phase_info:
+
+def _validate_composition(phase_info: list[_PhaseInfo]) -> list[WorkflowEdge]:
+    """Validate workflow signatures, then type-check the composed chain."""
+    for _sop_id, doc, _parsed, sig, _loops in phase_info:
         if sig is not None:
             wf_errors = validate_workflow_signature(sig)
             if wf_errors:
@@ -680,7 +627,6 @@ def plan_cmd(
                     f"Invalid workflow metadata in {doc_id}: " + "; ".join(wf_errors)
                 )
 
-    # ── Workflow composition check ──
     chain: list[tuple[str, WorkflowSignature]] = [
         (
             f"{doc.prefix}-{doc.acid}",
@@ -696,16 +642,21 @@ def plan_cmd(
                 f"Workflow type mismatch: {edge.from_doc} outputs "
                 f"'{edge.from_output}' but {edge.to_doc} expects '{edge.to_input}'"
             )
+    return edges
+
 
-    # ── Cross-SOP loop runtime checks (FXA-2218 D4) ──
-    # After composition order is fixed, every cross-SOP loop must:
-    #   (a) reference a target SOP that is part of this composed plan
-    #   (b) reference a target that comes BEFORE the source in plan order
-    #       (back-edge semantic — "on failure, retry from earlier step")
-    #
-    # Repeated SOP IDs are supported (e.g. plan "A B A"): all positions
-    # preserved; D4 accepts if ANY target occurrence precedes the source
-    # occurrence being evaluated (PR #59 Codex review P2 #5).
+def _validate_cross_sop_loops(phase_info: list[_PhaseInfo]) -> None:
+    """Cross-SOP loop runtime checks (FXA-2218 D4).
+
+    After composition order is fixed, every cross-SOP loop must:
+      (a) reference a target SOP that is part of this composed plan
+      (b) reference a target that comes BEFORE the source in plan order
+          (back-edge semantic — "on failure, retry from earlier step")
+
+    Repeated SOP IDs are supported (e.g. plan "A B A"): all positions
+    preserved; D4 accepts if ANY target occurrence precedes the source
+    occurrence being evaluated (PR #59 Codex review P2 #5).
+    """
     composed_positions: dict[str, list[int]] = {}
     for idx, (_sid, doc, _p, _sig, _lps) in enumerate(phase_info):
         composed_positions.setdefault(f"{doc.prefix}-{doc.acid}", []).append(idx)
@@ -733,145 +684,171 @@ def plan_cmd(
                     f"— target SOP precedes source; back-edges only"
                 )
 
-    composition_valid = all(e.compatible for e in edges) if edges else True
 
-    # ── Flat TODO output mode ──
-    if output_todo and not output_json:
-        todo_items: list[str] = []
-        phase_num = 0
-        checkbox = "□ " if human else "- [ ] "
-
-        for sop_id, doc, parsed, sig, loops in phase_info:
-            phase_num += 1
-            body = parsed.body
-            doc_id = f"{doc.prefix}-{doc.acid}"
-            items = _build_todo_items(phase_num, doc_id, body, loops, checkbox)
-            todo_items.extend(items)
-
-        if not todo_items:
-            return
-
-        # Header (with Composed from if task was used)
-        if composed_from_provenance:
-            header = _format_composed_from_header(composed_from_provenance)
-            click.echo(f"# {header}")
-            click.echo()
-        click.echo("# Flat TODO — Follow each item in order")
-        click.echo()
-        click.echo("\n".join(todo_items))
+def _emit_todo_text(
+    phase_info: list[_PhaseInfo],
+    composed_from_provenance: dict[str, list[str]] | None,
+    human: bool,
+    output_graph: bool,
+    graph_format: str,
+    graph_layout: str,
+    recommended_skills: list[dict] | None,
+) -> None:
+    """Flat TODO output mode (--todo without --json)."""
+    todo_items: list[str] = []
+    phase_num = 0
+    checkbox = "□ " if human else "- [ ] "
+
+    for _sop_id, doc, parsed, _sig, loops in phase_info:
+        phase_num += 1
+        doc_id = f"{doc.prefix}-{doc.acid}"
+        todo_items.extend(
+            _build_todo_items(phase_num, doc_id, parsed.body, loops, checkbox)
+        )
 
-        if output_graph:
-            provenance_map = _build_provenance_map(composed_from_provenance)
-            click.echo()
-            _emit_graph(phase_info, provenance_map, graph_format, graph_layout)
-        _emit_recommended_skills(recommended_skills)
+    if not todo_items:
         return
 
-    # ── JSON output mode ──
-    if output_json:
-        phases_json: list[dict] = []
-        todo_json: list[dict] = []
-        loops_json: list[dict] = []
-        phase_num = 0
-
-        for sop_id, doc, parsed, sig, loops in phase_info:
-            phase_num += 1
-            body = parsed.body
-            doc_id = f"{doc.prefix}-{doc.acid}"
-
-            steps_section = _extract_steps_section(body)
-            steps = _parse_steps_for_json(steps_section) if steps_section else []
-            phases_json.append(
-                {
-                    "phase": sop_id,
-                    "source_sop": sop_id,
-                    "steps": steps,
-                    "workflow_input": sig.input if sig else "",
-                    "workflow_output": sig.output if sig else "",
-                    "workflow_requires": sig.requires if sig else [],
-                    "workflow_provides": sig.provides if sig else [],
-                    "workflow_typed": sig is not None
-                    and bool(sig.input and sig.output),
-                }
-            )
+    # Header (with Composed from if task was used)
+    if composed_from_provenance:
+        header = _format_composed_from_header(composed_from_provenance)
+        click.echo(f"# {header}")
+        click.echo()
+    click.echo("# Flat TODO — Follow each item in order")
+    click.echo()
+    click.echo("\n".join(todo_items))
 
-            # Build todo items if --todo is set
-            if output_todo:
-                todo_items_json = _build_todo_json(phase_num, doc_id, body, loops)
-                todo_json.extend(todo_items_json)
-
-                # Build loops array with dotted step references. Cross-SOP
-                # loops emit `to` as the raw "PREFIX-ACID.step" string — same
-                # lexical form as the authored metadata (FXA-2218 Commit 4).
-                for loop in loops:
-                    if isinstance(loop.to_step, int):
-                        loop_to_ref = f"{phase_num}.{loop.to_step}"
-                    else:
-                        loop_to_ref = loop.to_step
-                    loops_json.append(
-                        {
-                            "id": loop.id,
-                            "from": f"{phase_num}.{loop.from_step}",
-                            "to": loop_to_ref,
-                            "max_iterations": loop.max_iterations,
-                            "sop": doc_id,
-                        }
-                    )
-
-        has_new_keys = (
-            output_todo
-            or output_graph
-            or (composed_from_provenance is not None)
-            or with_skills
-        )
-        schema_ver = "3" if with_skills else ("2" if has_new_keys else "1")
-
-        result = {
-            "schema_version": schema_ver,
-            "sop_ids": list(sop_ids),
-            "phases": phases_json,
-            "composition_valid": composition_valid,
-            "edges": [
-                {
-                    "from": e.from_doc,
-                    "to": e.to_doc,
-                    "typed": e.typed,
-                    "compatible": e.compatible,
-                    "from_output": e.from_output,
-                    "to_input": e.to_input,
-                }
-                for e in edges
-            ],
-        }
+    if output_graph:
+        provenance_map = _build_provenance_map(composed_from_provenance)
+        click.echo()
+        _emit_graph(phase_info, provenance_map, graph_format, graph_layout)
+    _emit_recommended_skills(recommended_skills)
+
+
+def _emit_json_output(
+    sop_ids: tuple[str, ...],
+    phase_info: list[_PhaseInfo],
+    edges: list[WorkflowEdge],
+    composition_valid: bool,
+    composed_from_provenance: dict[str, list[str]] | None,
+    output_todo: bool,
+    output_graph: bool,
+    graph_format: str,
+    graph_layout: str,
+    with_skills: bool,
+    recommended_skills: list[dict] | None,
+) -> None:
+    """JSON output mode (--json, optionally with --todo / --graph)."""
+    phases_json: list[dict] = []
+    todo_json: list[dict] = []
+    loops_json: list[dict] = []
+    phase_num = 0
+
+    for sop_id, doc, parsed, sig, loops in phase_info:
+        phase_num += 1
+        body = parsed.body
+        doc_id = f"{doc.prefix}-{doc.acid}"
 
-        if composed_from_provenance:
-            result["composed_from"] = composed_from_provenance
+        steps_section = _extract_steps_section(body)
+        steps = _parse_steps_for_json(steps_section) if steps_section else []
+        phases_json.append(
+            {
+                "phase": sop_id,
+                "source_sop": sop_id,
+                "steps": steps,
+                "workflow_input": sig.input if sig else "",
+                "workflow_output": sig.output if sig else "",
+                "workflow_requires": sig.requires if sig else [],
+                "workflow_provides": sig.provides if sig else [],
+                "workflow_typed": sig is not None and bool(sig.input and sig.output),
+            }
+        )
 
+        # Build todo items if --todo is set
         if output_todo:
-            result["todo"] = todo_json
-            result["loops"] = loops_json
-
-        if output_graph:
-            provenance_map = _build_provenance_map(composed_from_provenance)
-            mermaid_phases = _build_mermaid_phases(phase_info, provenance_map)
-            if graph_format in ("ascii", "both"):
-                result["ascii_graph"] = _render_layout(
-                    mermaid_phases, provenance_map, graph_layout
+            todo_json.extend(_build_todo_json(phase_num, doc_id, body, loops))
+
+            # Build loops array with dotted step references. Cross-SOP
+            # loops emit `to` as the raw "PREFIX-ACID.step" string — same
+            # lexical form as the authored metadata (FXA-2218 Commit 4).
+            for loop in loops:
+                if isinstance(loop.to_step, int):
+                    loop_to_ref = f"{phase_num}.{loop.to_step}"
+                else:
+                    loop_to_ref = loop.to_step
+                loops_json.append(
+                    {
+                        "id": loop.id,
+                        "from": f"{phase_num}.{loop.from_step}",
+                        "to": loop_to_ref,
+                        "max_iterations": loop.max_iterations,
+                        "sop": doc_id,
+                    }
                 )
-            if graph_format in ("mermaid", "both"):
-                result["graph_mermaid"] = render_mermaid(mermaid_phases)
 
-        if with_skills:
-            result["recommended_skills"] = recommended_skills or []
+    has_new_keys = (
+        output_todo
+        or output_graph
+        or (composed_from_provenance is not None)
+        or with_skills
+    )
+    schema_ver = "3" if with_skills else ("2" if has_new_keys else "1")
+
+    result = {
+        "schema_version": schema_ver,
+        "sop_ids": list(sop_ids),
+        "phases": phases_json,
+        "composition_valid": composition_valid,
+        "edges": [
+            {
+                "from": e.from_doc,
+                "to": e.to_doc,
+                "typed": e.typed,
+                "compatible": e.compatible,
+                "from_output": e.from_output,
+                "to_input": e.to_input,
+            }
+            for e in edges
+        ],
+    }
+
+    if composed_from_provenance:
+        result["composed_from"] = composed_from_provenance
 
-        emit_json(result)
-        return
+    if output_todo:
+        result["todo"] = todo_json
+        result["loops"] = loops_json
+
+    if output_graph:
+        provenance_map = _build_provenance_map(composed_from_provenance)
+        mermaid_phases = _build_mermaid_phases(phase_info, provenance_map)
+        if graph_format in ("ascii", "both"):
+            result["ascii_graph"] = _render_layout(
+                mermaid_phases, provenance_map, graph_layout
+            )
+        if graph_format in ("mermaid", "both"):
+            result["graph_mermaid"] = render_mermaid(mermaid_phases)
+
+    if with_skills:
+        result["recommended_skills"] = recommended_skills or []
 
-    # ── Second pass: render phased output (default behavior) ──
+    emit_json(result)
+
+
+def _emit_phased_text(
+    phase_info: list[_PhaseInfo],
+    composed_from_provenance: dict[str, list[str]] | None,
+    human: bool,
+    output_graph: bool,
+    graph_format: str,
+    graph_layout: str,
+    recommended_skills: list[dict] | None,
+) -> None:
+    """Default phased output (LLM checklist, or --human boxes)."""
     phases_text: list[str] = []
     phase_num = 0
 
-    for sop_id, doc, parsed, sig, loops in phase_info:
+    for sop_id, doc, parsed, sig, _loops in phase_info:
         body = parsed.body
         summary = extract_section(body, "What Is It?")
         title = doc.title
@@ -916,3 +893,128 @@ def plan_cmd(
         provenance_map = _build_provenance_map(composed_from_provenance)
         _emit_graph(phase_info, provenance_map, graph_format, graph_layout)
     _emit_recommended_skills(recommended_skills)
+
+
+@click.command("plan")
+@root_option
+@click.argument("sop_ids", nargs=-1)
+@click.option("--human", is_flag=True, help="Human-readable output")
+@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
+@click.option(
+    "--todo",
+    "output_todo",
+    is_flag=True,
+    help="Flat unified TODO list across selected SOPs",
+)
+@click.option(
+    "--graph",
+    "output_graph",
+    is_flag=True,
+    help="Append graph of composed plan (ASCII + fenced Mermaid by default)",
+)
+@click.option(
+    "--graph-format",
+    "graph_format",
+    type=click.Choice(["ascii", "mermaid", "both"]),
+    default="both",
+    help="Graph rendering format (requires --graph). Default: both.",
+)
+@click.option(
+    "--graph-layout",
+    "graph_layout",
+    type=click.Choice(["nested", "flat"]),
+    default="nested",
+    help=(
+        "ASCII graph layout (requires --graph, ASCII-only): 'nested' "
+        "(default, FXA-2218 — step-boxes inside phase-boxes with cross-SOP "
+        "tracks) or 'flat' (legacy, one phase-box per SOP)."
+    ),
+)
+@click.option(
+    "--task",
+    "task_description",
+    default=None,
+    help="Auto-compose SOPs by matching Task tags against task description",
+)
+@click.option(
+    "--with-skills",
+    is_flag=True,
+    help="Recommend matching skill documents for the task.",
+)
+@click.pass_context
+def plan_cmd(
+    ctx: click.Context,
+    sop_ids: tuple[str, ...],
+    human: bool,
+    output_json: bool,
+    output_todo: bool,
+    output_graph: bool,
+    graph_format: str,
+    graph_layout: str,
+    task_description: str | None,
+    with_skills: bool,
+) -> None:
+    """Generate workflow checklist from SOPs."""
+    _validate_option_coupling(ctx, output_graph, with_skills, task_description)
+
+    # Scan documents first (needed for --task resolution)
+    docs = scan_or_fail(ctx)
+    recommended_skills = (
+        list_skills(docs, task=task_description) if with_skills else None
+    )
+
+    # Handle --task flag for auto-composition
+    composed_from_provenance: dict[str, list[str]] | None = None
+    if task_description is not None:
+        sop_ids, composed_from_provenance = _resolve_sop_ids(
+            docs, sop_ids, task_description
+        )
+
+    if not sop_ids:
+        raise click.UsageError("Usage: af plan SOP_ID [SOP_ID ...]")
+
+    if output_json and human:
+        raise click.UsageError("--json and --human are mutually exclusive")
+
+    phase_info = _collect_phase_info(docs, sop_ids, output_json)
+    edges = _validate_composition(phase_info)
+    _validate_cross_sop_loops(phase_info)
+    composition_valid = all(e.compatible for e in edges) if edges else True
+
+    if output_todo and not output_json:
+        _emit_todo_text(
+            phase_info,
+            composed_from_provenance,
+            human,
+            output_graph,
+            graph_format,
+            graph_layout,
+            recommended_skills,
+        )
+        return
+
+    if output_json:
+        _emit_json_output(
+            sop_ids,
+            phase_info,
+            edges,
+            composition_valid,
+            composed_from_provenance,
+            output_todo,
+            output_graph,
+            graph_format,
+            graph_layout,
+            with_skills,
+            recommended_skills,
+        )
+        return
+
+    _emit_phased_text(
+        phase_info,
+        composed_from_provenance,
+        human,
+        output_graph,
+        graph_format,
+        graph_layout,
+        recommended_skills,
+    )
diff --git a/tests/test_architecture.py b/tests/test_architecture.py
index ff21d3b..6b3c725 100644
--- a/tests/test_architecture.py
+++ b/tests/test_architecture.py
@@ -111,3 +111,41 @@ def test_commands_use_named_schema_version_constants() -> None:
         lambda line: '"schema_version": "1"' in line, skip_helpers=True
     )
     assert offenders == [], f"use a named SCHEMA_VERSION constant: {offenders}"
+
+
+# Pre-CHG-2302 oversized functions, pinned at their current sizes — a
+# RATCHET: they may shrink but not grow, and new functions get the 150
+# cap. Decomposing them is recorded follow-up work (CHG-2302 §Out of
+# Scope); remove entries as they get decomposed.
+_GRANDFATHERED_FUNCTION_LINES = {
+    "create_cmd.py:create_cmd": 230,
+    "update_cmd.py:update_cmd": 283,
+    "validate_cmd.py:validate_cmd": 325,
+}
+
+
+def test_commands_functions_stay_decomposed() -> None:
+    """No function in commands/ may exceed 150 lines (CHG-2302).
+
+    Operationalizes the plan_cmd decomposition: the pre-change main
+    function had grown to 376 lines of nested mode branching, absorbing
+    every plan feature since FXA-2134. 150 leaves ~1.4x headroom over
+    the largest post-decomposition function (_emit_json_output, 108).
+    Three pre-existing functions are grandfathered at their current
+    sizes (ratchet — see _GRANDFATHERED_FUNCTION_LINES)."""
+    import ast
+
+    offenders: list[str] = []
+    for py in sorted(_COMMANDS_DIR.rglob("*.py")):
+        tree = ast.parse(py.read_text(encoding="utf-8"))
+        for node in ast.walk(tree):
+            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
+                length = (node.end_lineno or node.lineno) - node.lineno + 1
+                cap = _GRANDFATHERED_FUNCTION_LINES.get(f"{py.name}:{node.name}", 150)
+                if length > cap:
+                    offenders.append(
+                        f"{py.name}:{node.name} ({length} lines > cap {cap})"
+                    )
+    assert offenders == [], (
+        f"decompose oversized command functions (CHG-2302): {offenders}"
+    )
