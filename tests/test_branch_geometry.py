"""Tests for FXA-2227 Phase 3 — core/branch_geometry.py primitive.

11 invariants (I1-I11) + 6 goldens per CHG-2227 §"Phase 3 Spike Exit
Criteria". Goldens are hand-crafted from PRP-2225 §"Geometry algorithm
sketch" (PRP-2225:105-109); the Audit Ledger fixture replaces the
manual-eyeball gate from R1.
"""

from __future__ import annotations

import wcwidth

from fx_alfred.core.branch_geometry import (
    BranchRenderInput,
    compute_column_offsets,
    render_branch,
)
from fx_alfred.core.workflow import BranchTarget


def _make_input(
    *,
    siblings: list[tuple[int, str, str]],  # [(parent, branch, label), ...]
    sibling_texts: list[str] | None = None,
    parent_step_text: str = "Decision",
    converges_to: int | None = 4,
    converges_to_text: str | None = "Continue",
    box_width: int = 12,
) -> BranchRenderInput:
    targets = tuple(
        BranchTarget(parent=p, branch=b, label=label) for p, b, label in siblings
    )
    if sibling_texts is None:
        sibling_texts = [f"sibling-{b}" for _, b, _ in siblings]
    return BranchRenderInput(
        parent_step_text=parent_step_text,
        siblings=targets,
        sibling_texts=sibling_texts,
        converges_to=converges_to,
        converges_to_text=converges_to_text,
        box_width=box_width,
    )


# --------------------------------------------------------------------------
# Invariants I1–I11 (per CHG-2227 §"Phase 3 Primitive API Contract")
# --------------------------------------------------------------------------


def test_I1_compute_column_offsets_strictly_increasing() -> None:
    """I1: compute_column_offsets returns N strictly-increasing offsets."""
    for n in (2, 3, 4):
        offsets = compute_column_offsets(n_siblings=n, box_width=12)
        assert len(offsets) == n
        for prev, curr in zip(offsets, offsets[1:]):
            assert prev < curr, f"offsets not strictly increasing for n={n}: {offsets}"


def test_I2_lines_uniform_cell_width() -> None:
    """I2: All output lines have uniform visible-cell width via wcwidth."""
    out = render_branch(
        _make_input(
            siblings=[
                (3, "a", "pass"),
                (3, "b", "fail"),
                (3, "c", "escalate"),
            ]
        )
    )
    widths = {wcwidth.wcswidth(line) for line in out.lines}
    assert len(widths) == 1, f"non-uniform line widths: {widths}"


def test_I2_uniform_width_with_cjk_bodies() -> None:
    """I2 with CJK body texts (Gemini PR #69 R1 review — caught real bug).

    Pre-fix: sibling-box and convergence-box placement loops used plain
    enumerate without blanking trailing cells for wide chars, so any CJK
    body broke the uniform-width invariant. This test would have failed.
    """
    out = render_branch(
        _make_input(
            siblings=[(3, "a", "ok"), (3, "b", "ok")],
            sibling_texts=["完整性测试", "ok"],
            converges_to=None,
            converges_to_text=None,
        )
    )
    widths = {wcwidth.wcswidth(line) for line in out.lines}
    assert len(widths) == 1, (
        f"non-uniform line widths with CJK body: {widths}\n"
        + "\n".join(f"  ({wcwidth.wcswidth(line)}) {line!r}" for line in out.lines)
    )


def test_paint_combining_marks_attach_to_base_char() -> None:
    """Per Codex PR #69 bot review on 1dd32f0: combining marks (cw=0) must
    attach to the preceding base cell, not overwrite a new cell.

    "Café" written as 'C', 'a', 'f', 'e', '\\u0301' (combining acute) must
    render with the accent attached to 'e'. Pre-fix, the accent landed in
    a separate cell and was dropped or floated.
    """
    out = render_branch(
        _make_input(
            siblings=[(3, "a", ""), (3, "b", "")],
            sibling_texts=["Café", "ok"],
            converges_to=None,
            converges_to_text=None,
        )
    )
    rendered = "\n".join(out.lines)
    # The body should contain the combined "é" (e + combining acute) — assert
    # that the combining mark is present AND is attached to 'e' (i.e. they
    # appear together rather than separated).
    assert "́" in rendered, "combining acute U+0301 should be present"
    # The string "é" (e then combining) should be a substring — they're
    # in adjacent cells / same cell, not split across separate cells with
    # other content between them.
    assert "é" in rendered, "combining mark should attach to preceding base char 'e'"
    # Width invariant still holds.
    widths = {wcwidth.wcswidth(line) for line in out.lines}
    assert len(widths) == 1


