"""Tests for FXA-2227 Phase 5 — ascii_graph.py flat-layout integration with
branch_geometry primitive.

Per CHG-2227 §"Phase 5 — `ascii_graph.py` flat integration":
- Detect branch groups (same pattern as Phase 4) via discover_branch_groups.
- Call render_branch(...) directly WITHOUT phase-box wrapping (flat layout).
- No step_idx/step_indices widening — keep list[int].
- Existing tests/test_ascii_graph.py tests stay green (non-branchy phases
  render byte-identical to pre-Phase-5).
"""

from __future__ import annotations

import wcwidth

from fx_alfred.core.ascii_graph import render_ascii
from fx_alfred.core.workflow import BranchSignature, BranchTarget, LoopSignature


def _step(
    index: int,
    text: str,
    gate: bool = False,
    sub_branch: str | None = None,
) -> dict:
    s: dict = {"index": index, "text": text, "gate": gate}
    if sub_branch is not None:
        s["sub_branch"] = sub_branch
    return s


def _phase(
    sop_id: str,
    steps: list[dict],
    loops: list[LoopSignature] | None = None,
    branches: list[BranchSignature] | None = None,
) -> dict:
    p: dict = {"sop_id": sop_id, "steps": steps, "loops": loops or []}
    if branches is not None:
        p["branches"] = branches
    return p


def test_flat_3way_with_convergence() -> None:
    """3-way branch with convergence renders without inner phase-box wrapping.

    SOP shape:
      1. Setup
      2. Decision    <- parent (branches.from = 2)
      3a. pass       <- sibling
      3b. fail       <- sibling
      3c. esc        <- sibling
      4. Continue    <- convergence (auto-detected)
    """
    branches = [
        BranchSignature(
            from_step=2,
            to=(
                BranchTarget(parent=3, branch="a", label="pass"),
                BranchTarget(parent=3, branch="b", label="fail"),
                BranchTarget(parent=3, branch="c", label="esc"),
            ),
        )
    ]
    phases = [
        _phase(
            "TST-9001",
            [
                _step(1, "Setup"),
                _step(2, "Decision"),
                _step(3, "pass-body", sub_branch="a"),
                _step(3, "fail-body", sub_branch="b"),
                _step(3, "esc-body", sub_branch="c"),
                _step(4, "Continue"),
            ],
            branches=branches,
        )
    ]
    out = render_ascii(phases)
    # Branch tees and convergence join present.
    assert "┬" in out, f"expected branch tees in output:\n{out}"
    assert "pass" in out
    assert "fail" in out
    assert "esc" in out
    assert "┼" in out, f"expected convergence join in output:\n{out}"
    # Sibling body texts present.
    assert "pass-body" in out or "3a" in out, (
        f"expected sibling 3a content in output:\n{out}"
    )
    # Single outer box still wraps everything (flat layout: one box for the phase).
    assert "Phase 1: TST-9001" in out
    # No intermediate phase-box borders inside the branch geometry — all branch
    # geometry sits INSIDE the outer │...│ borders (flat, not nested step-boxes).
    lines = out.split("\n")
    # All content lines between the top ┌ and bottom └ must use │ ... │ form.
    top_row = next(i for i, line in enumerate(lines) if line.startswith("┌"))
    bottom_row = next(i for i, line in enumerate(lines) if line.startswith("└"))
    content_lines = lines[top_row + 1 : bottom_row]
    # No content line should start a new ┌ border (that would be an inner box).
    inner_box_openers = [ln for ln in content_lines if ln.startswith("┌")]
    assert not inner_box_openers, (
        "unexpected inner phase-box borders inside flat branch geometry:\n"
        + "\n".join(inner_box_openers)
    )


def test_flat_legacy_unchanged() -> None:
    """Phase WITHOUT branches: renders with no ┬ or ┼ markers (no regression)."""
    phases = [
        _phase(
            "COR-1500",
            [_step(1, "Red"), _step(2, "Green"), _step(3, "Refactor")],
        ),
    ]
    out = render_ascii(phases)
    assert "Phase 1: COR-1500" in out
    assert "[1.1]" in out
    assert "[1.2]" in out
    assert "[1.3]" in out
    # No branch markers should appear.
    assert "┬" not in out, f"unexpected branch tee in legacy output:\n{out}"
    assert "┼" not in out, f"unexpected convergence join in legacy output:\n{out}"


