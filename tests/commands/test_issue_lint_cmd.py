"""Tests for af issue lint subcommand (FXA-2292 / issue #169)."""

import json

import pytest

from click.testing import CliRunner
from fx_alfred.cli import cli

# Import-time assertion: this proves the production module is genuinely absent.
# When the implementer adds src/fx_alfred/commands/issue_cmd.py with `issue_cmd`,
# this import succeeds and all 27 tests transition from RED → GREEN. Until then,
# pytest collection fails with ModuleNotFoundError, which is the correct TDD RED state.
from fx_alfred.commands.issue_cmd import issue_cmd  # noqa: F401


pytestmark = pytest.mark.cli

TBD_PHRASES = [
    "TBD after PR review",
    "TBD after option selection",
    "implementer chooses",
    "exact spec to be drafted after reviewer pick",
    "to be decided in review",
]


# ---------------------------------------------------------------------------
# AC1 / AC22: help text
# ---------------------------------------------------------------------------


def test_lint_help_shows_body_file_and_json_flag():
    """AC1: af issue lint --help shows BODY_FILE positional and --json flag."""
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "lint", "--help"])
    assert result.exit_code == 0
    assert "issue lint" in result.output or "lint" in result.output
    assert "BODY_FILE" in result.output
    assert "--json" in result.output


def test_lint_issue_help_shows_lint_subcommand():
    """AC22: af issue --help shows lint as a subcommand of the issue group."""
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "--help"])
    assert result.exit_code == 0
    assert "lint" in result.output


# ---------------------------------------------------------------------------
# AC2: clean body → PASS
# ---------------------------------------------------------------------------


def test_lint_clean_body_pass(tmp_path):
    """AC2: clean body with no TBD phrases → exit 0, PASS message."""
    body = tmp_path / "body.md"
    body.write_text("This is a clean spec.\nAll decisions are made.\n")
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "lint", str(body)])
    assert result.exit_code == 0
    assert "PASS (0 violations)" in result.output


# ---------------------------------------------------------------------------
# AC3: violations — each phrase, multi-violation, multi-phrase
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("phrase", TBD_PHRASES)
def test_lint_each_phrase_fails(tmp_path, phrase):
    """AC3: each canonical TBD phrase produces a failure."""
    body = tmp_path / "body.md"
    body.write_text(f"Some text.\n{phrase}\nMore text.\n")
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "lint", str(body)])
    assert result.exit_code == 1
    assert "FAIL (1 violations)" in result.output


def test_lint_multi_violation_same_phrase(tmp_path):
    """AC3: same phrase on 3 lines → 3 violations sorted by line."""
    body = tmp_path / "body.md"
    body.write_text(
        "intro\n"
        "TBD after PR review: decision 1\n"
        "ok line\n"
        "TBD after PR review: decision 2\n"
        "TBD after PR review: decision 3\n"
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "lint", str(body)])
    assert result.exit_code == 1
    assert "FAIL (3 violations)" in result.output

    lines = [ln for ln in result.output.split("\n") if ln.startswith("✗")]
    assert len(lines) == 3
    assert "line 2" in lines[0]
    assert "line 4" in lines[1]
    assert "line 5" in lines[2]


def test_lint_multi_phrase_mixed_sorted(tmp_path):
    """AC3: 2 different phrases on different lines → sorted by line number."""
    body = tmp_path / "body.md"
    body.write_text(
        "header\n"
        "to be decided in review: something\n"
        "middle\n"
        "implementer chooses: something else\n"
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "lint", str(body)])
    assert result.exit_code == 1
    assert "FAIL (2 violations)" in result.output

    lines = [ln for ln in result.output.split("\n") if ln.startswith("✗")]
    assert len(lines) == 2
    # sorted by line: line 2 then line 4
    assert "line 2" in lines[0]
    assert "to be decided in review" in lines[0]
    assert "line 4" in lines[1]
    assert "implementer chooses" in lines[1]


# ---------------------------------------------------------------------------
# AC3: case-insensitive match
# ---------------------------------------------------------------------------