def test_I2_uniform_width_with_cjk_convergence_text() -> None:
    """I2 holds when the convergence step has CJK text (e.g. Audit Ledger)."""
    out = render_branch(
        _make_input(
            siblings=[(3, "a", "x"), (3, "b", "y")],
            sibling_texts=["A", "B"],
            converges_to=4,
            converges_to_text="审核账本入账",
        )
    )
    widths = {wcwidth.wcswidth(line) for line in out.lines}
    assert len(widths) == 1, f"non-uniform widths with CJK convergence: {widths}"


def test_I3_tee_at_each_offset() -> None:
    """I3: For each sibling i, the column at offsets[i] in parent_anchor_row is `┬`."""
    out = render_branch(
        _make_input(
            siblings=[
                (3, "a", "pass"),
                (3, "b", "fail"),
            ]
        )
    )
    parent_row = out.lines[out.parent_anchor_row]
    offsets = compute_column_offsets(n_siblings=2, box_width=12)
    for i, off in enumerate(offsets):
        assert parent_row[off] == "┬", (
            f"sibling {i}: expected '┬' at column {off}, got "
            f"{parent_row[off]!r} in row {parent_row!r}"
        )


def test_I4_n_labels_centered_at_tees() -> None:
    """I4: N labels for N edges, each centered at column c_i above its `┬`."""
    out = render_branch(
        _make_input(
            siblings=[
                (3, "a", "pass"),
                (3, "b", "fail"),
                (3, "c", "go"),
            ]
        )
    )
    # Label row sits between parent_anchor_row and the sibling boxes.
    # Find the row containing any of "pass" / "fail" / "go".
    label_row_idx = next(i for i, line in enumerate(out.lines) if "pass" in line)
    label_row = out.lines[label_row_idx]
    offsets = compute_column_offsets(n_siblings=3, box_width=12)
    for i, label in enumerate(("pass", "fail", "go")):
        # Each label's center should align with `c_i`.
        start = label_row.index(label)
        center = start + (len(label) - 1) // 2
        # Allow ±1 cell tolerance for odd-vs-even label widths.
        assert abs(center - offsets[i]) <= 1, (
            f"label {label!r} center {center} vs offset {offsets[i]} (diff > 1)"
        )


def test_I4_empty_label_blank_slot() -> None:
    """I4: Empty label leaves the slot blank but slot is reserved."""
    out = render_branch(
        _make_input(
            siblings=[
                (3, "a", "pass"),
                (3, "b", ""),
                (3, "c", "go"),
            ]
        )
    )
    label_row_idx = next(i for i, line in enumerate(out.lines) if "pass" in line)
    label_row = out.lines[label_row_idx]
    # 'pass' and 'go' are present; the middle slot has no label.
    assert "pass" in label_row
    assert "go" in label_row
    # Width of label row matches other lines (slot reserved).
    assert wcwidth.wcswidth(label_row) == wcwidth.wcswidth(out.lines[0])


def test_I4_all_empty_labels_collapse_row() -> None:
    """I4: If all labels are empty, the label row is omitted entirely."""
    out_with_labels = render_branch(
        _make_input(siblings=[(3, "a", "pass"), (3, "b", "fail")])
    )
    out_no_labels = render_branch(_make_input(siblings=[(3, "a", ""), (3, "b", "")]))
    assert len(out_no_labels.lines) == len(out_with_labels.lines) - 1


def test_I5_cjk_label_truncation() -> None:
    """I5: Labels >12 cells truncate via wcwidth (CJK chars count 2 cells)."""
    long_cjk = "通过失败处理理"  # 7 chars × 2 cells = 14 cells
    out = render_branch(
        _make_input(
            siblings=[
                (3, "a", long_cjk),
                (3, "b", "ok"),
            ]
        )
    )
    label_row = next(line for line in out.lines if "ok" in line)
    # Either appears truncated with `…`, or is shorter than the original
    assert long_cjk not in label_row, "CJK label should be truncated to ≤12 cells"


def test_I6_dangling_no_join() -> None:
    """I6: When converges_to is None, no `└──┼──┘` row is emitted."""
    out = render_branch(
        _make_input(
            siblings=[(3, "a", "x"), (3, "b", "y")],
            converges_to=None,
            converges_to_text=None,
        )
    )
    assert out.convergence_anchor_row is None
    # Output should not contain a join character.
    joined = "\n".join(out.lines)
    assert "┼" not in joined


