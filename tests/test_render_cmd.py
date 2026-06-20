"""Tests for the `af render` command."""

import pytest
from click.testing import CliRunner

from fx_alfred.cli import cli

pytestmark = pytest.mark.cli


def test_render_to_stdout(tmp_path):
    md = tmp_path / "a.md"
    md.write_text("# Title\n\nHello")
    result = CliRunner().invoke(cli, ["render", str(md)])
    assert result.exit_code == 0
    assert "<!DOCTYPE html>" in result.output
    assert "<h1>Title</h1>" in result.output


def test_render_to_output_file(tmp_path):
    md = tmp_path / "a.md"
    md.write_text("# Title")
    out = tmp_path / "a.html"
    result = CliRunner().invoke(cli, ["render", str(md), "-o", str(out)])
    assert result.exit_code == 0
    assert out.exists()
    html = out.read_text()
    assert "<!DOCTYPE html>" in html
    assert "<h1>Title</h1>" in html


def test_missing_file_errors(tmp_path):
    result = CliRunner().invoke(cli, ["render", str(tmp_path / "nope.md")])
    assert result.exit_code != 0
    assert "not found" in result.output.lower()


def test_title_defaults_to_first_h1(tmp_path):
    md = tmp_path / "a.md"
    md.write_text("# My Doc\n\ntext")
    result = CliRunner().invoke(cli, ["render", str(md)])
    assert "<title>My Doc</title>" in result.output


def test_title_falls_back_to_file_stem(tmp_path):
    md = tmp_path / "notes.md"
    md.write_text("no heading here")
    result = CliRunner().invoke(cli, ["render", str(md)])
    assert "<title>notes</title>" in result.output


def test_title_option_overrides(tmp_path):
    md = tmp_path / "a.md"
    md.write_text("# Heading")
    result = CliRunner().invoke(cli, ["render", str(md), "--title", "Custom"])
    assert "<title>Custom</title>" in result.output


def test_directory_input_errors(tmp_path):
    d = tmp_path / "adir"
    d.mkdir()
    result = CliRunner().invoke(cli, ["render", str(d)])
    assert result.exit_code != 0
    assert "not a file" in result.output.lower()


def test_title_ignores_heading_inside_code_fence(tmp_path):
    md = tmp_path / "a.md"
    md.write_text("```\n# fake title\n```\n\n# Real Title")
    result = CliRunner().invoke(cli, ["render", str(md)])
    assert "<title>Real Title</title>" in result.output
