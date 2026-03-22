"""Tests for af where command."""

import json
from pathlib import Path

from click.testing import CliRunner
from fx_alfred.cli import cli


def test_where_prints_path(sample_project, monkeypatch):
    """af where ALF-2201 prints the file path."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["where", "ALF-2201"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "ALF-2201-PRP-AF-CLI-Tool.md" in result.output


def test_where_by_acid_only(sample_project, monkeypatch):
    """af where 2201 finds document by ACID only."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["where", "2201"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "ALF-2201-PRP-AF-CLI-Tool.md" in result.output


def test_where_json_output(sample_project, monkeypatch):
    """af where ALF-2201 --json outputs JSON with doc_id, path, source, filename."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["where", "ALF-2201", "--json"], catch_exceptions=False)
    assert result.exit_code == 0

    data = json.loads(result.output)
    assert isinstance(data, dict)
    assert data["schema_version"] == "1"
    assert data["doc_id"] == "ALF-2201"
    assert data["source"] == "prj"
    assert data["filename"] == "ALF-2201-PRP-AF-CLI-Tool.md"
    assert "path" in data


def test_where_json_path_is_absolute(sample_project, monkeypatch):
    """af where --json returns absolute path."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["where", "ALF-2201", "--json"], catch_exceptions=False)
    assert result.exit_code == 0

    data = json.loads(result.output)
    assert data["schema_version"] == "1"
    assert Path(data["path"]).is_absolute()


def test_where_unknown_id_fails(sample_project, monkeypatch):
    """af where COR-9999 fails with error message."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["where", "COR-9999"])
    assert result.exit_code != 0
    assert "COR-9999" in result.output


def test_where_path_is_absolute(sample_project, monkeypatch):
    """af where ALF-2201 returns absolute path that exists on disk."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["where", "ALF-2201"], catch_exceptions=False)
    assert result.exit_code == 0
    output_path = result.output.strip()
    assert Path(output_path).is_absolute()
    assert Path(output_path).exists()


def test_where_pkg_layer(tmp_path, monkeypatch):
    """af where COR-1103 finds PKG layer document with absolute path that exists."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["where", "COR-1103"], catch_exceptions=False)
    assert result.exit_code == 0
    output_path = result.output.strip()
    assert Path(output_path).is_absolute()
    assert "COR-1103" in output_path
    assert Path(output_path).exists()


def test_where_pkg_layer_json(tmp_path, monkeypatch):
    """af where COR-1103 --json returns correct JSON for PKG layer document."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["where", "COR-1103", "--json"], catch_exceptions=False)
    assert result.exit_code == 0

    data = json.loads(result.output)
    assert data["schema_version"] == "1"
    assert data["doc_id"] == "COR-1103"
    assert data["source"] == "pkg"
    assert Path(data["path"]).is_absolute()
    assert "COR-1103" in data["filename"]
    assert Path(data["path"]).exists()
