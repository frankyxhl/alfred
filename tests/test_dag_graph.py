"""Tests for core/dag_graph.py — nested ASCII DAG renderer (FXA-2218)."""

from __future__ import annotations


from fx_alfred.core.dag_graph import render_dag
from fx_alfred.core.workflow import LoopSignature


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _step(index: int, text: str, gate: bool = False) -> dict:
    return {"index": index, "text": text, "gate": gate}


def _phase(
    sop_id: str, steps: list[dict], loops: list[LoopSignature] | None = None
) -> dict:
    return {"sop_id": sop_id, "steps": steps, "loops": loops or []}


# ---------------------------------------------------------------------------
# Basic rendering
# ---------------------------------------------------------------------------


class TestSingleSopNested:
    def test_single_sop_three_steps_produces_nested_structure(self):
        phases = [
            _phase(
                "COR-1500",
                [_step(1, "Red"), _step(2, "Green"), _step(3, "Refactor")],
            ),
        ]
        out = render_dag(phases)
        lines = out.split("\n")

        # Outer phase box present
        assert lines[0].startswith("┌") and lines[0].endswith("┐")
        assert lines[-1].startswith("└") and lines[-1].endswith("┘")

        # Phase header line
        assert "Phase 1: COR-1500" in lines[1]

        # Three inner step-boxes: one ┌──┐ line per step
        step_top_count = sum(
            1 for line in lines if "┌─" in line and line.strip().startswith("│")
        )
        assert step_top_count == 3

        # Steps rendered with dotted numbering
        assert "1.1 Red" in out
        assert "1.2 Green" in out
        assert "1.3 Refactor" in out

    def test_single_sop_no_inter_phase_arrow(self):
        phases = [_phase("COR-1500", [_step(1, "Solo")])]
        out = render_dag(phases)
        # Inter-phase ▼ appears only between phase boxes
        assert out.count("▼") == 0


class TestMultiSopNested:
    def test_two_sops_inter_phase_arrow(self):
        phases = [
            _phase("COR-1500", [_step(1, "A"), _step(2, "B")]),
            _phase("COR-1602", [_step(1, "C")]),
        ]
        out = render_dag(phases)
        out.split("\n")

        # At least one ▼ between the two phase boxes (plus 1 intra-phase ▼
        # between step 1 and step 2 of phase 1).
        assert out.count("▼") >= 2

        # Phase 2 appears AFTER phase 1 in output
        idx1 = out.index("Phase 1: COR-1500")
        idx2 = out.index("Phase 2: COR-1602")
        assert idx1 < idx2


# ---------------------------------------------------------------------------
# Cross-SOP back-edge track
# ---------------------------------------------------------------------------


