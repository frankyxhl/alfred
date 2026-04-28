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
