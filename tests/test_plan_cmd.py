"""Tests for af plan command (FXA-2134)."""

from pathlib import Path

from click.testing import CliRunner
from fx_alfred.cli import cli


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


def test_plan_init_mode(sample_project, monkeypatch):
    """--init flag outputs suggested prompt text (no SOP_IDs needed)."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "--init"], catch_exceptions=False)
    assert result.exit_code == 0
    # Init mode should suggest prompt snippets
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
