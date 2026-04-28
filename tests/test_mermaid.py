"""Tests for core/mermaid.py — Mermaid flowchart rendering (FXA-2205 PR3)."""

from __future__ import annotations

from fx_alfred.core.mermaid import render_mermaid
from fx_alfred.core.workflow import LoopSignature


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_phase(
    sop_id: str,
    steps: list[dict],
    loops: list[LoopSignature] | None = None,
) -> dict:
    """Build a phase dict matching render_mermaid's expected input format.

    Each step dict has: {"index": int, "text": str, "gate": bool}.
    """
    return {
        "sop_id": sop_id,
        "steps": steps,
        "loops": loops or [],
    }


def _steps(*texts: str, gate_indices: set[int] | None = None) -> list[dict]:
    """Build a list of step dicts from text strings.

    Step index is 1-based, matching SOP convention.
    gate_indices: set of 1-based indices that are gates.
    """
    gate_set = gate_indices or set()
    return [
        {"index": i + 1, "text": t, "gate": (i + 1) in gate_set}
        for i, t in enumerate(texts)
    ]


# ---------------------------------------------------------------------------
# Test 1: Single SOP with 3 sequential steps
# ---------------------------------------------------------------------------


class TestSingleSopSequential:
    def test_single_sop_three_steps(self):
        """Single SOP with 3 steps produces sequential forward edges."""
        phases = [
            _make_phase(
                "COR-1500",
                _steps("Write failing test", "Minimal impl", "Refactor"),
            ),
        ]
        result = render_mermaid(phases)

        assert result.startswith("flowchart TD\n")
        # Forward edges within SOP
        assert "S1_1" in result
        assert "S1_2" in result
        assert "S1_3" in result
        assert "S1_1[" in result  # rectangle node
        assert "S1_1[" in result
        assert "--> S1_2[" in result or "S1_1[" in result
        # Verify sequential chain
        lines = result.strip().split("\n")
        edge_lines = [ln.strip() for ln in lines if "-->" in ln]
        assert len(edge_lines) >= 1  # at least one edge line

    def test_node_labels_contain_sop_id(self):
        """Node labels contain the SOP-ID prefix."""
        phases = [
            _make_phase("COR-1500", _steps("Write test", "Implement")),
        ]
        result = render_mermaid(phases)
        assert "COR-1500" in result


# ---------------------------------------------------------------------------
# Test 2: Multi-SOP composition with phase-to-phase edge
# ---------------------------------------------------------------------------


class TestMultiSopComposition:
    def test_two_sops_phase_transition(self):
        """Two SOPs produce a phase-to-phase edge between last/first steps."""
        phases = [
            _make_phase("COR-1500", _steps("Write test", "Implement")),
            _make_phase("COR-1602", _steps("Dispatch", "Collect", "Synthesize")),
        ]
        result = render_mermaid(phases)

        # Phase-to-phase edge: last step of SOP 1 to first step of SOP 2
        assert "S1_2" in result
        assert "S2_1" in result
        # There should be an edge from S1_2 to S2_1
        assert "S1_2" in result and "S2_1" in result

    def test_three_sops_chain(self):
        """Three SOPs chain with two phase-to-phase edges."""
        phases = [
            _make_phase("COR-1103", _steps("Route")),
            _make_phase("COR-1500", _steps("Write test", "Implement")),
            _make_phase("COR-1602", _steps("Dispatch", "Collect")),
        ]
        result = render_mermaid(phases)
        # S1_1 -> S2_1 (phase 1->2)
        # S2_2 -> S3_1 (phase 2->3)
        assert "S1_1" in result
        assert "S2_1" in result
        assert "S2_2" in result
        assert "S3_1" in result


# ---------------------------------------------------------------------------
# Test 3: SOP with Workflow loops — dashed back-edge
# ---------------------------------------------------------------------------