def test_I7_join_centered_on_offsets_span() -> None:
    """I7: When converges_to is set, `┼` sits at column (c_1 + c_N) // 2."""
    out = render_branch(
        _make_input(
            siblings=[
                (3, "a", "x"),
                (3, "b", "y"),
                (3, "c", "z"),
            ]
        )
    )
    offsets = compute_column_offsets(n_siblings=3, box_width=12)
    expected_join_col = (offsets[0] + offsets[-1]) // 2
    # Find the row containing `┼`.
    join_row = next(line for line in out.lines if "┼" in line)
    assert join_row[expected_join_col] == "┼", (
        f"join `┼` at unexpected column; row={join_row!r}, "
        f"expected col {expected_join_col}"
    )


def test_I8_anchor_rows() -> None:
    """I8: parent_anchor_row=0; convergence_anchor_row≈len(lines)-2 if join."""
    out_join = render_branch(_make_input(siblings=[(3, "a", "x"), (3, "b", "y")]))
    assert out_join.parent_anchor_row == 0
    # Convergence step's box top edge sits near the bottom of the render.
    assert out_join.convergence_anchor_row is not None
    assert out_join.convergence_anchor_row < len(out_join.lines)
    assert out_join.convergence_anchor_row > out_join.parent_anchor_row


def test_I9_no_renderer_imports() -> None:
    """I9: branch_geometry must NOT import dag_graph or ascii_graph."""
    import fx_alfred.core.branch_geometry as mod

    src = mod.__file__
    with open(src) as f:
        content = f.read()
    assert "from fx_alfred.core.dag_graph" not in content
    assert "from fx_alfred.core.ascii_graph" not in content
    assert "import fx_alfred.core.dag_graph" not in content
    assert "import fx_alfred.core.ascii_graph" not in content


def test_I10_lower_arity_cap() -> None:
    """I10: 0 or 1 siblings raise ValueError (lower arity bound — Codex PR #69 R1)."""
    import pytest

    # 1 sibling — degenerate "branch", contract requires >= 2.
    with pytest.raises(ValueError, match="at least 2"):
        render_branch(_make_input(siblings=[(3, "a", "only")]))


def test_sibling_texts_length_mismatch_raises() -> None:
    """sibling_texts length must match siblings count (Codex PR #69 R1)."""
    import pytest

    with pytest.raises(ValueError, match="sibling_texts length"):
        render_branch(
            _make_input(
                siblings=[(3, "a", "x"), (3, "b", "y")],
                sibling_texts=["only-one"],  # 1 vs 2 siblings
            )
        )


def test_I10_four_way_cap() -> None:
    """I10: 5+ siblings raises ValueError (hard cap at 4)."""
    import pytest

    with pytest.raises(ValueError, match="4"):
        render_branch(
            _make_input(
                siblings=[
                    (3, "a", "1"),
                    (3, "b", "2"),
                    (3, "c", "3"),
                    (3, "d", "4"),
                    (3, "e", "5"),
                ]
            )
        )


def test_I11_step_anchor_rows_one_per_sibling() -> None:
    """I11: step_anchor_rows has exactly one entry per sibling, keyed by display ID."""
    out = render_branch(
        _make_input(
            siblings=[
                (3, "a", "p"),
                (3, "b", "f"),
                (3, "c", "e"),
            ]
        )
    )
    assert set(out.step_anchor_rows.keys()) == {"3a", "3b", "3c"}
    # Each anchor row points to a row that contains the sibling's text body.
    for sib_id, row_idx in out.step_anchor_rows.items():
        assert 0 <= row_idx < len(out.lines)


def test_I11_step_anchor_row_is_box_middle() -> None:
    """I11: anchor row points to the middle row of that sibling's box."""
    out = render_branch(
        _make_input(
            siblings=[(3, "a", "x"), (3, "b", "y")],
            sibling_texts=["AAA", "BBB"],
        )
    )
    # Middle of box "│ AAA │" should contain "AAA".
    aaa_row = out.lines[out.step_anchor_rows["3a"]]
    assert "AAA" in aaa_row, f"expected AAA in anchor row, got {aaa_row!r}"


# --------------------------------------------------------------------------
# Goldens — hand-crafted from PRP-2225 §"Geometry algorithm sketch".
# Phase 4 re-asserts the same outputs through the full nested renderer.
# --------------------------------------------------------------------------


def _render_lines(
    siblings: list[tuple[int, str, str]],
    *,
    sibling_texts: list[str] | None = None,
    converges_to: int | None = 4,
    converges_to_text: str | None = "Continue",
    box_width: int = 12,
) -> str:
    out = render_branch(
        _make_input(
            siblings=siblings,
            sibling_texts=sibling_texts,
            converges_to=converges_to,
            converges_to_text=converges_to_text,
            box_width=box_width,
        )
    )
    return "\n".join(out.lines)


