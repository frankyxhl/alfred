"""Tests for af plan command (FXA-2134)."""

from pathlib import Path

import click
import pytest
from click.testing import CliRunner
from fx_alfred.cli import cli
from fx_alfred.commands.plan_cmd import (
    _build_mermaid_phases,
    _format_phase,
    _parse_steps_for_json,
)
from fx_alfred.core.document import Document
from fx_alfred.core.parser import parse_metadata
from fx_alfred.core.workflow import BranchSignature, WorkflowSignature


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

    # Type stability: workflow_requires and workflow_provides must be lists
    # (not strings) even for untyped phases that hit the `else` fallback
    for phase in data["phases"]:
        assert isinstance(phase["workflow_requires"], list), (
            f"workflow_requires must be list, got {type(phase['workflow_requires'])}"
        )
        assert isinstance(phase["workflow_provides"], list), (
            f"workflow_provides must be list, got {type(phase['workflow_provides'])}"
        )


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


# ── Gate + Loop collision tests (FXA-2205 PR2 Round-2) ───────────────────────


def _create_sop_with_gate_and_loop(
    rules_dir: Path,
    prefix: str,
    acid: str,
    title: str,
    workflow_loops: str,
    steps_with_gate: str,
) -> Path:
    """Helper to create an SOP with Workflow loops and a gate step."""
    filename = f"{prefix}-{acid}-SOP-{title}.md"
    content = f"""# {prefix}-{acid}: {title.replace("-", " ")}

**Applies to:** Test
**Status:** Active
**Workflow loops:** {workflow_loops}
---
## What Is It?
A test SOP with gate and loop metadata.
## Steps
{steps_with_gate}
"""
    filepath = rules_dir / filename
    filepath.write_text(content)
    return filepath


def test_gate_plus_loop_from_collision_text(sample_project, monkeypatch):
    """Step that is gate AND from_step → text has BOTH ⚠️ gate prefix AND loop-back suffix."""
    rules_dir = sample_project / "rules"
    # Step 2 is both gate (✓) and loop from_step (from:2, to:1)
    _create_sop_with_gate_and_loop(
        rules_dir,
        "TST",
        "8001",
        "Gate-Loop-Collision",
        "[{id: retry, from: 2, to: 1, max_iterations: 3, condition: 'needs retry'}]",
        "1. First step\n2. Retry gate ✓\n3. Final step",
    )

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "--todo", "TST-8001"], catch_exceptions=False)
    assert result.exit_code == 0

    # Step 2 should have BOTH gate prefix AND loop-back suffix
    assert "⚠️ gate:" in result.output
    assert "🔁 if needs retry → back to 1.1 (max 3)" in result.output
    # Both markers should appear on the same line (step 2)
    lines = result.output.split("\n")
    step2_line = [line for line in lines if "1.2" in line][0]
    assert "⚠️ gate:" in step2_line
    assert "🔁 if needs retry" in step2_line


def test_gate_plus_loop_from_collision_json(sample_project, monkeypatch):
    """Step that is gate AND from_step → JSON has gate=True, loop_marker='loop-back'."""
    import json

    rules_dir = sample_project / "rules"
    _create_sop_with_gate_and_loop(
        rules_dir,
        "TST",
        "8001",
        "Gate-Loop-Collision",
        "[{id: retry, from: 2, to: 1, max_iterations: 3, condition: 'needs retry'}]",
        "1. First step\n2. Retry gate ✓\n3. Final step",
    )

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "--todo", "--json", "TST-8001"], catch_exceptions=False
    )
    assert result.exit_code == 0

    data = json.loads(result.output)
    # Find step 2 (index "1.2")
    step2 = [t for t in data["todo"] if t["index"] == "1.2"][0]
    assert step2["gate"] is True
    assert step2["loop_marker"] == "loop-back"


def test_gate_plus_loop_to_collision_text(sample_project, monkeypatch):
    """Step that is gate AND to_step → text has BOTH ⚠️ gate AND 🔁 loop-start."""
    rules_dir = sample_project / "rules"
    # Step 1 is both gate (✓) and loop to_step (from:2, to:1)
    _create_sop_with_gate_and_loop(
        rules_dir,
        "TST",
        "8002",
        "Gate-LoopStart-Collision",
        "[{id: retry, from: 2, to: 1, max_iterations: 3, condition: 'needs retry'}]",
        "1. Gate at loop start ✓\n2. Retry step\n3. Final step",
    )

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "--todo", "TST-8002"], catch_exceptions=False)
    assert result.exit_code == 0

    # Step 1 should have BOTH gate prefix AND loop-start prefix
    lines = result.output.split("\n")
    step1_line = [line for line in lines if "1.1" in line][0]
    assert "⚠️ gate:" in step1_line
    assert "🔁 loop-start:" in step1_line
    # Gate should be leftmost (applied after loop-start prepend)
    assert step1_line.index("⚠️") < step1_line.index("🔁 loop-start")


def test_gate_plus_loop_to_collision_json(sample_project, monkeypatch):
    """Step that is gate AND to_step → JSON has gate=True, loop_marker='loop-start'."""
    import json

    rules_dir = sample_project / "rules"
    _create_sop_with_gate_and_loop(
        rules_dir,
        "TST",
        "8002",
        "Gate-LoopStart-Collision",
        "[{id: retry, from: 2, to: 1, max_iterations: 3, condition: 'needs retry'}]",
        "1. Gate at loop start ✓\n2. Retry step\n3. Final step",
    )

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "--todo", "--json", "TST-8002"], catch_exceptions=False
    )
    assert result.exit_code == 0

    data = json.loads(result.output)
    # Find step 1 (index "1.1")
    step1 = [t for t in data["todo"] if t["index"] == "1.1"][0]
    assert step1["gate"] is True
    assert step1["loop_marker"] == "loop-start"


