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


def test_pkg_style_cor_only_rules_dir_is_not_a_root(tmp_path):
    """A rules/ dir containing only COR-* docs is the bundled PKG layer
    shape, not a PRJ root (scanner layer invariant: COR only in PKG).
    Discovery must keep walking — e.g. running from src/fx_alfred/core
    inside the alfred repo must resolve the repo root, not src/fx_alfred."""
    project = _make_project(tmp_path / "proj")
    pkg_like = project / "src" / "pkg"
    (pkg_like / "rules").mkdir(parents=True)
    (pkg_like / "rules" / "COR-1000-SOP-Create-SOP.md").write_text("# bundled")
    start = pkg_like / "core"
    start.mkdir()
    assert discover_root(start) == project


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
    # TST-7002 exists only under `elsewhere` — its presence proves --root
    # overrode cwd-based discovery (which would have found `inside`).
    assert "TST-7002" in result.output


# ── R1 panel additions (CHG-2300) ───────────────────────────────────────────


def test_oserror_during_iteration_skips_candidate(tmp_path, monkeypatch):
    """Entry-level OSErrors during the lazy iterdir() iteration skip the
    candidate instead of crashing (3/3 convergent R1 finding; glm located
    the lazy-iteration-outside-try defect)."""
    from pathlib import Path as _P

    project = _make_project(tmp_path / "proj")
    broken = project / "broken"
    (broken / "rules").mkdir(parents=True)
    (broken / "rules" / "TST-7009-SOP-Unreadable.md").write_text("x")

    real_iterdir = _P.iterdir

    def _exploding_iterdir(self):
        if self == broken / "rules":
            raise OSError("stale NFS handle")
        return real_iterdir(self)

    monkeypatch.setattr(_P, "iterdir", _exploding_iterdir)
    start = broken / "sub"
    start.mkdir()
    # broken/rules raises mid-scan → skipped; walk continues to project.
    assert discover_root(start) == project


def test_rules_as_file_is_not_a_root(tmp_path):
    """A file literally named 'rules' is skipped by the is_dir() guard
    (deepseek + minimax convergent R1 advisory)."""
    project = _make_project(tmp_path / "proj")
    weird = project / "weird"
    weird.mkdir()
    (weird / "rules").write_text("a file, not a directory")
    start = weird / "inner"
    start.mkdir()
    assert discover_root(start) == project


def test_usr_alfred_home_is_never_a_prj_root(tmp_path):
    """~/.alfred is the USR layer home — discovering it as a PRJ root would
    alias the same files into both layers (duplicate-ID LayerValidationError).
    Excluded explicitly (glm R1 finding). conftest's isolate_home points
    Path.home() at a fresh tmp dir, so this builds the scenario there."""
    from pathlib import Path as _P

    fake_alfred = _P.home() / ".alfred"
    (fake_alfred / "rules").mkdir(parents=True)
    (fake_alfred / "rules" / "TST-7010-SOP-Usr-Doc.md").write_text("# usr doc")
    start = fake_alfred / "notes"
    start.mkdir()
    # Pre-exclusion this would discover ~/.alfred; now it must fall back.
    assert discover_root(start) == start
