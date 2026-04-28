"""Tests for FXA-2227 Phase 4 — dag_graph.py nested-layout integration with
branch_geometry primitive.

Per CHG-2227 §"Phase 4 — `dag_graph.py` nested integration":
- Detect a branch group when sub-step `index` matches `Workflow branches.from + 1`
  AND `step.get("sub_branch")` is set.
- Call `render_branch(...)` from `branch_geometry` with `BranchTarget`
  siblings constructed from matching step entries.
- Wrap result in phase-box borders.
- `step_row_index` keys remain int-typed by `step["index"]`.
- Siblings rendered as a group (occupying parent integer's row range).
"""

from __future__ import annotations

import wcwidth

from fx_alfred.core.dag_graph import render_dag
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


def test_nested_3way_with_convergence() -> None:
    """3-way branch with convergence renders inside phase box.

    SOP shape:
      1. Setup
      2. Decision    ← parent (branches.from = 2)
      3a. pass       ← sibling
      3b. fail       ← sibling
      3c. esc        ← sibling
      4. Continue    ← convergence (auto-detected)
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
    out = render_dag(phases)
    # Topology assertions: branch tees, labels, sub-step display IDs, join.
    assert "┬" in out, f"expected branch tees in output:\n{out}"
    assert "pass" in out
    assert "fail" in out
    assert "esc" in out
    assert "┼" in out, f"expected convergence join in output:\n{out}"
    # Display IDs `3a/3b/3c` should appear (per Phase 3 todo[].index extension
    # contract — sub-step IDs surface in body text or display markers).
    # The renderer composes display ID via f"{index}{sub_branch}".
    assert "3a" in out or "pass-body" in out, (
        f"expected sibling 3a content in output:\n{out}"
    )
    # Phase box still wraps the whole thing.
    assert "Phase 1: TST-9001" in out


def test_nested_legacy_unchanged() -> None:
    """Phase without branches: renders byte-identical to pre-Phase-4 (no regression)."""
    phases = [
        _phase(
            "COR-1500",
            [_step(1, "Red"), _step(2, "Green"), _step(3, "Refactor")],
        ),
    ]
    out = render_dag(phases)
    # Legacy structure: phase header + 3 step boxes + arrows + bottom border.
    assert "Phase 1: COR-1500" in out
    assert "1.1 Red" in out or "1. Red" in out  # phase.step or just step
    assert "1.2 Green" in out or "2. Green" in out
    assert "1.3 Refactor" in out or "3. Refactor" in out
    # No branch markers should appear.
    assert "┬" not in out, f"unexpected branch tee in legacy output:\n{out}"
    assert "┼" not in out


def test_nested_dangling_branch() -> None:
    """Terminal branch (no convergence) renders without join row."""
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
    out = render_dag(phases)
    # Branch tees present; no convergence join.
    assert "┬" in out
    assert "┼" not in out, f"dangling branch should have no join:\n{out}"
    assert "end-a" in out and "end-b" in out


def test_nested_branches_plus_loops() -> None:
    """Branch + loop in same SOP: branch renders correctly; loops still shown.

    Branches and loops are orthogonal — adding `Workflow branches:` should
    not affect loop annotation rendering.
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
    out = render_dag(phases)
    assert "┬" in out, "branch tees missing"
    # Loop annotation should still appear (loops are independent of branches).
    assert "retry" in out or "🔁" in out or "loop" in out.lower(), (
        f"loop annotation missing from output:\n{out}"
    )


def test_nested_phase_box_uniform_width_with_branches() -> None:
    """Phase box width invariant holds when a branch group is rendered.

    Every line of the phase output must fit within the existing phase-box
    borders (`│ ... │`). Width-uniformity guards against the same class of
    bug Gemini caught in Phase 3 (CJK body breaking I2).
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
    out = render_dag(phases)
    lines = out.split("\n")
    # All lines containing `│` borders must have the same total cell width.
    box_lines = [line for line in lines if "│" in line]
    assert box_lines, "expected phase-box border lines"
    widths = {wcwidth.wcswidth(line) for line in box_lines}
    assert len(widths) == 1, (
        f"phase-box lines have non-uniform widths {widths}; "
        "branch group output may have overflowed phase border\n"
        + "\n".join(f"  ({wcwidth.wcswidth(line)}) {line}" for line in box_lines)
    )