def test_lint_case_insensitive_detection(tmp_path):
    """AC3: each phrase detected in UPPERCASE, lowercase, and MiXeD case."""
    body = tmp_path / "body.md"
    body.write_text(
        "TBD AFTER PR REVIEW\n"
        "tbd after option selection\n"
        "ImPlEmEnTeR cHoOsEs\n"
        "ExAcT sPeC tO bE dRaFtEd AfTeR rEvIeWeR pIcK\n"
        "To Be DeCiDeD iN rEvIeW\n"
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "lint", str(body)])
    assert result.exit_code == 1
    assert "FAIL (5 violations)" in result.output

    # Each line should report the canonical phrase, not the input text
    violations = [ln for ln in result.output.split("\n") if ln.startswith("✗")]
    assert len(violations) == 5
    canonical_matches = []
    for v in violations:
        # Extract match text (between last pair of quotes)
        canonical_matches.append(v.split('"')[-2])
    assert canonical_matches[0] == "TBD after PR review"
    assert canonical_matches[1] == "TBD after option selection"
    assert canonical_matches[2] == "implementer chooses"
    assert canonical_matches[3] == "exact spec to be drafted after reviewer pick"
    assert canonical_matches[4] == "to be decided in review"


# ---------------------------------------------------------------------------
# AC3: embedded / fenced code
# ---------------------------------------------------------------------------


def test_lint_phrase_embedded_in_sentence(tmp_path):
    """AC3: phrase as substring in a longer sentence is matched."""
    body = tmp_path / "body.md"
    body.write_text(
        "We need to handle the case where implementer chooses the library.\n"
        "The decision is TBD after PR review with the team.\n"
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "lint", str(body)])
    assert result.exit_code == 1
    assert "FAIL (2 violations)" in result.output


def test_lint_phrase_in_fenced_code_block(tmp_path):
    """AC3: phrase inside a fenced code block is matched (Phase 1 — deliberate)."""
    body = tmp_path / "body.md"
    body.write_text(
        "```python\n# TBD after option selection: choose parser\nx = 1\n```\n"
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "lint", str(body)])
    assert result.exit_code == 1
    assert "FAIL (1 violations)" in result.output


# ---------------------------------------------------------------------------
# AC4: stdin via -
# ---------------------------------------------------------------------------


def test_lint_stdin_dash_clean():
    """AC4: af issue lint - reads clean stdin → PASS."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["issue", "lint", "-"],
        input="All decisions final.\nNo TBDs here.\n",
    )
    assert result.exit_code == 0
    assert "PASS (0 violations)" in result.output


def test_lint_stdin_dash_dirty():
    """AC4: af issue lint - reads stdin with TBD phrase → FAIL."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["issue", "lint", "-"],
        input="implementer chooses: still open\n",
    )
    assert result.exit_code == 1
    assert "FAIL (1 violations)" in result.output


# ---------------------------------------------------------------------------
# AC5: --json output
# ---------------------------------------------------------------------------


def test_lint_json_clean(tmp_path):
    """AC5: --json on clean body → {result: PASS, violation_count: 0, violations: []}."""
    body = tmp_path / "body.md"
    body.write_text("Clean spec.\n")
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "lint", str(body), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["result"] == "PASS"
    assert data["violation_count"] == 0
    assert data["violations"] == []


def test_lint_json_with_violations(tmp_path):
    """AC5: --json with violations → proper JSON shape, violations sorted by line."""
    body = tmp_path / "body.md"
    body.write_text(
        "line 1\nTBD after PR review: pending\nline 3\nimplementer chooses: toolkit\n"
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "lint", str(body), "--json"])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["result"] == "FAIL"
    assert data["violation_count"] == 2
    violations = data["violations"]
    assert len(violations) == 2

    # Each violation has all 4 fields
    for v in violations:
        assert v["rule"] == "tbd-phrase"
        assert isinstance(v["line"], int)
        assert v["match"] in TBD_PHRASES

    # Sorted by line number
    assert violations[0]["line"] < violations[1]["line"]
    assert violations[0]["line"] == 2
    assert violations[1]["line"] == 4


def test_lint_json_parseable(tmp_path):
    """AC5: JSON output is valid and parseable by json.loads (no stray text)."""
    body = tmp_path / "body.md"
    body.write_text("implementer chooses: x\n")
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "lint", str(body), "--json"])
    # json.loads must not raise
    data = json.loads(result.output)
    assert data["violation_count"] == 1


def test_lint_json_no_stray_text(tmp_path):
    """AC5: --json output contains NO ✗ lines — only the JSON blob."""
    body = tmp_path / "body.md"
    body.write_text("TBD after PR review: needs review\n")
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "lint", str(body), "--json"])
    assert "✗" not in result.output


# ---------------------------------------------------------------------------
# AC6: phrase-order / multiple-phrase semantics
# ---------------------------------------------------------------------------


