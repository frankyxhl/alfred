# FXA-2300 Review Pack — Root Auto-Discovery

## Review request

Review this feature diff with the COR-1610 rubric pinned below. Unit = branch diff vs main. Cross-reference src/fx_alfred/context.py, core/document.py (FILENAME_PATTERN), core/scanner.py (layer invariants) at HEAD.

## What & why

get_root()'s silent cwd fallback meant af run from any project SUBDIRECTORY saw zero PRJ documents with no diagnostic — root cause of every documented command carrying `--root /Users/frank/Projects/alfred` long-form (2026-06-10 review: highest-leverage ergonomic papercut).

Change: new pure `discover_root(start)` in context.py — walks start + ancestors; first dir whose `rules/` contains ≥1 FILENAME_PATTERN-matching **non-COR** document wins; no match → `start` (byte-identical pre-change fallback). `get_root` no-flag path → `discover_root(Path.cwd())`. Explicit `--root` unchanged (wins). Help text + CLI epilog updated.

THE LOAD-BEARING REFINEMENT (real-world-found): the bundled PKG rules/ inside `src/fx_alfred/` is COR-only (scanner layer invariant: COR may only exist in PKG). Without the non-COR filter, running af from inside `src/fx_alfred/` discovered that directory as root → PRJ layer = the COR bundle → LayerValidationError crash. With the filter, discovery walks past it to the true repo root — verified live: `af status` from `src/fx_alfred/core` now resolves the full 290-doc corpus (was: zero PRJ docs pre-change; crash with naive discovery).

Compatibility matrix (verified — ALL existing tests pass unmodified):
- cwd == project root → discovered == cwd (identical)
- outside any project → fallback cwd (identical)
- project subdir → project root (the fix)
- nested roots → nearest qualifying ancestor wins
- decoy rules/ without pattern docs, or with COR-only docs → not a root, walk continues

8 new tests (5 discover_root unit + 1 PKG-shape + 2 CLI incl. explicit-root-wins). 992 total pass.

NOT in scope (no deductions per COR-1610 rule 4): marker-file/config-based root pinning; .git-based discovery; changing layer ordering; removing --root from docs.

## Pinned rubric — COR-1610

| Dimension | Weight |
|-----------|--------|
| Correctness | 25% |
| Test Coverage | 25% |
| Code Style | 15% |
| Security | 15% |
| Simplicity | 20% |

Rules: deductions cite file:line; BLOCKING vs ADVISORY; no out-of-scope deductions; verify tests before scoring; weighted average rounded to one decimal; >= 9.0 PASS. Recompute arithmetic before printing. Required output: Decision Matrix + weighted average + verdict + findings.

Special attention: (a) hunt for surprising-root scenarios the non-COR+pattern filter still admits (e.g. running af inside ~/.alfred if it had a rules/ subdir; tmp dirs; monorepos with multiple alfred projects) — is nearest-wins always the least-surprising choice? (b) performance: discover_root runs per invocation and iterdirs each ancestor's rules/ — any pathological case (deep paths, huge rules/ dirs, network mounts)? (c) is context.py the right home vs core/ (it imports FILENAME_PATTERN from core but lives with the Click glue)?

## The diff (vs main)

diff --git a/src/fx_alfred/cli.py b/src/fx_alfred/cli.py
index d26c33e..4fb88b0 100644
--- a/src/fx_alfred/cli.py
+++ b/src/fx_alfred/cli.py
@@ -16,7 +16,9 @@ Layer System:
 
   PKG: Bundled COR documents (read-only, included with fx-alfred)
   USR: Your personal documents in ~/.alfred/
-  PRJ: Project documents in ./rules/
+  PRJ: Project documents in rules/ — the project root is auto-discovered
+       from the nearest ancestor directory whose rules/ contains Alfred
+       documents (override with --root)
 
 Quick Start:
 
diff --git a/src/fx_alfred/context.py b/src/fx_alfred/context.py
index f92c001..d1d676f 100644
--- a/src/fx_alfred/context.py
+++ b/src/fx_alfred/context.py
@@ -2,6 +2,39 @@ from pathlib import Path
 
 import click
 
+from fx_alfred.core.document import FILENAME_PATTERN
+
+
+def discover_root(start: Path) -> Path:
+    """Return the nearest ancestor of ``start`` (inclusive) that is an
+    Alfred project root, else ``start`` itself.
+
+    A directory qualifies when its ``rules/`` subdirectory contains at
+    least one non-COR document matching ``FILENAME_PATTERN`` — bare
+    ``rules/`` folders from unrelated projects do not count, and neither
+    does the bundled PKG rules directory (COR-only by the scanner's layer
+    invariant; treating it as a PRJ root would raise LayerValidationError,
+    e.g. when running from inside ``src/fx_alfred/``). The fallback
+    preserves the pre-CHG-2300 behavior (cwd) for invocations outside any
+    Alfred project.
+    """
+    for candidate in (start, *start.parents):
+        rules_dir = candidate / "rules"
+        if not rules_dir.is_dir():
+            continue
+        try:
+            entries = rules_dir.iterdir()
+        except OSError:
+            continue
+        if any(
+            e.is_file()
+            and FILENAME_PATTERN.match(e.name)
+            and not e.name.startswith("COR-")
+            for e in entries
+        ):
+            return candidate
+    return start
+
 
 def _store_root(
     ctx: click.Context, param: click.Parameter, value: Path | None
@@ -19,13 +52,21 @@ def root_option(f):  # type: ignore[type-arg]
         type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),  # type: ignore[type-var]
         expose_value=False,
         callback=_store_root,
