from pathlib import Path

from click.testing import CliRunner
from fx_alfred.cli import cli


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