def test_gate_alone_no_loop_collision(sample_project, monkeypatch):
    """Gate without loop overlap → ⚠️ gate text and gate=True, loop_marker=null JSON."""
    import json

    rules_dir = sample_project / "rules"
    # No workflow loops, just a gate step
    _create_sop_with_gate_and_loop(
        rules_dir,
        "TST",
        "8003",
        "Gate-Only",
        "[]",  # no loops
        "1. First step\n2. Gate step ✓\n3. Final step",
    )

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "--todo", "--json", "TST-8003"], catch_exceptions=False
    )
    assert result.exit_code == 0

    data = json.loads(result.output)
    step2 = [t for t in data["todo"] if t["index"] == "1.2"][0]
    assert step2["gate"] is True
    assert step2["loop_marker"] is None

    # Text output
    result_text = runner.invoke(
        cli, ["plan", "--todo", "TST-8003"], catch_exceptions=False
    )
    assert result_text.exit_code == 0
    assert "⚠️ gate:" in result_text.output


def test_loop_to_and_from_same_step_multi_loop(sample_project, monkeypatch):
    """Step is both loop to_step AND loop_from (multi-loop edge) → loop-back takes precedence."""
    import json

    rules_dir = sample_project / "rules"
    # Step 2 is to_step of loop-a (from:3, to:2) AND from_step of loop-b (from:2, to:1)
    # This creates a chain: 1 ←(loop-b)← 2 ←(loop-a)← 3
    _create_sop_with_gate_and_loop(
        rules_dir,
        "TST",
        "8004",
        "Multi-Loop-Edge",
        "[{id: loop-a, from: 3, to: 2, max_iterations: 2, condition: 'a'}, "
        "{id: loop-b, from: 2, to: 1, max_iterations: 1, condition: 'b'}]",
        "1. First\n2. Middle (both to and from)\n3. Last",
    )

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "--todo", "--json", "TST-8004"], catch_exceptions=False
    )
    assert result.exit_code == 0

    data = json.loads(result.output)
    # Step 2 should have loop_marker="loop-back" (tiebreak: loop_from takes precedence)
    step2 = [t for t in data["todo"] if t["index"] == "1.2"][0]
    assert step2["loop_marker"] == "loop-back"

    # Text output should have BOTH loop-start prefix AND loop-back suffix
    result_text = runner.invoke(
        cli, ["plan", "--todo", "TST-8004"], catch_exceptions=False
    )
    assert result_text.exit_code == 0
    lines = result_text.output.split("\n")
    step2_line = [line for line in lines if "1.2" in line][0]
    assert "🔁 loop-start:" in step2_line
    assert "🔁 if b → back to 1.1 (max 1)" in step2_line


# ── Malformed Workflow loops regression tests (FXA-2205 PR2 P1 fix) ───────────


def _create_sop_with_malformed_loops(
    rules_dir: Path, prefix: str, acid: str, title: str
) -> Path:
    """Helper to create an SOP with malformed Workflow loops YAML."""
    filename = f"{prefix}-{acid}-SOP-{title}.md"
    # Intentionally malformed: 'from' is a string, not an int
    content = f"""# {prefix}-{acid}: {title.replace("-", " ")}

**Applies to:** Test
**Last updated:** 2026-04-16
**Last reviewed:** 2026-04-16
**Status:** Active
**Workflow loops:** [{{id: bad-loop, from: not-an-int, to: 1, max_iterations: 3, condition: "test"}}]

---

## What Is It?

A test SOP with malformed loops.

## Why

Testing error handling.

## When to Use

Testing.

## When NOT to Use

Not testing.

## Steps

1. First step
2. Second step
"""
    filepath = rules_dir / filename
    filepath.write_text(content)
    return filepath


def test_malformed_loops_warn_and_skip(sample_project, monkeypatch):
    """SOP with malformed loops + normal SOP → warns on bad, renders good."""
    rules_dir = sample_project / "rules"
    _create_sop_with_steps(rules_dir, "TST", "9001", "Good-SOP")
    _create_sop_with_malformed_loops(rules_dir, "TST", "9002", "Bad-Loops")

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "TST-9002", "TST-9001"], catch_exceptions=False
    )
    assert result.exit_code == 0
    # Should warn about the bad SOP
    assert "Warning" in result.output
    assert "malformed" in result.output.lower()
    # Should still render the good SOP
    assert "TST-9001" in result.output
    assert "## Phase" in result.output


def test_malformed_loops_todo_mode(sample_project, monkeypatch):
    """Malformed loops with --todo flag → warns and continues."""
    rules_dir = sample_project / "rules"
    _create_sop_with_steps(rules_dir, "TST", "9001", "Good-SOP")
    _create_sop_with_malformed_loops(rules_dir, "TST", "9002", "Bad-Loops")

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "--todo", "TST-9002", "TST-9001"], catch_exceptions=False
    )
    assert result.exit_code == 0
    # Should warn about the bad SOP
    assert "Warning" in result.output
    # Should still render the good SOP in TODO format
    assert "[TST-9001]" in result.output
    assert "- [ ]" in result.output


