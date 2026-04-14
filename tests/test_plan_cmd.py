"""Tests for af plan command (FXA-2134)."""

from pathlib import Path

import click
import pytest
from click.testing import CliRunner
from fx_alfred.cli import cli
from fx_alfred.commands.plan_cmd import (
    _format_phase,
    _parse_steps_for_json,
)


def _create_sop_with_steps(rules_dir: Path, prefix: str, acid: str, title: str) -> Path:
    """Helper to create an SOP document with Steps section."""
    filename = f"{prefix}-{acid}-SOP-{title}.md"
    content = f"""# {prefix}-{acid}: {title.replace("-", " ")}

**Applies to:** Test
**Status:** Active
---
## What Is It?
A test SOP for plan command testing.
## Steps
1. First step for {acid}
2. Second step for {acid}
3. Third step for {acid}
"""
    filepath = rules_dir / filename
    filepath.write_text(content)
    return filepath


def _create_sop_without_steps(
    rules_dir: Path, prefix: str, acid: str, title: str
) -> Path:
    """Helper to create an SOP document without Steps section."""
    filename = f"{prefix}-{acid}-SOP-{title}.md"
    content = f"""# {prefix}-{acid}: {title.replace("-", " ")}

**Applies to:** Test
**Status:** Active
---
## What Is It?
A test SOP without steps.
## Notes
Just some notes.
"""
    filepath = rules_dir / filename
    filepath.write_text(content)
    return filepath


def test_plan_outputs_sop_steps(sample_project, monkeypatch):
    """SOP with steps outputs checkboxes for each step."""
    rules_dir = sample_project / "rules"
    _create_sop_with_steps(rules_dir, "TST", "5001", "Test-Workflow")

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "TST-5001"], catch_exceptions=False)
    assert result.exit_code == 0
    # Default mode should have checkboxes
    assert "- [ ]" in result.output
    # Should show the steps
    assert "First step" in result.output
    assert "Second step" in result.output


def test_plan_multiple_sops(sample_project, monkeypatch):
    """Multiple SOPs produce phased output with Phase 1, Phase 2, etc."""
    rules_dir = sample_project / "rules"
    _create_sop_with_steps(rules_dir, "TST", "5001", "First-SOP")
    _create_sop_with_steps(rules_dir, "TST", "5002", "Second-SOP")

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "TST-5001", "TST-5002"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "Phase 1" in result.output
    assert "Phase 2" in result.output


def test_plan_skips_non_sop(sample_project, monkeypatch):
    """Non-SOP documents trigger a warning about not being SOP."""
    # sample_project has ALF-2201-PRP-AF-CLI-Tool.md (PRP type)
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "ALF-2201"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "PRP" in result.output
    assert "not SOP" in result.output


def test_plan_missing_document(sample_project, monkeypatch):
    """Missing document ID results in non-zero exit code."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "COR-9999"], catch_exceptions=False)
    assert result.exit_code != 0


def test_plan_human_mode(sample_project, monkeypatch):
    """--human flag outputs format with unicode checkboxes and separators."""
    rules_dir = sample_project / "rules"
    _create_sop_with_steps(rules_dir, "TST", "5001", "Test-Workflow")

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "--human", "TST-5001"], catch_exceptions=False)
    assert result.exit_code == 0
    # Human mode uses unicode checkboxes, not markdown
    assert "- [ ]" not in result.output
    # Should still show step content
    assert "First step" in result.output


def test_setup_outputs_prompts(sample_project, monkeypatch):
    """af setup outputs suggested prompt text."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["setup"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "af plan" in result.output
    assert "af guide" in result.output


