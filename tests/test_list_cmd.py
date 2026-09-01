import pytest


from pathlib import Path

from click.testing import CliRunner
from fx_alfred.cli import cli


pytestmark = pytest.mark.cli


def test_list_shows_documents(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["list"], catch_exceptions=False)
    assert result.exit_code == 0
    # PKG docs
    assert "COR-0001" in result.output
    assert "COR-1000" in result.output
    # PRJ docs
    assert "ALF-2201" in result.output
    assert "ALF-2202" in result.output


def test_list_shows_type_codes(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["list"], catch_exceptions=False)
    assert "REF" in result.output
    assert "SOP" in result.output
    assert "PRP" in result.output


def test_list_shows_source_labels(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["list"], catch_exceptions=False)
    assert "PKG" in result.output
    assert "PRJ" in result.output


def test_list_uses_spaces_not_tabs(sample_project, monkeypatch):
    """List output uses space alignment, not tabs."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["list"], catch_exceptions=False)
    assert result.exit_code == 0
    lines = result.output.strip().split("\n")
    # Each line should have double spaces between columns
    for line in lines:
        if "COR-" in line or "ALF-" in line:
            assert "\t" not in line, f"Found tab in: {line}"
            assert "  " in line, f"No double space in: {line}"


def test_list_with_root_before_subcommand(sample_project):
    """af --root <path> list works."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["--root", str(sample_project), "list"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "ALF-2201" in result.output


def test_list_with_root_after_subcommand(sample_project):
    """af list --root <path> works."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["list", "--root", str(sample_project)], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "ALF-2201" in result.output


def test_list_shows_usr_documents(tmp_path, monkeypatch):
    """af list shows documents from the USR layer (~/.alfred/)."""
    # isolate_home autouse fixture already patched Path.home() to tmp_path/fake_home
    user_alfred = Path.home() / ".alfred"
    user_alfred.mkdir(parents=True)
    (user_alfred / "TST-3000-SOP-Test.md").write_text("# Test SOP")

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["list"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "TST-3000" in result.output
    assert "USR" in result.output


def test_list_filter_type(sample_project, monkeypatch):
    """--type SOP shows only SOP documents (case-insensitive exact match)."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["list", "--type", "SOP"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "ALF-2202" in result.output  # SOP document
    assert "ALF-2201" not in result.output  # PRP document
    assert "ALF-0000" not in result.output  # REF document


def test_list_filter_type_case_insensitive(sample_project, monkeypatch):
    """--type sop (lowercase) matches SOP documents."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["list", "--type", "sop"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "ALF-2202" in result.output  # SOP document


def test_list_filter_prefix(sample_project, monkeypatch):
    """--prefix ALF shows only ALF documents."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["list", "--prefix", "ALF"], catch_exceptions=False)
    assert result.exit_code == 0
    # ALF docs should be shown
    assert "ALF-2201" in result.output
    assert "ALF-2202" in result.output
    assert "ALF-0000" in result.output
    # COR docs should NOT be shown
    assert "COR-0001" not in result.output
    assert "COR-1000" not in result.output


def test_list_filter_source(sample_project, monkeypatch):
    """--source prj shows only PRJ layer documents."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["list", "--source", "prj"], catch_exceptions=False)
    assert result.exit_code == 0
    # PRJ docs (ALF-*) should be shown
    assert "ALF-2201" in result.output
    assert "ALF-2202" in result.output
    assert "PRJ" in result.output
    # PKG docs should NOT be shown
    assert "COR-0001" not in result.output
    assert "PKG" not in result.output


def test_list_filter_combined(sample_project, monkeypatch):
    """--type SOP --prefix ALF shows only ALF SOPs (AND logic)."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["list", "--type", "SOP", "--prefix", "ALF"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "ALF-2202" in result.output  # ALF SOP
    assert "ALF-2201" not in result.output  # ALF PRP (wrong type)
    assert "ALF-0000" not in result.output  # ALF REF (wrong type)


