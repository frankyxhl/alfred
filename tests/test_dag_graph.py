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