def test_flat_dangling_branch() -> None:
    """Terminal branch (no convergence): ┬ present, ┼ absent."""
    branches = [
        BranchSignature(
            from_step=2,
            to=(
                BranchTarget(parent=3, branch="a", label="end-a"),
                BranchTarget(parent=3, branch="b", label="end-b"),
            ),
        )
    ]
    phases = [
        _phase(
            "TST-9002",
            [
                _step(1, "Setup"),
                _step(2, "Decision"),
                _step(3, "Final A", sub_branch="a"),
                _step(3, "Final B", sub_branch="b"),
            ],
            branches=branches,
        )
    ]
    out = render_ascii(phases)
    assert "┬" in out, f"branch tees missing:\n{out}"
    assert "┼" not in out, f"dangling branch should have no join:\n{out}"
    assert "end-a" in out and "end-b" in out


def test_flat_branches_plus_loops() -> None:
    """Branch + intra-SOP loop in same SOP: branch markers + loop track both render.

    Loops are orthogonal to branches — adding `Workflow branches:` should NOT
    break the existing right-side vertical loop track.
    """
    branches = [
        BranchSignature(
            from_step=2,
            to=(
                BranchTarget(parent=3, branch="a", label="ok"),
                BranchTarget(parent=3, branch="b", label="no"),
            ),
        )
    ]
    loops = [
        LoopSignature(
            id="retry",
            from_step=4,
            to_step=1,
            max_iterations=3,
            condition="failed",
        )
    ]
    phases = [
        _phase(
            "TST-9003",
            [
                _step(1, "Setup"),
                _step(2, "Decision"),
                _step(3, "Path A", sub_branch="a"),
                _step(3, "Path B", sub_branch="b"),
                _step(4, "Continue"),
            ],
            loops=loops,
            branches=branches,
        )
    ]
    out = render_ascii(phases)
    assert "┬" in out, "branch tees missing"
    # Loop annotation should still appear (vertical track or inline).
    assert "◄──────┐" in out or "→ back to" in out or "max 3" in out, (
        f"loop annotation missing from output:\n{out}"
    )


