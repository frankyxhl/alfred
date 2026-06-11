"""Tests for af export — single-file runbook (PRP-2303).

Covers the 11 Specified Behaviors plus the shared routing helper.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from click.testing import CliRunner

from fx_alfred.cli import cli

pytestmark = pytest.mark.cli


def _write_doc(
    rules_dir: Path,
    prefix: str,
    acid: str,
    type_code: str,
    title: str,
    status: str = "Active",
    body_extra: str = "",
    role: str | None = None,
) -> Path:
    role_line = f"**Document role:** {role}\n" if role else ""
    content = f"""# {type_code}-{acid}: {title.replace("-", " ")}

**Applies to:** Test
**Status:** {status}
{role_line}
---

## What Is It?

Body of {prefix}-{acid}.
{body_extra}
---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-06-12 | Init | T |
"""
    path = rules_dir / f"{prefix}-{acid}-{type_code}-{title}.md"
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def project(tmp_path):
    rules = tmp_path / "rules"
    rules.mkdir()
    _write_doc(rules, "TST", "6001", "SOP", "Alpha-Sop")
    _write_doc(rules, "TST", "6002", "SOP", "Beta-Sop", status="Draft")
    _write_doc(rules, "TST", "6003", "REF", "Gamma-Ref")
    _write_doc(rules, "TST", "6004", "PRP", "Delta-Prp")
    _write_doc(rules, "TST", "6000", "SOP", "Workflow-Routing", role="routing")
    return tmp_path


def _run(project, *args):
    runner = CliRunner()
    return runner.invoke(
        cli, ["export", "--root", str(project), *args], catch_exceptions=False
    )


# ── Behavior 1: selection algebra ───────────────────────────────────────────


def test_default_scope_active_sop_and_ref(project):
    result = _run(project)
    assert result.exit_code == 0
    out = result.output
    assert "TST-6001" in out  # Active SOP
    assert "TST-6003" in out  # Active REF
    assert "TST-6002" not in out  # Draft excluded
    assert "TST-6004" not in out  # PRP excluded


def test_all_lifts_type_and_status_gates(project):
    out = _run(project, "--all").output
    assert "TST-6002" in out and "TST-6004" in out


def test_positional_ids_bypass_scope_and_dedupe(project):
    result = _run(project, "TST-6004", "TST-6004")
    assert result.exit_code == 0
    # PRP included despite default scope; rendered exactly once.
    assert result.output.count("═ TST-6004 · PRP") == 1


def test_positional_union_with_filtered_pool(project):
    out = _run(project, "TST-6004", "--type", "REF").output
    assert "TST-6004" in out  # positional bypasses --type
    assert "TST-6003" in out  # filtered pool
    assert "TST-6001" not in out  # SOP excluded by explicit --type


def test_status_filter_case_insensitive(project):
    out = _run(project, "--status", "draft", "--type", "SOP").output
    assert "TST-6002" in out
    assert "TST-6001" not in out


def test_unknown_status_matches_zero_exits_2(project):
    result = _run(project, "--status", "Bogus")
    assert result.exit_code == 2


# ── Behavior 2: ordering — routing first ────────────────────────────────────


def test_routing_doc_first_and_only_once(project):
    out = _run(project).output
    first = out.index("═ TST-6000 · SOP")
    assert first < out.index("═ TST-6001 · SOP")
    assert out.count("═ TST-6000 · SOP") == 1


# ── Behavior 3 + --list ─────────────────────────────────────────────────────


def test_contents_table_lines(project):
    out = _run(project).output
    assert "TST-6001  SOP  PRJ  Active  Alpha Sop" in out


def test_list_dry_run_no_document_bodies(project):
    result = _run(project, "--list")
    assert result.exit_code == 0
    assert "TST-6001  SOP  PRJ  Active  Alpha Sop" in result.output
    assert "Body of TST-6001" not in result.output


# ── Behavior 4: determinism + encoding ──────────────────────────────────────


def test_deterministic_output(project):
    assert _run(project).output == _run(project).output


def test_cjk_content_unescaped(project, tmp_path):
    rules = project / "rules"
    _write_doc(rules, "TST", "6005", "SOP", "Cjk-Sop", body_extra="跨模型评审内容。")
    out = _run(project).output
    assert "跨模型评审内容" in out


# ── Behavior 5: per-document failure policy ────────────────────────────────


def test_malformed_doc_skipped_with_warning(project):
    rules = project / "rules"
    (rules / "TST-6009-SOP-Broken-Doc.md").write_text(
        "not a valid alfred document", encoding="utf-8"
    )
    result = _run(project)
    assert result.exit_code == 0
    assert "TST-6001" in result.output  # export continues
    combined = result.output + (result.stderr or "")
    assert "skipped TST-6009" in combined
    assert "MalformedDocumentError" in combined


# ── Behavior 6: -o semantics ────────────────────────────────────────────────


def test_output_file_written_and_overwritten(project, tmp_path):
    target = tmp_path / "runbook.md"
    target.write_text("PREVIOUS-CONTENT-SENTINEL", encoding="utf-8")
    result = _run(project, "-o", str(target))
    assert result.exit_code == 0
    text = target.read_text(encoding="utf-8")
    assert "ALFRED RUNBOOK" in text
    assert "PREVIOUS-CONTENT-SENTINEL" not in text


def test_output_dash_means_stdout(project):
    out = _run(project, "-o", "-").output
    assert "ALFRED RUNBOOK" in out


def test_output_to_directory_fails(project, tmp_path):
    d = tmp_path / "adir"
    d.mkdir()
    result = _run(project, "-o", str(d))
    assert result.exit_code == 1


# ── Behavior 7: exit codes ──────────────────────────────────────────────────


def test_empty_selection_usage_error_exit_2(project):
    result = _run(project, "--prefix", "ZZZ")
    assert result.exit_code == 2


# ── Behaviors 8–11: header, delimiter, counts, stderr stream ───────────────


def test_header_counts_show_all_layers(project):
    out = _run(project).output
    first_line_block = out.split("HOW TO USE")[0]
    assert (
        "PKG" in first_line_block
        and "USR" in first_line_block
        and "PRJ" in first_line_block
    )
    assert "UTF-8" in first_line_block


def test_delimiter_full_pattern(project):
    out = _run(project).output
    assert "═ TST-6001 · SOP · PRJ · Active ═" in out


def _stderr_capable_runner() -> CliRunner:
    """CliRunner with separately-captured stderr across supported Click.

    Click 8.0/8.1 expose ``mix_stderr`` as a CliRunner.__init__ PARAMETER
    (not a class attribute — hasattr() is the wrong probe; codex PR #201
    P2 + deepseek R1 convergent finding): pass mix_stderr=False there.
    Click 8.2+ removed the parameter and always captures stderr separately.
    """
    import inspect

    if "mix_stderr" in inspect.signature(CliRunner.__init__).parameters:
        return CliRunner(mix_stderr=False)
    return CliRunner()


def test_summary_and_privacy_warning_on_stderr(project):
    runner = _stderr_capable_runner()
    result = runner.invoke(
        cli,
        ["export", "--root", str(project)],
        catch_exceptions=False,
    )
    err = result.stderr if hasattr(result, "stderr") else ""
    assert "exported" in err
    assert "review for private material" in err


# ── Shared routing helper units (new core surface) ──────────────────────────


def test_routing_helper_detection(project):
    from fx_alfred.core.parser import parse_metadata
    from fx_alfred.core.routing import document_status, is_routing_document
    from fx_alfred.core.scanner import scan_documents

    docs = scan_documents(project)
    by_id = {f"{d.prefix}-{d.acid}": d for d in docs if d.prefix == "TST"}
    routing = by_id["TST-6000"]
    parsed = parse_metadata(routing.resolve_resource().read_text(encoding="utf-8"))
    assert is_routing_document(routing, parsed) is True
    assert document_status(parsed) == "Active"
    plain = by_id["TST-6001"]
    parsed_plain = parse_metadata(plain.resolve_resource().read_text(encoding="utf-8"))
    assert is_routing_document(plain, parsed_plain) is False


# ── R1 panel additions: remaining selection-surface coverage (glm) ─────────


def test_source_filter(project):
    out = _run(project, "--source", "prj").output
    assert "TST-6001" in out
    assert "COR-1103" not in out  # PKG excluded


def test_tag_filter(project):
    rules = project / "rules"
    _write_doc(rules, "TST", "6006", "SOP", "Tagged-Sop", body_extra="")
    path = rules / "TST-6006-SOP-Tagged-Sop.md"
    text = path.read_text(encoding="utf-8").replace(
        "**Status:** Active", "**Status:** Active\n**Tags:** export-demo"
    )
    path.write_text(text, encoding="utf-8")
    out = _run(project, "--tag", "export-demo").output
    assert "TST-6006" in out
    assert "TST-6001" not in out


def test_doc_without_status_excluded_by_default(project):
    rules = project / "rules"
    content = """# SOP-6007: No Status Doc

