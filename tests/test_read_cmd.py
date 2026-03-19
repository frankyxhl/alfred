from click.testing import CliRunner
from fx_alfred.cli import cli


def test_read_by_prefix_acid(tmp_path, monkeypatch):
    """Read by PREFIX-ACID format."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["read", "COR-1000"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "SOP" in result.output


def test_read_by_acid_only(tmp_path, monkeypatch):
    """Read by ACID only (backward compat)."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["read", "1000"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "SOP" in result.output


def test_read_by_prefix_acid_from_prj(sample_project, monkeypatch):
    """Read PRJ doc by PREFIX-ACID."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["read", "ALF-2201"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "# AF CLI" in result.output


def test_read_not_found(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["read", "COR-9999"], catch_exceptions=False)
    assert result.exit_code != 0
    assert "COR-9999" in result.output


def test_read_not_found_acid_only(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["read", "9999"], catch_exceptions=False)
    assert result.exit_code != 0
    assert "9999" in result.output


def test_read_ambiguous_acid(sample_project, monkeypatch):
    """When multiple docs share same ACID, error with options."""
    # sample_project has PKG COR-0000 + PRJ ALF-0000
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["read", "0000"])
    assert result.exit_code != 0
    assert "Ambiguous" in result.output
    assert "COR-0000" in result.output
    assert "ALF-0000" in result.output


def test_read_with_root_option(sample_project):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--root", str(sample_project), "read", "ALF-2201"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "# AF CLI" in result.output


def test_read_with_root_after_subcommand(sample_project):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["read", "--root", str(sample_project), "ALF-2201"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "# AF CLI" in result.output


def test_read_failure_shows_friendly_error(sample_project, monkeypatch):
    """Read failure shows friendly CLI error, not raw traceback."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    # ALF-2201 exists in sample_project, temporarily break it
    import os

    doc_path = sample_project / "rules" / "ALF-2201-PRP-AF-CLI-Tool.md"
    os.chmod(doc_path, 0o000)
    try:
        result = runner.invoke(cli, ["read", "ALF-2201"])
        assert result.exit_code != 0
        assert "Failed to read" in result.output
    finally:
        os.chmod(doc_path, 0o644)


def test_read_json(sample_project, monkeypatch):
    """--json outputs JSON object with document metadata and content."""
    import json

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["read", "ALF-2201", "--json"], catch_exceptions=False)
    assert result.exit_code == 0

    data = json.loads(result.output)
    assert isinstance(data, dict)

    # Check required fields
    assert data["prefix"] == "ALF"
    assert data["acid"] == "2201"
    assert data["type_code"] == "PRP"
    assert data["title"] == "AF CLI Tool"
    assert data["source"] == "prj"
    assert "content" in data
    assert "# AF CLI" in data["content"]