def test_malformed_loops_json_mode_silent_skip(sample_project, monkeypatch):
    """Malformed loops with --json → silent skip, no warning in output."""
    import json

    rules_dir = sample_project / "rules"
    _create_sop_with_steps(rules_dir, "TST", "9001", "Good-SOP")
    _create_sop_with_malformed_loops(rules_dir, "TST", "9002", "Bad-Loops")

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "--json", "TST-9002", "TST-9001"], catch_exceptions=False
    )
    assert result.exit_code == 0

    data = json.loads(result.output)
    # Only the good SOP should be in phases
    assert len(data["phases"]) == 1
    assert data["phases"][0]["phase"] == "TST-9001"
    # No warning in JSON output (per existing convention)
    assert "Warning" not in result.output


# ── af plan --graph CLI integration tests (FXA-2205 PR3) ────────────────────


def test_graph_alone_on_cor_1602(sample_project, monkeypatch):
    """--graph on COR-1602 (has loops) → phased output + fenced mermaid block with back-edge."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "--graph", "COR-1602"], catch_exceptions=False)
    assert result.exit_code == 0

    # Should have phased output (default format)
    assert "## Phase" in result.output
    # Should have fenced mermaid block
    assert "```mermaid" in result.output
    assert "flowchart TD" in result.output
    assert "```" in result.output
    # Should have dashed back-edge from loop (from:7, to:3)
    assert "-." in result.output
    assert ".->" in result.output


def test_todo_graph_combo(sample_project, monkeypatch):
    """--todo --graph → flat TODO + mermaid block at end."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "--todo", "--graph", "COR-1602"], catch_exceptions=False
    )
    assert result.exit_code == 0

    # Should have flat TODO format
    assert "- [ ]" in result.output
    assert "[COR-1602]" in result.output
    # Should NOT have phased output
    assert "## Phase" not in result.output
    # Should have mermaid block
    assert "```mermaid" in result.output
    assert "flowchart TD" in result.output


def test_json_graph_has_graph_mermaid_key(sample_project, monkeypatch):
    """--json --graph → JSON has `graph_mermaid` key (string type); schema_version == "2"."""
    import json

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "--json", "--graph", "COR-1602"], catch_exceptions=False
    )
    assert result.exit_code == 0

    data = json.loads(result.output)
    assert "graph_mermaid" in data
    assert isinstance(data["graph_mermaid"], str)
    assert data["graph_mermaid"].startswith("flowchart TD")
    assert data["schema_version"] == "2"


def test_json_graph_todo_all_keys(sample_project, monkeypatch):
    """--json --graph --todo → JSON has all new keys (todo, loops, graph_mermaid)."""
    import json

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["plan", "--json", "--graph", "--todo", "COR-1602"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    data = json.loads(result.output)
    assert "todo" in data
    assert "loops" in data
    assert "graph_mermaid" in data
    assert data["schema_version"] == "2"


def test_json_alone_no_graph_mermaid(sample_project, monkeypatch):
    """--json alone (no --graph) → no graph_mermaid key; schema unchanged."""
    import json

    rules_dir = sample_project / "rules"
    _create_sop_with_steps(rules_dir, "TST", "7001", "First-SOP")

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "--json", "TST-7001"], catch_exceptions=False)
    assert result.exit_code == 0

    data = json.loads(result.output)
    assert "graph_mermaid" not in data
    assert data["schema_version"] == "1"


def test_default_plan_byte_identical(sample_project, monkeypatch):
    """Default af plan (no new flags) → byte-identical to pre-PR-3 output."""
    rules_dir = sample_project / "rules"
    _create_sop_with_steps(rules_dir, "TST", "7001", "First-SOP")

    monkeypatch.chdir(sample_project)
    runner = CliRunner()

    # Default output
    result1 = runner.invoke(cli, ["plan", "TST-7001"], catch_exceptions=False)
    assert result1.exit_code == 0

    # Should have phased output headers and RULES
    assert "## Phase" in result1.output
    assert "## RULES" in result1.output
    # Should NOT have any mermaid content
    assert "```mermaid" not in result1.output
    assert "flowchart TD" not in result1.output
    assert "graph_mermaid" not in result1.output


def test_graph_human_combo(sample_project, monkeypatch):
    """--graph --human → human-readable phased output + mermaid block appended."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "--graph", "--human", "COR-1602"], catch_exceptions=False
    )
    assert result.exit_code == 0

    # Human format markers
    assert "□" in result.output or "═══" in result.output
    # Mermaid block still appended
    assert "```mermaid" in result.output
    assert "flowchart TD" in result.output


def test_malformed_loops_graph_mode(sample_project, monkeypatch):
    """Malformed loops SOP + --graph → warns and skips bad SOP (regression test)."""
    rules_dir = sample_project / "rules"
    _create_sop_with_steps(rules_dir, "TST", "9001", "Good-SOP")
    _create_sop_with_malformed_loops(rules_dir, "TST", "9002", "Bad-Loops")

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "--graph", "TST-9002", "TST-9001"], catch_exceptions=False
    )
    assert result.exit_code == 0
    # Should warn about the bad SOP
    assert "Warning" in result.output
    assert "malformed" in result.output.lower()
    # Should still have mermaid block for the good SOP
    assert "```mermaid" in result.output
    assert "flowchart TD" in result.output


# ── af plan --task auto-composition tests (FXA-2205 PR4) ────────────────────


def _create_sop_with_task_tags(
    rules_dir: Path,
    prefix: str,
    acid: str,
    title: str,
    task_tags: str,
    always_included: bool = False,
    workflow_input: str = "",
    workflow_output: str = "",
) -> Path:
    """Helper to create an SOP with Task tags metadata.

    Note: Uses non-COR prefix by default to avoid PKG-layer collision.
    """
    filename = f"{prefix}-{acid}-SOP-{title}.md"
    always_line = "**Always included:** true\n" if always_included else ""
    input_line = f"**Workflow input:** {workflow_input}\n" if workflow_input else ""
    output_line = f"**Workflow output:** {workflow_output}\n" if workflow_output else ""
    sop_content = f"""# {prefix}-{acid}: {title.replace("-", " ")}