-        help="Project root directory",
+        help=(
+            "Project root directory (default: nearest ancestor whose rules/ "
+            "contains Alfred documents, else the working directory)"
+        ),
     )(f)
 
 
 def get_root(ctx: click.Context) -> Path:
-    """Get root directory from click context."""
+    """Get root directory from click context.
+
+    Explicit ``--root`` wins; otherwise the nearest Alfred project root
+    above the working directory is used (CHG-2300), falling back to the
+    working directory itself.
+    """
     root_ctx = ctx.find_root()
     if root_ctx.obj and "root" in root_ctx.obj:
         return root_ctx.obj["root"]
-    return Path.cwd()
+    return discover_root(Path.cwd())
diff --git a/tests/test_root_discovery.py b/tests/test_root_discovery.py
new file mode 100644
index 0000000..04aa2c8
--- /dev/null
+++ b/tests/test_root_discovery.py
@@ -0,0 +1,127 @@
+"""Tests for project-root auto-discovery (CHG-2300).
+
+When --root is absent, get_root() walks up from cwd to the nearest
+ancestor whose rules/ contains at least one Alfred-pattern document;
+no qualifying ancestor → cwd fallback (the pre-CHG-2300 behavior).
+"""
+
+from __future__ import annotations
+
+import pytest
+
+from click.testing import CliRunner
+
+from fx_alfred.cli import cli
+from fx_alfred.context import discover_root
+
+pytestmark = pytest.mark.cli
+
+
+def _make_project(root):
+    rules = root / "rules"
+    rules.mkdir(parents=True)
+    (rules / "TST-7001-SOP-Marker-Doc.md").write_text(
+        """# SOP-7001: Marker Doc
+
+**Applies to:** Test
+**Status:** Active
+---
+## What Is It?
+Marker.
+## Steps
+1. Only step
+""",
+        encoding="utf-8",
+    )
+    return root
+
+
+# ── discover_root unit cases (A1) ──────────────────────────────────────────
+
+
+def test_cwd_is_root(tmp_path):
+    project = _make_project(tmp_path / "proj")
+    assert discover_root(project) == project
+
+
+def test_subdir_resolves_to_project_root(tmp_path):
+    project = _make_project(tmp_path / "proj")
+    deep = project / "src" / "pkg"
+    deep.mkdir(parents=True)
+    assert discover_root(deep) == project
+
+
+def test_nested_roots_nearest_wins(tmp_path):
+    outer = _make_project(tmp_path / "outer")
+    inner = _make_project(outer / "sub" / "inner")
+    start = inner / "deeper"
+    start.mkdir()
+    assert discover_root(start) == inner
+
+
+def test_no_marker_falls_back_to_start(tmp_path):
+    plain = tmp_path / "plain" / "dir"
+    plain.mkdir(parents=True)
+    assert discover_root(plain) == plain
+
+
+def test_pkg_style_cor_only_rules_dir_is_not_a_root(tmp_path):
+    """A rules/ dir containing only COR-* docs is the bundled PKG layer
+    shape, not a PRJ root (scanner layer invariant: COR only in PKG).
+    Discovery must keep walking — e.g. running from src/fx_alfred/core
+    inside the alfred repo must resolve the repo root, not src/fx_alfred."""
+    project = _make_project(tmp_path / "proj")
+    pkg_like = project / "src" / "pkg"
+    (pkg_like / "rules").mkdir(parents=True)
+    (pkg_like / "rules" / "COR-1000-SOP-Create-SOP.md").write_text("# bundled")
+    start = pkg_like / "core"
+    start.mkdir()
+    assert discover_root(start) == project
+
+
+def test_rules_without_pattern_docs_is_not_a_root(tmp_path):
+    project = _make_project(tmp_path / "proj")
+    decoy = project / "vendor"
+    (decoy / "rules").mkdir(parents=True)
+    (decoy / "rules" / "README.md").write_text("not an alfred doc")
+    (decoy / "rules" / "notes.txt").write_text("nope")
+    # decoy/rules has files but none match FILENAME_PATTERN → keep walking.
+    assert discover_root(decoy) == project
+
+
+# ── CLI behavior (A2) ───────────────────────────────────────────────────────
+
+
+def test_af_list_from_subdirectory_sees_prj_docs(tmp_path, monkeypatch):
+    project = _make_project(tmp_path / "proj")
+    subdir = project / "src"
+    subdir.mkdir()
+    monkeypatch.chdir(subdir)
+
+    runner = CliRunner()
+    result = runner.invoke(cli, ["list"], catch_exceptions=False)
+    assert result.exit_code == 0
+    assert "TST-7001" in result.output
+
+
+def test_explicit_root_wins_over_discovery(tmp_path, monkeypatch):
+    inside = _make_project(tmp_path / "inside")
+    elsewhere = _make_project(tmp_path / "elsewhere")
+    # cwd discovery would find `inside`; --root must override to `elsewhere`.
+    monkeypatch.chdir(inside)
+    (elsewhere / "rules" / "TST-7002-SOP-Other-Doc.md").write_text(
+        (inside / "rules" / "TST-7001-SOP-Marker-Doc.md")
+        .read_text(encoding="utf-8")
+        .replace("7001", "7002")
+        .replace("Marker Doc", "Other Doc"),
+        encoding="utf-8",
+    )
+
+    runner = CliRunner()
+    result = runner.invoke(
+        cli, ["list", "--root", str(elsewhere)], catch_exceptions=False
+    )
+    assert result.exit_code == 0
+    # TST-7002 exists only under `elsewhere` — its presence proves --root
+    # overrode cwd-based discovery (which would have found `inside`).
+    assert "TST-7002" in result.output