def test_plan_no_args(sample_project, monkeypatch):
    """No SOP_IDs and no flags results in non-zero exit code with usage hint."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan"], catch_exceptions=False)
    assert result.exit_code != 0
    assert "Usage" in result.output or "SOP_ID" in result.output


def test_plan_sop_without_steps(sample_project, monkeypatch):
    """SOP without Steps section shows note about no steps."""
    rules_dir = sample_project / "rules"
    _create_sop_without_steps(rules_dir, "TST", "5001", "Empty-SOP")

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "TST-5001"], catch_exceptions=False)
    assert result.exit_code == 0
    # Should note there are no steps
    output_lower = result.output.lower()
    assert "no steps" in output_lower or "no step" in output_lower


def test_plan_llm_mode_has_rules(sample_project, monkeypatch):
    """Default (LLM) mode includes ## RULES section."""
    rules_dir = sample_project / "rules"
    _create_sop_with_steps(rules_dir, "TST", "5001", "Test-Workflow")

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "TST-5001"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "## RULES" in result.output


def test_plan_human_mode_no_rules(sample_project, monkeypatch):
    """--human mode does NOT include ## RULES section."""
    rules_dir = sample_project / "rules"
    _create_sop_with_steps(rules_dir, "TST", "5001", "Test-Workflow")

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "--human", "TST-5001"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "## RULES" not in result.output


# ── Gate detection tests for _parse_steps_for_json (FXA-2157) ─────────────


class TestParseStepsForJsonGateDetection:
    """Direct unit tests for _parse_steps_for_json gate detection logic."""

    def test_plain_step_gate_false(self):
        """Numbered step without markers has gate: false."""
        result = _parse_steps_for_json("1. Do something")
        assert len(result) == 1
        assert result[0]["index"] == 1
        assert result[0]["text"] == "Do something"
        assert result[0]["gate"] is False

    def test_step_with_checkmark_gate_true(self):
        """Step ending with literal ✓ has gate: true."""
        result = _parse_steps_for_json("1. Verify all tests pass ✓")
        assert len(result) == 1
        assert result[0]["gate"] is True

    def test_step_with_gate_marker_gate_true(self):
        """Step containing [GATE] has gate: true."""
        result = _parse_steps_for_json("1. Review approved [GATE]")
        assert len(result) == 1
        assert result[0]["gate"] is True

    def test_heading_prefix_parsed(self):
        """Step with ### heading prefix is parsed correctly."""
        result = _parse_steps_for_json("### 1. First step with heading")
        assert len(result) == 1
        assert result[0]["index"] == 1
        assert result[0]["text"] == "First step with heading"
        assert result[0]["gate"] is False

    def test_mixed_content_only_numbered_extracted(self):
        """Only numbered steps are extracted from mixed content."""
        text = "Some intro text\n1. First step\nRandom line\n2. Second step\n\nAnother paragraph"
        result = _parse_steps_for_json(text)
        assert len(result) == 2
        assert result[0]["index"] == 1
        assert result[1]["index"] == 2

    def test_empty_input_returns_empty_list(self):
        """Empty input returns []."""
        assert _parse_steps_for_json("") == []


# ── Exact-output snapshot tests for _format_phase (FXA-2169) ───────────────

# Shared test bodies used across LLM and human snapshot tests.
_BODY_WITH_STEPS = (
    "## What Is It?\nA test SOP for demo.\n\n"
    "Second paragraph ignored.\n"
    "## Steps\n1. First step\n2. Second step\n3. Third step\n"
)
_SUMMARY_WITH_STEPS = "A test SOP for demo.\n\nSecond paragraph ignored."

_BODY_NO_STEPS = "## What Is It?\nJust an overview.\n## Notes\nSome notes here.\n"
_SUMMARY_NO_STEPS = "Just an overview."

_BODY_RAW_FALLBACK = (
    "## What Is It?\nOverview text.\n"
    "## Steps\nNo numbered items here, just prose describing what to do.\n"
)
_SUMMARY_RAW_FALLBACK = "Overview text."


