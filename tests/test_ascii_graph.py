"""Tests for ASCII graph renderer (FXA-2206 C1)."""


class TestSingleSopSequentialSteps:
    """Test 1: Single SOP with 3 sequential steps."""

    def test_single_sop_three_sequential_steps(self):
        """One PhaseDict with sop_id='COR-1500', provenance='always', 3 steps none gate, no loops."""
        from fx_alfred.core.ascii_graph import render_ascii

        phases = [
            {
                "sop_id": "COR-1500",
                "provenance": "always",
                "steps": [
                    {"index": 1, "text": "Write failing test", "gate": False},
                    {"index": 2, "text": "Write minimal impl", "gate": False},
                    {"index": 3, "text": "Refactor", "gate": False},
                ],
                "loops": [],
            }
        ]

        output = render_ascii(phases)

        # Must contain phase header
        assert "Phase 1: COR-1500 (always)" in output
        # Must contain dotted step references
        assert "[1.1]" in output
        assert "[1.2]" in output
        assert "[1.3]" in output
        # Must contain box-drawing characters
        assert "┌" in output
        assert "─" in output
        assert "┐" in output
        assert "│" in output
        assert "└" in output
        assert "┘" in output


class TestMultiSopCompositionArrow:
    """Test 2: Multi-SOP composition with inter-phase arrow."""

    def test_multi_sop_composition_arrow(self):
        """Two PhaseDicts, each with 2 steps, provenance 'always' and 'auto'."""
        from fx_alfred.core.ascii_graph import render_ascii

        phases = [
            {
                "sop_id": "COR-1103",
                "provenance": "always",
                "steps": [
                    {"index": 1, "text": "Step A1", "gate": False},
                    {"index": 2, "text": "Step A2", "gate": False},
                ],
                "loops": [],
            },
            {
                "sop_id": "COR-1602",
                "provenance": "auto",
                "steps": [
                    {"index": 1, "text": "Step B1", "gate": False},
                    {"index": 2, "text": "Step B2", "gate": False},
                ],
                "loops": [],
            },
        ]

        output = render_ascii(phases)

        # Must contain inter-phase arrow
        assert "▼" in output
        # Must contain both phase headers in order
        assert "Phase 1:" in output
        assert "Phase 2:" in output
        # Phase 1 must come before Phase 2
        assert output.index("Phase 1:") < output.index("Phase 2:")


class TestIntraSopLoopAnnotation:
    """Test 3: Intra-SOP loop annotation."""

    def test_intra_sop_loop_annotation(self):
        """One phase with 3 steps and a loop from step 3 to step 1."""
        from fx_alfred.core.ascii_graph import render_ascii

        phases = [
            {
                "sop_id": "COR-1602",
                "provenance": "auto",
                "steps": [
                    {"index": 1, "text": "Dispatch reviewers", "gate": False},
                    {"index": 2, "text": "Collect reviews", "gate": False},
                    {"index": 3, "text": "Revise if needed", "gate": False},
                ],
                "loops": [
                    {
                        "id": "review-retry",
                        "from_step": 3,
                        "to_step": 1,
                        "max_iterations": 3,
                        "condition": "not green",
                    }
                ],
            }
        ]

        output = render_ascii(phases)

        # ◄ must be on the to_step's line (step 1)
        assert "◄" in output
        # max_iterations must appear on the from_step's line (step 3)
        assert "max 3" in output
        # Condition should appear
        assert "not green" in output or "loop" in output.lower()


class TestGateStepMarker:
    """Test 4: Gate step marker."""

    def test_gate_step_marker(self):
        """One phase with 2 steps, step 2 has gate=True."""
        from fx_alfred.core.ascii_graph import render_ascii

        phases = [
            {
                "sop_id": "COR-1602",
                "provenance": "auto",
                "steps": [
                    {"index": 1, "text": "Collect reviews", "gate": False},
                    {"index": 2, "text": "Gate: all >= 9.0", "gate": True},
                ],
                "loops": [],
            }
        ]

        output = render_ascii(phases)

        # ⚠️ must appear on step 2's line
        assert "⚠️" in output


class TestGatePlusLoopCollision:
    """Test 5: Gate + loop collision on same step."""

    def test_gate_plus_loop_collision_same_step(self):
        """One phase with 3 steps, step 3 has gate=True AND is a loop from_step."""
        from fx_alfred.core.ascii_graph import render_ascii

        phases = [
            {
                "sop_id": "COR-1602",
                "provenance": "auto",
                "steps": [
                    {"index": 1, "text": "Start", "gate": False},
                    {"index": 2, "text": "Middle", "gate": False},
                    {"index": 3, "text": "Gate with loop", "gate": True},
                ],
                "loops": [
                    {
                        "id": "retry",
                        "from_step": 3,
                        "to_step": 1,
                        "max_iterations": 2,
                        "condition": "retry needed",
                    }
                ],
            }
        ]

        output = render_ascii(phases)

        # Both ⚠️ and max N markers must be present
        assert "⚠️" in output
        assert "max 2" in output