class TestCrossSopBackEdge:
    def test_cross_sop_loop_emits_arrow_in_and_out_glyphs(self):
        phases = [
            _phase("COR-1500", [_step(1, "Red"), _step(2, "Refactor")]),
            _phase(
                "COR-1602",
                [_step(1, "Dispatch"), _step(2, "Gate", gate=True)],
                loops=[
                    LoopSignature(
                        id="cx",
                        from_step=2,
                        to_step="COR-1500.2",
                        max_iterations=3,
                        condition="if fail",
                    )
                ],
            ),
        ]
        out = render_dag(phases)

        # Arrow-in glyph `◄───┐` at target row (COR-1500.2)
        assert "◄───┐" in out
        # Arrow-out glyph `───┘` at source row (COR-1602.2)
        assert "───┘" in out
        # Max-iterations annotation present on the source row
        assert "max 3" in out
        # Condition text used verbatim (no "if if" duplication)
        assert "if if" not in out
        assert "if fail" in out

    def test_cross_sop_track_extends_outside_phase_box(self):
        phases = [
            _phase("COR-1500", [_step(1, "Red"), _step(2, "Refactor")]),
            _phase(
                "COR-1602",
                [_step(1, "Gate", gate=True)],
                loops=[
                    LoopSignature(
                        id="cx",
                        from_step=1,
                        to_step="COR-1500.2",
                        max_iterations=3,
                        condition="",
                    )
                ],
            ),
        ]
        out = render_dag(phases)
        lines = out.split("\n")

        # Some line has the track pipe `│` to the RIGHT of the phase-box
        # right border (i.e., appears in a column past _PHASE_BOX_WIDTH).
        # We check by counting: at least one line has at least 2 `│`s
        # appearing with one deep in the tail past col 55.
        track_cols = []
        for line in lines:
            # Find positions of `│` characters.
            positions = [i for i, c in enumerate(line) if c == "│"]
            if positions and positions[-1] > 55:
                track_cols.append(positions[-1])
        assert len(track_cols) > 0, "No track pipe found past phase-box right border"

    def test_cross_sop_loop_ignored_if_target_not_in_plan(self):
        """If the cross-SOP target SOP isn't composed, renderer silently skips
        the loop (af plan would have already raised D4 upstream, so this is
        purely defensive)."""
        phases = [
            _phase(
                "COR-1602",
                [_step(1, "Gate", gate=True)],
                loops=[
                    LoopSignature(
                        id="cx",
                        from_step=1,
                        to_step="COR-9999.1",
                        max_iterations=3,
                        condition="",
                    )
                ],
            ),
        ]
        out = render_dag(phases)
        # No back-edge glyphs (the arrow-in `◄` and the " max N" annotation
        # are unique to rendered loops — step-box corners alone use `┘` too).
        assert "◄" not in out
        assert "max 3" not in out


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_phases_returns_empty_string(self):
        assert render_dag([]) == ""

    def test_phase_with_no_steps_skipped(self):
        phases = [
            _phase("COR-EMPTY", []),
            _phase("COR-1500", [_step(1, "A")]),
        ]
        out = render_dag(phases)
        # COR-EMPTY is skipped (no steps); positional phase_num is preserved
        # (COR-1500 at list index 1 renders as "Phase 2", step "2.1 A").
        assert "COR-EMPTY" not in out
        assert "Phase 2: COR-1500" in out
        assert "2.1 A" in out

    def test_long_step_text_truncated(self):
        long_text = "A" * 120
        phases = [_phase("COR-1500", [_step(1, long_text)])]
        out = render_dag(phases)
        # Full 120-char text should not appear
        assert long_text not in out
        # Truncation indicator
        assert "..." in out


# ---------------------------------------------------------------------------
# FXA-2218 R2 fixes — multi-loop inline fallback, intra-SOP annotations,
# orphan-arrow fix
# ---------------------------------------------------------------------------


class TestMultiLoopInlineFallback:
    def test_two_cross_sop_loops_fall_back_to_inline_annotations(self):
        """With 2+ cross-SOP loops, renderer falls back to inline
        annotations on each source step's content row — avoiding the
        multi-track overlap corruption bug caught at CHG review R1."""
        phases = [
            _phase(
                "COR-1500",
                [_step(1, "A"), _step(2, "B")],
            ),
            _phase(
                "COR-1600",
                [_step(1, "C")],
                loops=[
                    LoopSignature(
                        id="cx1",
                        from_step=1,
                        to_step="COR-1500.1",
                        max_iterations=3,
                        condition="if fail A",
                    )
                ],
            ),
            _phase(
                "COR-1700",
                [_step(1, "D")],
                loops=[
                    LoopSignature(
                        id="cx2",
                        from_step=1,
                        to_step="COR-1500.2",
                        max_iterations=5,
                        condition="if fail B",
                    )
                ],
            ),
        ]
        out = render_dag(phases)

        # No vertical track glyphs when falling back to inline.
        assert "◄───┐" not in out
        # Both annotations visible, fully intact (no overlap corruption).
        assert "🔁 → COR-1500.1 max 3 if fail A" in out
        assert "🔁 → COR-1500.2 max 5 if fail B" in out

    def test_single_cross_sop_loop_still_uses_vertical_track(self):
        """Single-loop case keeps the full track rendering (R1 behaviour)."""
        phases = [
            _phase("COR-1500", [_step(1, "A"), _step(2, "B")]),
            _phase(
                "COR-1600",
                [_step(1, "C")],
                loops=[
                    LoopSignature(
                        id="cx",
                        from_step=1,
                        to_step="COR-1500.2",
                        max_iterations=3,
                        condition="",
                    )
                ],
            ),
        ]
        out = render_dag(phases)

        # Vertical track glyphs present.
        assert "◄───┐" in out
        assert "───┘" in out
        # No inline fallback annotation for the single-loop case.
        assert "🔁 → COR-1500" not in out


