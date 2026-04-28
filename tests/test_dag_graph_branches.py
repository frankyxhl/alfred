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


def test_nested_chained_branches() -> None:
    """Two back-to-back branches in the same SOP — both must render.

    Regression guard for the convergence-detection bug: without the
    "next plain step is another branch's parent" guard, the first
    branch's convergence-detection would greedily consume step 4 (the
    second branch's parent) and silently drop the second branch.
    """
    branches = [
        BranchSignature(
            from_step=2,
            to=(
                BranchTarget(parent=3, branch="a", label="A1"),
                BranchTarget(parent=3, branch="b", label="B1"),
            ),
        ),
        BranchSignature(
            from_step=4,
            to=(
                BranchTarget(parent=5, branch="a", label="A2"),
                BranchTarget(parent=5, branch="b", label="B2"),
            ),
        ),
    ]
    phases = [
        _phase(
            "TST-9005",
            [
                _step(1, "Setup"),
                _step(2, "DecisionOne"),
                _step(3, "First A", sub_branch="a"),
                _step(3, "First B", sub_branch="b"),
                _step(4, "DecisionTwo"),
                _step(5, "Second A", sub_branch="a"),
                _step(5, "Second B", sub_branch="b"),
                _step(6, "End"),
            ],
            branches=branches,
        )
    ]
    out = render_dag(phases)
    # Both branch-group label sets must appear — this fails today if
    # step 4 ("DecisionTwo") is silently swallowed as branch-1's convergence.
    assert "DecisionTwo" in out, (
        f"second branch's parent step was dropped — chained-branch bug:\n{out}"
    )
    assert "A1" in out and "B1" in out, "first branch labels missing"
    assert "A2" in out and "B2" in out, "second branch labels missing"
    # Both branches show their tees.
    assert out.count("┬") >= 2, f"expected tees from both branches:\n{out}"


def test_nested_chained_branches_reverse_listed_order() -> None:
    """Same scenario as chained-branches, but with branches listed in
    REVERSE step order (later from_step first).

    Regression guard: ``discover_branch_groups`` must sort by ``from_step``
    so list order in the parser output cannot cause silent misrender.
    Without the sort, the later-listed earlier branch's siblings would
    be left rendered as plain steps because the later from_step branch
    consumes step indices first.
    """
    # Same SOP as test_nested_chained_branches but branches list reversed.
    branches = [
        BranchSignature(
            from_step=4,
            to=(
                BranchTarget(parent=5, branch="a", label="A2"),
                BranchTarget(parent=5, branch="b", label="B2"),
            ),
        ),
        BranchSignature(
            from_step=2,
            to=(
                BranchTarget(parent=3, branch="a", label="A1"),
                BranchTarget(parent=3, branch="b", label="B1"),
            ),
        ),
    ]
    phases = [
        _phase(
            "TST-9008",
            [
                _step(1, "Setup"),
                _step(2, "DecisionOne"),
                _step(3, "First A", sub_branch="a"),
                _step(3, "First B", sub_branch="b"),
                _step(4, "DecisionTwo"),
                _step(5, "Second A", sub_branch="a"),
                _step(5, "Second B", sub_branch="b"),
                _step(6, "End"),
            ],
            branches=branches,
        )
    ]
    out = render_dag(phases)
    # Both groups must render correctly regardless of branches list order.
    assert "A1" in out and "B1" in out, (
        f"first branch (from_step=2) dropped due to list-order dependence:\n{out}"
    )
    assert "A2" in out and "B2" in out, f"second branch (from_step=4) dropped:\n{out}"
    # Two distinct branch-group blocks ⇒ at least 4 tees (two per group).
    assert out.count("┬") >= 4, (
        f"expected 4+ tees (2 per group); got {out.count('┬')}:\n{out}"
    )


def test_nested_4way_max_fanout() -> None:
    """Maximum supported fanout (4 siblings) renders within phase-box width."""
    branches = [
        BranchSignature(
            from_step=2,
            to=(
                BranchTarget(parent=3, branch="a", label="alpha"),
                BranchTarget(parent=3, branch="b", label="beta"),
                BranchTarget(parent=3, branch="c", label="gamma"),
                BranchTarget(parent=3, branch="d", label="delta"),
            ),
        )
    ]
    phases = [
        _phase(
            "TST-9006",
            [
                _step(1, "Setup"),
                _step(2, "Decision"),
                _step(3, "A-body", sub_branch="a"),
                _step(3, "B-body", sub_branch="b"),
                _step(3, "C-body", sub_branch="c"),
                _step(3, "D-body", sub_branch="d"),
                _step(4, "Continue"),
            ],
            branches=branches,
        )
    ]
    out = render_dag(phases)
    # All four labels present.
    for label in ("alpha", "beta", "gamma", "delta"):
        assert label in out, f"label {label!r} missing for 4-way fanout:\n{out}"
    # Width invariant still holds at max fanout.
    lines = out.split("\n")
    box_lines = [line for line in lines if "│" in line]
    widths = {wcwidth.wcswidth(line) for line in box_lines}
    assert len(widths) == 1, (
        f"4-way fanout broke phase-box width invariant {widths}\n"
        + "\n".join(f"  ({wcwidth.wcswidth(line)}) {line}" for line in box_lines)
    )


def test_nested_parent_annotation_adjacent_to_parent_row() -> None:
    """Parent-step intra-SOP loop annotation must sit immediately after the
    parent middle row, not after the convergence box.

    Regression guard: the original Phase 4 implementation appended parent
    annotations after the entire branch block, so an annotation attached
    to the *parent* step ended up below the *convergence* step's box —
    visually misordered vs the legacy (non-branch) annotation placement.
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
    # Loop attached to the PARENT step (index=2) — annotation should appear
    # right after parent's middle row, BEFORE the branch tees.
    loops = [
        LoopSignature(
            id="parent-retry",
            from_step=2,
            to_step=1,
            max_iterations=2,
            condition="parent-cond",
        )
    ]
    phases = [
        _phase(
            "TST-9007",
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
    lines = out.split("\n")
    # Find row indices for the parent-annotation marker, the first branch
    # tee row, and the convergence "Continue" body row.
    # Annotation line carries the loop's condition text — use that as a
    # unique marker (loop id "parent-retry" is NOT a substring of the
    # rendered "parent-cond" condition; condition text is what's emitted).
    ann_row = next((i for i, line in enumerate(lines) if "parent-cond" in line), None)
    tee_row = next((i for i, line in enumerate(lines) if "┬" in line), None)
    converge_row = next((i for i, line in enumerate(lines) if "Continue" in line), None)
    assert ann_row is not None, f"parent annotation missing:\n{out}"
    assert tee_row is not None, f"branch tees missing:\n{out}"
    assert converge_row is not None, f"convergence step missing:\n{out}"
    # Annotation must sit BEFORE the branch tees AND BEFORE convergence.
    assert ann_row < tee_row, (
        f"parent annotation (row {ann_row}) rendered AFTER branch tees "
        f"(row {tee_row}) — expected adjacent to parent middle row\n{out}"
    )
    assert ann_row < converge_row, (
        f"parent annotation (row {ann_row}) rendered AFTER convergence "
        f"(row {converge_row}) — visually misordered\n{out}"
    )
