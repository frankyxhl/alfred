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


def test_single_sibling_branch_rejected() -> None:
    """Branch with only one declared sibling target → group not produced.

    Codex review C5 (P1): the branch_geometry.render_branch primitive
    requires n >= 2 siblings (raises ValueError on n=1). Validator
    currently allows single-target ``to:`` so the discovery layer must
    reject these to prevent renderer crashes on accepted inputs.
    """
    steps = [
        _step(1),
        _step(2),  # would-be parent
        _step(3, sub_branch="a"),  # only one sibling
        _step(4),
    ]
    bsig = BranchSignature(
        from_step=2,
        to=(BranchTarget(parent=3, branch="a", label="solo"),),
    )
    assert discover_branch_groups(steps, [bsig]) == []


def test_five_sibling_branch_rejected() -> None:
    """Branch with 5 declared ``to`` targets → group not produced (graceful skip).

    Codex review N4 (P1): ``render_branch`` hard-fails on >4 siblings. The
    discovery layer must reject 5+ to prevent renderer crashes on accepted
    inputs (validator allows any non-empty ``to``).
    """
    steps = [
        _step(1),
        _step(2),  # would-be parent
        _step(3, sub_branch="a"),
        _step(3, sub_branch="b"),
        _step(3, sub_branch="c"),
        _step(3, sub_branch="d"),
        _step(3, sub_branch="e"),
        _step(4),
    ]
    bsig = _bsig(2, "a", "b", "c", "d", "e")
    assert discover_branch_groups(steps, [bsig]) == []


def test_skipped_branch_does_not_block_earlier_convergence() -> None:
    """A malformed single-target branch (will be skipped) must not block an
    earlier valid branch from converging at the same step.

    Codex review N3 (P2): ``other_branch_starts`` was built from ALL
    declarations including ones that will later be skipped (n<2 siblings).
    A skipped ``from: 4`` declaration would prevent the earlier valid branch
    from treating step 4 as its convergence, silently dropping the join.
    The fix restricts ``other_branch_starts`` to branches with 2 <= len(to) <= 4.
    """
    # Branch A: valid 2-way, from_step=2, should converge at step 4 (idx 4).
    # Branch B: malformed single-target, from_step=4, will be skipped by n<2 guard.
    steps = [
        _step(1),
        _step(2),  # parent of branch A
        _step(3, sub_branch="a"),
        _step(3, sub_branch="b"),
        _step(4),  # convergence of branch A; also from_step of (skipped) branch B
    ]
    branch_a = _bsig(2, "a", "b")
    branch_b = BranchSignature(
        from_step=4,
        to=(BranchTarget(parent=5, branch="a", label="solo"),),
    )
    groups = discover_branch_groups(steps, [branch_a, branch_b])
    assert len(groups) == 1, f"expected only branch A rendered, got {len(groups)}"
    assert groups[0].convergence_idx == 4, (
        f"branch A should converge at idx 4, got {groups[0].convergence_idx}"
    )


def test_partial_sibling_coverage_rejected() -> None:
    """Branch declares a letter that has no matching sibling step → group
    is skipped rather than crashing the renderer with a KeyError on the
    missing letter (Codex N5).
    """
    steps = [
        _step(1),
        _step(2),  # parent
        _step(3, sub_branch="a"),
        _step(3, sub_branch="b"),
        # missing 3c — declared but not present
    ]
    bsig = BranchSignature(
        from_step=2,
        to=(
            BranchTarget(parent=3, branch="a", label="A"),
            BranchTarget(parent=3, branch="b", label="B"),
            BranchTarget(parent=3, branch="c", label="C"),  # orphan
        ),
    )
    assert discover_branch_groups(steps, [bsig]) == []


def test_duplicate_target_ids_in_to_rejected() -> None:
    """Branch with duplicate target IDs in `to` (e.g., (a, a, b, c, d) —
    5 declared entries) is rejected by the declared-count guard, even
    though only 4 unique letters {a,b,c,d} are present and would otherwise
    pass the collected-letters set-equality check (Codex N6).
    """
    steps = [
        _step(1),
        _step(2),
        _step(3, sub_branch="a"),
        _step(3, sub_branch="b"),
        _step(3, sub_branch="c"),
        _step(3, sub_branch="d"),
    ]
    bsig = BranchSignature(
        from_step=2,
        to=(
            BranchTarget(parent=3, branch="a", label="A1"),
            BranchTarget(parent=3, branch="a", label="A2"),  # duplicate
            BranchTarget(parent=3, branch="b", label="B"),
            BranchTarget(parent=3, branch="c", label="C"),
            BranchTarget(parent=3, branch="d", label="D"),
        ),
    )
    assert discover_branch_groups(steps, [bsig]) == []


def test_sibling_collection_constrained_to_declared_letters() -> None:
    """Discovery only consumes siblings whose ``sub_branch`` letter is
    declared in the active branch's ``to`` tuple.

    Codex review C6 (P2): if two branches share the same ``from_step``
    (a shape parser doesn't reject), the first one would otherwise
    absorb all siblings of both, producing a length-mismatch crash in
    the renderer primitive. Constraining by declared letter prevents
    cross-claiming.
    """
    # Branch A declares letters {a, b}. Branch B (same from_step)
    # declares letters {c, d}. Steps list 3a, 3b, 3c, 3d in order.
    steps = [
        _step(1),
        _step(2),  # parent (shared from_step)
        _step(3, sub_branch="a"),
        _step(3, sub_branch="b"),
        _step(3, sub_branch="c"),
        _step(3, sub_branch="d"),
    ]
    branch_a = BranchSignature(
        from_step=2,
        to=(
            BranchTarget(parent=3, branch="a", label="A"),
            BranchTarget(parent=3, branch="b", label="B"),
        ),
    )
    branch_b = BranchSignature(
        from_step=2,
        to=(
            BranchTarget(parent=3, branch="c", label="C"),
            BranchTarget(parent=3, branch="d", label="D"),
        ),
    )
    groups = discover_branch_groups(steps, [branch_a, branch_b])
    # Branch A should claim 3a/3b only (not 3c/3d).
    assert len(groups) >= 1
    g_a = next(g for g in groups if g.branch_signature is branch_a)
    assert g_a.sibling_indices == (2, 3), (
        f"branch_a wrongly absorbed siblings beyond its declared letters: "
        f"{g_a.sibling_indices}"
    )