**Applies to:** Test

---

## What Is It?

No Status field.

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-06-12 | Init | T |
"""
    (rules / "TST-6007-SOP-No-Status-Doc.md").write_text(content, encoding="utf-8")
    assert "TST-6007" not in _run(project).output  # default gate excludes
    assert "TST-6007" in _run(project, "TST-6007").output  # positional includes


def test_all_with_status_filter_and_semantics(project):
    out = _run(project, "--all", "--status", "Active").output
    assert "TST-6004" in out  # PRP: type gate lifted by --all
    assert "TST-6002" not in out  # Draft excluded by explicit --status


def test_version_fallback_unknown(monkeypatch):
    import importlib.metadata as md

    from fx_alfred.commands.export_cmd import _version

    def _raise(_name):
        raise md.PackageNotFoundError

    monkeypatch.setattr(md, "version", _raise)
    assert _version() == "unknown"


def test_positional_id_of_skipped_doc_warned_specifically(project):
    rules = project / "rules"
    (rules / "TST-6010-SOP-Corrupt-Doc.md").write_text(
        "not a valid alfred document", encoding="utf-8"
    )
    runner = _stderr_capable_runner()
    result = runner.invoke(
        cli,
        ["export", "--root", str(project), "TST-6010", "TST-6001"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    err = result.stderr if hasattr(result, "stderr") else ""
    assert "requested TST-6010 was skipped" in err
    assert "TST-6001" in result.output


def test_only_requested_doc_skipped_fails_loudly_not_no_match(tmp_path):
    """A positional ID that MATCHED but was skipped must not masquerade as
    'no documents matched' exit 2; warnings precede a clear exit-1 error
    (codex PR #201 P2 #2)."""
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "TST-6011-SOP-Only-Corrupt.md").write_text(
        "not a valid alfred document", encoding="utf-8"
    )
    runner = _stderr_capable_runner()
    result = runner.invoke(cli, ["export", "--root", str(tmp_path), "TST-6011"])
    assert result.exit_code == 1  # ClickException, not UsageError(2)
    err = result.stderr if hasattr(result, "stderr") else result.output
    assert "skipped TST-6011" in err
    assert "requested TST-6011 was skipped" in err
    assert "all matches were skipped" in err