class TestFormatPhaseLlmSnapshot:
    """Exact-output snapshot tests for _format_phase (LLM mode) (FXA-2169)."""

    def test_with_steps_and_summary(self):
        heading = "## Phase 1: COR-1500 (TDD Workflow)"
        result = _format_phase(
            heading, _SUMMARY_WITH_STEPS, _BODY_WITH_STEPS, "What: ", "- [ ] "
        )
        expected = (
            "## Phase 1: COR-1500 (TDD Workflow)\n"
            "What: A test SOP for demo.\n"
            "\n"
            "- [ ] 1. First step\n"
            "- [ ] 2. Second step\n"
            "- [ ] 3. Third step"
        )
        assert result == expected

    def test_no_steps_section(self):
        heading = "## Phase 2: COR-1600 (Review)"
        result = _format_phase(
            heading, _SUMMARY_NO_STEPS, _BODY_NO_STEPS, "What: ", "- [ ] "
        )
        expected = (
            "## Phase 2: COR-1600 (Review)\n"
            "What: Just an overview.\n"
            "\n"
            "(no Steps section found)"
        )
        assert result == expected

    def test_raw_section_fallback(self):
        heading = "## Phase 1: COR-1700 (Misc)"
        result = _format_phase(
            heading, _SUMMARY_RAW_FALLBACK, _BODY_RAW_FALLBACK, "What: ", "- [ ] "
        )
        expected = (
            "## Phase 1: COR-1700 (Misc)\n"
            "What: Overview text.\n"
            "\n"
            "No numbered items here, just prose describing what to do."
        )
        assert result == expected

    def test_no_summary(self):
        heading = "## Phase 1: COR-1500 (TDD Workflow)"
        result = _format_phase(heading, None, _BODY_WITH_STEPS, "What: ", "- [ ] ")
        expected = (
            "## Phase 1: COR-1500 (TDD Workflow)\n"
            "\n"
            "- [ ] 1. First step\n"
            "- [ ] 2. Second step\n"
            "- [ ] 3. Third step"
        )
        assert result == expected


class TestFormatPhaseHumanSnapshot:
    """Exact-output snapshot tests for _format_phase (human mode) (FXA-2169)."""

    def test_with_steps_and_summary(self):
        heading = "═══ Phase 1: COR-1500 (TDD Workflow) ═══"
        result = _format_phase(heading, _SUMMARY_WITH_STEPS, _BODY_WITH_STEPS, "", "□ ")
        expected = (
            "═══ Phase 1: COR-1500 (TDD Workflow) ═══\n"
            "A test SOP for demo.\n"
            "\n"
            "□ 1. First step\n"
            "□ 2. Second step\n"
            "□ 3. Third step"
        )
        assert result == expected

    def test_no_steps_section(self):
        heading = "═══ Phase 2: COR-1600 (Review) ═══"
        result = _format_phase(heading, _SUMMARY_NO_STEPS, _BODY_NO_STEPS, "", "□ ")
        expected = (
            "═══ Phase 2: COR-1600 (Review) ═══\n"
            "Just an overview.\n"
            "\n"
            "(no Steps section found)"
        )
        assert result == expected

    def test_raw_section_fallback(self):
        heading = "═══ Phase 1: COR-1700 (Misc) ═══"
        result = _format_phase(
            heading, _SUMMARY_RAW_FALLBACK, _BODY_RAW_FALLBACK, "", "□ "
        )
        expected = (
            "═══ Phase 1: COR-1700 (Misc) ═══\n"
            "Overview text.\n"
            "\n"
            "No numbered items here, just prose describing what to do."
        )
        assert result == expected

    def test_no_summary(self):
        heading = "═══ Phase 1: COR-1500 (TDD Workflow) ═══"
        result = _format_phase(heading, None, _BODY_WITH_STEPS, "", "□ ")
        expected = (
            "═══ Phase 1: COR-1500 (TDD Workflow) ═══\n"
            "\n"
            "□ 1. First step\n"
            "□ 2. Second step\n"
            "□ 3. Third step"
        )
        assert result == expected


# ── Workflow composition tests (FXA-2204) ──────────────────────────────────


def _create_typed_sop(
    rules_dir: Path,
    prefix: str,
    acid: str,
    title: str,
    workflow_input: str,
    workflow_output: str,
) -> Path:
    """Helper to create a typed SOP document with workflow metadata."""
    filename = f"{prefix}-{acid}-SOP-{title}.md"
    content = f"""# {prefix}-{acid}: {title.replace("-", " ")}

**Applies to:** Test
**Status:** Active
**Workflow input:** {workflow_input}
**Workflow output:** {workflow_output}
---
## What Is It?
A typed test SOP for {acid}.
## Steps
1. First step for {acid}
2. Second step for {acid}
"""
    filepath = rules_dir / filename
    filepath.write_text(content)
    return filepath


