"""Tests for --json output mode on guide, plan, search, validate commands (FXA-2142)."""

import json
from pathlib import Path

from click.testing import CliRunner
from fx_alfred.cli import cli


# =============================================================================
# GUIDE --json
# =============================================================================


def test_guide_json_outputs_valid_json(sample_project, monkeypatch):
    """guide --json outputs valid JSON."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["guide", "--json"], catch_exceptions=False)
    assert result.exit_code == 0
    # Should parse without error
    data = json.loads(result.output)
    assert isinstance(data, dict)


def test_guide_json_has_schema_version(sample_project, monkeypatch):
    """guide --json has schema_version "1"."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["guide", "--json"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data.get("schema_version") == "1"


def test_guide_json_has_routing_docs_array(sample_project, monkeypatch):
    """guide --json has routing_docs array with correct structure."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["guide", "--json"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "routing_docs" in data
    assert isinstance(data["routing_docs"], list)

    # PKG layer has COR-1103 routing doc
    routing_docs = data["routing_docs"]
    assert len(routing_docs) >= 1

    # Check structure of routing doc
    doc = routing_docs[0]
    assert "doc_id" in doc
    assert "title" in doc
    assert "source" in doc
    assert "status" in doc
    assert "role" in doc

    # COR-1103 should be in PKG layer
    cor_1103 = next((d for d in routing_docs if d["doc_id"] == "COR-1103"), None)
    assert cor_1103 is not None
    assert cor_1103["source"] == "PKG"
    assert cor_1103["status"] == "Active"
    assert cor_1103["role"] == "routing"


def test_guide_json_includes_usr_routing(sample_project, monkeypatch):
    """guide --json includes USR layer routing doc when present."""
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
    result = runner.invoke(cli, ["guide", "--json"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)

    routing_docs = data["routing_docs"]
    usr_doc = next((d for d in routing_docs if d["doc_id"] == "ALF-2207"), None)
    assert usr_doc is not None
    assert usr_doc["source"] == "USR"


def test_guide_json_includes_prj_routing(sample_project, monkeypatch):
    """guide --json includes PRJ layer routing doc when present."""
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
    result = runner.invoke(cli, ["guide", "--json"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)

    routing_docs = data["routing_docs"]
    prj_doc = next((d for d in routing_docs if d["doc_id"] == "FXA-2125"), None)
    assert prj_doc is not None
    assert prj_doc["source"] == "PRJ"


def test_guide_json_skips_deprecated(sample_project, monkeypatch):
    """guide --json skips Deprecated routing docs."""
    routing_doc = sample_project / "rules" / "FXA-2125-SOP-Workflow-Routing-PRJ.md"
    routing_doc.write_text(
        """# SOP-2125: Workflow Routing PRJ

**Applies to:** FXA
**Status:** Deprecated

---

Should not appear
"""
    )
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["guide", "--json"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)

    routing_docs = data["routing_docs"]
    deprecated = next((d for d in routing_docs if d["doc_id"] == "FXA-2125"), None)
    assert deprecated is None


def test_guide_text_output_unchanged_without_json(sample_project, monkeypatch):
    """guide without --json outputs unchanged text format."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["guide"], catch_exceptions=False)
    assert result.exit_code == 0
    # Should NOT be valid JSON
    try:
        json.loads(result.output)
        assert False, "Output should not be valid JSON without --json"
    except json.JSONDecodeError:
        pass
    # Should contain expected text markers
    assert "Workflow Routing" in result.output or "COR-1103" in result.output


# =============================================================================
# PLAN --json
# =============================================================================


def test_plan_json_outputs_valid_json(sample_project, monkeypatch):
    """plan --json outputs valid JSON."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "--json", "COR-1500"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, dict)


def test_plan_json_has_schema_version(sample_project, monkeypatch):
    """plan --json has schema_version "1"."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "--json", "COR-1500"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data.get("schema_version") == "1"


