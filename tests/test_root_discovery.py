"""Tests for project-root auto-discovery (CHG-2300).

When --root is absent, get_root() walks up from cwd to the nearest
ancestor whose rules/ contains at least one Alfred-pattern document;
no qualifying ancestor → cwd fallback (the pre-CHG-2300 behavior).
"""

from __future__ import annotations

import pytest

from click.testing import CliRunner

from fx_alfred.cli import cli
from fx_alfred.context import discover_root

pytestmark = pytest.mark.cli


def _make_project(root):
    rules = root / "rules"
    rules.mkdir(parents=True)
    (rules / "TST-7001-SOP-Marker-Doc.md").write_text(
        """# SOP-7001: Marker Doc

**Applies to:** Test
**Status:** Active
---
## What Is It?
Marker.
## Steps
1. Only step
""",
        encoding="utf-8",
    )
    return root


# ── discover_root unit cases (A1) ──────────────────────────────────────────


def test_cwd_is_root(tmp_path):
    project = _make_project(tmp_path / "proj")
    assert discover_root(project) == project


def test_subdir_resolves_to_project_root(tmp_path):
    project = _make_project(tmp_path / "proj")
    deep = project / "src" / "pkg"
    deep.mkdir(parents=True)
    assert discover_root(deep) == project


def test_nested_roots_nearest_wins(tmp_path):
    outer = _make_project(tmp_path / "outer")
    inner = _make_project(outer / "sub" / "inner")
    start = inner / "deeper"
    start.mkdir()
    assert discover_root(start) == inner


def test_no_marker_falls_back_to_start(tmp_path):
    plain = tmp_path / "plain" / "dir"
    plain.mkdir(parents=True)
    assert discover_root(plain) == plain


def test_rules_without_pattern_docs_is_not_a_root(tmp_path):
    project = _make_project(tmp_path / "proj")
    decoy = project / "vendor"
    (decoy / "rules").mkdir(parents=True)
    (decoy / "rules" / "README.md").write_text("not an alfred doc")
    (decoy / "rules" / "notes.txt").write_text("nope")
    # decoy/rules has files but none match FILENAME_PATTERN → keep walking.
    assert discover_root(decoy) == project


# ── CLI behavior (A2) ───────────────────────────────────────────────────────


def test_af_list_from_subdirectory_sees_prj_docs(tmp_path, monkeypatch):
    project = _make_project(tmp_path / "proj")
    subdir = project / "src"
    subdir.mkdir()
    monkeypatch.chdir(subdir)

    runner = CliRunner()
    result = runner.invoke(cli, ["list"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "TST-7001" in result.output


def test_explicit_root_wins_over_discovery(tmp_path, monkeypatch):
    inside = _make_project(tmp_path / "inside")
    elsewhere = _make_project(tmp_path / "elsewhere")
    # cwd discovery would find `inside`; --root must override to `elsewhere`.
    monkeypatch.chdir(inside)
    (elsewhere / "rules" / "TST-7002-SOP-Other-Doc.md").write_text(
        (inside / "rules" / "TST-7001-SOP-Marker-Doc.md")
        .read_text(encoding="utf-8")
        .replace("7001", "7002")
        .replace("Marker Doc", "Other Doc"),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli, ["list", "--root", str(elsewhere)], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "TST-7002" in result.output
    assert "TST-7001" not in result.output
