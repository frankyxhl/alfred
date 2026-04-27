"""Branch + convergence geometry primitive (FXA-2227 Phase 3).

Pure-function ASCII geometry for forward branches with edge labels and
auto-detected convergence. Used by both :mod:`fx_alfred.core.dag_graph`
(nested layout, wraps in phase boxes) and :mod:`fx_alfred.core.ascii_graph`
(flat layout, no wrapping). Mathematically pure: no I/O, no global state,
no imports from renderer modules (invariant I9).

API contract locked in CHG-2227 §"Phase 3 Primitive API Contract":
2 dataclasses (BranchRenderInput, BranchRenderOutput) + 4 functions
(render_branch, compute_column_offsets, render_label_row, render_join_row).

Geometry rules (per PRP-2225 §"Geometry algorithm sketch", PRP-2225:105-109):

- Column offsets: N siblings render at columns ``c_1..c_N`` chosen so each
  fits a sibling box of ``box_width`` cells with a 2-cell gutter between
  adjacent siblings. ``c_i = box_width // 2 + i * (box_width + GUTTER)``.
- Label row (between parent box bottom and sibling box top): each label
  centers at column ``c_i`` (above its `┬`). Max-width per label =
  ``min(c_i - prev_boundary, next_boundary - c_i) * 2 - 2`` cells via
  ``wcwidth``, where ``prev_boundary = (c_{i-1} + c_i) // 2`` for i>=2 else
  ``0``, and ``next_boundary = (c_i + c_{i+1}) // 2`` for i<N else
  ``box_total_width - 1``. Empty labels leave the slot blank; all-empty
  collapses the row.
- Join: when ``converges_to is not None``, draw a ``└──┼──┘`` row with
  ``┼`` at column ``(c_1 + c_N) // 2``. Otherwise tails dangle (no join).
"""

from __future__ import annotations

from dataclasses import dataclass

import wcwidth

from fx_alfred.core.workflow import BranchTarget

# Renderer hard cap per CHG-2227 §"Out of scope": more than 4-way branches
# fall back to linear-with-inline-labels in higher-level renderers.
_MAX_SIBLINGS = 4
# Inter-sibling gutter (cells between adjacent sibling box borders).
_GUTTER = 2
# Maximum label width in visible cells (per CHG-2227 wcwidth cap).
_MAX_LABEL_CELLS = 12


@dataclass(frozen=True)
class BranchRenderInput:
    """Input to ``render_branch``. See module docstring for geometry rules.

    Attributes:
        parent_step_text: Body text of the parent step (already truncated to
            ``box_width``). Rendered above the branch as a single-row box.
        siblings: Ordered tuple of ``BranchTarget`` (parent: int, branch: str,
            label: str). The primitive composes the display ID
            ``f"{parent}{branch}"`` internally.
        sibling_texts: Body text per sibling (positional with ``siblings``).
        converges_to: Integer step number that all siblings converge to, or
            ``None`` for terminal/dangling branches.
        converges_to_text: Body text for the convergence step (only used when
            ``converges_to is not None``).
        box_width: Per-step box width in visible cells.
    """

    parent_step_text: str
    siblings: tuple[BranchTarget, ...]
    sibling_texts: list[str]
    converges_to: int | None
    converges_to_text: str | None
    box_width: int


@dataclass(frozen=True)
class BranchRenderOutput:
    """Output from ``render_branch``. See module docstring for geometry rules.

    Attributes:
        lines: The full ASCII render, one string per terminal row. Per
            invariant I2, all lines have uniform visible-cell width.
        parent_anchor_row: Row index where the parent box's bottom edge sits.
        convergence_anchor_row: Row index where the convergence step's top
            edge sits, or ``None`` for dangling branches.
        step_anchor_rows: Mapping from sibling display ID (``"3a"``, ``"3b"``)
            to the row index of that sibling box's middle row (where the
            text body sits). Required by ``dag_graph.py`` to anchor
            right-side loop tracks against sibling rows.
    """

    lines: list[str]
    parent_anchor_row: int
    convergence_anchor_row: int | None
    step_anchor_rows: dict[str, int]


def compute_column_offsets(
    n_siblings: int, box_width: int, gutter: int = _GUTTER
) -> list[int]:
    """Return N strictly-increasing column offsets, one per sibling.

    Each offset is the *center column* of that sibling's box. Adjacent
    siblings are spaced ``box_width + gutter`` cells apart.
    """
    half = box_width // 2
    return [half + i * (box_width + gutter) for i in range(n_siblings)]