def test_plan_json_has_sop_ids(sample_project, monkeypatch):
    """plan --json has sop_ids array matching input."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "--json", "COR-1500"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "sop_ids" in data
    assert data["sop_ids"] == ["COR-1500"]


def test_plan_json_has_phases_array(sample_project, monkeypatch):
    """plan --json has phases array with correct structure."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "--json", "COR-1500"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "phases" in data
    assert isinstance(data["phases"], list)
    assert len(data["phases"]) >= 1

    # Check phase structure
    phase = data["phases"][0]
    assert "phase" in phase
    assert "source_sop" in phase
    assert "steps" in phase
    assert phase["source_sop"] == "COR-1500"

    # Steps should have index, text, gate fields
    steps = phase["steps"]
    assert isinstance(steps, list)
    if steps:
        step = steps[0]
        assert "index" in step
        assert "text" in step
        assert "gate" in step


def test_plan_json_multiple_sops(sample_project, monkeypatch):
    """plan --json with multiple SOPs creates multiple phases."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "--json", "COR-1500", "COR-1103"], catch_exceptions=False
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["sop_ids"] == ["COR-1500", "COR-1103"]
    assert len(data["phases"]) == 2


def test_plan_json_phase_names_match_sop_ids(sample_project, monkeypatch):
    """plan --json phase names derived from SOP IDs (phase per SOP)."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "--json", "COR-1500"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)

    # Phase should be named (could be SOP ID or derived name)
    phase = data["phases"][0]
    assert phase["phase"] is not None
    assert phase["source_sop"] == "COR-1500"


def test_plan_text_output_unchanged_without_json(sample_project, monkeypatch):
    """plan without --json outputs unchanged text format."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "COR-1500"], catch_exceptions=False)
    assert result.exit_code == 0
    # Should NOT be valid JSON
    try:
        json.loads(result.output)
        assert False, "Output should not be valid JSON without --json"
    except json.JSONDecodeError:
        pass
    # Should contain expected text markers
    assert "COR-1500" in result.output


# =============================================================================
# SEARCH --json
# =============================================================================


def test_search_json_outputs_valid_json(sample_project, monkeypatch):
    """search --json outputs valid JSON."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "--json", "routing"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, dict)


def test_search_json_has_schema_version(sample_project, monkeypatch):
    """search --json has schema_version "1"."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "--json", "routing"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data.get("schema_version") == "1"


def test_search_json_has_query(sample_project, monkeypatch):
    """search --json has query field matching input."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "--json", "routing"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data.get("query") == "routing"


def test_search_json_has_results_array(sample_project, monkeypatch):
    """search --json has results array with correct structure."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "--json", "routing"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "results" in data
    assert isinstance(data["results"], list)

    # COR-1103 contains "routing" in title/content
    if data["results"]:
        res = data["results"][0]
        assert "doc_id" in res
        assert "title" in res
        assert "source" in res
        assert "snippet" in res


def test_search_json_finds_cor_1103(sample_project, monkeypatch):
    """search --json finds COR-1103 for 'routing' query."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "--json", "routing"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)

    cor_1103 = next((r for r in data["results"] if r["doc_id"] == "COR-1103"), None)
    assert cor_1103 is not None
    assert cor_1103["source"] == "PKG"
    assert "snippet" in cor_1103
    assert len(cor_1103["snippet"]) > 0


def test_search_json_no_matches(sample_project, monkeypatch):
    """search --json returns empty results for no matches."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["search", "--json", "xyzzyplugh"], catch_exceptions=False
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["query"] == "xyzzyplugh"
    assert data["results"] == []


def test_search_text_output_unchanged_without_json(sample_project, monkeypatch):
    """search without --json outputs unchanged text format."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "routing"], catch_exceptions=False)
    assert result.exit_code == 0
    # Should NOT be valid JSON
    try:
        json.loads(result.output)
        assert False, "Output should not be valid JSON without --json"
    except json.JSONDecodeError:
        pass
    # Should contain expected text markers
    assert "COR-1103" in result.output


# =============================================================================
# VALIDATE --json
# =============================================================================


def test_validate_json_outputs_valid_json(sample_project, monkeypatch):
    """validate --json outputs valid JSON."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--json"], catch_exceptions=False)
    # Exit code may be 0 or 1 depending on validation results
    data = json.loads(result.output)
    assert isinstance(data, dict)


def test_validate_json_has_schema_version(sample_project, monkeypatch):
    """validate --json has schema_version "1"."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--json"], catch_exceptions=False)
    data = json.loads(result.output)
    assert data.get("schema_version") == "1"