def test_list_filter_exact_match(sample_project, monkeypatch):
    """--type SO does NOT match SOP (exact match required)."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["list", "--type", "SO"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "No documents found." in result.output


def test_list_json(sample_project, monkeypatch):
    """--json outputs JSON array with document fields."""
    import json

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["list", "--json"], catch_exceptions=False)
    assert result.exit_code == 0

    data = json.loads(result.output)
    assert isinstance(data, list)

    # Find ALF-2201 in the output
    alf_2201 = next(
        (d for d in data if d["prefix"] == "ALF" and d["acid"] == "2201"), None
    )
    assert alf_2201 is not None
    assert alf_2201["type_code"] == "PRP"
    assert alf_2201["title"] == "AF CLI Tool"
    assert alf_2201["source"] == "prj"
    assert alf_2201["directory"] == "rules"


def test_list_json_with_type_filter(sample_project, monkeypatch):
    """--json combined with --type filter outputs filtered JSON array."""
    import json

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["list", "--json", "--type", "SOP"], catch_exceptions=False
    )
    assert result.exit_code == 0

    data = json.loads(result.output)
    assert isinstance(data, list)

    # All returned docs should be SOP type
    for doc in data:
        assert doc["type_code"] == "SOP"

    # Should include ALF-2202 (SOP doc)
    acids = [d["acid"] for d in data]
    assert "2202" in acids


def test_list_json_empty_result(sample_project, monkeypatch):
    """--json emits exactly `[]` when filters match no documents.

    Locks the public JSON contract — consumers rely on --json always producing
    valid JSON, and an empty-array shape is the documented way to signal
    zero matches. Closes coverage gap at list_cmd.py:66.
    """
    import json

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    # "ZZ" is not a valid type_code, so filter matches nothing
    result = runner.invoke(
        cli, ["list", "--json", "--type", "ZZ"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert result.output == "[]\n"
    assert json.loads(result.output) == []


# ── FXA-2314: USR sub-project layer via projects.json mapping ─────────────────


def _setup_mapped_list_context(tmp_path):
    """Build a fixture with one USR doc, one subproject doc, and a mapping.

    Returns (alfred_dir, ext_repo, other_project).
    """
    import json as _json  # local import to avoid shadowing module-level

    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True, exist_ok=True)

    # Genuine USR-layer doc (NOT in any subproject dir)
    (alfred / "ALF-2207-SOP-Workflow-Routing-USR.md").write_text(
        "# USR doc", encoding="utf-8"
    )

    # Subproject dir
    nrv_dir = alfred / "NRV"
    nrv_dir.mkdir(exist_ok=True)
    (nrv_dir / "NRV-2500-SOP-Workflow-Routing-PRJ.md").write_text(
        "# Subproject doc", encoding="utf-8"
    )

    ext_repo = tmp_path / "ext_repo"
    ext_repo.mkdir(exist_ok=True)

    other_project = tmp_path / "other_project"
    other_project.mkdir(exist_ok=True)

    (alfred / "projects.json").write_text(
        _json.dumps({"projects": {str(ext_repo.resolve()): "NRV"}}),
        encoding="utf-8",
    )
    return alfred, ext_repo, other_project


def test_list_subproject_docs_labelled_prj_in_mapped_context(tmp_path):
    """Subproject docs appear with source='prj' in a mapped context (--json)."""
    import json as _json

    _, ext_repo, _ = _setup_mapped_list_context(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["list", "--json", "--root", str(ext_repo)], catch_exceptions=False
    )
    assert result.exit_code == 0
    data = _json.loads(result.output)
    nrv_doc = next(
        (d for d in data if d["prefix"] == "NRV" and d["acid"] == "2500"), None
    )
    assert nrv_doc is not None, "NRV-2500 must appear in list output for mapped context"
    assert nrv_doc["source"] == "prj", (
        f"Expected source='prj' for NRV-2500 in mapped context, got '{nrv_doc['source']}'"
    )


def test_list_source_usr_excludes_subproject_docs(tmp_path):
    """--source usr must NOT include subproject docs in a mapped context."""
    _, ext_repo, _ = _setup_mapped_list_context(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["list", "--source", "usr", "--root", str(ext_repo)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "NRV-2500" not in result.output, (
        "NRV-2500 is a subproject (PRJ) doc in mapped context — must NOT appear under --source usr"
    )


def test_list_unmapped_context_hides_subproject_docs(tmp_path):
    """From an unmapped context, registered subproject docs are absent (global USR exclusion)."""
    import json as _json

    _, _, other_project = _setup_mapped_list_context(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["list", "--json", "--root", str(other_project)], catch_exceptions=False
    )
    assert result.exit_code == 0
    data = _json.loads(result.output)
    nrv_docs = [d for d in data if d.get("prefix") == "NRV"]
    assert len(nrv_docs) == 0, (
        "NRV subproject docs must NOT appear in an unmapped context "
        "(global USR exclusion keeps them isolated)"
    )


def test_list_redirected_prj_doc_directory_in_json(tmp_path):
    """Redirected PRJ doc has directory=='NRV' (not '.alfred') in --json output."""
    import json as _json

    _, ext_repo, _ = _setup_mapped_list_context(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["list", "--json", "--root", str(ext_repo)], catch_exceptions=False
    )
    assert result.exit_code == 0
    data = _json.loads(result.output)
    nrv_doc = next(
        (d for d in data if d["prefix"] == "NRV" and d["acid"] == "2500"), None
    )
    assert nrv_doc is not None, "NRV-2500 must appear in list --json output"
    assert nrv_doc["directory"] == "NRV", (
        f"Expected directory='NRV' for redirected PRJ doc, got '{nrv_doc.get('directory')}'"
    )


# ------------------------------------------------- FXA-2330 registry trigger


def test_list_touches_project_registry(sample_project, monkeypatch):
    """list in a project context appends a registry row (FXA-2330)."""
    from fx_alfred.core.registry import load_registry

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["list"], catch_exceptions=False)
    assert result.exit_code == 0
    entries = load_registry(
        Path.home() / ".alfred" / "USR-9000-REF-Project-SOP-Registry.md"
    )
    assert [(e.prefix, e.doc_count) for e in entries] == [("ALF", 3)]


def test_list_outside_project_leaves_registry_untouched(tmp_path, monkeypatch):
    """No PRJ docs → registry must not even be created (FXA-2330)."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["list"], catch_exceptions=False)
    assert result.exit_code == 0
    assert not (
        Path.home() / ".alfred" / "USR-9000-REF-Project-SOP-Registry.md"
    ).exists()


def test_list_json_output_unpolluted_by_registry_trigger(sample_project, monkeypatch):
    """Registry trigger is silent: --json output stays a valid bare array."""
    import json as _json

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["list", "--json"], catch_exceptions=False)
    assert result.exit_code == 0
    data = _json.loads(result.output)
    assert isinstance(data, list)


def test_list_first_invocation_shows_bootstrapped_usr9000(sample_project, monkeypatch):
    """R4 P2: `af list --source usr` must show USR-9000 on the very invocation
    that creates it (re-scan after trigger write)."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["list", "--source", "usr"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "USR-9000" in result.output


def test_list_skips_registry_write_when_prj_holds_usr9000(tmp_path, monkeypatch):
    """R5 P1: a PRJ doc already using USR-9000 must block the registry write
    (duplicate-ID across layers), warn, and not break the command."""
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "USR-9000-SOP-Custom.md").write_text("# custom", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli, ["list"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "USR-9000" in result.output  # the PRJ doc still lists fine
    assert not (
        Path.home() / ".alfred" / "USR-9000-REF-Project-SOP-Registry.md"
    ).exists()