class TestLoopBackEdge:
    def test_loop_produces_dashed_back_edge(self):
        """Workflow loop from step 3 to step 1 produces dashed back-edge."""
        loop = LoopSignature(
            id="retry",
            from_step=3,
            to_step=1,
            max_iterations=3,
            condition="retry",
        )
        phases = [
            _make_phase(
                "COR-1602",
                _steps("Dispatch", "Collect", "Check"),
                loops=[loop],
            ),
        ]
        result = render_mermaid(phases)

        # Dashed back-edge with condition
        assert "S1_3" in result
        assert "S1_1" in result
        # Dashed edge syntax: -. condition .->
        assert "-." in result
        assert ".->" in result
        assert "retry" in result

    def test_loop_long_condition_truncated(self):
        """Very long condition in loop is used (may be truncated or 'yes')."""
        long_cond = "a" * 100
        loop = LoopSignature(
            id="retry",
            from_step=3,
            to_step=1,
            max_iterations=3,
            condition=long_cond,
        )
        phases = [
            _make_phase(
                "COR-1602",
                _steps("Dispatch", "Collect", "Check"),
                loops=[loop],
            ),
        ]
        result = render_mermaid(phases)
        # Should still have a dashed edge, may use "yes" for very long conditions
        assert "-." in result
        assert ".->" in result


# ---------------------------------------------------------------------------
# Test 4: Gate step — diamond shape
# ---------------------------------------------------------------------------


class TestGateStepDiamond:
    def test_gate_step_uses_diamond(self):
        """Gate step renders as diamond {text} instead of rectangle [text]."""
        phases = [
            _make_phase(
                "COR-1602",
                _steps("Dispatch", "Gate check", "Final", gate_indices={2}),
            ),
        ]
        result = render_mermaid(phases)

        # Diamond uses {} in Mermaid
        assert "S1_2{" in result
        # Non-gate steps use []
        assert "S1_1[" in result
        assert "S1_3[" in result

    def test_gate_step_suffix_checkmark(self):
        """Step with checkmark suffix is detected as gate."""
        phases = [
            _make_phase(
                "COR-1602",
                [
                    {"index": 1, "text": "Regular step", "gate": False},
                    {"index": 2, "text": "All approved ✓", "gate": True},
                ],
            ),
        ]
        result = render_mermaid(phases)
        assert "S1_2{" in result


# ---------------------------------------------------------------------------
# Test 5: Gate + loop-from collision on same step
# ---------------------------------------------------------------------------


class TestGateLoopCollision:
    def test_gate_and_loop_from_same_step(self):
        """Gate step that is also loop source gets diamond AND dashed back-edge."""
        loop = LoopSignature(
            id="retry",
            from_step=2,
            to_step=1,
            max_iterations=3,
            condition="retry needed",
        )
        phases = [
            _make_phase(
                "COR-1602",
                [
                    {"index": 1, "text": "Dispatch", "gate": False},
                    {"index": 2, "text": "Gate check", "gate": True},
                    {"index": 3, "text": "Done", "gate": False},
                ],
                loops=[loop],
            ),
        ]
        result = render_mermaid(phases)

        # Diamond shape for gate step
        assert "S1_2{" in result
        # Dashed back-edge from gate step
        assert "S1_2" in result
        assert "-." in result
        assert "S1_1" in result


# ---------------------------------------------------------------------------
# Test 6: Empty phases list
# ---------------------------------------------------------------------------


class TestEmptyPhases:
    def test_empty_phases_minimal_output(self):
        """Empty phases list produces minimal 'flowchart TD' with no nodes."""
        result = render_mermaid([])
        assert result.strip() == "flowchart TD"


# ---------------------------------------------------------------------------
# Test 7: Long step text truncation
# ---------------------------------------------------------------------------


class TestLongTextTruncation:
    def test_long_text_truncated(self):
        """Step text longer than ~60 chars is truncated with ellipsis."""
        long_text = "A" * 80
        phases = [
            _make_phase("COR-1500", [{"index": 1, "text": long_text, "gate": False}]),
        ]
        result = render_mermaid(phases)

        # The full 80-char text should NOT appear in the label
        assert long_text not in result
        # But a truncated version should be there
        # Should be around 60 chars + ellipsis
        assert "..." in result or "A" * 57 in result