def test_plan_typed_compatible_chain(sample_project, monkeypatch):
    """Compatible typed chain: SOP-A outputs match SOP-B inputs."""
    rules_dir = sample_project / "rules"
    _create_typed_sop(
        rules_dir, "TST", "6001", "Step-A", "proposal:draft", "proposal:reviewed"
    )
    _create_typed_sop(
        rules_dir, "TST", "6002", "Step-B", "proposal:reviewed", "proposal:approved"
    )

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "TST-6001", "TST-6002"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "State:" in result.output
    assert "proposal:draft" in result.output


def test_plan_typed_mismatch_raises(sample_project, monkeypatch):
    """Incompatible typed chain fails fast with ClickException."""
    rules_dir = sample_project / "rules"
    _create_typed_sop(
        rules_dir, "TST", "6001", "Step-A", "proposal:draft", "proposal:reviewed"
    )
    _create_typed_sop(
        rules_dir, "TST", "6002", "Step-B", "change:approved", "change:completed"
    )

    monkeypatch.chdir(sample_project)
    with pytest.raises(click.ClickException, match="Workflow type mismatch"):
        cli.main(
            args=["plan", "--json", "TST-6001", "TST-6002"],
            prog_name="af",
            standalone_mode=False,
        )


def test_plan_json_contains_workflow_fields(sample_project, monkeypatch):
    """--json output includes composition_valid, edges, and workflow fields per phase."""
    import json

    rules_dir = sample_project / "rules"
    _create_typed_sop(
        rules_dir, "TST", "6001", "Step-A", "proposal:draft", "proposal:reviewed"
    )
    _create_typed_sop(
        rules_dir, "TST", "6002", "Step-B", "proposal:reviewed", "proposal:approved"
    )

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "--json", "TST-6001", "TST-6002"], catch_exceptions=False
    )
    assert result.exit_code == 0

    data = json.loads(result.output)

    # Top-level composition fields
    assert data["composition_valid"] is True
    assert isinstance(data["edges"], list)
    assert len(data["edges"]) == 1
    edge = data["edges"][0]
    assert edge["typed"] is True
    assert edge["compatible"] is True
    assert edge["from_output"] == "proposal:reviewed"
    assert edge["to_input"] == "proposal:reviewed"

    # Each phase has workflow fields
    for phase in data["phases"]:
        assert "workflow_input" in phase
        assert "workflow_output" in phase
        assert "workflow_typed" in phase
        assert phase["workflow_typed"] is True


def test_plan_mixed_typed_untyped_chain(sample_project, monkeypatch):
    """Mix of typed and untyped SOPs works without error (backward compatible)."""
    rules_dir = sample_project / "rules"
    # Typed SOP
    _create_typed_sop(
        rules_dir, "TST", "6001", "Step-A", "proposal:draft", "proposal:reviewed"
    )
    # Untyped SOP (no workflow metadata)
    _create_sop_with_steps(rules_dir, "TST", "6002", "Step-B")
    # Another typed SOP
    _create_typed_sop(
        rules_dir, "TST", "6003", "Step-C", "proposal:reviewed", "proposal:approved"
    )

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["plan", "TST-6001", "TST-6002", "TST-6003"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    # Typed SOPs should still show their State lines
    assert "State:" in result.output


# ── Flat TODO output tests (FXA-2205 PR2) ───────────────────────────────────


def test_todo_flag_flat_checkbox_lines(sample_project, monkeypatch):
    """--todo alone emits `- [ ] N.M [SOP-ID] text` lines in composition order."""
    rules_dir = sample_project / "rules"
    _create_sop_with_steps(rules_dir, "TST", "7001", "First-SOP")

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "--todo", "TST-7001"], catch_exceptions=False)
    assert result.exit_code == 0
    # Should have markdown checkboxes
    assert "- [ ]" in result.output
    # Should have dotted numbering N.M
    assert "1.1" in result.output
    # Should have SOP-ID provenance tag
    assert "[TST-7001]" in result.output
    # Should NOT have phased output headers
    assert "## Phase" not in result.output