class TestIntraSopInlineAnnotation:
    def test_intra_sop_loop_emits_inline_annotation_line(self):
        """Intra-SOP loops render as a `🔁 → N.M max K cond` annotation line
        immediately below the source step's box, inside the phase box.
        Addresses Codex CHG R1 blocker: no silent omission in the default
        nested layout."""
        phases = [
            _phase(
                "COR-1602",
                [_step(1, "Dispatch"), _step(2, "Score"), _step(3, "Gate", gate=True)],
                loops=[
                    LoopSignature(
                        id="retry",
                        from_step=3,
                        to_step=1,
                        max_iterations=3,
                        condition="if fail",
                    )
                ],
            ),
        ]
        out = render_dag(phases)
        assert "🔁 → 1.1 max 3 if fail" in out

    def test_intra_sop_loop_emits_inside_phase_box(self):
        """The annotation line must be inside the phase box (between the
        step-box bottom and the phase-box bottom border)."""
        phases = [
            _phase(
                "COR-1602",
                [_step(1, "A"), _step(2, "B")],
                loops=[
                    LoopSignature(
                        id="r",
                        from_step=2,
                        to_step=1,
                        max_iterations=2,
                        condition="",
                    )
                ],
            ),
        ]
        out = render_dag(phases)
        lines = out.split("\n")
        # Find the annotation line and verify it's wrapped in `│ ... │`
        ann_line = next(line for line in lines if "🔁 →" in line)
        assert ann_line.startswith("│")
        assert ann_line.endswith("│")


class TestSameStepMultiLoop:
    def test_same_step_two_intra_sop_loops_both_render(self):
        """A single step with two outbound intra-SOP loops renders both —
        no silent data loss (FXA-2218 R3 fix for the dict-overwrite bug)."""
        phases = [
            _phase(
                "COR-1602",
                [_step(1, "Start"), _step(2, "Verify"), _step(3, "Gate", gate=True)],
                loops=[
                    LoopSignature(
                        id="r1",
                        from_step=3,
                        to_step=1,
                        max_iterations=3,
                        condition="if code fail",
                    ),
                    LoopSignature(
                        id="r2",
                        from_step=3,
                        to_step=2,
                        max_iterations=5,
                        condition="if verify fail",
                    ),
                ],
            ),
        ]
        out = render_dag(phases)
        # Both loops present in the output (may be truncated for display
        # but the "target step" portion of each should remain visible).
        assert "🔁 → 1.1 max 3" in out
        # Second loop's target + max shows up (condition may truncate).
        assert "🔁 → 1.2 max 5" in out
        # Joiner between the two annotations
        assert " ; " in out

    def test_same_step_two_cross_sop_loops_both_render(self):
        """Same step with two cross-SOP loops → inline fallback preserves
        both via " ; " joiner (FXA-2218 R3 fix)."""
        phases = [
            _phase("COR-1500", [_step(1, "A"), _step(2, "B")]),
            _phase(
                "COR-1602",
                [_step(1, "Gate", gate=True)],
                loops=[
                    LoopSignature(
                        id="cx1",
                        from_step=1,
                        to_step="COR-1500.1",
                        max_iterations=3,
                        condition="if code fail",
                    ),
                    LoopSignature(
                        id="cx2",
                        from_step=1,
                        to_step="COR-1500.2",
                        max_iterations=5,
                        condition="if review fail",
                    ),
                ],
            ),
        ]
        out = render_dag(phases)
        assert "🔁 → COR-1500.1 max 3 if code fail" in out
        assert "🔁 → COR-1500.2 max 5 if review fail" in out
        # Joined on same row with " ; "
        assert " ; " in out