def _truncate_to_cells(s: str, max_cells: int) -> str:
    """Truncate ``s`` to at most ``max_cells`` visible cells (wcwidth)."""
    width = wcwidth.wcswidth(s)
    if width <= max_cells:
        return s
    # Walk character by character; stop when adding the next char would
    # exceed (max_cells - 1) (reserve 1 cell for the ellipsis).
    out_chars: list[str] = []
    used = 0
    for ch in s:
        cw = wcwidth.wcwidth(ch)
        if cw < 0:
            cw = 1
        if used + cw > max_cells - 1:
            break
        out_chars.append(ch)
        used += cw
    return "".join(out_chars) + "…"


def _pad_to_cells(s: str, total_cells: int) -> str:
    """Right-pad ``s`` with spaces to exactly ``total_cells`` visible cells."""
    used = wcwidth.wcswidth(s)
    if used >= total_cells:
        return s
    return s + " " * (total_cells - used)


def _box_lines(text: str, box_width: int) -> list[str]:
    """Return 3 lines forming a single-row box around ``text`` (wcwidth-aware).

    Inner text area = ``box_width - 2`` cells (2 borders).
    """
    inner = box_width - 2
    truncated = _truncate_to_cells(text, inner)
    padded = _pad_to_cells(truncated, inner)
    top = "┌" + "─" * inner + "┐"
    middle = "│" + padded + "│"
    bottom = "└" + "─" * inner + "┘"
    return [top, middle, bottom]


def _box_lines_with_tees(box_width: int, tee_offsets_local: list[int]) -> str:
    """Return the BOTTOM border of a box with `┬` at given local column offsets."""
    inner = box_width - 2
    chars = ["─"] * inner
    for off in tee_offsets_local:
        # Local offsets are within the inner area (0 .. inner-1).
        if 0 <= off < inner:
            chars[off] = "┬"
    return "└" + "".join(chars) + "┘"


def render_label_row(labels: list[str], offsets: list[int], box_width: int) -> str:
    """Render the label row: each label centers above its tee at offsets[i].

    Empty labels yield blank slots. Returned string padded to total render
    width via ``_pad_to_cells``.
    """
    n = len(labels)
    total_width = box_width + (n - 1) * (box_width + _GUTTER) if n > 0 else box_width
    # Build as a list of cells then join.
    row = list(" " * total_width)
    for i, label in enumerate(labels):
        if not label:
            continue
        # Compute boundaries for max-width-per-slot collision avoidance.
        prev_boundary = (offsets[i - 1] + offsets[i]) // 2 if i >= 1 else 0
        next_boundary = (
            (offsets[i] + offsets[i + 1]) // 2 if i < n - 1 else total_width - 1
        )
        max_w = min(offsets[i] - prev_boundary, next_boundary - offsets[i]) * 2 - 2
        max_w = min(max_w, _MAX_LABEL_CELLS)
        if max_w <= 0:
            continue
        truncated = _truncate_to_cells(label, max_w)
        truncated_w = wcwidth.wcswidth(truncated)
        # Center the truncated label at column offsets[i].
        start = offsets[i] - (truncated_w - 1) // 2
        # Place character-by-character, advancing by cell width.
        col = start
        for ch in truncated:
            cw = wcwidth.wcwidth(ch)
            if cw < 0:
                cw = 1
            if 0 <= col < total_width:
                row[col] = ch
                # Wide chars occupy 2 cells; blank the next cell.
                if cw == 2 and col + 1 < total_width:
                    row[col + 1] = ""
            col += cw
    # Drop empty placeholders (used for wide-char trailing cells).
    return "".join(c for c in row if c != "")


def render_join_row(offsets: list[int]) -> str:
    """Render the convergence join row: `└──┼──┘` shape spanning offsets.

    `┼` sits at column ``(offsets[0] + offsets[-1]) // 2``. Returns the
    join span (without surrounding padding); caller positions it within
    the full render width.
    """
    if not offsets:
        return ""
    total_width = offsets[-1] - offsets[0] + 1
    join_col_global = (offsets[0] + offsets[-1]) // 2
    join_col_local = join_col_global - offsets[0]
    chars = ["─"] * total_width
    chars[0] = "└"
    chars[-1] = "┘"
    chars[join_col_local] = "┼"
    return "".join(chars)