def test_flat_loop_track_crosses_branch_group_clean_intermediate_rows() -> None:
    """Loop whose from_step→to_step range crosses a branch group renders cleanly.

    SOP shape:
      1. Setup         <- loop to_step (◄──────┐ lands here)
      2. Decision      <- branch parent
      3a. Ba           <- sibling
      3b. Bb           <- sibling
      4. Continue      <- convergence
      5. End           <- loop from_step (─────┘ max N lands here)

    Structural invariants:
    - ◄──────┐ appears on the "[1.1] Setup" body row (to_step body row)
    - ─────┘ max appears on the "[1.5] End" body row, NOT on any box-border row
    - All intermediate rows between to_step and from_step have │ at the track col
    - No row contains ...│ (no truncation-of-box-drawing geometry)
    """
    branches = [
        BranchSignature(
            from_step=2,
            to=(
                BranchTarget(parent=3, branch="a", label="ok"),
                BranchTarget(parent=3, branch="b", label="no"),
            ),
        )
    ]
    loops = [
        LoopSignature(
            id="retry",
            from_step=5,
            to_step=1,
            max_iterations=3,
            condition="",
        )
    ]
    phases = [
        _phase(
            "TST-9010",
            [
                _step(1, "Setup"),
                _step(2, "Decision"),
                _step(3, "Ba", sub_branch="a"),
                _step(3, "Bb", sub_branch="b"),
                _step(4, "Continue"),
                _step(5, "End"),
            ],
            loops=loops,
            branches=branches,
        )
    ]
    out = render_ascii(phases)
    lines = out.split("\n")

    # Find the to_step body row: must contain "◄──────┐"
    to_rows = [ln for ln in lines if "◄──────┐" in ln]
    assert to_rows, f"◄──────┐ not found in output:\n{out}"
    # The to_step row must contain "[1.1]" (Setup body)
    assert all("[1.1]" in ln for ln in to_rows), (
        "◄──────┐ landed on wrong row (expected [1.1] Setup body):\n"
        + "\n".join(to_rows)
    )

    # Find the from_step suffix row: must contain "─────┘ max" or "──────┘ max"
    from_rows = [ln for ln in lines if "┘ max" in ln]
    assert from_rows, f"┘ max not found in output:\n{out}"
    # The from_step row must contain "[1.5]" (End body) and NOT be a box-border row
    for fr in from_rows:
        assert "[1.5]" in fr, (
            f"─────┘ max landed on wrong row (expected [1.5] End body):\n{fr}"
        )
        # Must not be a pure box-drawing row
        stripped = fr.strip(" │")
        assert not all(ch in "┌┐└┘─┴┬┼│▼◄► " for ch in stripped if stripped), (
            f"─────┘ max landed on a box-drawing row:\n{fr}"
        )

    # All intermediate rows between to_step and from_step must have │ at track col.
    # Find the row indices of to_step and from_step in lines.
    to_idx = next(i for i, ln in enumerate(lines) if "◄──────┐" in ln)
    from_idx = next(i for i, ln in enumerate(lines) if "┘ max" in ln)
    assert to_idx < from_idx, "to_step row must precede from_step row"
    # Find the track column (column of ┐ in to_step row).
    to_row = lines[to_idx]
    track_col = to_row.index("┐")  # rightmost ┐ is the track corner
    for i in range(to_idx + 1, from_idx):
        ln = lines[i]
        assert len(ln) > track_col and ln[track_col] == "│", (
            f"Intermediate row {i} missing │ at track col {track_col}:\n{ln!r}"
        )

    # No row must contain "...│" (box-drawing mangled by shrink_for_track).
    mangled = [ln for ln in lines if "...│" in ln]
    assert not mangled, (
        "found rows with '...│' (box-drawing geometry mangled):\n" + "\n".join(mangled)
    )


def test_flat_branch_box_borders_not_mangled_by_loop_track() -> None:
    """Box-border rows (─ runs) must not be truncated with '...│' by loop track.

    Same SOP as test_flat_loop_track_crosses_branch_group_clean_intermediate_rows.
    After rendering, every row that contains a ─ run (box horizontal border)
    must NOT contain '...│'.
    """
    branches = [
        BranchSignature(
            from_step=2,
            to=(
                BranchTarget(parent=3, branch="a", label="ok"),
                BranchTarget(parent=3, branch="b", label="no"),
            ),
        )
    ]
    loops = [
        LoopSignature(
            id="retry",
            from_step=5,
            to_step=1,
            max_iterations=3,
            condition="",
        )
    ]
    phases = [
        _phase(
            "TST-9011",
            [
                _step(1, "Setup"),
                _step(2, "Decision"),
                _step(3, "Ba", sub_branch="a"),
                _step(3, "Bb", sub_branch="b"),
                _step(4, "Continue"),
                _step(5, "End"),
            ],
            loops=loops,
            branches=branches,
        )
    ]
    out = render_ascii(phases)
    lines = out.split("\n")
    # Rows that contain horizontal-border runs (─ sequences) are box borders.
    border_rows = [ln for ln in lines if "──" in ln]
    assert border_rows, "expected box-border rows in output"
    mangled_borders = [ln for ln in border_rows if "...│" in ln]
    assert not mangled_borders, (
        "box-border rows were mangled with '...│':\n" + "\n".join(mangled_borders)
    )


