"""Nested-layout ASCII DAG renderer for `af plan --graph` (FXA-2218).

Default under ``--graph-layout=nested``. Emits an ASCII DAG: each SOP is an
outer phase-box containing inner step-boxes with ``▼`` connectors.

Loop rendering (v1, FXA-2218):

- **Intra-SOP loops** render as a dedicated ``🔁 → N.M max K cond``
  annotation line inside the phase box, immediately below the source
  step's box.
- **Cross-SOP loops** (exactly one in the composed plan) render as a
  right-side vertical track that leaves the source phase box, traverses
  the inter-phase gutter, and re-enters the target phase box at the
  target step's row. ``◄───┐`` at target, ``│`` at intermediate rows,
  ``───┘ max N cond`` at source.
- **Multiple cross-SOP loops** (≥ 2 in the composed plan) fall back to
  inline ``🔁 → PREFIX-ACID.step max N cond`` annotations on each
  source step's content row, to the right of the phase-box border. This
  avoids the multi-track overlap corruption where later tracks' vertical
  pipes would clobber earlier tracks' suffix text. Full interval-graph
  column packing is deferred to a follow-up PRP.
- **Same-step multi-loop**: when a single step has more than one
  outbound loop (intra or cross), annotations are joined with `` ; ``
  on the same row — no silent data loss (R3 fix).

Reuses only the visual-width / padding / truncation primitives from
``core.ascii_graph``; all layout logic (nested boxes, cross-SOP track
routing, inline fallback) is net-new.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fx_alfred.core.ascii_graph import _pad_visual, _truncate_visual, _visual_width
from fx_alfred.core.workflow import CROSS_SOP_REF, LoopSignature

if TYPE_CHECKING:
    from fx_alfred.core.phases import PhaseDict, StepDict
    from fx_alfred.core.workflow import BranchSignature

# ── Geometry constants ───────────────────────────────────────────────────────

# Inner text width of a step-box (between the "│ " and " │" borders).
_STEP_INNER = 45
# Step-box full width (with borders): "│ " + text + " │" = text + 4.
_STEP_BOX_WIDTH = _STEP_INNER + 4
# Phase-box inner width (between "│" and "│"): step-box + " " on both sides + 2
# corner chars accounted for elsewhere. Keeps 2-space margin around step-box.
_PHASE_INNER = _STEP_BOX_WIDTH + 4
# Phase-box full width: "│" + inner + "│".
_PHASE_BOX_WIDTH = _PHASE_INNER + 2
# Gutter between phase-box right edge and the "┐"/"┘" glyph column.
# 4 chars gives "◄───┐" (5 glyphs: the first fans into the gutter, the last
# sits in the track column proper).
_TRACK_GUTTER = 4
# Width each cross-SOP track occupies: 1 column for the │/┐/┘ glyph plus
# 1 space before the next track column. Adjacent tracks share the gutter
# above, so the per-track cost after the first is ``_TRACK_COL``.
_TRACK_COL = 2


# ── Per-step box rendering ───────────────────────────────────────────────────


def _render_step_box(text: str) -> tuple[str, str, str]:
    """Render a step box as ``(top, middle, bottom)`` lines.

    Each line is exactly ``_STEP_BOX_WIDTH`` visual cells wide.
    """
    top = "┌" + "─" * (_STEP_BOX_WIDTH - 2) + "┐"
    truncated = _truncate_visual(text, _STEP_INNER)
    padded = _pad_visual(truncated, _STEP_INNER)
    middle = f"│ {padded} │"
    bottom = "└" + "─" * (_STEP_BOX_WIDTH - 2) + "┘"
    return top, middle, bottom


def _render_arrow_line(inside_phase: bool) -> str:
    """Render a ``▼`` connector line between two step-boxes (inside a phase-box)
    or between two phase-boxes (inside_phase=False).

    Returns a line exactly ``_PHASE_BOX_WIDTH`` cells wide. When
    ``inside_phase=False`` the ``│...│`` phase borders are replaced with
    spaces so the arrow floats between phase boxes.
    """
    # Arrow sits centered over the step box's bottom connector column.
    # Step-box is positioned at (phase inner start + 2 spaces margin), so its
    # center column (relative to phase inner) is: 2 + (_STEP_BOX_WIDTH-1)//2.
    arrow_col_in_inner = 2 + (_STEP_BOX_WIDTH - 1) // 2
    inner = (
        " " * arrow_col_in_inner + "▼" + " " * (_PHASE_INNER - arrow_col_in_inner - 1)
    )
    if inside_phase:
        return f"│{inner}│"
    return f" {inner} "


def _render_step_bottom_connector(has_next: bool) -> str:
    """Render the bottom line of a step-box: uses ``┬`` if there's a ``▼`` below
    to connect to, else a plain ``─`` run.

    Returns the step-box bottom (width ``_STEP_BOX_WIDTH``).
    """
    if not has_next:
        return "└" + "─" * (_STEP_BOX_WIDTH - 2) + "┘"
    # Replace the center dash with ``┴`` (step box bottom connects to arrow).
    center = (_STEP_BOX_WIDTH - 1) // 2
    dashes = list("─" * (_STEP_BOX_WIDTH - 2))
    dashes[center - 1] = "┴"
    return "└" + "".join(dashes) + "┘"


# ── Per-phase rendering ──────────────────────────────────────────────────────


def _identify_branch_group(
    steps: list["StepDict"],
    branches: list["BranchSignature"],
) -> tuple[int, int, "BranchSignature"] | None:
    """Find the index range of a branch group in ``steps``.

    Returns ``(parent_idx, end_idx, branch_signature)`` where:
    - ``parent_idx`` is the index of the parent step in ``steps`` (whose
      ``step["index"] == branch.from_step``);
    - ``end_idx`` is the index *after* the last step consumed by the branch
      group (parent + siblings + optional convergence). Use as ``end_idx``
      in slicing.
    - ``branch_signature`` is the matching :class:`BranchSignature`.

    Returns ``None`` if no branch group is present.

    Per FXA-2227 Phase 4 GREEN, only the FIRST branch group is detected
    here; the caller iterates and may invoke this repeatedly on the
    remainder of the steps list. (For Mid scope, SOPs typically have at
    most one branch group; multi-branch is supported by the schema but
    rare in practice.)
    """
    if not branches:
        return None
    for bsig in branches:
        from_step = bsig.from_step
        # Locate parent step.
        parent_idx = None
        for i, s in enumerate(steps):
            if s["index"] == from_step and "sub_branch" not in s:
                parent_idx = i
                break
        if parent_idx is None:
            continue
        # Walk forward: collect contiguous sub-step siblings with
        # index == from_step + 1.
        i = parent_idx + 1
        sibling_count = 0
        while (
            i < len(steps)
            and steps[i].get("sub_branch") is not None
            and steps[i]["index"] == from_step + 1
        ):
            sibling_count += 1
            i += 1
        if sibling_count == 0:
            continue
        # The sibling group is steps[parent_idx+1 : parent_idx+1+sibling_count].
        # Convergence (if any) is the next plain step — but NOT if that
        # plain step is itself another branch's parent (chained-branch case).
        # Without this guard, a back-to-back branch like
        #   from_step=2 (siblings 3a/3b), then from_step=4 (siblings 5a/5b)
        # would silently consume step 4 as the first branch's "convergence"
        # and skip it from rendering, dropping the second branch entirely.
        other_branch_starts = {b.from_step for b in branches if b is not bsig}
        if (
            i < len(steps)
            and "sub_branch" not in steps[i]
            and steps[i]["index"] not in other_branch_starts
        ):
            end_idx = i + 1
        else:
            end_idx = i
        return parent_idx, end_idx, bsig
    return None


def _render_branch_group(  # noqa: PLR0913 — coordinated branch+convergence rendering
    phase_num: int,
    parent_step: "StepDict",
    sibling_steps: list["StepDict"],
    convergence_step: "StepDict | None",
    branch_signature: "BranchSignature",
    step_row_index: dict[tuple[int, int], int],
    canvas_row_offset: int,
    pre_lines_count: int,
    parent_annotations: list[str] | None = None,
) -> list[str]:
    """Render a branch group inside the phase box.

    Returns the list of lines (each padded to ``_PHASE_BOX_WIDTH``). Renders
    parent step's TOP + MIDDLE box rows normally, then delegates to
    ``branch_geometry.render_branch`` for the connector + label + sibling
    boxes + (optional) convergence. Each primitive line is centered within
    the phase inner area and wrapped in `│ ... │` borders.
    """
    from fx_alfred.core.branch_geometry import (
        BranchRenderInput,
        render_branch,
    )

    out_lines: list[str] = []

    # Render parent step's TOP + MIDDLE rows normally.
    parent_text = f"{phase_num}.{parent_step['index']} {parent_step['text']}"
    parent_top, parent_middle, _parent_bottom = _render_step_box(parent_text)
    pad_left = "  "
    pad_right = " " * (_PHASE_INNER - _STEP_BOX_WIDTH - len(pad_left))
    out_lines.append(f"│{pad_left}{parent_top}{pad_right}│")
    # Record parent step's content row.
    step_row_index[(phase_num, parent_step["index"])] = (
        canvas_row_offset + pre_lines_count + len(out_lines)
    )
    out_lines.append(f"│{pad_left}{parent_middle}{pad_right}│")

    # Parent-step intra-SOP loop annotations sit adjacent to the parent
    # middle row (matching the legacy non-branch path's annotation placement
    # — annotation goes immediately after the source step's content row,
    # not after the whole branch block).
    if parent_annotations:
        joined = " ; ".join(parent_annotations)
        ann = _truncate_visual(joined, _PHASE_INNER - 4)
        ann_padded = _pad_visual(ann, _PHASE_INNER - 2)
        out_lines.append(f"│ {ann_padded} │")

    # Build BranchRenderInput.
    n = len(branch_signature.to)
    # Pick a sibling box width that fits inside _STEP_BOX_WIDTH alignment.
    # For 2/3 siblings: 12 cells; for 4: 10 cells. Total widths:
    # 2-way: 12 + 1*(12+2) = 26; 3-way: 12 + 2*(12+2) = 40; 4-way: 10 + 3*(10+2) = 46.
    # All fit within _STEP_BOX_WIDTH = 49 cells.
    sibling_box_width = 12 if n <= 3 else 10

    sibling_texts = [s["text"] for s in sibling_steps]
    primitive_input = BranchRenderInput(
        parent_step_text=parent_text,
        siblings=branch_signature.to,
        sibling_texts=sibling_texts,
        converges_to=(convergence_step["index"] if convergence_step else None),
        converges_to_text=(convergence_step["text"] if convergence_step else None),
        box_width=sibling_box_width,
    )
    primitive_out = render_branch(primitive_input)

    # Each primitive line is `total_width` cells wide; pad to _STEP_BOX_WIDTH
    # then wrap in phase borders. Center the primitive output within the
    # step-box-equivalent column band so it visually aligns with the parent
    # step's top/middle rows.
    primitive_width = _visual_width(primitive_out.lines[0])
    indent = max(0, (_STEP_BOX_WIDTH - primitive_width) // 2)
    indent_pad = " " * indent
    line_pad_after = _STEP_BOX_WIDTH - primitive_width - indent

    for prim_idx, prim_line in enumerate(primitive_out.lines):
        wrapped = (
            f"│{pad_left}{indent_pad}{prim_line}"
            + " " * line_pad_after
            + f"{pad_right}│"
        )
        out_lines.append(wrapped)
        # Track convergence step row for cross-SOP loop overlay.
        if (
            convergence_step is not None
            and primitive_out.convergence_anchor_row is not None
            and prim_idx == primitive_out.convergence_anchor_row
        ):
            # The "anchor row" in primitive output is convergence box top
            # border; the content (text body) row is one below.
            step_row_index[(phase_num, convergence_step["index"])] = (
                canvas_row_offset + pre_lines_count + len(out_lines)
            )
    return out_lines


def _render_phase(
    phase_num: int,
    phase: PhaseDict,
    step_row_index: dict[tuple[int, int], int],
    canvas_row_offset: int,
    intra_sop_annotations: dict[int, list[str]] | None = None,
) -> list[str]:
    """Render a single phase as a list of lines (each exactly ``_PHASE_BOX_WIDTH``
    cells wide). Populates ``step_row_index[(phase_num, step_index)]`` with the
    row index (in the combined canvas) of each step's content row.

    ``intra_sop_annotations`` maps 1-based step index to a **list** of
    annotation strings — one per intra-SOP loop originating at that step.
    Multiple loops from the same step are joined with `` ; `` on the
    annotation line (FXA-2218 R3 — no silent data loss).
    """
    annotations = intra_sop_annotations or {}
    lines: list[str] = []
    sop_id = phase["sop_id"]
    steps = phase["steps"]
    branches = phase.get("branches", [])

    # Header line: "Phase N: SOP-ID"
    header_text = f"Phase {phase_num}: {sop_id}"
    header = _truncate_visual(header_text, _PHASE_INNER - 2)
    header_padded = _pad_visual(header, _PHASE_INNER - 2)
    lines.append("┌" + "─" * _PHASE_INNER + "┐")
    lines.append(f"│ {header_padded} │")
    # Blank line under header.
    lines.append("│" + " " * _PHASE_INNER + "│")

    # FXA-2227 Phase 4: detect branch groups and replace the per-step
    # rendering for those step ranges with branch_geometry primitive output.
    skip_indices: set[int] = set()
    branch_groups: dict[
        int, tuple[list["StepDict"], "StepDict | None", "BranchSignature"]
    ] = {}
    if branches:
        # Find ALL branch groups (one pass per branch).
        remaining = steps
        offset = 0
        while True:
            result = _identify_branch_group(remaining, branches)
            if result is None:
                break
            parent_local_idx, end_local_idx, bsig = result
            parent_global_idx = offset + parent_local_idx
            sibling_global_start = parent_global_idx + 1
            # Convergence is the last entry in the group if it's a plain step.
            sibling_global_end = offset + end_local_idx
            sibling_steps_global = list(range(sibling_global_start, sibling_global_end))
            # Determine convergence.
            convergence_global_idx: int | None = None
            if (
                end_local_idx > parent_local_idx + 1
                and "sub_branch" not in remaining[end_local_idx - 1]
            ):
                convergence_global_idx = offset + end_local_idx - 1
                sibling_steps_global = list(
                    range(sibling_global_start, convergence_global_idx)
                )
            sib_steps = [steps[i] for i in sibling_steps_global]
            conv_step = (
                steps[convergence_global_idx]
                if convergence_global_idx is not None
                else None
            )
            branch_groups[parent_global_idx] = (sib_steps, conv_step, bsig)
            for i in sibling_steps_global:
                skip_indices.add(i)
            if convergence_global_idx is not None:
                skip_indices.add(convergence_global_idx)
            # Continue scanning past this group.
            offset += end_local_idx
            remaining = remaining[end_local_idx:]
            # Remove the consumed branch from candidate list to avoid
            # re-matching the same branch.
            branches = [b for b in branches if b is not bsig]

    step_count = len(steps)
    for s_idx, step in enumerate(steps):
        if s_idx in skip_indices:
            continue
        # Branch group: render the whole group here, then advance past it.
        if s_idx in branch_groups:
            sib_steps, conv_step, bsig = branch_groups[s_idx]
            group_lines = _render_branch_group(
                phase_num=phase_num,
                parent_step=step,
                sibling_steps=sib_steps,
                convergence_step=conv_step,
                branch_signature=bsig,
                step_row_index=step_row_index,
                canvas_row_offset=canvas_row_offset,
                pre_lines_count=len(lines),
                parent_annotations=annotations.get(step["index"], []),
            )
            lines.extend(group_lines)
            # Convergence-step annotations sit after the convergence box
            # (same pattern as regular steps below — annotation row follows
            # the step's content row).
            if conv_step is not None:
                step_annotations = annotations.get(conv_step["index"], [])
                if step_annotations:
                    joined = " ; ".join(step_annotations)
                    ann = _truncate_visual(joined, _PHASE_INNER - 4)
                    ann_padded = _pad_visual(ann, _PHASE_INNER - 2)
                    lines.append(f"│ {ann_padded} │")
            # Primitive already provides arrows internally; no inter-step
            # arrow needed here.
            continue
        step_text = f"{phase_num}.{step['index']} {step['text']}"
        top, middle, bottom = _render_step_box(step_text)
        has_next = s_idx < step_count - 1
        if has_next:
            bottom = _render_step_bottom_connector(has_next=True)
        # Indent step-box 2 spaces inside the phase inner.
        pad_left = "  "
        pad_right = " " * (_PHASE_INNER - _STEP_BOX_WIDTH - len(pad_left))
        lines.append(f"│{pad_left}{top}{pad_right}│")
        # Record the content row's position in the combined canvas.
        step_row_index[(phase_num, step["index"])] = canvas_row_offset + len(lines)
        lines.append(f"│{pad_left}{middle}{pad_right}│")
        lines.append(f"│{pad_left}{bottom}{pad_right}│")

        # Intra-SOP loop annotation line below the step-box. Multiple loops
        # on the same source step join with " ; " so none are silently lost
        # (FXA-2218 R3 — same-source multi-loop fix).
        step_annotations = annotations.get(step["index"], [])
        if step_annotations:
            joined = " ; ".join(step_annotations)
            ann = _truncate_visual(joined, _PHASE_INNER - 4)
            ann_padded = _pad_visual(ann, _PHASE_INNER - 2)
            lines.append(f"│ {ann_padded} │")

        if has_next:
            lines.append(_render_arrow_line(inside_phase=True))

    # Phase bottom border.
    lines.append("└" + "─" * _PHASE_INNER + "┘")
    return lines


def _build_intra_sop_annotations(
    phase: PhaseDict, phase_num: int
) -> dict[int, list[str]]:
    """Return ``{from_step: [annotation_text, ...]}`` for every intra-SOP
    loop in this phase. Multiple loops from the same step accumulate into
    the list (FXA-2218 R3 — no silent data loss).
    """
    annotations: dict[int, list[str]] = {}
    for loop in phase.get("loops", []):
        if not isinstance(loop.to_step, int):
            continue
        cond = loop.condition.strip() if loop.condition else ""
        suffix = f"max {loop.max_iterations}"
        if cond:
            suffix += f" {cond}"
        text = f"🔁 → {phase_num}.{loop.to_step} {suffix}"
        annotations.setdefault(loop.from_step, []).append(text)
    return annotations


# ── Cross-SOP track allocation + overlay ─────────────────────────────────────


def _collect_cross_sop_loops(
    phases: list[PhaseDict],
) -> list[tuple[int, LoopSignature, int, int]]:
    """Return a list of ``(source_phase_num, loop, target_phase_num, target_step)``
    tuples for every cross-SOP loop whose target SOP is in the composed plan.

    Phase numbers are 1-based. When a target SOP appears more than once in
    the composition (e.g. plan ``A, B, A`` with a loop in ``B`` → ``A.*``),
    we bind to the **nearest preceding** occurrence — matching ``plan_cmd``'s
    D4 semantic that accepts the back-edge if ANY occurrence precedes the
    source (PR #59 Codex review P2 #6). Otherwise the renderer silently
    dropped valid edges bound to the trailing occurrence.

    Loops whose target is not in the composition at all are silently skipped
    — ``af plan`` D4 already raised a ClickException, so reaching here with
    an unresolved target is a defensive skip.
    """
    sop_id_to_phase_nums: dict[str, list[int]] = {}
    for idx, phase in enumerate(phases, start=1):
        sop_id_to_phase_nums.setdefault(phase["sop_id"], []).append(idx)

    result: list[tuple[int, LoopSignature, int, int]] = []
    for src_idx, phase in enumerate(phases, start=1):
        for loop in phase.get("loops", []):
            if not isinstance(loop.to_step, str):
                continue
            m = CROSS_SOP_REF.match(loop.to_step)
            if m is None:
                continue
            target_sop = f"{m.group('prefix')}-{m.group('acid')}"
            target_step = int(m.group("step"))
            target_positions = sop_id_to_phase_nums.get(target_sop, [])
            # Pick the nearest target occurrence that precedes the source
            # (max idx with idx < src_idx). If none precede, skip — either
            # the target isn't composed or it only appears after source.
            preceding = [p for p in target_positions if p < src_idx]
            if not preceding:
                continue
            target_phase_num = max(preceding)
            result.append((src_idx, loop, target_phase_num, target_step))
    return result


def _overwrite_at(line: str, visual_col: int, text: str) -> str:
    """Return ``line`` with ``text`` overlaid starting at VISUAL column
    ``visual_col``.

    Visual-cell aware — handles double-width glyphs (CJK, emoji) by walking
    the string and tracking visual offset rather than character index
    (PR #59 Codex review P2 #3).

    If a multi-cell glyph straddles the start or end of the overlay region,
    it is replaced with spaces for the cells that fall inside the overlay
    (the whole glyph is consumed — we can't split a CJK char in half).
    Pads with spaces if ``visual_col`` exceeds the line's visual width.
    """
    text_width = _visual_width(text)
    end_col = visual_col + text_width

    prefix_parts: list[str] = []
    visual = 0
    i = 0
    # Phase 1: consume chars that fit entirely before visual_col.
    while i < len(line):
        ch = line[i]
        cw = _visual_width(ch)
        if visual + cw > visual_col:
            break
        prefix_parts.append(ch)
        visual += cw
        i += 1

    # If we stopped because the next char would straddle visual_col, fill
    # the remaining cells with spaces and skip the straddling char entirely
    # (its right-side cells fall inside the overlay and are replaced).
    if visual < visual_col:
        prefix_parts.append(" " * (visual_col - visual))
        if i < len(line):
            # Consume the straddling char's full width (its right-side cells
            # are overwritten by `text`, its left-side cells already padded).
            visual += _visual_width(line[i])
            i += 1
        else:
            # visual_col is beyond line end — fully pad to visual_col.
            visual = visual_col
    else:
        # Prefix landed exactly at visual_col.
        visual = visual_col

    # Phase 2: skip chars whose cells fall inside [visual_col, end_col).
    # Straddling end: replace remainder cells with spaces in the suffix.
    while i < len(line):
        ch = line[i]
        cw = _visual_width(ch)
        if visual + cw > end_col:
            break
        visual += cw
        i += 1

    suffix_pad = ""
    if visual < end_col:
        # Straddling end — consume the straddling char, pad its right-side
        # cells (those BEYOND end_col) with spaces in the suffix.
        if i < len(line):
            cw = _visual_width(line[i])
            # Cells of this char that fall past end_col:
            past = (visual + cw) - end_col
            suffix_pad = " " * past
            i += 1

    suffix = suffix_pad + line[i:]
    return "".join(prefix_parts) + text + suffix


def _overlay_cross_sop_tracks(
    canvas: list[str],
    phases: list[PhaseDict],
    step_row_index: dict[tuple[int, int], int],
) -> list[str]:
    """Draw right-side vertical tracks for every cross-SOP back-edge loop.

    v1 constraint: only **one** cross-SOP loop renders as a track. Two or
    more loops fall back to inline annotation on the source step's content
    row (FXA-2218 R2 — safer than track overlap corruption; full interval-
    graph packing deferred to a follow-up PRP).
    """
    cross_loops = _collect_cross_sop_loops(phases)
    if not cross_loops:
        return canvas
    if len(cross_loops) > 1:
        return _overlay_inline_cross_sop(canvas, cross_loops, step_row_index)

    # Each loop reserves one track column at a fixed offset to the right of
    # the phase-box right edge. The "┐"/"┘" glyphs sit at ``track_col``; the
    # preceding "◄───" / "───" fan leftward into the gutter without overlapping
    # the phase-box border.
    base_col = _PHASE_BOX_WIDTH + _TRACK_GUTTER - 1  # column of the first "┐"

    # Extend every canvas line to the required width with trailing spaces.
    # Reserve enough for the longest arrow_out suffix we may write.
    max_suffix = max(
        (
            len(f" max {loop.max_iterations} if {loop.condition}")
            for _, loop, _, _ in cross_loops
        ),
        default=0,
    )
    max_col = base_col + len(cross_loops) * _TRACK_COL + max_suffix + 4
    canvas = [_pad_visual(line, max_col) for line in canvas]

    for track_i, (src_phase_num, loop, tgt_phase_num, tgt_step) in enumerate(
        cross_loops
    ):
        track_col = base_col + track_i * _TRACK_COL
        src_row = step_row_index.get((src_phase_num, loop.from_step))
        tgt_row = step_row_index.get((tgt_phase_num, tgt_step))
        if src_row is None or tgt_row is None:
            continue
        # Back-edge: source comes AFTER target in the canvas.
        if src_row <= tgt_row:
            continue

        # Arrow-in at target row: "◄───┐" with "┐" at track_col.
        arrow_in = "◄───┐"
        canvas[tgt_row] = _overwrite_at(
            canvas[tgt_row], track_col - (len(arrow_in) - 1), arrow_in
        )

        # Vertical pipe at all intermediate rows (skip the target row itself).
        for r in range(tgt_row + 1, src_row):
            canvas[r] = _overwrite_at(canvas[r], track_col, "│")

        # Arrow-out at source row: "───┘" with "┘" at track_col, then suffix.
        # Condition text is used verbatim (the SOP author phrases it
        # naturally — typically already contains "if ..."; we don't prefix
        # another "if" to avoid "if if fail"-style duplication).
        cond = loop.condition.strip() if loop.condition else ""
        suffix = f" max {loop.max_iterations}"
        if cond:
            suffix += f" {cond}"
        arrow_out = f"───┘{suffix}"
        canvas[src_row] = _overwrite_at(canvas[src_row], track_col - 3, arrow_out)

    return canvas


def _overlay_inline_cross_sop(
    canvas: list[str],
    cross_loops: list[tuple[int, LoopSignature, int, int]],
    step_row_index: dict[tuple[int, int], int],
) -> list[str]:
    """Fallback for multi-loop cross-SOP rendering: emit an inline annotation
    on each source step's content row instead of drawing tracks. Multiple
    loops originating at the same source step are joined with `` ; `` so
    none are silently lost (FXA-2218 R3).
    """
    # Accumulate annotations keyed by source row — a list per row to
    # preserve all loops that share a source step.
    annotations_by_row: dict[int, list[str]] = {}
    for _src_phase_num, loop, _tgt_phase_num, _tgt_step in cross_loops:
        src_row = step_row_index.get((_src_phase_num, loop.from_step))
        if src_row is None:
            continue
        cond = loop.condition.strip() if loop.condition else ""
        suffix = f"max {loop.max_iterations}"
        if cond:
            suffix += f" {cond}"
        annotations_by_row.setdefault(src_row, []).append(
            f"🔁 → {loop.to_step} {suffix}"
        )

    if not annotations_by_row:
        return canvas

    # Render each row's annotation list as a " ; "-joined string prefixed
    # by gutter spacing.
    rendered: dict[int, str] = {
        row: "  " + " ; ".join(texts) for row, texts in annotations_by_row.items()
    }
    max_ann_len = max(len(a) for a in rendered.values())
    target_width = _PHASE_BOX_WIDTH + _TRACK_GUTTER + max_ann_len
    canvas = [_pad_visual(line, target_width) for line in canvas]
    for row, annotation in rendered.items():
        canvas[row] = _overwrite_at(canvas[row], _PHASE_BOX_WIDTH, annotation)
    return canvas


# ── Public entry point ───────────────────────────────────────────────────────


def render_dag(
    phases: list[PhaseDict],
    provenance_map: dict[str, str] | None = None,
) -> str:
    """Render composed phases as a nested-layout ASCII DAG.

    ``provenance_map`` is accepted for parity with ``render_ascii`` but is
    not yet consumed by the nested layout; SOP provenance (``auto`` /
    ``always`` / ``explicit``) is expressible via the header but v1 keeps
    the header minimal. Future enhancement.
    """
    if not phases:
        return ""

    # Step 1 — pre-filter phases that actually have steps; this avoids the
    # orphan ``▼`` bug when a trailing phase has no Steps section (R2 fix).
    renderable_phases = [
        (idx + 1, phase) for idx, phase in enumerate(phases) if phase.get("steps")
    ]

    # Step 2 — render each renderable phase; record step row positions in the
    # final canvas. Intra-SOP loops are collected per-phase as inline
    # annotation lines (R2 fix — no more silent omission in nested layout).
    canvas: list[str] = []
    step_row_index: dict[tuple[int, int], int] = {}

    for i, (phase_num, phase) in enumerate(renderable_phases):
        intra_annotations = _build_intra_sop_annotations(phase, phase_num)
        phase_lines = _render_phase(
            phase_num=phase_num,
            phase=phase,
            step_row_index=step_row_index,
            canvas_row_offset=len(canvas),
            intra_sop_annotations=intra_annotations,
        )
        canvas.extend(phase_lines)
        # Inter-phase ``▼`` connector only between phases that actually render.
        if i < len(renderable_phases) - 1:
            canvas.append(_render_arrow_line(inside_phase=False))

    # Step 3 — overlay cross-SOP tracks on the right side of the canvas.
    canvas = _overlay_cross_sop_tracks(canvas, phases, step_row_index)

    return "\n".join(canvas)