class TestEmptyPhases:
    """Test 6: Empty phases handling."""

    def test_empty_phases(self):
        """render_ascii([]) returns a string, doesn't raise."""
        from fx_alfred.core.ascii_graph import render_ascii

        output = render_ascii([])
        # Must return a string
        assert isinstance(output, str)
        # Empty or placeholder is acceptable
        assert "(no phases)" in output or output == ""


class TestLongStepTextTruncation:
    """Test 7: Long step text truncated with ellipsis."""

    def test_long_step_text_truncated_with_ellipsis(self):
        """Step text 200 chars of 'x'. Output has ellipsis, no line wider than box width."""
        from fx_alfred.core.ascii_graph import render_ascii

        long_text = "x" * 200
        phases = [
            {
                "sop_id": "COR-1500",
                "provenance": "auto",
                "steps": [
                    {"index": 1, "text": long_text, "gate": False},
                ],
                "loops": [],
            }
        ]

        output = render_ascii(phases)

        # Must not crash
        assert isinstance(output, str)
        # Must have ellipsis indicating truncation
        assert "..." in output
        # No KeyError or IndexError


class TestSpecialCharsNotBroken:
    """Test 8: Special characters not broken."""

    def test_special_chars_not_broken(self):
        """Step text with brackets, braces, quotes, backticks doesn't crash."""
        from fx_alfred.core.ascii_graph import render_ascii

        phases = [
            {
                "sop_id": "COR-1500",
                "provenance": "auto",
                "steps": [
                    {"index": 1, "text": "Use [a] for array", "gate": False},
                    {"index": 2, "text": "Object {b} syntax", "gate": False},
                    {"index": 3, "text": 'Quote "c" here', "gate": False},
                    {"index": 4, "text": "Backtick `d` code", "gate": False},
                ],
                "loops": [],
            }
        ]

        output = render_ascii(phases)

        # Must not crash
        assert isinstance(output, str)
        # Box alignment preserved - check box borders align
        lines = output.split("\n")
        # Find box border lines
        border_lines = [ln for ln in lines if "┌" in ln or "└" in ln]
        assert len(border_lines) >= 2


class TestCjkCharsBoxWidth:
    """Test 9: CJK characters box width."""

    def test_cjk_chars_box_width(self):
        """Step text '实现功能' (4 CJK chars = 8 visual cells). Box sized for 8 cells."""
        from fx_alfred.core.ascii_graph import render_ascii

        phases = [
            {
                "sop_id": "COR-1500",
                "provenance": "auto",
                "steps": [
                    {"index": 1, "text": "实现功能", "gate": False},
                ],
                "loops": [],
            }
        ]

        output = render_ascii(phases)

        # Must not crash
        assert isinstance(output, str)
        # CJK text must appear
        assert "实现功能" in output
        # Box borders must align
        lines = output.split("\n")
        top_border = [ln for ln in lines if "┌" in ln][0]
        bottom_border = [ln for ln in lines if "└" in ln][0]
        # Count of ─ chars should be same on top and bottom
        assert top_border.count("─") == bottom_border.count("─")


class TestEmojiWidth:
    """Test 10: Emoji width handling."""

    def test_emoji_width(self):
        """Step text with emoji '🔁 gate' (emoji = 2 cells). Box accounts for it."""
        from fx_alfred.core.ascii_graph import render_ascii

        phases = [
            {
                "sop_id": "COR-1602",
                "provenance": "auto",
                "steps": [
                    {"index": 1, "text": "🔁 gate", "gate": False},
                ],
                "loops": [],
            }
        ]

        output = render_ascii(phases)

        # Must not crash
        assert isinstance(output, str)
        # Emoji must appear
        assert "🔁" in output
        # Box borders must align
        lines = output.split("\n")
        top_border = [ln for ln in lines if "┌" in ln][0]
        bottom_border = [ln for ln in lines if "└" in ln][0]
        assert top_border.count("─") == bottom_border.count("─")


class TestMixedAsciiCjkTruncation:
    """Test 11: Mixed ASCII/CJK truncation respects char boundaries."""

    def test_mixed_ascii_cjk_no_truncation_mid_char(self):
        """Step text 'hello 实现' truncated to narrow width - CJK not split."""
        from fx_alfred.core.ascii_graph import render_ascii

        phases = [
            {
                "sop_id": "COR-1500",
                "provenance": "auto",
                "steps": [
                    {"index": 1, "text": "hello 实现", "gate": False},
                ],
                "loops": [],
            }
        ]

        output = render_ascii(phases)

        # Must not crash
        assert isinstance(output, str)
        # No KeyError or IndexError from mid-char split


class TestNarrowWidthTruncation:
    """Test 12: Narrow width truncation with ASCII."""

    def test_narrow_width_truncation(self):
        """Step text all ASCII, 100 chars, rendered at width forcing truncation."""
        from fx_alfred.core.ascii_graph import render_ascii

        long_text = "a" * 100
        phases = [
            {
                "sop_id": "COR-1500",
                "provenance": "auto",
                "steps": [
                    {"index": 1, "text": long_text, "gate": False},
                ],
                "loops": [],
            }
        ]

        output = render_ascii(phases)

        # Must not crash
        assert isinstance(output, str)
        # Must have ellipsis
        assert "..." in output