def test_flat_4way_fanout() -> None:
    """4-way branch with convergence: all 4 labels present, width-uniformity holds."""
    branches = [
        BranchSignature(
            from_step=2,
            to=(
                BranchTarget(parent=3, branch="a", label="A"),
                BranchTarget(parent=3, branch="b", label="B"),
                BranchTarget(parent=3, branch="c", label="C"),
                BranchTarget(parent=3, branch="d", label="D"),
            ),
        )
    ]
    phases = [
        _phase(
            "TST-9012",
            [
                _step(1, "Start"),
                _step(2, "Fork"),
                _step(3, "Aa", sub_branch="a"),
                _step(3, "Bb", sub_branch="b"),
                _step(3, "Cc", sub_branch="c"),
                _step(3, "Dd", sub_branch="d"),
                _step(4, "Merge"),
            ],
            branches=branches,
        )
    ]
    out = render_ascii(phases)
    # All 4 labels present.
    for label in ("A", "B", "C", "D"):
        assert label in out, f"label {label!r} missing from output:\n{out}"
    # Width-uniformity: all │-containing lines have same total cell width.
    lines = out.split("\n")
    box_lines = [ln for ln in lines if "│" in ln]
    assert box_lines, "expected phase-box border lines"
    widths = {wcwidth.wcswidth(ln) for ln in box_lines}
    assert len(widths) == 1, (
        f"phase-box lines have non-uniform widths {widths}:\n"
        + "\n".join(f"  ({wcwidth.wcswidth(ln)}) {ln}" for ln in box_lines)
    )


def test_flat_sibling_text_paired_by_branch_letter() -> None:
    """Siblings declared (a, b, c) but steps listed (c, a, b): column order follows
    declared label order, not step-definition order.

    Uses short body texts that fit in 12-cell sibling box: 'Ba', 'Bb', 'Bc'.
    """
    branches = [
        BranchSignature(
            from_step=2,
            to=(
                BranchTarget(parent=3, branch="a", label="A"),
                BranchTarget(parent=3, branch="b", label="B"),
                BranchTarget(parent=3, branch="c", label="C"),
            ),
        )
    ]
    phases = [
        _phase(
            "TST-9013",
            [
                _step(1, "Start"),
                _step(2, "Split"),
                # Steps listed in (c, a, b) order — different from declared (a, b, c).
                _step(3, "Bc", sub_branch="c"),
                _step(3, "Ba", sub_branch="a"),
                _step(3, "Bb", sub_branch="b"),
                _step(4, "Join"),
            ],
            branches=branches,
        )
    ]
    out = render_ascii(phases)
    # All three body texts must appear.
    for body in ("Ba", "Bb", "Bc"):
        assert body in out, f"sibling body {body!r} missing:\n{out}"
    # In each sibling row, left-to-right order must be Ba, Bb, Bc
    # (matching declared a, b, c — not the step-list c, a, b order).
    sibling_row = next(
        (ln for ln in out.split("\n") if "Ba" in ln and "Bb" in ln and "Bc" in ln),
        None,
    )
    assert sibling_row is not None, (
        "could not find a single row containing Ba, Bb, Bc:\n" + out
    )
    assert (
        sibling_row.index("Ba") < sibling_row.index("Bb") < sibling_row.index("Bc")
    ), f"column order is wrong (expected Ba < Bb < Bc):\n{sibling_row}"


def test_flat_phase_box_uniform_width_with_branches() -> None:
    """Width-uniformity invariant: every │-containing line has the same total width.

    Same precedent as Phase 4's test_nested_phase_box_uniform_width_with_branches.
    """
    branches = [
        BranchSignature(
            from_step=2,
            to=(
                BranchTarget(parent=3, branch="a", label="A"),
                BranchTarget(parent=3, branch="b", label="B"),
            ),
        )
    ]
    phases = [
        _phase(
            "TST-9004",
            [
                _step(1, "First"),
                _step(2, "Decision"),
                _step(3, "Path A", sub_branch="a"),
                _step(3, "Path B", sub_branch="b"),
                _step(4, "After"),
            ],
            branches=branches,
        )
    ]
    out = render_ascii(phases)
    lines = out.split("\n")
    # All lines containing │ borders must have the same total cell width.
    box_lines = [line for line in lines if "│" in line]
    assert box_lines, "expected phase-box border lines"
    widths = {wcwidth.wcswidth(line) for line in box_lines}
    assert len(widths) == 1, (
        f"phase-box lines have non-uniform widths {widths}; "
        "branch group output may have overflowed phase border\n"
        + "\n".join(f"  ({wcwidth.wcswidth(line)}) {line}" for line in box_lines)
    )