def test_lint_two_phrases_same_line(tmp_path):
    """AC6: one line with 2 canonical phrases → 2 violations at same line number."""
    body = tmp_path / "body.md"
    body.write_text("header\nTBD after PR review and implementer chooses both apply\n")
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "lint", str(body)])
    assert result.exit_code == 1
    assert "FAIL (2 violations)" in result.output

    violations = [ln for ln in result.output.split("\n") if ln.startswith("✗")]
    assert len(violations) == 2
    # Both at the same line number (line 2, 1-based)
    assert "line 2" in violations[0]
    assert "line 2" in violations[1]
    assert "TBD after PR review" in violations[0]
    assert "implementer chooses" in violations[1]


def test_lint_substring_no_word_boundary(tmp_path):
    """AC6: phrase embedded without spaces as substring of a longer word → matched."""
    body = tmp_path / "body.md"
    body.write_text("FooTBD after PR reviewBar\n")
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "lint", str(body)])
    assert result.exit_code == 1
    assert "FAIL (1 violations)" in result.output


def test_lint_duplicate_phrase_same_line_counted_once(tmp_path):
    """Duplicate phrase on same line: substring check is boolean → 1 per phrase per line."""
    body = tmp_path / "body.md"
    body.write_text("implementer chooses: A or implementer chooses: B, take pick\n")
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "lint", str(body)])
    # "implementer chooses" appears twice on same line → counted once
    assert "FAIL (1 violations)" in result.output


# ---------------------------------------------------------------------------
# Edge cases: file I/O
# ---------------------------------------------------------------------------


def test_lint_file_not_found():
    """Non-existent file → non-zero exit code."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["issue", "lint", "/nonexistent/path/to/file.md"],
    )
    assert result.exit_code != 0


def test_lint_empty_file_pass(tmp_path):
    """Empty file → 0 violations, PASS exit 0."""
    body = tmp_path / "body.md"
    body.write_text("")
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "lint", str(body)])
    assert result.exit_code == 0
    assert "PASS (0 violations)" in result.output


def test_lint_whitespace_only_pass(tmp_path):
    """File with only newlines and whitespace → 0 violations, PASS exit 0."""
    body = tmp_path / "body.md"
    body.write_text("   \n\n  \t \n")
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "lint", str(body)])
    assert result.exit_code == 0
    assert "PASS (0 violations)" in result.output


def test_lint_utf8_with_emoji_and_chinese(tmp_path):
    """UTF-8 BOM and non-ASCII chars: phrase still detected with emoji/Chinese."""
    body = tmp_path / "body.md"
    body.write_text(
        "﻿# Spec\n"
        "决策: implementer chooses the approach 🎉\n"
        "备注: TBD after PR review with 团队\n"
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "lint", str(body)])
    assert result.exit_code == 1
    assert "FAIL (2 violations)" in result.output


# ---------------------------------------------------------------------------
# Output structure / blank-line handling
# ---------------------------------------------------------------------------


def test_lint_output_blank_line_before_result(tmp_path):
    """A blank line separates the violations list from the Lint result line."""
    body = tmp_path / "body.md"
    body.write_text("TBD after PR review\n")
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "lint", str(body)])
    # After the violations line, there should be a blank line before "Lint result:"
    output = result.output
    # Strip trailing whitespace but keep internal structure
    assert "\n\nLint result:" in output


def test_lint_output_structure_clean_pass(tmp_path):
    """Exact output structure for clean PASS case."""
    body = tmp_path / "body.md"
    body.write_text("All decided.\n")
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "lint", str(body)])
    # Clean case: blank line then "Lint result: PASS (0 violations)"
    # click.echo() adds \n, so: echo("") → "\n", echo("Lint result: ...") → "Lint result: ...\n"
    # Combined: "\nLint result: PASS (0 violations)\n"
    assert "✗" not in result.output
    assert "PASS (0 violations)" in result.output


def test_lint_output_structure_exact_fail(tmp_path):
    """Exact output structure for a single-violation FAIL case."""
    body = tmp_path / "body.md"
    body.write_text("line 1\nto be decided in review: item\nline 3\n")
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "lint", str(body)])
    output = result.output
    # Should contain: ✗ line → blank line → Lint result: FAIL line
    assert "✗ TBD-phrase detected at line 2:" in output
    assert '"to be decided in review"' in output
    assert "\n\nLint result:" in output
    assert "FAIL (1 violations)" in output
    assert result.exit_code == 1