def test_validate_json_has_results_array(sample_project, monkeypatch):
    """validate --json has results array with per-document validation."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--json"], catch_exceptions=False)
    data = json.loads(result.output)
    assert "results" in data
    assert isinstance(data["results"], list)

    # Each result should have doc_id, valid, errors
    if data["results"]:
        res = data["results"][0]
        assert "doc_id" in res
        assert "valid" in res
        assert "errors" in res
        assert isinstance(res["errors"], list)


def test_validate_json_valid_doc(sample_project, monkeypatch):
    """validate --json shows valid:true for documents with no issues."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--json"], catch_exceptions=False)
    data = json.loads(result.output)

    # PKG layer docs should be valid (COR-* are well-formed)
    pkg_results = [r for r in data["results"] if r["doc_id"].startswith("COR-")]
    for res in pkg_results[:5]:  # Check first 5 COR docs
        assert res["valid"] is True
        assert res["errors"] == []


def test_validate_json_invalid_doc(sample_project, monkeypatch):
    """validate --json shows valid:false with errors for invalid docs."""
    # Create an invalid document (missing required metadata)
    rules_dir = sample_project / "rules"
    bad_doc = rules_dir / "FXA-9999-SOP-Bad-Doc.md"
    bad_doc.write_text(
        """# SOP-9999: Bad Doc

This doc is missing required metadata fields.
"""
    )
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--json"], catch_exceptions=False)
    # Exit code 1 when issues found
    assert result.exit_code == 1
    data = json.loads(result.output)

    # Find our bad doc
    bad_result = next((r for r in data["results"] if r["doc_id"] == "FXA-9999"), None)
    assert bad_result is not None
    assert bad_result["valid"] is False
    assert len(bad_result["errors"]) > 0


def test_validate_json_exit_code_zero_when_valid(sample_project, monkeypatch):
    """validate --json exits 0 when all docs valid."""
    # Use only PKG layer (COR docs are valid)
    # sample_project has no issues in PKG layer
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--json"], catch_exceptions=False)
    # If there are issues in PRJ layer docs, exit code may be 1
    # For clean run, exit code 0
    data = json.loads(result.output)
    all_valid = all(r["valid"] for r in data["results"])
    if all_valid:
        assert result.exit_code == 0


def test_validate_json_exit_code_nonzero_when_invalid(sample_project, monkeypatch):
    """validate --json exits 1 when any doc invalid."""
    rules_dir = sample_project / "rules"
    bad_doc = rules_dir / "FXA-9999-SOP-Bad-Doc.md"
    bad_doc.write_text("# Invalid doc\nNo metadata at all.")
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--json"], catch_exceptions=False)
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert any(not r["valid"] for r in data["results"])


def test_validate_text_output_unchanged_without_json(sample_project, monkeypatch):
    """validate without --json outputs unchanged text format."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate"], catch_exceptions=False)
    # Should NOT be valid JSON
    try:
        json.loads(result.output)
        assert False, "Output should not be valid JSON without --json"
    except json.JSONDecodeError:
        pass
    # Should contain expected text markers
    assert "documents checked" in result.output.lower()


# =============================================================================
# MIXED TESTS
# =============================================================================


def test_all_commands_json_no_mixed_output(sample_project, monkeypatch):
    """All --json commands produce pure JSON with no text mixed in."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()

    # guide
    result = runner.invoke(cli, ["guide", "--json"], catch_exceptions=False)
    data = json.loads(result.output)
    assert "schema_version" in data

    # plan
    result = runner.invoke(cli, ["plan", "--json", "COR-1500"], catch_exceptions=False)
    data = json.loads(result.output)
    assert "schema_version" in data

    # search
    result = runner.invoke(cli, ["search", "--json", "routing"], catch_exceptions=False)
    data = json.loads(result.output)
    assert "schema_version" in data

    # validate
    result = runner.invoke(cli, ["validate", "--json"], catch_exceptions=False)
    data = json.loads(result.output)
    assert "schema_version" in data