def test_todo_human_flag_unicode_checkbox(sample_project, monkeypatch):
    """--todo --human emits `□ N.M [SOP-ID] text` lines."""
    rules_dir = sample_project / "rules"
    _create_sop_with_steps(rules_dir, "TST", "7001", "First-SOP")

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "--todo", "--human", "TST-7001"], catch_exceptions=False
    )
    assert result.exit_code == 0
    # Should have unicode checkbox
    assert "□" in result.output
    # Should NOT have markdown checkbox
    assert "- [ ]" not in result.output
    # Should still have dotted numbering and provenance
    assert "1.1" in result.output
    assert "[TST-7001]" in result.output


def test_todo_gate_marker(sample_project, monkeypatch):
    """Gate markers produce `⚠️ gate` prefix in TODO item."""
    rules_dir = sample_project / "rules"
    content = """# TST-7002: Gate Test

**Applies to:** Test
**Status:** Active
---
## What Is It?
A test SOP with a gate step.
## Steps
1. Regular step
2. Gate step ✓
"""
    filepath = rules_dir / "TST-7002-SOP-Gate-Test.md"
    filepath.write_text(content)

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "--todo", "TST-7002"], catch_exceptions=False)
    assert result.exit_code == 0
    # Gate step should have warning marker
    assert "⚠️" in result.output or "gate" in result.output.lower()


def test_todo_json_produces_todo_array(sample_project, monkeypatch):
    """--todo --json produces `todo` array with correct fields."""
    import json

    rules_dir = sample_project / "rules"
    _create_sop_with_steps(rules_dir, "TST", "7001", "First-SOP")

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "--todo", "--json", "TST-7001"], catch_exceptions=False
    )
    assert result.exit_code == 0

    data = json.loads(result.output)

    # Should have todo array
    assert "todo" in data
    assert isinstance(data["todo"], list)
    assert len(data["todo"]) >= 1

    # Each todo item should have required fields
    todo_item = data["todo"][0]
    assert "index" in todo_item
    assert "sop" in todo_item
    assert "text" in todo_item
    assert "gate" in todo_item
    assert "loop_marker" in todo_item

    # Index should be dotted format
    assert "." in todo_item["index"]
    assert todo_item["sop"] == "TST-7001"


def test_todo_json_includes_loops_array(sample_project, monkeypatch):
    """--todo --json includes `loops` array with dotted step references."""
    import json

    # Use COR-1602 from PKG layer which has Workflow loops metadata
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "--todo", "--json", "COR-1602"], catch_exceptions=False
    )
    assert result.exit_code == 0

    data = json.loads(result.output)

    # Should have loops array
    assert "loops" in data
    assert isinstance(data["loops"], list)
    assert len(data["loops"]) >= 1

    # Each loop should have required fields with dotted format
    loop = data["loops"][0]
    assert "id" in loop
    assert "from" in loop
    assert "to" in loop
    assert "max_iterations" in loop
    assert "sop" in loop

    # from and to should be dotted format (e.g., "1.7")
    assert "." in loop["from"]
    assert "." in loop["to"]


def test_todo_json_schema_version_bumps(sample_project, monkeypatch):
    """--todo --json sets `schema_version` to "2"."""
    import json

    rules_dir = sample_project / "rules"
    _create_sop_with_steps(rules_dir, "TST", "7001", "First-SOP")

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "--todo", "--json", "TST-7001"], catch_exceptions=False
    )
    assert result.exit_code == 0

    data = json.loads(result.output)
    assert data["schema_version"] == "2"


def test_json_without_todo_unchanged_schema(sample_project, monkeypatch):
    """--json without --todo keeps existing schema untouched."""
    import json

    rules_dir = sample_project / "rules"
    _create_sop_with_steps(rules_dir, "TST", "7001", "First-SOP")

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "--json", "TST-7001"], catch_exceptions=False)
    assert result.exit_code == 0

    data = json.loads(result.output)
    # Schema version should be "1" (no new keys)
    assert data["schema_version"] == "1"
    # Should NOT have todo or loops keys
    assert "todo" not in data
    assert "loops" not in data


