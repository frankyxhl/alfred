"""Tests for af plan command (FXA-2134)."""

from pathlib import Path

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
    """Incompatible typed chain raises ClickException with mismatch message."""
    rules_dir = sample_project / "rules"
    _create_typed_sop(
        rules_dir, "TST", "6001", "Step-A", "proposal:draft", "proposal:reviewed"
    )
    _create_typed_sop(
        rules_dir, "TST", "6002", "Step-B", "change:approved", "change:completed"
    )

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "TST-6001", "TST-6002"])
    assert result.exit_code != 0
    assert "Workflow type mismatch" in result.output


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