**Applies to:** Test
**Status:** Active
{always_line}{input_line}{output_line}**Task tags:** {task_tags}
---
## What Is It?
A test SOP with task tags.
## Steps
1. First step for {acid}
2. Second step for {acid}
"""
    filepath = rules_dir / filename
    filepath.write_text(sop_content)
    return filepath


def test_task_flag_includes_tagged_sop(sample_project, monkeypatch):
    """--task 'implement FXA-2117 PRP' includes TST-1500 (has 'implement' tag)."""
    rules_dir = sample_project / "rules"
    _create_sop_with_task_tags(
        rules_dir,
        "TST",
        "1500",
        "TDD",
        "[implement, feature, tdd, code, code-change, fix]",
    )
    _create_sop_with_task_tags(
        rules_dir, "TST", "1103", "Routing", "[]", always_included=True
    )

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "--task", "implement FXA-2117 PRP"], catch_exceptions=False
    )
    assert result.exit_code == 0
    # Should include TST-1500 (matched by 'implement' tag)
    assert "TST-1500" in result.output
    # Should include TST-1103 (always included)
    assert "TST-1103" in result.output


def test_task_no_match_raises_exit_2(sample_project, monkeypatch):
    """--task 'rare unmatched xyzzy' → exit 2 with diagnostic message."""
    rules_dir = sample_project / "rules"
    _create_sop_with_task_tags(
        rules_dir, "TST", "1103", "Routing", "[]", always_included=True
    )

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "--task", "rare unmatched xyzzy"], catch_exceptions=False
    )
    # Exit code 2 for empty tag match
    assert result.exit_code == 2
    # Should have diagnostic message
    assert "matched 0 tagged SOPs" in result.output or "Try:" in result.output


def test_task_json_todo_graph_combo(sample_project, monkeypatch):
    """--task ... --todo --graph --json → JSON has composed_from, todo, graph_mermaid."""
    import json

    rules_dir = sample_project / "rules"
    _create_sop_with_task_tags(
        rules_dir, "TST", "1500", "TDD", "[implement, feature, tdd]"
    )
    _create_sop_with_task_tags(
        rules_dir, "TST", "1103", "Routing", "[]", always_included=True
    )

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["plan", "--task", "implement feature", "--todo", "--graph", "--json"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    data = json.loads(result.output)
    # Should have composed_from key
    assert "composed_from" in data
    assert "always" in data["composed_from"]
    assert "auto" in data["composed_from"]
    # Should have todo array
    assert "todo" in data
    # Should have graph_mermaid
    assert "graph_mermaid" in data
    # Schema version should be "2" or higher
    assert data["schema_version"] in ("2", "3")


def test_task_with_positional_union(sample_project, monkeypatch):
    """--task ... TST-XXX → positional + tag matches, no duplicates."""
    rules_dir = sample_project / "rules"
    _create_sop_with_task_tags(
        rules_dir, "TST", "1500", "TDD", "[implement, feature, tdd]"
    )
    _create_sop_with_task_tags(rules_dir, "TST", "7001", "Other", "[other, misc]")
    _create_sop_with_task_tags(
        rules_dir, "TST", "1103", "Routing", "[]", always_included=True
    )

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "--task", "implement feature", "TST-7001"], catch_exceptions=False
    )
    assert result.exit_code == 0
    # Should include TST-7001 (positional)
    assert "TST-7001" in result.output
    # Should include TST-1500 (tag matched)
    assert "TST-1500" in result.output
    # Should include TST-1103 (always included)
    assert "TST-1103" in result.output


def test_default_plan_no_task_byte_identical(sample_project, monkeypatch):
    """Default af plan COR-XXX (no --task) → byte-identical to pre-PR4 output."""
    rules_dir = sample_project / "rules"
    _create_sop_with_task_tags(rules_dir, "TST", "7001", "First-SOP", "[test]")

    monkeypatch.chdir(sample_project)
    runner = CliRunner()

    # Default output (no --task)
    result = runner.invoke(cli, ["plan", "TST-7001"], catch_exceptions=False)
    assert result.exit_code == 0

    # Should have phased output headers and RULES
    assert "## Phase" in result.output
    assert "## RULES" in result.output
    # Should NOT have Composed from header
    assert "Composed from:" not in result.output


def test_task_without_value_click_error(sample_project, monkeypatch):
    """--task without value → Click error (non-zero exit)."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    # --task requires a value
    result = runner.invoke(cli, ["plan", "--task"], catch_exceptions=False)
    assert result.exit_code != 0


