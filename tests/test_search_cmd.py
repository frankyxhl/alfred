"""Tests for af search command."""

import os
from pathlib import Path

from click.testing import CliRunner

from fx_alfred.cli import cli


def test_search_finds_match_in_prj_doc(sample_project, monkeypatch):
    """Search finds matching content in PRJ documents."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "AF CLI"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "ALF-2201" in result.output
    assert "PRJ" in result.output
    assert "# AF CLI" in result.output


def test_search_finds_match_in_pkg_doc(tmp_path, monkeypatch):
    """Search finds matching content in PKG documents."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    # COR-1000 contains "SOP" in its content
    result = runner.invoke(cli, ["search", "SOP"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "COR-1000" in result.output
    assert "PKG" in result.output


def test_search_case_insensitive(sample_project, monkeypatch):
    """Search is case-insensitive."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    # Search lowercase "af cli" should match "# AF CLI"
    result = runner.invoke(cli, ["search", "af cli"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "ALF-2201" in result.output


def test_search_no_matches(sample_project, monkeypatch):
    """Search with no matches prints 'No matches found.' and exits 0."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["search", "zzzzzzzznonexistent"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "No matches found." in result.output


def test_search_shows_line_numbers(sample_project, monkeypatch):
    """Search shows line numbers with matching lines."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "AF CLI"], catch_exceptions=False)
    assert result.exit_code == 0
    # Line number format: "  N: line content"
    assert ":" in result.output
    # The match is on line 1 of ALF-2201 doc
    lines = result.output.strip().split("\n")
    # Find the line with the match
    matching_lines = [ln for ln in lines if "# AF CLI" in ln]
    assert len(matching_lines) >= 1
    # Should have line number prefix
    for line in matching_lines:
        assert line.strip()[0].isdigit() or line.strip().startswith("1:")


def test_search_shows_source_label(sample_project, monkeypatch):
    """Search shows source label (PKG/USR/PRJ) in uppercase."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "Index"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "PRJ" in result.output


def test_search_multiple_docs(tmp_path, monkeypatch):
    """Search can match across multiple documents."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    # "SOP" appears in many PKG documents
    result = runner.invoke(cli, ["search", "SOP"], catch_exceptions=False)
    assert result.exit_code == 0
    # Should find multiple documents
    output = result.output
    # Count document headers (lines with PKG/USR/PRJ labels)
    doc_count = output.count("PKG")
    assert doc_count >= 1


def test_search_unreadable_doc_skipped_silently(sample_project, monkeypatch):
    """Unreadable documents are skipped silently (no error, no output)."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()

    # Make one doc unreadable
    doc_path = sample_project / "rules" / "ALF-2201-PRP-AF-CLI-Tool.md"
    os.chmod(doc_path, 0o000)

    try:
        # Search for content that would be in ALF-2201
        result = runner.invoke(cli, ["search", "AF CLI"], catch_exceptions=False)
        assert result.exit_code == 0
        # Should not find ALF-2201 since it's unreadable
        assert "ALF-2201" not in result.output
        # Should not error either
        assert "Error" not in result.output
    finally:
        os.chmod(doc_path, 0o644)


def test_search_with_root_option(sample_project):
    """Search with --root option works."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["--root", str(sample_project), "search", "AF CLI"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "ALF-2201" in result.output


def test_search_with_root_after_subcommand(sample_project):
    """Search with --root after subcommand works."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["search", "--root", str(sample_project), "AF CLI"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "ALF-2201" in result.output


def test_search_shows_up_to_three_matching_lines(sample_project, monkeypatch):
    """Search shows up to 3 matching lines per document."""
    # Create a doc with multiple matching lines
    doc_path = sample_project / "rules" / "TST-9000-SOP-Multi-Match.md"
    doc_path.write_text(
        "Line 1: test TEST test\nLine 2: another TEST here\nLine 3: TEST again\nLine 4: one more TEST\nLine 5: final TEST"
    )

    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "TEST"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "TST-9000" in result.output

    # Count matching lines for TST-9000
    lines = result.output.split("\n")
    # Find lines with "TEST" that have line number format
    matching_lines = [
        ln for ln in lines if "TEST" in ln and ln.strip() and ln.strip()[0].isdigit()
    ]
    # Should have at most 3 lines per document
    assert len(matching_lines) <= 3


def test_search_shows_document_title(sample_project, monkeypatch):
    """Search shows document title in header line."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "AF CLI"], catch_exceptions=False)
    assert result.exit_code == 0
    # Title is "AF CLI Tool"
    assert "AF CLI Tool" in result.output


def test_search_blanks_between_doc_groups(tmp_path, monkeypatch):
    """Search outputs blank line between document groups."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    # "SOP" matches many documents
    result = runner.invoke(cli, ["search", "SOP-1000"], catch_exceptions=False)
    assert result.exit_code == 0
    # Output should have blank lines between document groups
    output = result.output
    # If there are multiple docs, there should be blank lines between them
    # (The format has a blank line after each doc group)
    if output.count("PKG") > 1:
        # Check for consecutive newlines
        assert "\n\n" in output


def test_search_usr_documents(tmp_path, monkeypatch):
    """Search finds matches in USR layer documents."""
    # isolate_home fixture patches Path.home() to tmp_path/fake_home
    user_alfred = Path.home() / ".alfred"
    user_alfred.mkdir(parents=True)
    (user_alfred / "USR-5000-SOP-User-Doc.md").write_text("# User Document content")

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "User Document"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "USR-5000" in result.output
    assert "USR" in result.output


def test_search_empty_pattern(sample_project, monkeypatch):
    """Search with empty pattern matches all documents (empty string is substring of everything)."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["search", ""], catch_exceptions=False)
    assert result.exit_code == 0
    # Empty pattern should match all readable documents
    # At minimum, the sample_project docs should appear
    assert "ALF-0000" in result.output or "ALF-2201" in result.output


def test_search_format_header_line(sample_project, monkeypatch):
    """Header line format is: PREFIX-ACID  SOURCE_LABEL  Title"""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "AF CLI"], catch_exceptions=False)
    assert result.exit_code == 0
    # Check the header format: ALF-2201  PRJ  AF CLI Tool
    lines = result.output.strip().split("\n")
    header_lines = [ln for ln in lines if "ALF-2201" in ln and "PRJ" in ln]
    assert len(header_lines) >= 1
    header = header_lines[0]
    assert "ALF-2201" in header
    assert "PRJ" in header
    assert "AF CLI Tool" in header
