"""ASCII box-and-arrow graph renderer for terminal output.

Pure stdlib. No external dependencies. Renders phase composition as
terminal-friendly ASCII boxes with inter-phase arrows and intra-SOP loop
annotations.

FXA-2206 C1.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fx_alfred.core.phases import PhaseDict

# Minimum inner content width (fits in 50-wide box: '│ ' + 46 + ' │' = 50)
INNER_MIN = 46

# Maximum inner content width (fits in 80-wide terminal: 76 + 4 = 80)
INNER_MAX = 76

# Track reservation for loop annotations (vertical track)
# " ◄──────┐" = 9 chars, " ─────┘ max N" = ~13 chars
TRACK_RESERVE = 14


def _visual_width(s: str) -> int:
    """Return visual cell width (1 or 2 per char).

    Handles:
    - CJK characters (2 cells each)
    - Emoji (2 cells each)
    - Misc Symbols + Dingbats (⚠️, 🔁, etc.) — 2 cells each
    - Combining marks (0 cells)
    - ASCII (1 cell each)
    """
    width = 0
    for ch in s:
        code = ord(ch)
        # Wide chars: CJK unified ideographs, emoji, common double-width zones
        if (
            0x1100 <= code <= 0x115F  # Hangul Jamo init
            or 0x2E80 <= code <= 0x303E  # CJK radicals, Kangxi
            or 0x3041 <= code <= 0x33FF  # Hiragana, Katakana, CJK compat
            or 0x3400 <= code <= 0x4DBF  # CJK ext A
            or 0x4E00 <= code <= 0x9FFF  # CJK unified
            or 0xA000 <= code <= 0xA4CF  # Yi
            or 0xAC00 <= code <= 0xD7A3  # Hangul syllables
            or 0xF900 <= code <= 0xFAFF  # CJK compat ideographs
            or 0xFE30 <= code <= 0xFE4F  # CJK compat forms
            or 0xFF00 <= code <= 0xFF60  # Fullwidth forms
            or 0xFFE0 <= code <= 0xFFE6  # Fullwidth signs
            or 0x2600 <= code <= 0x27BF  # Misc Symbols + Dingbats (⚠️, 🔁, etc.)
            or 0x1F000 <= code <= 0x1FFFF  # Emoji blocks (SMP)
            or 0x20000 <= code <= 0x2FFFD  # CJK ext B-F (SIP)
            or 0x30000 <= code <= 0x3FFFD  # CJK ext G (TIP)
        ):
            width += 2
        elif (
            0x0300 <= code <= 0x036F  # Combining diacritical marks
            or 0x200B <= code <= 0x200F  # ZWJ, etc.
            or 0xFE00 <= code <= 0xFE0F  # Variation selectors
        ):
            # Combining marks, ZWJ, variation selectors — zero width
            pass
        else:
            width += 1
    return width


def _truncate_visual(s: str, max_visual: int) -> str:
    """Truncate string to max_visual cells, appending '...' if truncated.

    Respects char boundaries (never splits a wide char mid-character).
    """
    if _visual_width(s) <= max_visual:
        return s
    # Need to leave room for '...'
    budget = max_visual - 3
    if budget <= 0:
        return "." * max_visual
    out = []
    w = 0
    for ch in s:
        cw = _visual_width(ch)
        if w + cw > budget:
            break
        out.append(ch)
        w += cw
    return "".join(out) + "..."


def _pad_visual(s: str, target_visual: int) -> str:
    """Right-pad string with ASCII spaces to reach target visual width."""
    cur = _visual_width(s)
    if cur >= target_visual:
        return s
    return s + " " * (target_visual - cur)


def _loop_attr(loop: object, name: str, default=None):
    """Read a loop attribute from either a TypedDict (dict) or a dataclass.

    PhaseDict loops may be either dict-like (per the TypedDict contract) or
    LoopSignature dataclasses (as produced by workflow.parse_workflow_loops).
    We accept both so callers don't need to normalise.
    """
    if isinstance(loop, dict):
        return loop.get(name, default)
    return getattr(loop, name, default)


def _build_step_base_text(phase_num: int, step: dict) -> str:
    """Build step base text WITHOUT loop annotations.

    Includes: [N.M] prefix, gate marker, step text.
    """
    idx = step["index"]
    txt = step["text"]
    gate = step.get("gate", False)

    prefix = f"[{phase_num}.{idx}] "
    if gate:
        prefix += "⚠️ "
    return prefix + txt


def _apply_loop_track(
    lines: list[str],
    loops: list,
    phase_num: int,
    inner_width: int,
    step_indices: list[int],
) -> list[str]:
    """Apply vertical loop track to step lines.

    For the first loop in the phase:
    - Determine track column reservation from the right edge of the box.
    - Shrink step text (with ellipsis) as needed to free the track column.
    - On to_step: overlay ``" ◄──────┐"`` at the track column.
    - On intermediate steps: overlay ``"│"`` aligned under ``┐``.
    - On from_step: overlay ``" ─────┘ max N"`` (or include condition when it
      fits) at the track column.

    When the box is too narrow to reserve a full track, fall back to an inline
    annotation ``" → back to P.K (max N)"`` appended to the from_step line
    (truncating existing text if necessary). Additional loops in the phase
    are rendered inline on their own from_step lines so no loop is silently
    dropped.
    """
    if not loops:
        return lines

    result_lines = list(lines)

    # Render every loop: first loop gets the vertical track; extras go inline.
    for loop_idx, loop in enumerate(loops):
        to_step = _loop_attr(loop, "to_step")
        from_step = _loop_attr(loop, "from_step")
        max_iter = _loop_attr(loop, "max_iterations")
        condition = _loop_attr(loop, "condition", "") or ""

        # Find step line indices (lines[0] is header, steps start at lines[1]).
        to_line_idx = None
        from_line_idx = None
        for i, step_idx in enumerate(step_indices):
            if step_idx == to_step:
                to_line_idx = i + 1  # +1 for header line
            if step_idx == from_step:
                from_line_idx = i + 1

        if to_line_idx is None or from_line_idx is None:
            continue

        rendered_vertical = False
        if loop_idx == 0:
            rendered_vertical = _render_vertical_track(
                result_lines,
                inner_width,
                to_line_idx,
                from_line_idx,
                to_step,
                from_step,
                max_iter,
                condition,
                step_indices,
            )

        if not rendered_vertical:
            _render_inline_loop(
                result_lines,
                inner_width,
                from_line_idx,
                phase_num,
                to_step,
                max_iter,
                condition,
            )

    return result_lines


def _render_vertical_track(
    lines: list[str],
    inner_width: int,
    to_line_idx: int,
    from_line_idx: int,
    to_step: int,
    from_step: int,
    max_iter: object,
    condition: str,
    step_indices: list[int],
) -> bool:
    """Mutate ``lines`` in place to draw a vertical loop track.

    Returns True when the track was rendered, False when the box is too
    narrow and the caller should fall back to an inline annotation.
    """
    # Track suffix shapes ── match the CHG §Step 4 authoritative sample.
    # to_suffix:  " ◄──────┐"  (leading space, ◄, 6 hyphens, ┐) = 9 cells.
    # from_suffix: " ──────┘ max N"  (leading space, 7 hyphens, ┘, " max N")
    #              where ┘ column is aligned exactly under ┐.
    to_suffix = " ◄──────┐"
    corner_offset = _visual_width(to_suffix) - 1  # column of ┐ within to_suffix
    # Build the from_step prefix so ┘ aligns with ┐: space + N hyphens + ┘
    # such that total width (including leading space) == corner_offset + 1.
    # Leading space takes 1 cell, so hyphen count = corner_offset - 1.
    from_prefix = " " + "─" * (corner_offset - 1) + "┘"
    base_from_suffix = f"{from_prefix} max {max_iter}"
    cond_from_suffix = (
        f"{from_prefix} max {max_iter} if {condition}"
        if condition
        else base_from_suffix
    )

    # Reserve the widest suffix we might render so both to_step and from_step
    # fit. When a condition is supplied we prefer to keep space for it, but
    # fall back to the base suffix if the box is too narrow.
    to_reserve = _visual_width(to_suffix)
    base_reserve = max(to_reserve, _visual_width(base_from_suffix))
    cond_reserve = max(to_reserve, _visual_width(cond_from_suffix))

    use_condition = bool(condition) and inner_width - cond_reserve >= 4
    reserve = cond_reserve if use_condition else base_reserve

    # Need room for at least 3 cells of content before the track (for "...").
    if inner_width - reserve < 4:
        return False

    track_col = inner_width - reserve

    # to_step row: shrink base to track_col, pad, append the arrow-in marker.
    base = _shrink_for_track(lines[to_line_idx], track_col)
    lines[to_line_idx] = _pad_visual(base, track_col) + to_suffix

    # Intermediate rows: place `│` under the ┐ glyph.
    pipe_col = track_col + corner_offset
    for step_idx in step_indices:
        if to_step < step_idx < from_step:
            pos_in_steps = step_indices.index(step_idx)
            line_idx = pos_in_steps + 1  # +1 for header
            if line_idx >= len(lines):
                continue
            mid = _shrink_for_track(lines[line_idx], pipe_col)
            lines[line_idx] = _pad_visual(mid, pipe_col) + "│"

    # from_step row: append the arrow-out marker.
    base = _shrink_for_track(lines[from_line_idx], track_col)
    padded = _pad_visual(base, track_col)
    suffix = cond_from_suffix if use_condition else base_from_suffix
    lines[from_line_idx] = padded + suffix
    return True


def _shrink_for_track(line: str, limit: int) -> str:
    """Return ``line`` truncated so its visual width fits within ``limit``.

    Uses :func:`_truncate_visual` (ellipsis-aware) so meaningful content is
    preserved rather than sliced mid-character.
    """
    if _visual_width(line) <= limit:
        return line
    return _truncate_visual(line, limit)


def _render_inline_loop(
    lines: list[str],
    inner_width: int,
    from_line_idx: int,
    phase_num: int,
    to_step: int,
    max_iter: object,
    condition: str,
) -> None:
    """Append an inline loop annotation to from_step line (fallback path).

    Mutates ``lines`` in place so the loop is never silently dropped.
    """
    if from_line_idx >= len(lines):
        return
    base_inline = f" → back to {phase_num}.{to_step} (max {max_iter})"
    cond_inline = f"{base_inline} if {condition}" if condition else base_inline

    current = lines[from_line_idx]
    # Try the richer form first; otherwise fall back to the compact form.
    for suffix in (cond_inline, base_inline):
        combined = current + suffix
        if _visual_width(combined) <= inner_width:
            lines[from_line_idx] = combined
            return
        # If suffix alone exceeds inner_width, shrink base and append.
        shrink_target = inner_width - _visual_width(suffix)
        if shrink_target >= 4:
            shrunk = _shrink_for_track(current, shrink_target)
            lines[from_line_idx] = _pad_visual(shrunk, shrink_target) + suffix
            return
    # Last resort: drop condition, overwrite entire line with marker.
    marker = f"→ {phase_num}.{to_step} max {max_iter}"
    if _visual_width(marker) <= inner_width:
        lines[from_line_idx] = marker


def render_ascii(phases: list[PhaseDict]) -> str:
    """Render phases as ASCII box-and-arrow diagram.

    Args:
        phases: List of PhaseDict objects, each containing sop_id, steps, loops,
                and optionally provenance.

    Returns:
        String containing the ASCII diagram.
    """
    if not phases:
        return "(no phases)\n"

    # Phase 1: build inner lines per phase (base text WITHOUT loop annotations)
    # Structure: list of (lines, loops, step_indices) tuples
    all_phase_data: list[tuple[list[str], list, list[int]]] = []

    for phase_idx, phase in enumerate(phases, 1):
        sop_id = phase.get("sop_id", "UNKNOWN")
        prov = phase.get("provenance")
        steps = phase.get("steps", [])
        loops = phase.get("loops", [])

        # Header line
        header = f"Phase {phase_idx}: {sop_id}"
        if prov:
            header += f" ({prov})"

        # Build step base texts WITHOUT loop annotations
        step_lines: list[str] = []
        step_indices: list[int] = []
        for step in steps:
            step_indices.append(step["index"])
            base = _build_step_base_text(phase_idx, step)
            step_lines.append(base)

        all_phase_data.append(([header] + step_lines, loops, step_indices))

    # Phase 2: determine global box width (before loop track)
    max_inner = INNER_MIN
    for lines, _, _ in all_phase_data:
        for ln in lines:
            max_inner = max(max_inner, _visual_width(ln))

    # Reserve space for loop track if any phase has loops
    has_loops = any(loops for _, loops, _ in all_phase_data)
    if has_loops:
        max_inner = max(max_inner, INNER_MIN + TRACK_RESERVE)

    inner_width = min(max_inner, INNER_MAX)
    box_width = inner_width + 4  # '│ ' + inner + ' │'
    center = box_width // 2

    # Phase 3: apply loop tracks and emit boxes
    out_lines: list[str] = []
    n_phases = len(all_phase_data)

    for p_idx, (lines, loops, step_indices) in enumerate(all_phase_data):
        # Step A: truncate base lines to inner_width (ellipsis-aware).
        truncated_lines = [
            _truncate_visual(ln, inner_width) if _visual_width(ln) > inner_width else ln
            for ln in lines
        ]

        # Step B: layer the loop track on top. The track renderer owns
        # further shrinkage of base text so the track column stays clear.
        lines_with_track = _apply_loop_track(
            truncated_lines, loops, p_idx + 1, inner_width, step_indices
        )

        # Step C: pad every line to exactly inner_width for box alignment.
        padded_lines = [_pad_visual(ln, inner_width) for ln in lines_with_track]

        # Top border
        out_lines.append("┌" + "─" * (box_width - 2) + "┐")

        # Content lines
        for ln in padded_lines:
            out_lines.append("│ " + ln + " │")

        # Bottom border
        if p_idx == n_phases - 1:
            # Last phase: plain bottom border
            out_lines.append("└" + "─" * (box_width - 2) + "┘")
        else:
            # Non-last phase: bottom border with ┬ at center
            left_dashes = center - 1
            right_dashes = box_width - 3 - left_dashes
            out_lines.append("└" + "─" * left_dashes + "┬" + "─" * right_dashes + "┘")
            # ▼ line (no separate │ line)
            out_lines.append(" " * center + "▼")

    return "\n".join(out_lines) + "\n"