def _assert_uniform_width(out) -> None:
    """Per Gemini PR #69 R2 advisory: hoist the I2 width-uniformity check
    into a single helper so every golden inherits the guard for free."""
    widths = {wcwidth.wcswidth(line) for line in out.lines}
    assert len(widths) == 1, f"non-uniform line widths: {widths}\n" + "\n".join(
        f"  ({wcwidth.wcswidth(line)}) {line!r}" for line in out.lines
    )


def _render_out(
    siblings: list[tuple[int, str, str]],
    *,
    sibling_texts: list[str] | None = None,
    converges_to: int | None = 4,
    converges_to_text: str | None = "Continue",
    box_width: int = 12,
):
    return render_branch(
        _make_input(
            siblings=siblings,
            sibling_texts=sibling_texts,
            converges_to=converges_to,
            converges_to_text=converges_to_text,
            box_width=box_width,
        )
    )


def test_golden_2way_simple() -> None:
    """Golden: 2-way branch sanity check."""
    out = _render_out(siblings=[(3, "a", "ok"), (3, "b", "no")])
    rendered = "\n".join(out.lines)
    # Must contain key topology markers.
    assert "┬" in rendered
    assert "ok" in rendered and "no" in rendered
    assert "┼" in rendered  # convergence
    _assert_uniform_width(out)


def test_golden_3way_simple() -> None:
    """Golden: 3-way branch matches PRP-2225 §Geometry algorithm sketch shape."""
    out = _render_out(siblings=[(3, "a", "pass"), (3, "b", "fail"), (3, "c", "esc")])
    rendered = "\n".join(out.lines)
    # Three tees in parent row, three labels, three sibling boxes, one join.
    assert rendered.count("┬") == 3
    assert "pass" in rendered and "fail" in rendered and "esc" in rendered
    assert "┼" in rendered
    _assert_uniform_width(out)


def test_golden_4way_at_hard_cap() -> None:
    """Golden: 4-way (the renderer's hard cap) renders without raising."""
    out = _render_out(
        siblings=[
            (3, "a", "p"),
            (3, "b", "f"),
            (3, "c", "e"),
            (3, "d", "x"),
        ]
    )
    rendered = "\n".join(out.lines)
    assert rendered.count("┬") == 4
    assert "┼" in rendered
    _assert_uniform_width(out)


def test_golden_dangling() -> None:
    """Golden: terminal branch (no convergence) renders without join row."""
    out = _render_out(
        siblings=[(3, "a", "end1"), (3, "b", "end2")],
        converges_to=None,
        converges_to_text=None,
    )
    rendered = "\n".join(out.lines)
    assert "┼" not in rendered  # no join
    assert "end1" in rendered and "end2" in rendered
    _assert_uniform_width(out)


def test_golden_cjk_truncation() -> None:
    """Golden: CJK label visibly truncated via wcwidth-aware cap."""
    long_cjk = "通过失败处理理理"  # 8×2 = 16 cells, exceeds 12 cap
    out = _render_out(siblings=[(3, "a", long_cjk), (3, "b", "ok")])
    rendered = "\n".join(out.lines)
    # Original full label not present; truncation marker present.
    assert long_cjk not in rendered
    assert "ok" in rendered
    _assert_uniform_width(out)


def test_golden_audit_ledger_fixture() -> None:
    """Golden: PRP-2225 Audit Ledger 3-way fixture (replaces R1 manual eyeball).

    Hand-crafted from PRP-2225 §"Geometry algorithm sketch" (PRP-2225:105-109).
    Phase 4 re-asserts the same output through the full nested renderer stack.

    Tightened per Gemini PR #69 R1 advisory: also asserts uniform line
    widths. Pre-fix the CJK sibling texts produced rows 5 cells too wide
    on the body row, breaking I2 — this test (with width assertion) would
    have caught the bug that Gemini found via manual render.
    """
    out = render_branch(
        _make_input(
            siblings=[
                (3, "a", "通过"),  # CJK label — pass
                (3, "b", "失败"),  # CJK label — fail
                (3, "c", "升级"),  # CJK label — escalate
            ],
            sibling_texts=[
                "五类 No Silent",
                "Entry 完整性",
                "Challenge 入口",
            ],
            converges_to=4,
            converges_to_text="Audit Ledger Entry",
        )
    )
    rendered = "\n".join(out.lines)
    # Three tees + three labels + three sibling boxes + join + convergence.
    assert rendered.count("┬") == 3
    assert "通过" in rendered
    assert "失败" in rendered
    assert "升级" in rendered
    assert "┼" in rendered
    # Width-uniformity assertion — the regression guard for Gemini's bug.
    widths = {wcwidth.wcswidth(line) for line in out.lines}
    assert len(widths) == 1, (
        f"Audit Ledger render has non-uniform line widths: {widths}\n"
        + "\n".join(f"  ({wcwidth.wcswidth(line)}) {line}" for line in out.lines)
    )
