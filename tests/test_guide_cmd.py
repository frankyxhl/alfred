from pathlib import Path

from click.testing import CliRunner
from fx_alfred.cli import cli


def test_guide_outputs_content(sample_project, monkeypatch):
    """Guide command outputs routing content from PKG layer."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["guide"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "Workflow Routing" in result.output


def test_guide_outputs_pkg_routing(sample_project, monkeypatch):
    """PKG routing doc (COR-1103) content appears in output."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["guide"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "COR-1103" in result.output
    assert "Intent-Based Router" in result.output


def test_guide_outputs_usr_routing(sample_project, monkeypatch):
    """USR routing doc content appears when present."""
    user_alfred = Path.home() / ".alfred"
    user_alfred.mkdir(parents=True, exist_ok=True)
    routing_doc = user_alfred / "ALF-2207-SOP-Workflow-Routing-USR.md"
    routing_doc.write_text(
        """# SOP-2207: Workflow Routing USR

**Applies to:** All
**Status:** Active

---

USR routing test content here
"""
    )
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["guide"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "ALF-2207" in result.output
    assert "USR routing test content here" in result.output


def test_guide_outputs_prj_routing(sample_project, monkeypatch):
    """PRJ routing doc content appears when present."""
    routing_doc = sample_project / "rules" / "FXA-2125-SOP-Workflow-Routing-PRJ.md"
    routing_doc.write_text(
        """# SOP-2125: Workflow Routing PRJ

**Applies to:** FXA
**Status:** Active

---

PRJ routing test content here
"""
    )
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["guide"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "FXA-2125" in result.output
    assert "PRJ routing test content here" in result.output


def test_guide_skips_deprecated_routing(sample_project, monkeypatch):
    """Deprecated routing doc is not shown."""
    routing_doc = sample_project / "rules" / "FXA-2125-SOP-Workflow-Routing-PRJ.md"
    routing_doc.write_text(
        """# SOP-2125: Workflow Routing PRJ

**Applies to:** FXA
**Status:** Deprecated

---

This should not appear
"""
    )
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["guide"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "This should not appear" not in result.output


def test_guide_missing_layer_shows_note(sample_project, monkeypatch):
    """Missing USR/PRJ routing doc shows note."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["guide"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "no active routing document found" in result.output


def test_guide_shows_layer_separators(sample_project, monkeypatch):
    """Output contains layer separator headers."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["guide"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "PKG:" in result.output


def test_guide_malformed_routing_continues(sample_project, monkeypatch):
    """Malformed doc shows error, continues to next layer."""
    routing_doc = sample_project / "rules" / "FXA-2125-SOP-Workflow-Routing-PRJ.md"
    routing_doc.write_text("This is not a valid document at all")
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["guide"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "malformed" in result.output.lower()


def test_guide_multi_active_warns(sample_project, monkeypatch):
    """Warning when multiple Active routing docs in same layer."""
    doc1 = sample_project / "rules" / "FXA-2125-SOP-Workflow-Routing-PRJ.md"
    doc1.write_text(
        """# SOP-2125: Workflow Routing PRJ

**Applies to:** FXA
**Status:** Active

---

First routing doc
"""
    )
    doc2 = sample_project / "rules" / "FXA-2126-SOP-Workflow-Routing-PRJ2.md"
    doc2.write_text(
        """# SOP-2126: Workflow Routing PRJ2

**Applies to:** FXA
**Status:** Active

---

Second routing doc
"""
    )
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["guide"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "warning" in result.output.lower() or "Warning" in result.output


def test_guide_selects_lowest_acid(sample_project, monkeypatch):
    """When multiple Active, uses lowest ACID doc."""
    doc1 = sample_project / "rules" / "FXA-2125-SOP-Workflow-Routing-PRJ.md"
    doc1.write_text(
        """# SOP-2125: Workflow Routing PRJ

**Applies to:** FXA
**Status:** Active

---

Lowest ACID content
"""
    )
    doc2 = sample_project / "rules" / "FXA-2126-SOP-Workflow-Routing-PRJ2.md"
    doc2.write_text(
        """# SOP-2126: Workflow Routing PRJ2

**Applies to:** FXA
**Status:** Active

---

Higher ACID content
"""
    )
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["guide"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "Lowest ACID content" in result.output
    assert "FXA-2125" in result.output


def test_help_contains_quickstart():
    """af --help output contains quick-start content."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "PREFIX-ACID" in result.output or "Document Naming" in result.output
    assert "PKG" in result.output or "Layer" in result.output