# ── CHG-2304: repeatable --source/--type + --include ────────────────────────


def test_repeatable_source_pkg_plus_prj_excludes_usr(project, monkeypatch):
    from pathlib import Path as _P

    usr = _P.home() / ".alfred"
    usr.mkdir(exist_ok=True)
    _write_doc(usr, "WUK", "6500", "SOP", "Usr-Sop")
    out = _run(project, "--source", "pkg", "--source", "prj").output
    assert "TST-6001" in out  # PRJ
    assert "COR-1103" in out  # PKG
    assert "WUK-6500" not in out  # USR excluded


def test_repeatable_type(project):
    out = _run(
        project,
        "--type",
        "SOP",
        "--type",
        "PRP",
        "--status",
        "Active",
        "--source",
        "prj",
    ).output
    assert "TST-6001" in out and "TST-6004" in out
    assert "TST-6003" not in out  # REF excluded by explicit type set


def test_include_file_rendered_and_listed(project):
    (project / "README.md").write_text(
        "# Project Readme\n\nHello 项目。", encoding="utf-8"
    )
    runner = _stderr_capable_runner()
    result = runner.invoke(
        cli,
        ["export", "--root", str(project), "--include", "README.md"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "═ FILE: README.md ═" in result.output
    assert "Hello 项目。" in result.output
    assert "README.md  FILE  -  -  README.md" in result.output  # contents line
    err = result.stderr if hasattr(result, "stderr") else ""
    assert "+ 1 file" in err
    assert "review for private material" in err  # includes trigger the warning


def test_include_missing_file_skipped_with_warning(project):
    runner = _stderr_capable_runner()
    result = runner.invoke(
        cli,
        ["export", "--root", str(project), "--include", "nope.md"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    err = result.stderr if hasattr(result, "stderr") else ""
    assert "skipped nope.md" in err


def test_include_in_list_dry_run(project):
    (project / "README.md").write_text("# R", encoding="utf-8")
    out = _run(project, "--list", "--include", "README.md").output
    assert "README.md  FILE  -  -  README.md" in out
    assert "# R" not in out  # dry run: no content


def test_unrelated_corrupt_doc_keeps_no_match_exit_2(tmp_path):
    """A corrupt document that the filters never reached must not turn a
    true no-match into an export failure: --prefix ZZZ stays UsageError
    exit 2 (codex PR #201 P2 #3)."""
    rules = tmp_path / "rules"
    rules.mkdir()
    _write_doc(rules, "TST", "6001", "SOP", "Alpha-Sop")
    (rules / "TST-6012-SOP-Corrupt.md").write_text("garbage", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(cli, ["export", "--root", str(tmp_path), "--prefix", "ZZZ"])
    assert result.exit_code == 2  # UsageError — the skip was irrelevant


def test_filter_relevant_skip_fails_loudly(tmp_path):
    """When the only filter-matching documents were skipped, exit 1 with
    the all-matches-skipped error (filename-derivable relevance)."""
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "ZZX-6013-SOP-Corrupt.md").write_text("garbage", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(cli, ["export", "--root", str(tmp_path), "--prefix", "ZZX"])
    assert result.exit_code == 1
    assert "all matches were skipped" in result.output