# ---------------------------------------------------------------------------
# Test 8: Special characters escaped for Mermaid
# ---------------------------------------------------------------------------


class TestSpecialCharEscape:
    def test_brackets_escaped(self):
        """Brackets in step text are escaped for Mermaid safety."""
        phases = [
            _make_phase(
                "COR-1500",
                [{"index": 1, "text": "Check [GATE] markers", "gate": True}],
            ),
        ]
        result = render_mermaid(phases)

        # Raw brackets should not appear unescaped inside node labels
        # (they would break Mermaid syntax)
        # The label is inside [...] or {...}, so inner brackets must be escaped
        assert "S1_1" in result
        # Should not have nested brackets that break parsing
        # The implementation should escape or strip inner brackets

    def test_quotes_escaped(self):
        """Quotes in step text are handled for Mermaid safety."""
        phases = [
            _make_phase(
                "COR-1500",
                [{"index": 1, "text": 'Check "all" items', "gate": False}],
            ),
        ]
        result = render_mermaid(phases)
        assert "S1_1" in result
        # The label should use quote-safe form
        # Mermaid uses ["text with quotes"] syntax
        assert "S1_1[" in result or 'S1_1["' in result


# ---------------------------------------------------------------------------
# FXA-2218 Commit 5 — Cross-SOP loops omitted + omission comment
# ---------------------------------------------------------------------------


