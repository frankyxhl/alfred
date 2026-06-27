"""Tests for project-root auto-discovery (CHG-2300).

When --root is absent, get_root() walks up from cwd to the nearest
ancestor whose rules/ contains at least one Alfred-pattern document;
no qualifying ancestor → cwd fallback (the pre-CHG-2300 behavior).
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

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


# ── FXA-2314: mapping-aware root discovery ────────────────────────────────────


def _write_projects_json(alfred_dir: Path, mapping: dict) -> None:
    (alfred_dir / "projects.json").write_text(
        json.dumps({"projects": mapping}), encoding="utf-8"
    )


def test_discover_root_mapped_ancestor_recognized(tmp_path):
    """discover_root returns the mapped ancestor when cwd is inside a mapped repo.

    Without the feature: discover_root falls back to `start` (no rules/ found).
    With the feature:    it recognises ext_repo as a mapping key and returns it.
    """
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True)
    ext_repo = tmp_path / "ext_repo"
    subdir = ext_repo / "src" / "pkg"
    subdir.mkdir(parents=True)

    _write_projects_json(alfred, {str(ext_repo.resolve()): "NRV"})

    result = discover_root(subdir)
    assert result == ext_repo, (
        f"Expected discover_root to return mapped ext_repo, got {result}"
    )


def test_discover_root_nearest_mapped_ancestor_wins(tmp_path):
    """When several mapped ancestors exist, the DEEPEST (nearest) one wins."""
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True)

    outer = tmp_path / "outer"
    inner = outer / "sub" / "inner"
    deep = inner / "src"
    deep.mkdir(parents=True)

    _write_projects_json(
        alfred,
        {
            str(outer.resolve()): "OUT",
            str(inner.resolve()): "INN",
        },
    )

    result = discover_root(deep)
    assert result == inner, (
        f"Deepest mapped ancestor must win; expected {inner}, got {result}"
    )


def test_discover_root_mapped_beats_distant_rules_ancestor(tmp_path):
    """Deepest match wins whether it's a rules/ ancestor or a mapped ancestor.

    Setup: outer has rules/ (discovered by old logic); inner is a mapping key
    (no rules/).  Starting from inner/src, the nearest qualifying ancestor is
    inner (mapped) — it must beat the more distant outer (rules/).
    """
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True)

    outer = _make_project(tmp_path / "outer")
    inner = outer / "sub" / "inner"
    start = inner / "src"
    start.mkdir(parents=True)

    _write_projects_json(alfred, {str(inner.resolve()): "INN"})

    result = discover_root(start)
    assert result == inner, (
        f"Nearest (mapped) inner must beat the more distant outer (rules/); got {result}"
    )


def test_discover_root_explicit_root_overrides_mapping(tmp_path, monkeypatch):
    """Explicit --root always wins over mapping-based discovery.

    This is a regression guard (--root already worked before FXA-2314) and
    ensures the new mapping branch doesn't accidentally break --root priority.
    """
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True)

    ext_repo = tmp_path / "ext_repo"
    ext_repo.mkdir()
    _write_projects_json(alfred, {str(ext_repo.resolve()): "NRV"})

    # elsewhere has its own rules/; --root points here
    elsewhere = _make_project(tmp_path / "elsewhere")

    # cwd is inside ext_repo (mapping would normally resolve here)
    monkeypatch.chdir(ext_repo)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["list", "--root", str(elsewhere)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    # TST-7001 only exists under elsewhere (created by _make_project)
    assert "TST-7001" in result.output, (
        "--root must override mapping-based discovery; TST-7001 from elsewhere must appear"
    )


def test_discover_root_many_to_one_each_key_resolves(tmp_path):
    """Many-to-one mapping: each registered key independently discovers its own root."""
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True)

    repo_a = tmp_path / "repo_a"
    repo_b = tmp_path / "repo_b"
    src_a = repo_a / "src"
    src_b = repo_b / "src"
    src_a.mkdir(parents=True)
    src_b.mkdir(parents=True)

    _write_projects_json(
        alfred,
        {
            str(repo_a.resolve()): "NRV",
            str(repo_b.resolve()): "NRV",  # many-to-one: both map to "NRV"
        },
    )

    assert discover_root(src_a) == repo_a, (
        f"src_a must resolve to repo_a; got {discover_root(src_a)}"
    )
    assert discover_root(src_b) == repo_b, (
        f"src_b must resolve to repo_b; got {discover_root(src_b)}"
    )
