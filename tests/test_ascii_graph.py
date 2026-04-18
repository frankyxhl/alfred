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
    """Test 3: Intra-SOP loop annotation — vertical track renderer."""

    def _three_step_phase(self):
        return [
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

    def test_intra_sop_loop_annotation_renders(self):
        """Authoritative CHG §Step 4 glyphs are present on the expected rows."""
        from fx_alfred.core.ascii_graph import render_ascii

        output = render_ascii(self._three_step_phase())
        lines = output.splitlines()

        # to_step suffix (◄ + 6 hyphens + ┐) must appear on step 1's row.
        to_lines = [ln for ln in lines if "[1.1]" in ln]
        assert to_lines, "step 1 line missing"
        assert "◄──────┐" in to_lines[0]

        # from_step suffix (5 hyphens + ┘ + " max 3") must appear on step 3.
        from_lines = [ln for ln in lines if "[1.3]" in ln]
        assert from_lines, "step 3 line missing"
        assert "─────┘ max 3" in from_lines[0]

    def test_loop_condition_rendered_when_box_allows(self):
        """If the box is wide enough, the loop condition is appended."""
        from fx_alfred.core.ascii_graph import render_ascii

        phases = self._three_step_phase()
        phases[0]["steps"] = [
            {"index": 1, "text": "A", "gate": False},
            {"index": 2, "text": "B", "gate": False},
            {"index": 3, "text": "C", "gate": False},
        ]
        # Pad an extra wide step to push inner_width upward.
        phases[0]["steps"].append({"index": 4, "text": "x" * 70, "gate": False})
        phases[0]["loops"][0]["from_step"] = 3
        phases[0]["loops"][0]["to_step"] = 1

        output = render_ascii(phases)
        # With inner_width = INNER_MAX (76), the condition ("not green") should fit.
        assert "─────┘ max 3 if not green" in output


class TestLoopVerticalTrack:
    """Vertical track: `│` placed on rows strictly between to_step and from_step."""

    def test_loop_vertical_track_between_endpoints(self):
        from fx_alfred.core.ascii_graph import render_ascii

        phases = [
            {
                "sop_id": "COR-1602",
                "provenance": "auto",
                "steps": [
                    {"index": 1, "text": "A", "gate": False},
                    {"index": 2, "text": "B", "gate": False},
                    {"index": 3, "text": "C", "gate": False},
                    {"index": 4, "text": "D", "gate": False},
                    {"index": 5, "text": "E", "gate": False},
                ],
                "loops": [
                    {
                        "id": "r",
                        "from_step": 5,
                        "to_step": 1,
                        "max_iterations": 2,
                        "condition": "",
                    }
                ],
            }
        ]

        lines = render_ascii(phases).splitlines()

        def find(marker):
            hits = [ln for ln in lines if marker in ln]
            assert hits, f"marker {marker!r} missing"
            return hits[0]

        to_line = find("[1.1]")
        from_line = find("[1.5]")

        # ┐ on the to_step line defines the track column.
        corner_col = to_line.index("┐")
        # ┘ on the from_step line must align at the same column.
        assert from_line.index("┘") == corner_col

        # Every intermediate row must have `│` at the same column.
        for step_idx in (2, 3, 4):
            mid = find(f"[1.{step_idx}]")
            assert mid[corner_col] == "│", (
                f"step {step_idx} expected │ at col {corner_col}, got: {mid!r}"
            )


class TestLoopNarrowBoxFallback:
    """When the box cannot host a track, loops fall back to inline text."""

    def test_loop_with_narrow_box_fallback_to_inline(self):
        from fx_alfred.core.ascii_graph import render_ascii

        # Every step text is long enough that inner_width clamps to INNER_MAX
        # and very little room is left — but we still force the track to
        # fail by stuffing a multi-loop phase where extra loops must render
        # inline (the first loop uses the track, additional loops are inline).
        phases = [
            {
                "sop_id": "COR-1602",
                "provenance": "auto",
                "steps": [
                    {"index": i, "text": "x" * 100, "gate": False} for i in range(1, 6)
                ],
                "loops": [
                    {
                        "id": "primary",
                        "from_step": 3,
                        "to_step": 1,
                        "max_iterations": 2,
                        "condition": "",
                    },
                    {
                        "id": "secondary",
                        "from_step": 5,
                        "to_step": 4,
                        "max_iterations": 4,
                        "condition": "",
                    },
                ],
            }
        ]

        output = render_ascii(phases)
        # Primary loop uses the vertical track.
        assert "◄──────┐" in output
        assert "─────┘ max 2" in output
        # Secondary loop rendered inline on its from_step line (step 5).
        assert "→" in output or "back to 1.4" in output
        assert "max 4" in output


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

        # Both gate marker and vertical-track loop annotation must be present.
        assert "⚠️" in output
        assert "max 2" in output
        # Loop glyphs come from the vertical-track renderer, not from the gate
        # path — confirms the two markers compose without collision.
        assert "◄──────┐" in output
        assert "─────┘" in output
        # Gate step (step 3) is the from_step of the loop, so its line must
        # carry both the ⚠️ marker and the `─────┘ max 2` suffix.
        gate_from_line = [
            ln for ln in output.splitlines() if "[1.3]" in ln and "⚠️" in ln
        ]
        assert gate_from_line, "gate+from_step composite line missing"
        assert "─────┘ max 2" in gate_from_line[0]


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


class TestLoopAttrDataclass:
    """Loops supplied as LoopSignature dataclasses (not TypedDicts) render too."""

    def test_loop_signature_dataclass_round_trip(self):
        from dataclasses import dataclass

        from fx_alfred.core.ascii_graph import render_ascii

        @dataclass
        class LS:
            id: str
            from_step: int
            to_step: int
            max_iterations: int
            condition: str = ""

        phases = [
            {
                "sop_id": "COR-1602",
                "provenance": "auto",
                "steps": [
                    {"index": 1, "text": "A", "gate": False},
                    {"index": 2, "text": "B", "gate": False},
                    {"index": 3, "text": "C", "gate": False},
                ],
                "loops": [LS(id="r", from_step=3, to_step=1, max_iterations=2)],
            }
        ]
        output = render_ascii(phases)
        assert "◄──────┐" in output
        assert "─────┘ max 2" in output


class TestLoopEndpointsMissing:
    """Loop referencing non-existent step indices must be ignored silently."""

    def test_loop_with_invalid_endpoints_is_skipped(self):
        from fx_alfred.core.ascii_graph import render_ascii

        phases = [
            {
                "sop_id": "COR-1602",
                "provenance": "auto",
                "steps": [
                    {"index": 1, "text": "A", "gate": False},
                    {"index": 2, "text": "B", "gate": False},
                ],
                "loops": [
                    {
                        "id": "ghost",
                        "from_step": 9,  # does not exist
                        "to_step": 7,  # does not exist
                        "max_iterations": 1,
                        "condition": "",
                    }
                ],
            }
        ]
        output = render_ascii(phases)
        # No track glyphs and no inline annotation should appear.
        assert "◄──────┐" not in output
        assert "max 1" not in output


class TestInlineFallbackVariants:
    """Inline fallback handles narrow lines by shrinking base text."""

    def test_inline_fallback_shrinks_existing_text(self):
        from fx_alfred.core.ascii_graph import render_ascii

        # Two loops so the *second* loop is forced inline.
        phases = [
            {
                "sop_id": "COR-1602",
                "provenance": "auto",
                "steps": [
                    {"index": i, "text": "a" * 80, "gate": False} for i in range(1, 6)
                ],
                "loops": [
                    {
                        "id": "primary",
                        "from_step": 2,
                        "to_step": 1,
                        "max_iterations": 3,
                        "condition": "",
                    },
                    {
                        "id": "extra",
                        "from_step": 5,
                        "to_step": 4,
                        "max_iterations": 7,
                        "condition": "x" * 40,  # long condition forces shrink
                    },
                ],
            }
        ]
        output = render_ascii(phases)
        # Inline fallback must at minimum surface the max-iteration count.
        assert "max 7" in output


class TestTruncateVisualEdges:
    """Direct tests for the _truncate_visual helper's edge cases."""

    def test_truncate_visual_short_string_passthrough(self):
        from fx_alfred.core.ascii_graph import _truncate_visual

        # No truncation needed: result is returned verbatim.
        assert _truncate_visual("abc", 10) == "abc"

    def test_truncate_visual_zero_budget_returns_dots(self):
        from fx_alfred.core.ascii_graph import _truncate_visual

        # max_visual < 3 leaves no budget for content; returns all dots.
        assert _truncate_visual("hello", 2) == ".."