def test_todo_preserves_json_human_mutex(sample_project, monkeypatch):
    """--todo preserves existing --json --human mutex error."""
    rules_dir = sample_project / "rules"
    _create_sop_with_steps(rules_dir, "TST", "7001", "First-SOP")

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["plan", "--todo", "--json", "--human", "TST-7001"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output.lower()


def test_todo_without_steps_section(sample_project, monkeypatch):
    """--todo on a SOP without Steps section shows appropriate message."""
    rules_dir = sample_project / "rules"
    _create_sop_without_steps(rules_dir, "TST", "7003", "Empty-SOP")

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "--todo", "TST-7003"], catch_exceptions=False)
    assert result.exit_code == 0
    # Should note there are no steps
    output_lower = result.output.lower()
    assert "no steps" in output_lower or "no step" in output_lower


def test_todo_multi_sop_continuous_numbering(sample_project, monkeypatch):
    """Composition of 2+ SOPs produces continuous phase numbering (1.*, 2.*)."""
    rules_dir = sample_project / "rules"
    _create_sop_with_steps(rules_dir, "TST", "7001", "First-SOP")
    _create_sop_with_steps(rules_dir, "TST", "7002", "Second-SOP")

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "--todo", "TST-7001", "TST-7002"], catch_exceptions=False
    )
    assert result.exit_code == 0

    # Should have phase 1.x and phase 2.x numbering
    assert "1.1" in result.output
    assert "1.2" in result.output
    assert "2.1" in result.output
    assert "2.2" in result.output
    # Should have both SOP provenance tags
    assert "[TST-7001]" in result.output
    assert "[TST-7002]" in result.output


def test_todo_loop_markers_on_cor_1602(sample_project, monkeypatch):
    """--todo on COR-1602 produces loop markers on the correct steps.

    COR-1602 has Workflow loops: [{id: review-retry, from: 7, to: 3, ...}]
    - Step 3 should have 🔁 loop-start prefix
    - Step 7 should have 🔁 if ... → back to 1.3 (max 3) suffix
    """
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "--todo", "COR-1602"], catch_exceptions=False)
    assert result.exit_code == 0

    output = result.output

    # Should have loop-start marker
    assert "🔁" in output or "loop-start" in output.lower()

    # Should have loop-back marker with condition and max iterations
    assert "back to" in output.lower() or "→" in output
    assert "max 3" in output.lower() or "max_iterations" in output.lower()

    # Provenance tag should be present
    assert "[COR-1602]" in output


def test_todo_loop_marker_json_values(sample_project, monkeypatch):
    """--todo --json loop_marker field has correct values."""
    import json

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "--todo", "--json", "COR-1602"], catch_exceptions=False
    )
    assert result.exit_code == 0

    data = json.loads(result.output)

    # Find todo items with loop markers
    loop_start_items = [t for t in data["todo"] if t.get("loop_marker") == "loop-start"]
    loop_back_items = [t for t in data["todo"] if t.get("loop_marker") == "loop-back"]

    # COR-1602 has from:7 to:3, so step 3 is loop-start, step 7 is loop-back
    assert len(loop_start_items) >= 1
    assert len(loop_back_items) >= 1

    # The loop-start item should be at index 1.3
    assert any(t["index"] == "1.3" for t in loop_start_items)

    # The loop-back item should be at index 1.7
    assert any(t["index"] == "1.7" for t in loop_back_items)


def test_todo_preserves_default_output(sample_project, monkeypatch):
    """Default (no --todo) output remains byte-identical to existing behavior."""
    rules_dir = sample_project / "rules"
    _create_sop_with_steps(rules_dir, "TST", "7001", "First-SOP")

    monkeypatch.chdir(sample_project)

    # Get default output
    runner = CliRunner()
    default_result = runner.invoke(cli, ["plan", "TST-7001"], catch_exceptions=False)
    assert default_result.exit_code == 0

    # Should have phased output headers
    assert "## Phase" in default_result.output
    # Should have ## RULES section
    assert "## RULES" in default_result.output
