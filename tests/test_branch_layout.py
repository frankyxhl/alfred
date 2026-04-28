"""Unit tests for `core.branch_layout.discover_branch_groups`.

The discovery primitive is shared between the nested (`dag_graph.py`) and
flat (`ascii_graph.py`, Phase 5) renderers, so it owns the convergence-
detection contract. These tests pin down behaviors that both renderers rely
on, separately from any rendering concern.
"""

from __future__ import annotations

from fx_alfred.core.branch_layout import BranchGroup, discover_branch_groups
from fx_alfred.core.workflow import BranchSignature, BranchTarget


def _step(index: int, text: str = "x", sub_branch: str | None = None) -> dict:
    s: dict = {"index": index, "text": text, "gate": False}
    if sub_branch is not None:
        s["sub_branch"] = sub_branch
    return s


def _bsig(from_step: int, *branches: str) -> BranchSignature:
    return BranchSignature(
        from_step=from_step,
        to=tuple(
            BranchTarget(parent=from_step + 1, branch=ch, label=ch.upper())
            for ch in branches
        ),
    )


def test_no_branches_returns_empty() -> None:
    assert discover_branch_groups([_step(1), _step(2)], []) == []


def test_no_matching_parent_returns_empty() -> None:
    """Branch declares from_step=99 but no plain step with index 99."""
    groups = discover_branch_groups([_step(1), _step(2)], [_bsig(99, "a", "b")])
    assert groups == []


def test_simple_branch_with_convergence() -> None:
    steps = [
        _step(1),
        _step(2),  # parent
        _step(3, sub_branch="a"),
        _step(3, sub_branch="b"),
        _step(4),  # convergence
    ]
    groups = discover_branch_groups(steps, [_bsig(2, "a", "b")])
    assert len(groups) == 1
    g = groups[0]
    assert g.parent_idx == 1
    assert g.sibling_indices == (2, 3)
    assert g.convergence_idx == 4
    assert g.end_idx == 5


def test_dangling_branch_no_convergence() -> None:
    steps = [
        _step(1),
        _step(2),  # parent
        _step(3, sub_branch="a"),
        _step(3, sub_branch="b"),
    ]
    groups = discover_branch_groups(steps, [_bsig(2, "a", "b")])
    assert len(groups) == 1
    assert groups[0].convergence_idx is None
    assert groups[0].end_idx == 4  # last sibling + 1


def test_chained_branches_convergence_disambiguation() -> None:
    """Back-to-back branches: second branch's parent must NOT be consumed
    as the first branch's convergence."""
    steps = [
        _step(1),
        _step(2),  # parent of first branch
        _step(3, sub_branch="a"),
        _step(3, sub_branch="b"),
        _step(4),  # parent of second branch (NOT convergence of first)
        _step(5, sub_branch="a"),
        _step(5, sub_branch="b"),
        _step(6),  # convergence of second branch
    ]
    groups = discover_branch_groups(steps, [_bsig(2, "a", "b"), _bsig(4, "a", "b")])
    assert len(groups) == 2
    g1, g2 = groups
    # First branch: no convergence (step 4 is reserved as second branch's parent).
    assert g1.parent_idx == 1
    assert g1.sibling_indices == (2, 3)
    assert g1.convergence_idx is None
    # Second branch: convergence is step 6 (idx 7).
    assert g2.parent_idx == 4
    assert g2.sibling_indices == (5, 6)
    assert g2.convergence_idx == 7


def test_branch_list_order_independence() -> None:
    """Branches given in reverse list order must produce the same groups
    as forward order — discovery sorts by from_step internally."""
    steps = [
        _step(1),
        _step(2),
        _step(3, sub_branch="a"),
        _step(3, sub_branch="b"),
        _step(4),
        _step(5, sub_branch="a"),
        _step(5, sub_branch="b"),
        _step(6),
    ]
    forward = discover_branch_groups(steps, [_bsig(2, "a", "b"), _bsig(4, "a", "b")])
    reverse = discover_branch_groups(steps, [_bsig(4, "a", "b"), _bsig(2, "a", "b")])
    # Same parent_idx/sibling_indices/convergence_idx — only the
    # branch_signature object identity differs.
    assert [(g.parent_idx, g.sibling_indices, g.convergence_idx) for g in forward] == [
        (g.parent_idx, g.sibling_indices, g.convergence_idx) for g in reverse
    ]


def test_groups_returned_in_step_order() -> None:
    """Output sorted by parent_idx ascending, regardless of input order."""
    steps = [
        _step(1),
        _step(2),  # branch A parent
        _step(3, sub_branch="a"),
        _step(3, sub_branch="b"),
        _step(4),
        _step(5),  # branch B parent
        _step(6, sub_branch="a"),
        _step(6, sub_branch="b"),
    ]
    groups = discover_branch_groups(steps, [_bsig(5, "a", "b"), _bsig(2, "a", "b")])
    assert [g.parent_idx for g in groups] == [1, 5]


def test_branch_with_no_siblings_skipped() -> None:
    """Branch declared but no sub_branch siblings present — group not
    produced (would be malformed)."""
    steps = [_step(1), _step(2), _step(3), _step(4)]
    assert discover_branch_groups(steps, [_bsig(2, "a", "b")]) == []


def test_branchgroup_end_idx_with_convergence() -> None:
    g = BranchGroup(
        parent_idx=1,
        sibling_indices=(2, 3),
        convergence_idx=4,
        branch_signature=_bsig(2, "a", "b"),
    )
    assert g.end_idx == 5


def test_branchgroup_end_idx_dangling() -> None:
    g = BranchGroup(
        parent_idx=1,
        sibling_indices=(2, 3),
        convergence_idx=None,
        branch_signature=_bsig(2, "a", "b"),
    )
    assert g.end_idx == 4