def render_branch(input: BranchRenderInput) -> BranchRenderOutput:
    """Render a forward branch with optional auto-detected convergence.

    See module docstring + invariants I1–I11 for the contract. Raises
    ``ValueError`` if ``len(input.siblings) > 4`` (invariant I10).
    """
    n = len(input.siblings)
    if n > _MAX_SIBLINGS:
        raise ValueError(f"branch_geometry hard cap is 4 siblings; got {n}")
    if n == 0:
        raise ValueError("branch_geometry requires >= 2 siblings")

    box_width = input.box_width
    offsets = compute_column_offsets(n_siblings=n, box_width=box_width)
    total_width = offsets[-1] + (box_width - box_width // 2)  # right edge

    lines: list[str] = []

    # Row 0: parent box bottom border (with `┬` at each c_i). Per invariant
    # I8, `parent_anchor_row == 0` — the caller is responsible for rendering
    # the parent step's body/top-border above this output. The primitive
    # only owns the geometry from the parent's bottom edge downward, so
    # both `dag_graph` (nested phase-box wrapping) and `ascii_graph` (no
    # wrapping) can drop the primitive's lines under their own parent rows.
    parent_box = _box_lines(input.parent_step_text, total_width)  # noqa: F841 — kept for parity
    bottom_chars = list("└" + "─" * (total_width - 2) + "┘")
    for off in offsets:
        if 0 < off < total_width - 1:
            bottom_chars[off] = "┬"
    lines.append("".join(bottom_chars))
    parent_anchor_row = 0

    # Optional label row.
    labels = [t.label for t in input.siblings]
    if any(label for label in labels):
        lines.append(render_label_row(labels, offsets, box_width))

    # Arrow row: `▼` at each c_i, padded blanks elsewhere.
    arrow_row = list(" " * total_width)
    for off in offsets:
        if 0 <= off < total_width:
            arrow_row[off] = "▼"
    lines.append("".join(arrow_row))

    # Sibling boxes — three rows each, side-by-side.
    sibling_box_top = list(" " * total_width)
    sibling_box_middle = list(" " * total_width)
    sibling_box_bottom = list(" " * total_width)
    step_anchor_rows: dict[str, int] = {}
    middle_row_idx = len(lines) + 1  # row where text body sits
    for i, (target, body) in enumerate(zip(input.siblings, input.sibling_texts)):
        bw = box_width
        b = _box_lines(body, bw)
        # Place the box centered at offsets[i].
        start = offsets[i] - bw // 2
        for j, ch in enumerate(b[0]):
            if 0 <= start + j < total_width:
                sibling_box_top[start + j] = ch
        for j, ch in enumerate(b[1]):
            if 0 <= start + j < total_width:
                sibling_box_middle[start + j] = ch
        for j, ch in enumerate(b[2]):
            if 0 <= start + j < total_width:
                sibling_box_bottom[start + j] = ch
        step_anchor_rows[f"{target.parent}{target.branch}"] = middle_row_idx
    lines.append("".join(sibling_box_top))
    lines.append("".join(sibling_box_middle))
    lines.append("".join(sibling_box_bottom))

    convergence_anchor_row: int | None = None
    if input.converges_to is not None:
        # Join row spanning offsets[0] to offsets[-1].
        join_str = render_join_row(offsets)
        join_row_full = list(" " * total_width)
        for j, ch in enumerate(join_str):
            join_row_full[offsets[0] + j] = ch
        lines.append("".join(join_row_full))

        # Single arrow row from `┼` down to convergence step.
        join_col = (offsets[0] + offsets[-1]) // 2
        arrow_row2 = list(" " * total_width)
        if 0 <= join_col < total_width:
            arrow_row2[join_col] = "▼"
        lines.append("".join(arrow_row2))

        # Convergence box centered at join_col.
        conv_text = input.converges_to_text or ""
        conv_box = _box_lines(conv_text, box_width)
        start = join_col - box_width // 2
        conv_top = list(" " * total_width)
        conv_mid = list(" " * total_width)
        conv_bot = list(" " * total_width)
        for j, ch in enumerate(conv_box[0]):
            if 0 <= start + j < total_width:
                conv_top[start + j] = ch
        for j, ch in enumerate(conv_box[1]):
            if 0 <= start + j < total_width:
                conv_mid[start + j] = ch
        for j, ch in enumerate(conv_box[2]):
            if 0 <= start + j < total_width:
                conv_bot[start + j] = ch
        lines.append("".join(conv_top))
        convergence_anchor_row = len(lines) - 1
        lines.append("".join(conv_mid))
        lines.append("".join(conv_bot))

    # Pad every line to uniform total_width via wcwidth (invariant I2).
    lines = [_pad_to_cells(line, total_width) for line in lines]

    return BranchRenderOutput(
        lines=lines,
        parent_anchor_row=parent_anchor_row,
        convergence_anchor_row=convergence_anchor_row,
        step_anchor_rows=step_anchor_rows,
    )