class TestVisualWidthOverlay:
    def test_cross_sop_arrow_aligned_when_target_row_has_cjk(self):
        """Cross-SOP track arrow-in must land at the correct VISUAL column
        even when the target step row contains double-width glyphs. Prior
        to the visual-width-aware _overwrite_at fix, character indexing
        collided with visual indexing and the arrow drifted right by the
        double-width delta (PR #59 Codex review P2 #3)."""
        phases = [
            _phase(
                "COR-1500",
                [_step(1, "中文测试"), _step(2, "B")],
            ),
            _phase(
                "COR-1602",
                [_step(1, "Gate", gate=True)],
                loops=[
                    LoopSignature(
                        id="cx",
                        from_step=1,
                        to_step="COR-1500.1",
                        max_iterations=3,
                        condition="",
                    )
                ],
            ),
        ]
        out = render_dag(phases)
        lines = out.split("\n")

        # Find the CJK target row and the track pipe rows below it.
        target_row = next(line for line in lines if "中文测试" in line)
        # The target row must contain the arrow-in glyph.
        assert "◄───┐" in target_row

        # Compute VISUAL column of the '┐' glyph on target row — must match
        # the visual column of '│' pipe on the following row (which we know
        # is ASCII-only and character-aligned).
        def _visual_col_of(line: str, ch: str) -> int:
            from fx_alfred.core.ascii_graph import _visual_width

            pos = 0
            for c in line:
                if c == ch:
                    return pos
                pos += _visual_width(c)
            return -1

        target_corner_col = _visual_col_of(target_row, "┐")
        # The intermediate pipe row: find a line with track pipe `│` after
        # the phase-box right edge. The very next line should have the pipe
        # on the same column as the corner.
        next_row_idx = lines.index(target_row) + 1
        # Find all `│` positions in that row; the last one is the track pipe.
        next_row = lines[next_row_idx]
        pipe_positions = []
        pos = 0
        from fx_alfred.core.ascii_graph import _visual_width

        for c in next_row:
            if c == "│":
                pipe_positions.append(pos)
            pos += _visual_width(c)

        # Track pipe is the rightmost `│` on the intermediate row.
        assert pipe_positions, "No track pipe found on intermediate row"
        track_pipe_col = pipe_positions[-1]

        assert target_corner_col == track_pipe_col, (
            f"Target-row '┐' at visual col {target_corner_col} but track pipe "
            f"at visual col {track_pipe_col} — overlay is not visual-width-aware"
        )


class TestNoOrphanArrowOnTrailingEmptyPhase:
    def test_last_phase_with_no_steps_skipped_without_orphan_arrow(self):
        """If the last phase has no Steps section, the inter-phase ▼ that
        would otherwise point to it must not be emitted (R2 fix for
        Gemini-flagged orphan-arrow bug)."""
        phases = [
            _phase("COR-1500", [_step(1, "A"), _step(2, "B")]),
            _phase("COR-EMPTY", []),  # has no steps — must be skipped
        ]
        out = render_dag(phases)
        lines = out.split("\n")
        # Last non-empty line is a phase-box bottom border, not an arrow.
        non_empty = [ln for ln in lines if ln.strip()]
        assert non_empty[-1].startswith("└"), (
            f"Expected phase-box close as last line; got: {non_empty[-1]!r}"
        )
        # The ▼ count equals the intra-phase arrows only (1 for step1->step2).
        assert out.count("▼") == 1
