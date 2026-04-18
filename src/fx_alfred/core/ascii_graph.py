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


def _visual_width(s: str) -> int:
    """Return visual cell width (1 or 2 per char).

    Handles:
    - CJK characters (2 cells each)
    - Emoji (2 cells each)
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
            or 0x1F000 <= code <= 0x1FFFF  # Emoji blocks (SMP)
            or 0x20000 <= code <= 0x2FFFD  # CJK ext B-F (SIP)
            or 0x30000 <= code <= 0x3FFFD  # CJK ext G (TIP)
        ):
            width += 2
        elif (
            0x0300 <= code <= 0x036F  # Combining diacritical marks
            or 0x200B <= code <= 0x200F  # ZWJ, etc.
            or code == 0xFE0F  # Variation selector
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

    # Phase 1: build inner lines per phase (raw text, no box chars)
    all_phase_lines: list[list[str]] = []

    for phase_idx, phase in enumerate(phases, 1):
        sop_id = phase.get("sop_id", "UNKNOWN")
        prov = phase.get("provenance")
        steps = phase.get("steps", [])
        loops = phase.get("loops", [])

        loop_to_map = {_loop_attr(lp, "to_step"): lp for lp in loops}
        loop_from_map = {_loop_attr(lp, "from_step"): lp for lp in loops}

        # Header line
        header = f"Phase {phase_idx}: {sop_id}"
        if prov:
            header += f" ({prov})"

        # Step lines
        step_lines: list[str] = []
        for step in steps:
            idx = step["index"]
            txt = step["text"]
            gate = step.get("gate", False)

            prefix = f"[{phase_idx}.{idx}] "
            if gate:
                prefix += "⚠️ "
            base = prefix + txt

            # Loop annotations
            if idx in loop_to_map:
                base = base + " ◄──────┐"
            if idx in loop_from_map:
                lp = loop_from_map[idx]
                annot = f" ─────┘ max {_loop_attr(lp, 'max_iterations')}"
                cond = _loop_attr(lp, "condition", "") or ""
                if cond:
                    with_cond = annot + f" if {cond}"
                    base_with_cond = base + with_cond
                    if _visual_width(base_with_cond) <= INNER_MAX:
                        base = base_with_cond
                    else:
                        base = base + annot
                else:
                    base = base + annot

            step_lines.append(base)

        # Truncate any line exceeding INNER_MAX
        def _trunc_if_needed(line: str) -> str:
            if _visual_width(line) > INNER_MAX:
                return _truncate_visual(line, INNER_MAX)
            return line

        header = _trunc_if_needed(header)
        step_lines = [_trunc_if_needed(sl) for sl in step_lines]

        all_phase_lines.append([header] + step_lines)

    # Phase 2: determine global box width
    max_inner = INNER_MIN
    for lines in all_phase_lines:
        for ln in lines:
            max_inner = max(max_inner, _visual_width(ln))
    inner_width = min(max_inner, INNER_MAX)
    box_width = inner_width + 4  # '│ ' + inner + ' │'
    center = box_width // 2

    # Phase 3: emit boxes
    out_lines: list[str] = []
    n_phases = len(all_phase_lines)

    for p_idx, lines in enumerate(all_phase_lines):
        # Top border
        out_lines.append("┌" + "─" * (box_width - 2) + "┐")

        # Content lines
        for ln in lines:
            out_lines.append("│ " + _pad_visual(ln, inner_width) + " │")

        # Bottom border
        if p_idx == n_phases - 1:
            # Last phase: plain bottom border
            out_lines.append("└" + "─" * (box_width - 2) + "┘")
        else:
            # Non-last phase: bottom border with ┬ at center
            left_dashes = center - 1
            right_dashes = box_width - 2 - left_dashes
            out_lines.append("└" + "─" * left_dashes + "┬" + "─" * right_dashes + "┘")
            # ▼ line (no separate │ line)
            out_lines.append(" " * center + "▼")

    return "\n".join(out_lines) + "\n"
