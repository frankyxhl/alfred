"""Nested-layout ASCII DAG renderer for `af plan --graph` (FXA-2218).

Default under ``--graph-layout=nested`` (flag added in Commit 7). Emits an
ASCII DAG: each SOP is an outer phase-box containing inner step-boxes with
``▼`` connectors; intra-SOP loops render as right-side vertical tracks
inside the phase box; cross-SOP loops render as right-side vertical tracks
that extend **outside** the phase boxes, in a dedicated track column per
loop, spanning from the target step's box in an earlier phase down to the
source step's box in a later phase.

Reuses only the visual-width / padding / truncation primitives from
``core.ascii_graph``; all layout logic (nested boxes, cross-SOP track
routing, track column allocation) is net-new.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fx_alfred.core.ascii_graph import _pad_visual, _truncate_visual
from fx_alfred.core.workflow import CROSS_SOP_REF, LoopSignature

if TYPE_CHECKING:
    from fx_alfred.core.phases import PhaseDict

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


def _render_phase(
    phase_num: int,
    phase: PhaseDict,
    step_row_index: dict[tuple[int, int], int],
    canvas_row_offset: int,
    intra_sop_annotations: dict[int, str] | None = None,
) -> list[str]:
    """Render a single phase as a list of lines (each exactly ``_PHASE_BOX_WIDTH``
    cells wide). Populates ``step_row_index[(phase_num, step_index)]`` with the
    row index (in the combined canvas) of each step's content row.

    ``intra_sop_annotations`` maps 1-based step index to an annotation string
    (e.g. ``"🔁 → 2.1 max 3 if fail"``) emitted on a dedicated annotation line
    immediately below the step-box bottom. Cross-SOP loops inline-fall-back
    is handled separately in ``_overlay_inline_cross_sop`` (FXA-2218 R2).
    """
    annotations = intra_sop_annotations or {}
    lines: list[str] = []
    sop_id = phase["sop_id"]
    steps = phase["steps"]

    # Header line: "Phase N: SOP-ID"
    header_text = f"Phase {phase_num}: {sop_id}"
    header = _truncate_visual(header_text, _PHASE_INNER - 2)
    header_padded = _pad_visual(header, _PHASE_INNER - 2)
    lines.append("┌" + "─" * _PHASE_INNER + "┐")
    lines.append(f"│ {header_padded} │")
    # Blank line under header.
    lines.append("│" + " " * _PHASE_INNER + "│")

    step_count = len(steps)
    for s_idx, step in enumerate(steps):
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

        # Intra-SOP loop annotation line below the step-box (if any).
        annotation = annotations.get(step["index"])
        if annotation is not None:
            ann = _truncate_visual(annotation, _PHASE_INNER - 4)
            ann_padded = _pad_visual(ann, _PHASE_INNER - 2)
            lines.append(f"│ {ann_padded} │")

        if has_next:
            lines.append(_render_arrow_line(inside_phase=True))

    # Phase bottom border.
    lines.append("└" + "─" * _PHASE_INNER + "┘")
    return lines


def _build_intra_sop_annotations(phase: PhaseDict, phase_num: int) -> dict[int, str]:
    """Return ``{from_step: annotation_text}`` for every intra-SOP loop in
    this phase. Used by ``render_dag`` to show intra-SOP loops as inline
    annotation lines rather than vertical tracks inside the phase-box
    (FXA-2218 R2 — Codex-blocked silent omission fix).
    """
    annotations: dict[int, str] = {}
    for loop in phase.get("loops", []):
        if not isinstance(loop.to_step, int):
            continue
        cond = loop.condition.strip() if loop.condition else ""
        suffix = f"max {loop.max_iterations}"
        if cond:
            suffix += f" {cond}"
        annotations[loop.from_step] = f"🔁 → {phase_num}.{loop.to_step} {suffix}"
    return annotations


# ── Cross-SOP track allocation + overlay ─────────────────────────────────────


def _collect_cross_sop_loops(
    phases: list[PhaseDict],
) -> list[tuple[int, LoopSignature, int, int]]:
    """Return a list of ``(source_phase_num, loop, target_phase_num, target_step)``
    tuples for every cross-SOP loop whose target SOP is in the composed plan.

    Phase numbers are 1-based. Loops whose target is not in the composition are
    silently skipped — ``af plan`` raised a ClickException upstream (D4) so
    reaching here with an unresolved target would be a bug; the filter here is
    defensive.
    """
    sop_id_to_phase_num: dict[str, int] = {
        phase["sop_id"]: idx + 1 for idx, phase in enumerate(phases)
    }
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
            target_phase_num = sop_id_to_phase_num.get(target_sop)
            if target_phase_num is None:
                continue
            result.append((src_idx, loop, target_phase_num, target_step))
    return result


def _overwrite_at(line: str, col: int, text: str) -> str:
    """Return ``line`` with ``text`` overlaid starting at column ``col``
    (ASCII-width; caller ensures ``line`` has no double-width glyphs in the
    overwrite span).

    Pads with spaces if ``col`` exceeds current length.
    """
    if col > len(line):
        line = line + " " * (col - len(line))
    prefix = line[:col]
    suffix = line[col + len(text) :]
    return prefix + text + suffix


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
    on each source step's content row instead of drawing tracks. The
    annotation appears to the right of the phase-box, never crossing any
    other loop's rendering.
    """
    # Compute max line width so every annotation fits.
    annotations: dict[int, str] = {}
    for _src_phase_num, loop, _tgt_phase_num, _tgt_step in cross_loops:
        src_row = step_row_index.get((_src_phase_num, loop.from_step))
        if src_row is None:
            continue
        cond = loop.condition.strip() if loop.condition else ""
        suffix = f"max {loop.max_iterations}"
        if cond:
            suffix += f" {cond}"
        annotations[src_row] = f"  🔁 → {loop.to_step} {suffix}"

    if not annotations:
        return canvas

    max_ann_len = max(len(a) for a in annotations.values())
    target_width = _PHASE_BOX_WIDTH + _TRACK_GUTTER + max_ann_len
    canvas = [_pad_visual(line, target_width) for line in canvas]
    for row, annotation in annotations.items():
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