def test_task_bigram_matches_hyphenated_tag(sample_project, monkeypatch):
    """Bigram 'code change' matches 'code-change' tag."""
    rules_dir = sample_project / "rules"
    _create_sop_with_task_tags(
        rules_dir, "TST", "1500", "TDD", "[code-change, implement]"
    )

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "--task", "code change feature"], catch_exceptions=False
    )
    assert result.exit_code == 0
    # Should match via bigram "code-change"
    assert "TST-1500" in result.output


def test_task_header_shows_provenance(sample_project, monkeypatch):
    """--task output header shows (always) / (auto) / (explicit) markers."""
    rules_dir = sample_project / "rules"
    _create_sop_with_task_tags(rules_dir, "TST", "1500", "TDD", "[implement]")
    _create_sop_with_task_tags(
        rules_dir, "TST", "1103", "Routing", "[]", always_included=True
    )

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "--task", "implement feature"], catch_exceptions=False
    )
    assert result.exit_code == 0
    # Should have Composed from header with markers
    assert "Composed from:" in result.output
    assert "(always)" in result.output
    assert "(auto)" in result.output


def test_task_json_composed_from_structure(sample_project, monkeypatch):
    """--task --json composed_from has always/auto lists."""
    import json

    rules_dir = sample_project / "rules"
    _create_sop_with_task_tags(rules_dir, "TST", "1500", "TDD", "[implement]")
    _create_sop_with_task_tags(
        rules_dir, "TST", "1103", "Routing", "[]", always_included=True
    )

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "--task", "implement", "--json"], catch_exceptions=False
    )
    assert result.exit_code == 0

    data = json.loads(result.output)
    assert "composed_from" in data
    cf = data["composed_from"]
    assert "always" in cf
    assert "auto" in cf
    assert "explicit" in cf
    assert isinstance(cf["always"], list)
    assert isinstance(cf["auto"], list)
    assert isinstance(cf["explicit"], list)
    # TST-1103 should be in always
    assert "TST-1103" in cf["always"]
    # TST-1500 should be in auto
    assert "TST-1500" in cf["auto"]


# ── FXA-2206: --graph-format flag matrix ───────────────────────────────────


def test_graph_default_format_has_both_ascii_and_mermaid(sample_project, monkeypatch):
    """Test 13: af plan --graph (default format=both) → ASCII + fenced Mermaid."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "--graph", "COR-1602"], catch_exceptions=False)
    assert result.exit_code == 0
    # ASCII block: box-drawing chars present
    assert "┌" in result.output
    assert "└" in result.output
    assert "Phase 1:" in result.output
    # Fenced Mermaid still present
    assert "```mermaid" in result.output
    assert "flowchart TD" in result.output
    # Order: ASCII box must precede the Mermaid fence
    assert result.output.index("┌") < result.output.index("```mermaid")


def test_graph_format_mermaid_backward_compat(sample_project, monkeypatch):
    """Test 14: --graph --graph-format=mermaid → no ASCII block; back-compat."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["plan", "--graph", "--graph-format", "mermaid", "COR-1602"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    # Mermaid present
    assert "```mermaid" in result.output
    assert "flowchart TD" in result.output
    # ASCII box-drawing must NOT be present
    assert "┌" not in result.output
    # └ in └─...─┘ would be an ASCII-graph bottom border; must not be present.
    # Default phased output does not use box-drawing chars.
    assert "└" not in result.output
    assert "▼" not in result.output


def test_graph_format_ascii_only(sample_project, monkeypatch):
    """Test 15: --graph --graph-format=ascii → ASCII only; no fenced Mermaid."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["plan", "--graph", "--graph-format", "ascii", "COR-1602"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "┌" in result.output
    # No Mermaid fence
    assert "```mermaid" not in result.output
    assert "flowchart TD" not in result.output


def test_graph_format_without_graph_errors(sample_project, monkeypatch):
    """Test 16: --graph-format without --graph → click.UsageError, exit 2."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["plan", "--graph-format", "ascii", "COR-1602"],
        catch_exceptions=False,
    )
    assert result.exit_code == 2
    assert "--graph-format requires --graph" in result.output


def test_json_graph_default_has_both_keys(sample_project, monkeypatch):
    """Test 17: --graph --json (default format=both) → JSON has ascii_graph + graph_mermaid."""
    import json

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "--json", "--graph", "COR-1602"], catch_exceptions=False
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "ascii_graph" in data
    assert "graph_mermaid" in data
    assert isinstance(data["ascii_graph"], str)
    assert isinstance(data["graph_mermaid"], str)
    assert data["schema_version"] == "2"


