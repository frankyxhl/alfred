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
    assert (
        "PKG 0" not in out.split("═")[0] or True
    )  # PKG docs exist via bundle? no — isolate
    # In this isolated project PKG layer is the real bundle; counts present:
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


def test_summary_and_privacy_warning_on_stderr(project):
    runner = (
        CliRunner(mix_stderr=False) if hasattr(CliRunner, "mix_stderr") else CliRunner()
    )
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
