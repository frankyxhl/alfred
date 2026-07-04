import pytest


from pathlib import Path
import json

from click.testing import CliRunner
from fx_alfred.cli import cli


pytestmark = [pytest.mark.cli, pytest.mark.docs, pytest.mark.integration]


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


def test_guide_text_output_shows_display_labels(sample_project, monkeypatch):
    """guide text output shows display labels (PKG/USR/PRJ), not raw values.

    Guard: text mode uses SOURCE_LABELS (uppercase) for human readability.
    The JSON fix (#297) must not affect text output — the ``label`` variable
    on line 26 of guide_cmd.py is independent of the JSON ``source`` field.
    """
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["guide"], catch_exceptions=False)
    assert result.exit_code == 0
    # Text output uses display labels in separator headers: "PKG:", "USR:", "PRJ:"
    assert "PKG:" in result.output

    # The raw lowercase "pkg:" must NOT appear as a section header
    # (guide_cmd.py:26 builds label from source.upper() for text output)
    for line in result.output.split("\n"):
        if line.strip().startswith("pkg:"):
            assert False, (
                f"Raw source leaked into text section header: {line.strip()!r}"
            )


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


def test_guide_detects_routing_by_metadata_role(sample_project, monkeypatch):
    """Doc with 'Document role: routing' metadata is treated as routing doc even without filename pattern."""
    routing_doc = sample_project / "rules" / "FXA-9999-SOP-Custom-Name.md"
    routing_doc.write_text(
        """# SOP-9999: Custom Named Routing Doc

**Applies to:** FXA
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Active
**Document role:** routing

---

Metadata role routing content here
"""
    )
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["guide"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "Metadata role routing content here" in result.output


def test_help_contains_quickstart():
    """af --help output contains quick-start content."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "PREFIX-ACID" in result.output or "Document Naming" in result.output
    assert "PKG" in result.output or "Layer" in result.output


def test_guide_appends_usage_record_to_user_log(sample_project, monkeypatch):
    """af guide records routing-doc usage in the user ledger."""
    monkeypatch.chdir(sample_project)

    result = CliRunner().invoke(cli, ["guide"], catch_exceptions=False)

    assert result.exit_code == 0
    files = sorted((Path.home() / ".alfred" / "logs").glob("*.jsonl"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text(encoding="utf-8").strip())
    assert payload["command"] == "guide"
    assert payload["usage_kind"] == "routing_docs"
    assert payload["agent_name"] == "af"
    assert payload["refs"]
    assert payload["result_count"] == len(payload["refs"])


def test_guide_reminds_active_process_declaration(sample_project, monkeypatch):
    """Closing reminder tells operators to open replies with a COR-1402 line."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["guide"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "active-process line" in result.output
    assert "COR-1402" in result.output
    json_result = runner.invoke(cli, ["guide", "--json"], catch_exceptions=False)
    assert json_result.exit_code == 0
    assert "active-process line" not in json_result.output


def test_guide_logging_failure_does_not_break_command(sample_project, monkeypatch):
    """Usage telemetry is fail-open for the user-facing command."""
    monkeypatch.chdir(sample_project)

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("fx_alfred.commands.guide_cmd.append_usage_event", boom)

    result = CliRunner().invoke(cli, ["guide"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "Workflow Routing" in result.output


# ── FXA-2314: USR sub-project layer via projects.json mapping ─────────────────


def _setup_mapped_guide_context(tmp_path):
    """Build the full fixture for a mapped-root guide test.

    Layout:
        ~/.alfred/ALF-2207-SOP-Workflow-Routing-USR.md   (sole USR routing doc)
        ~/.alfred/NRV/NRV-2500-SOP-Workflow-Routing-PRJ.md  (subproject)
        ~/.alfred/projects.json  → { <ext_repo>: "NRV" }
        <ext_repo>/  (no rules/)
    """
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True, exist_ok=True)

    # Sole USR routing doc
    (alfred / "ALF-2207-SOP-Workflow-Routing-USR.md").write_text(
        "# SOP-2207: Workflow Routing USR\n\n"
        "**Applies to:** All\n"
        "**Status:** Active\n\n"
        "---\n\n"
        "USR routing content.\n",
        encoding="utf-8",
    )

    # Subproject routing doc
    nrv_dir = alfred / "NRV"
    nrv_dir.mkdir(exist_ok=True)
    (nrv_dir / "NRV-2500-SOP-Workflow-Routing-PRJ.md").write_text(
        "# SOP-2500: Workflow Routing PRJ\n\n"
        "**Applies to:** NRV\n"
        "**Status:** Active\n\n"
        "---\n\n"
        "NRV subproject routing content.\n",
        encoding="utf-8",
    )

    ext_repo = tmp_path / "ext_repo"
    ext_repo.mkdir(exist_ok=True)

    (alfred / "projects.json").write_text(
        json.dumps({"projects": {str(ext_repo.resolve()): "NRV"}}),
        encoding="utf-8",
    )
    return ext_repo


def test_guide_mapped_root_no_usr_layer_warning(tmp_path):
    """Mapped root: guide must NOT warn about multiple active routing docs in USR."""
    ext_repo = _setup_mapped_guide_context(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["guide", "--root", str(ext_repo)], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "2 active routing docs in USR layer" not in result.output, (
        "With NRV mapped as PRJ, ALF-2207 should be the sole USR routing doc "
        "— no 'multiple active' warning should appear"
    )


def test_guide_mapped_root_shows_subproject_routing_doc_under_prj(tmp_path):
    """Mapped root: guide shows the subproject routing doc in the PRJ section."""
    ext_repo = _setup_mapped_guide_context(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["guide", "--root", str(ext_repo)], catch_exceptions=False
    )
    assert result.exit_code == 0
    # The PRJ section header must reference NRV-2500
    assert "PRJ: NRV-2500" in result.output, (
        "Guide output must show NRV-2500 as the PRJ routing doc in a mapped context"
    )
    # The "no active routing document found" placeholder must NOT appear for PRJ
    assert "PRJ: (no active routing document found)" not in result.output