def test_json_graph_ascii_format_no_mermaid_key(sample_project, monkeypatch):
    """Test 18: --json --graph --graph-format=ascii → JSON has ascii_graph only."""
    import json

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["plan", "--json", "--graph", "--graph-format", "ascii", "COR-1602"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "ascii_graph" in data
    assert "graph_mermaid" not in data


def test_json_graph_mermaid_format_no_ascii_key(sample_project, monkeypatch):
    """Test 19: --json --graph --graph-format=mermaid → JSON has graph_mermaid only."""
    import json

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["plan", "--json", "--graph", "--graph-format", "mermaid", "COR-1602"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "graph_mermaid" in data
    assert "ascii_graph" not in data


def test_default_plan_unchanged_no_graph_no_ascii(sample_project, monkeypatch):
    """Test 20: default af plan (no --graph) → no ASCII, no Mermaid (regression)."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "COR-1602"], catch_exceptions=False)
    assert result.exit_code == 0
    # Phased output should be there
    assert "## Phase" in result.output
    # No ASCII box, no Mermaid fence
    assert "┌" not in result.output
    assert "```mermaid" not in result.output
    assert "flowchart TD" not in result.output
    assert "ascii_graph" not in result.output


def test_task_evolve_cli_graph_shows_both_backedges(sample_project, monkeypatch):
    """Test 21: af plan --task "evolve CLI" --todo --graph composes COR-1103 +
    COR-1402 + FXA-2148 + FXA-2149 with both Phase-7 back-edges.

    Skipped if the live FXA-2148/FXA-2149 SOPs aren't reachable from the
    sample_project fixture; otherwise asserts both SOPs appear and both
    back-edges are present in the Mermaid output.
    """
    # Use real project root (not sample_project) — the real SOPs live there.
    real_root = Path(__file__).parent.parent
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "plan",
            "--root",
            str(real_root),
            "--task",
            "evolve CLI",
            "--todo",
            "--graph",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    # Both SOP IDs present
    assert "FXA-2148" in result.output
    assert "FXA-2149" in result.output
    # ASCII block precedes Mermaid fence
    assert "┌" in result.output
    assert "```mermaid" in result.output
    assert result.output.index("┌") < result.output.index("```mermaid")
    # Two Mermaid back-edges — one per SOP's Phase-7 loop.
    # Pattern "-. ... .->" appears once per loop.
    mermaid_section = result.output[result.output.index("```mermaid") :]
    assert mermaid_section.count(".->") >= 2


def test_plan_todo_raw_section_text_fallback(tmp_path):
    """--todo emits raw Steps-section text when no `N. ` numbered items are found.

    Pins the documented fallback at plan_cmd.py:276: when _extract_steps_section
    returns non-None but _parse_steps_for_json returns [] (because the regex
    `^(?:###\\s+)?(\\d+)\\.\\s+(.+)` matches no lines), the TODO emits a single
    line `{phase}.1 [{sop_id}] {steps_section.strip()}`. This is user-observable
    behaviour for SOPs that have a placeholder Steps section (e.g. fresh drafts).
    """
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "TST-2100-SOP-Prose-Steps.md").write_text(
        "# SOP-2100: Prose Steps\n\n"
        "**Applies to:** Test\n"
        "**Last updated:** 2026-04-19\n"
        "**Last reviewed:** 2026-04-19\n"
        "**Status:** Active\n\n---\n\n"
        "## What Is It?\n\nA test SOP.\n\n"
        "## Why\n\nTest.\n\n"
        "## When to Use\n\nTest.\n\n"
        "## When NOT to Use\n\nTest.\n\n"
        "## Steps\n\nTODO: fill in the numbered steps.\n\n"
        "---\n\n## Change History\n\n"
        "| Date | Change | By |\n|------|--------|----|\n"
        "| 2026-04-19 | Initial | — |\n"
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["plan", "TST-2100", "--todo", "--root", str(tmp_path)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "[TST-2100] TODO: fill in the numbered steps." in result.output


# ---------------------------------------------------------------------------
# FXA-2218 D4 — af plan cross-SOP runtime checks + output-contract branching
# ---------------------------------------------------------------------------


def _write_sop_with_cross_sop_loop(
    path: Path, prefix: str, acid: str, title: str, to_ref: str, from_step: int = 3
):
    """Helper: write an SOP with a cross-SOP Workflow loop."""
    content = f"""# SOP-{acid}: {title}

**Applies to:** Test
**Last updated:** 2026-04-19
**Last reviewed:** 2026-04-19
**Status:** Active
**Workflow loops:** [{{id: cx, from: {from_step}, to: "{to_ref}", max_iterations: 3, condition: "if fail"}}]

---

## What Is It?

Test.

## Why

Test.

## When to Use

Test.

## When NOT to Use

Test.

## Steps

1. A
2. B
3. C

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-19 | Initial | — |
"""
    path.write_text(content)


def _write_simple_sop(path: Path, prefix: str, acid: str, title: str):
    """Helper: write a minimal-valid SOP with 3 steps and no loops."""
    content = f"""# SOP-{acid}: {title}

**Applies to:** Test
**Last updated:** 2026-04-19
**Last reviewed:** 2026-04-19
**Status:** Active

---

## What Is It?

Test.

## Why

Test.

## When to Use

Test.

## When NOT to Use

Test.

## Steps

1. A
2. B
3. C

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-19 | Initial | — |
"""
    path.write_text(content)


def test_plan_cross_sop_target_not_in_composed_plan(tmp_path):
    """D4: af plan errors if cross-SOP target is not in the composed plan."""
    rules = tmp_path / "rules"
    rules.mkdir()
    _write_sop_with_cross_sop_loop(
        rules / "TST-2200-SOP-Source.md", "TST", "2200", "Source", to_ref="TST-2100.1"
    )
    # TST-2100 NOT written to rules — cross-ref dangles at plan time.

    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "TST-2200", "--root", str(tmp_path)], catch_exceptions=False
    )
    assert result.exit_code != 0
    assert "TST-2100" in result.output
    assert "not in composed plan" in result.output


def test_plan_cross_sop_forward_direction_rejected(tmp_path):
    """D4: af plan errors if cross-SOP target comes AFTER source in plan order."""
    rules = tmp_path / "rules"
    rules.mkdir()
    # Source SOP (TST-2200) loops back to TST-2100, but we compose
    # `TST-2200 TST-2100` — target is AFTER source, not before.
    _write_sop_with_cross_sop_loop(
        rules / "TST-2200-SOP-Source.md", "TST", "2200", "Source", to_ref="TST-2100.1"
    )
    _write_simple_sop(rules / "TST-2100-SOP-Target.md", "TST", "2100", "Target")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["plan", "TST-2200", "TST-2100", "--root", str(tmp_path)],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "back-edges only" in result.output


def test_plan_cross_sop_happy_path_todo_shows_dotted_ref(tmp_path):
    """D4 happy path: --todo TODO suffix shows 'back to PREFIX-ACID.step' for cross-SOP."""
    rules = tmp_path / "rules"
    rules.mkdir()
    _write_simple_sop(rules / "TST-2100-SOP-Target.md", "TST", "2100", "Target")
    _write_sop_with_cross_sop_loop(
        rules / "TST-2200-SOP-Source.md", "TST", "2200", "Source", to_ref="TST-2100.1"
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["plan", "TST-2100", "TST-2200", "--todo", "--root", str(tmp_path)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    # The loop-back annotation should render the raw cross-SOP ref, not a
    # malformed "{phase}.TST-2100.1" form.
    assert "back to TST-2100.1" in result.output
    assert "2.TST-2100.1" not in result.output


def test_plan_cross_sop_happy_path_json_loops_shows_raw_ref(tmp_path):
    """D4 happy path: --json loops[].to emits raw 'PREFIX-ACID.step' for cross-SOP."""
    import json

    rules = tmp_path / "rules"
    rules.mkdir()
    _write_simple_sop(rules / "TST-2100-SOP-Target.md", "TST", "2100", "Target")
    _write_sop_with_cross_sop_loop(
        rules / "TST-2200-SOP-Source.md", "TST", "2200", "Source", to_ref="TST-2100.1"
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "plan",
            "TST-2100",
            "TST-2200",
            "--todo",
            "--json",
            "--root",
            str(tmp_path),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    loops = data.get("loops", [])
    assert any(
        loop["to"] == "TST-2100.1" and loop["sop"] == "TST-2200" for loop in loops
    ), f"Expected cross-SOP loop with to='TST-2100.1'; got loops={loops}"


# ---------------------------------------------------------------------------
# FXA-2218 Commit 7 — --graph-layout flag + dispatch
# ---------------------------------------------------------------------------


def test_graph_layout_nested_default(sample_project, monkeypatch):
    """Default --graph output uses nested layout (inner step-boxes visible)."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    # COR-1602 has a well-formed Steps section + loops so the renderer
    # produces meaningful nested output.
    result = runner.invoke(
        cli,
        ["plan", "--graph", "--graph-format", "ascii", "COR-1602"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    # Nested layout renders outer phase-box + inner step-boxes. Count "┌─"
    # occurrences — flat has 1 (outer only), nested has 1 per phase + 1 per
    # step inside. COR-1602 has multiple steps, so >= 2 indicates nested.
    assert result.output.count("┌─") >= 2, (
        "Expected nested layout with inner step-boxes; got:\n" + result.output
    )


def test_graph_layout_flat_produces_legacy_format(sample_project, monkeypatch):
    """--graph-layout=flat falls back to the legacy ascii_graph renderer."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "plan",
            "--graph",
            "--graph-format",
            "ascii",
            "--graph-layout",
            "flat",
            "COR-1602",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    # Flat layout: one outer box per phase, steps as text lines inside
    # (no inner ┌─ step-boxes). Count of "┌─" equals phase count (1 here).
    assert result.output.count("┌─") == 1


def test_plan_cross_sop_accepts_repeated_target_with_earlier_occurrence(tmp_path):
    """D4 must accept a cross-SOP loop in `B` targeting `A` when plan is
    `A B A` — the leading `A` precedes `B`, so the back-edge is valid
    even though the trailing `A` does not (PR #59 Codex review P2 #5)."""
    rules = tmp_path / "rules"
    rules.mkdir()
    _write_simple_sop(rules / "TST-2100-SOP-A.md", "TST", "2100", "A")
    _write_sop_with_cross_sop_loop(
        rules / "TST-2200-SOP-B.md",
        "TST",
        "2200",
        "B",
        to_ref="TST-2100.1",
    )

    runner = CliRunner()
    # Compose A, B, A — A appears twice. Loop in B targets A.1.
    result = runner.invoke(
        cli,
        [
            "plan",
            "TST-2100",
            "TST-2200",
            "TST-2100",
            "--root",
            str(tmp_path),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (
        f"D4 rejected valid back-edge across repeated SOP: {result.output}"
    )


def test_plan_cross_sop_still_rejects_when_all_target_occurrences_after_source(
    tmp_path,
):
    """D4 still rejects a cross-SOP loop when ALL target occurrences come
    AFTER the source (regression for the any-precedes-source semantics)."""
    rules = tmp_path / "rules"
    rules.mkdir()
    _write_simple_sop(rules / "TST-2100-SOP-A.md", "TST", "2100", "A")
    _write_sop_with_cross_sop_loop(
        rules / "TST-2200-SOP-B.md",
        "TST",
        "2200",
        "B",
        to_ref="TST-2100.1",
    )

    runner = CliRunner()
    # Compose B first, then A twice — A only appears AFTER B.
    result = runner.invoke(
        cli,
        [
            "plan",
            "TST-2200",
            "TST-2100",
            "TST-2100",
            "--root",
            str(tmp_path),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "back-edges only" in result.output


def test_graph_layout_without_graph_errors(sample_project, monkeypatch):
    """--graph-layout without --graph raises UsageError (same coupling as --graph-format)."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["plan", "--graph-layout", "flat", "COR-1500"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "--graph-layout requires --graph" in result.output


# ── FXA-2227 Phase 8a: _build_mermaid_phases branch propagation ─────────────


def _make_branchy_phase_info(prefix: str = "TST", acid: str = "9900"):
    """Build a minimal phase_info tuple for a 3-way fan-out SOP fixture."""
    content = """\
# TST-9900: Branchy SOP

**Applies to:** Test
**Last updated:** 2026-04-28
**Last reviewed:** 2026-04-28
**Status:** Active
**Workflow branches:** [{from: 2, to: [{id: 3a, label: pass}, {id: 3b, label: fail}, {id: 3c, label: esc}]}]
---

## What Is It?

A test SOP with 3-way branch.

## Why

Test.

## When to Use

Test.

## When NOT to Use

Test.

## Steps

1. Setup
2. Decision
3a. Pass path
3b. Fail path
3c. Escalate path
4. Continue

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-28 | Initial | — |
"""
    parsed = parse_metadata(content)
    doc = Document(
        prefix=prefix,
        acid=acid,
        type_code="SOP",
        title="Branchy SOP",
        directory="rules",
        source="prj",
    )
    sig = WorkflowSignature(input="", output="")
    loops = []
    return [(f"{prefix}-{acid}", doc, parsed, sig, loops)]


def test_plan_propagates_branches_to_phase_payload():
    """_build_mermaid_phases sets 'branches' key when SOP has Workflow branches:.

    Asserts:
    - The PhaseDict has a 'branches' key.
    - branches is a list with one BranchSignature entry.
    - branches[0].from_step == 2.
    - branches[0].to has 3 BranchTarget entries with labels pass/fail/esc.
    """
    phase_info = _make_branchy_phase_info()
    phases = _build_mermaid_phases(phase_info)

    assert len(phases) == 1
    phase = phases[0]
    assert "branches" in phase, "PhaseDict missing 'branches' key for branchy SOP"

    branches = phase["branches"]
    assert isinstance(branches, list)
    assert len(branches) == 1

    sig = branches[0]
    assert isinstance(sig, BranchSignature)
    assert sig.from_step == 2

    targets = sig.to
    assert len(targets) == 3
    labels = {t.label for t in targets}
    assert labels == {"pass", "fail", "esc"}


def test_plan_no_branches_key_for_legacy_sop():
    """_build_mermaid_phases does NOT set 'branches' key for a legacy SOP.

    Preserves the optional-field discipline: PhaseDict shape stays minimal
    for SOPs that have no Workflow branches: field.
    """
    content = """\
# TST-9901: Legacy SOP

**Applies to:** Test
**Last updated:** 2026-04-28
**Last reviewed:** 2026-04-28
**Status:** Active

---

## What Is It?

A legacy SOP with no branches.

## Why

Test.

## When to Use

Test.

## When NOT to Use

Test.

## Steps

1. Step one
2. Step two

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-28 | Initial | — |
"""
    parsed = parse_metadata(content)
    doc = Document(
        prefix="TST",
        acid="9901",
        type_code="SOP",
        title="Legacy SOP",
        directory="rules",
        source="prj",
    )
    sig = WorkflowSignature(input="", output="")
    phase_info = [("TST-9901", doc, parsed, sig, [])]

    phases = _build_mermaid_phases(phase_info)

    assert len(phases) == 1
    assert "branches" not in phases[0], (
        "PhaseDict must NOT have 'branches' key for legacy SOP (optional-field discipline)"
    )


def test_plan_handles_malformed_branches_gracefully():
    """_build_mermaid_phases raises ClickException (not MalformedDocumentError) for invalid Workflow branches: YAML.

    Mirrors the loop-parsing guard: a single bad SOP must not propagate a bare
    MalformedDocumentError to the caller.  The ClickException message must
    include the document's prefix-ACID so the user knows which SOP failed.
    """
    content = """\
# TST-9902: Malformed Branches SOP

**Applies to:** Test
**Last updated:** 2026-04-28
**Last reviewed:** 2026-04-28
**Status:** Active
**Workflow branches:** [{from: not-an-int, to: [{id: 3a, label: pass}]}]

---

## What Is It?

A test SOP with malformed branches.

## Why

Test.

## When to Use

Test.

## When NOT to Use

Test.

## Steps

1. Step one
2. Step two

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-28 | Initial | — |
"""
    parsed = parse_metadata(content)
    doc = Document(
        prefix="TST",
        acid="9902",
        type_code="SOP",
        title="Malformed Branches SOP",
        directory="rules",
        source="prj",
    )
    sig = WorkflowSignature(input="", output="")
    phase_info = [("TST-9902", doc, parsed, sig, [])]

    with pytest.raises(click.ClickException) as exc_info:
        _build_mermaid_phases(phase_info)

    assert "TST-9902" in str(exc_info.value.format_message())