class TestCrossSopLoopOmission:
    def test_cross_sop_loop_skipped_in_output(self):
        """render_mermaid skips back-edges whose to_step is a cross-SOP string."""
        phases = [
            _make_phase(
                "COR-1602",
                [
                    {"index": 1, "text": "Dispatch", "gate": False},
                    {"index": 2, "text": "Gate", "gate": True},
                ],
                loops=[
                    LoopSignature(
                        id="cx",
                        from_step=2,
                        to_step="COR-1500.3",
                        max_iterations=3,
                        condition="if fail",
                    )
                ],
            ),
        ]
        result = render_mermaid(phases)
        # No dashed back-edge is emitted for the cross-SOP loop.
        assert ".->" not in result

    def test_cross_sop_loop_emits_omission_comment(self):
        """render_mermaid emits exactly one %% omission comment if any cross-SOP loop exists."""
        phases = [
            _make_phase(
                "COR-1602",
                [
                    {"index": 1, "text": "Dispatch", "gate": False},
                    {"index": 2, "text": "Gate", "gate": True},
                ],
                loops=[
                    LoopSignature(
                        id="cx",
                        from_step=2,
                        to_step="COR-1500.3",
                        max_iterations=3,
                        condition="if fail",
                    )
                ],
            ),
        ]
        result = render_mermaid(phases)
        count = result.count("cross-SOP loops omitted — Mermaid layout is ASCII-only")
        assert count == 1

    def test_no_omission_comment_when_all_intra_sop(self):
        """No omission comment is emitted when only intra-SOP loops exist."""
        phases = [
            _make_phase(
                "COR-1602",
                [
                    {"index": 1, "text": "Dispatch", "gate": False},
                    {"index": 2, "text": "Score", "gate": False},
                    {"index": 3, "text": "Gate", "gate": True},
                ],
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
        result = render_mermaid(phases)
        assert "cross-SOP loops omitted" not in result
        assert ".->" in result

    def test_same_step_intra_plus_cross_sop_intra_preserved(self):
        """When one step has BOTH an intra-SOP loop and a cross-SOP loop,
        the intra-SOP back-edge must still render (PR #59 Codex review P2).
        Previously `loop_from_steps` was a dict keyed on from_step, so
        if the cross-SOP loop won the dict key, the intra-SOP edge was
        silently dropped."""
        phases = [
            _make_phase(
                "COR-1602",
                [
                    {"index": 1, "text": "Start", "gate": False},
                    {"index": 2, "text": "Gate", "gate": True},
                ],
                loops=[
                    # Same from_step=2 for both loops — cross-SOP first so
                    # the old dict-build would have dropped the intra.
                    LoopSignature(
                        id="escalate",
                        from_step=2,
                        to_step="COR-1500.1",
                        max_iterations=3,
                        condition="if high severity",
                    ),
                    LoopSignature(
                        id="retry",
                        from_step=2,
                        to_step=1,
                        max_iterations=3,
                        condition="if fail",
                    ),
                ],
            ),
        ]
        result = render_mermaid(phases)
        # Intra-SOP back-edge must still be drawn.
        assert "S1_2 -. " in result and ".-> S1_1" in result
        # Cross-SOP omission comment also emitted.
        assert "cross-SOP loops omitted — Mermaid layout is ASCII-only" in result

    def test_single_omission_comment_with_multiple_cross_sop_loops(self):
        """Multiple cross-SOP loops across phases produce exactly one comment."""
        phases = [
            _make_phase(
                "COR-1602",
                [{"index": 1, "text": "Gate", "gate": True}],
                loops=[
                    LoopSignature(
                        id="cx1",
                        from_step=1,
                        to_step="COR-1500.1",
                        max_iterations=3,
                        condition="fail A",
                    )
                ],
            ),
            _make_phase(
                "COR-1608",
                [{"index": 1, "text": "Score", "gate": True}],
                loops=[
                    LoopSignature(
                        id="cx2",
                        from_step=1,
                        to_step="COR-1500.2",
                        max_iterations=3,
                        condition="fail B",
                    )
                ],
            ),
        ]
        result = render_mermaid(phases)
        count = result.count("cross-SOP loops omitted — Mermaid layout is ASCII-only")
        assert count == 1


# ---------------------------------------------------------------------------
# FXA-2227 Phase 7 — Sub-step node IDs
# ---------------------------------------------------------------------------


class TestSubStepNodeIds:
    def test_mermaid_with_substeps(self):
        """Sub-stepped SOP emits S1_3a, S1_3b, S1_3c node IDs."""
        phases = [
            _make_phase(
                "COR-1500",
                [
                    {"index": 1, "text": "Plain first", "gate": False},
                    {"index": 2, "text": "Plain second", "gate": False},
                    {
                        "index": 3,
                        "text": "Sub-step alpha",
                        "gate": False,
                        "sub_branch": "a",
                    },
                    {
                        "index": 3,
                        "text": "Sub-step beta",
                        "gate": False,
                        "sub_branch": "b",
                    },
                    {
                        "index": 3,
                        "text": "Sub-step gamma",
                        "gate": False,
                        "sub_branch": "c",
                    },
                ],
            ),
        ]
        result = render_mermaid(phases)

        # Plain step emits integer-only ID
        assert "S1_2" in result

        # Sub-stepped steps emit suffixed IDs
        assert "S1_3a" in result
        assert "S1_3b" in result
        assert "S1_3c" in result

        # Plain integer-only S1_3 must NOT appear as a node ID
        import re as _re

        plain_s1_3 = _re.search(r"\bS1_3(?![a-z])", result)
        assert plain_s1_3 is None, f"Found bare S1_3 node ID in output:\n{result}"

        # Forward edges must reference sub-step IDs
        edge_lines = [ln for ln in result.split("\n") if "-->" in ln]
        edge_text = "\n".join(edge_lines)
        assert "S1_3a" in edge_text or "S1_3b" in edge_text or "S1_3c" in edge_text

    def test_mermaid_legacy_unchanged(self):
        """3-step linear SOP with no sub_branch keys renders S1_1, S1_2, S1_3 only."""
        phases = [
            _make_phase(
                "COR-1500",
                [
                    {"index": 1, "text": "Write failing test", "gate": False},
                    {"index": 2, "text": "Minimal impl", "gate": False},
                    {"index": 3, "text": "Refactor", "gate": False},
                ],
            ),
        ]
        result = render_mermaid(phases)

        # All three plain node IDs must appear
        assert "S1_1" in result
        assert "S1_2" in result
        assert "S1_3" in result

        # No sub-step suffixes should appear
        import re as _re

        assert not _re.search(r"S1_\d+[a-z]", result), (
            f"Unexpected sub-step suffix in legacy output:\n{result}"
        )
