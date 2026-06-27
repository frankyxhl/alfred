"""Tests for fx_alfred.core.projects (FXA-2314).

All imports are done lazily inside test functions so this file can be
collected by pytest even before the module exists.  In the RED phase every
test fails with ImportError; after implementation they exercise the real
behaviour.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ── lazy importers (keep collection-time ImportError out of module scope) ────


def _load_projects():
    from fx_alfred.core.projects import load_projects  # noqa: PLC0415

    return load_projects


def _resolve_subproject():
    from fx_alfred.core.projects import resolve_subproject  # noqa: PLC0415

    return resolve_subproject


# ── load_projects ─────────────────────────────────────────────────────────────


def test_valid_map_parses_correctly():
    """A well-formed projects.json returns the full mapping dict."""
    load_projects = _load_projects()
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True, exist_ok=True)
    data = {"projects": {"/abs/path/repo": "NRV", "/abs/other/repo": "ALF"}}
    (alfred / "projects.json").write_text(json.dumps(data), encoding="utf-8")
    result = load_projects()
    assert result == {"/abs/path/repo": "NRV", "/abs/other/repo": "ALF"}


def test_missing_file_returns_empty_dict():
    """Missing ~/.alfred/projects.json returns {} without crashing."""
    load_projects = _load_projects()
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True, exist_ok=True)
    # No projects.json written
    result = load_projects()
    assert result == {}


def test_alfred_dir_absent_returns_empty_dict():
    """If ~/.alfred/ itself doesn't exist, return {} without crashing."""
    load_projects = _load_projects()
    # isolate_home gives us a fresh fake_home; do NOT create .alfred
    result = load_projects()
    assert result == {}


def test_malformed_json_returns_empty_and_warns(capsys):
    """Malformed JSON => {} AND a warning is written to stderr (or stdout)."""
    load_projects = _load_projects()
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True, exist_ok=True)
    (alfred / "projects.json").write_text(
        "{this is not: valid json{{{", encoding="utf-8"
    )
    result = load_projects()
    assert result == {}
    captured = capsys.readouterr()
    assert captured.err or captured.out, (
        "Expected a warning on stderr (or stdout) for a malformed-but-present projects.json"
    )


def test_wrong_shape_returns_empty():
    """JSON without 'projects' top-level key => {}."""
    load_projects = _load_projects()
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True, exist_ok=True)
    (alfred / "projects.json").write_text(
        json.dumps({"mappings": {"/abs/repo": "NRV"}}), encoding="utf-8"
    )
    result = load_projects()
    assert result == {}


def test_unknown_top_level_keys_returns_empty():
    """JSON with only unknown top-level keys => {}."""
    load_projects = _load_projects()
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True, exist_ok=True)
    (alfred / "projects.json").write_text(
        json.dumps({"foo": "bar", "baz": 123}), encoding="utf-8"
    )
    result = load_projects()
    assert result == {}


def test_projects_value_not_dict_returns_empty():
    """projects.json where 'projects' value is a list (not dict) => {}."""
    load_projects = _load_projects()
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True, exist_ok=True)
    (alfred / "projects.json").write_text(
        json.dumps({"projects": ["/abs/repo", "NRV"]}), encoding="utf-8"
    )
    result = load_projects()
    assert result == {}


def test_relative_key_ignored_with_warning(capsys):
    """Relative path key is excluded from the result and a warning is emitted."""
    load_projects = _load_projects()
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True, exist_ok=True)
    data = {"projects": {"relative/path": "NRV", "/abs/valid": "ALF"}}
    (alfred / "projects.json").write_text(json.dumps(data), encoding="utf-8")
    result = load_projects()
    assert "relative/path" not in result, "Relative key must be excluded"
    assert "/abs/valid" in result, "Absolute key must be kept"
    captured = capsys.readouterr()
    assert captured.err or captured.out, "Expected a warning for the relative key"


def test_value_with_path_separator_rejected(capsys):
    """Value containing '/' is rejected and a warning is emitted."""
    load_projects = _load_projects()
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True, exist_ok=True)
    (alfred / "projects.json").write_text(
        json.dumps({"projects": {"/abs/repo": "sub/dir"}}), encoding="utf-8"
    )
    result = load_projects()
    assert result == {}
    captured = capsys.readouterr()
    assert captured.err or captured.out, (
        "Expected a warning for value with path separator"
    )


def test_value_dot_rejected(capsys):
    """Value '.' is rejected and a warning is emitted."""
    load_projects = _load_projects()
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True, exist_ok=True)
    (alfred / "projects.json").write_text(
        json.dumps({"projects": {"/abs/repo": "."}}), encoding="utf-8"
    )
    result = load_projects()
    assert result == {}
    captured = capsys.readouterr()
    assert captured.err or captured.out, "Expected a warning for value '.'"


def test_value_dotdot_rejected(capsys):
    """Value '..' is rejected and a warning is emitted."""
    load_projects = _load_projects()
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True, exist_ok=True)
    (alfred / "projects.json").write_text(
        json.dumps({"projects": {"/abs/repo": ".."}}), encoding="utf-8"
    )
    result = load_projects()
    assert result == {}
    captured = capsys.readouterr()
    assert captured.err or captured.out, "Expected a warning for value '..'"


def test_value_empty_string_rejected(capsys):
    """Empty string value is rejected and a warning is emitted."""
    load_projects = _load_projects()
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True, exist_ok=True)
    (alfred / "projects.json").write_text(
        json.dumps({"projects": {"/abs/repo": ""}}), encoding="utf-8"
    )
    result = load_projects()
    assert result == {}
    captured = capsys.readouterr()
    assert captured.err or captured.out, "Expected a warning for empty-string value"


def test_mixed_valid_and_invalid_entries(capsys):
    """Valid entries are kept; invalid entries (relative key, bad value) are excluded."""
    load_projects = _load_projects()
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True, exist_ok=True)
    data = {
        "projects": {
            "/abs/good": "NRV",  # valid
            "relative/bad": "ALF",  # relative key → excluded + warned
            "/abs/dot": ".",  # bad value → excluded + warned
        }
    }
    (alfred / "projects.json").write_text(json.dumps(data), encoding="utf-8")
    result = load_projects()
    assert "/abs/good" in result
    assert result["/abs/good"] == "NRV"
    assert "relative/bad" not in result
    assert "/abs/dot" not in result


def test_not_cached_across_calls():
    """load_projects reads the file fresh each call (no stale module-level cache)."""
    load_projects = _load_projects()
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True, exist_ok=True)
    pj = alfred / "projects.json"
    pj.write_text(json.dumps({"projects": {"/abs/repo": "NRV"}}), encoding="utf-8")
    first = load_projects()
    # Overwrite the file
    pj.write_text(json.dumps({"projects": {"/abs/repo": "ALF"}}), encoding="utf-8")
    second = load_projects()
    assert second == {"/abs/repo": "ALF"}, (
        "Second call must reflect updated file — module-level cache leaks across invocations"
    )
    assert first != second


def test_many_to_one_mapping_allowed():
    """Multiple roots may map to the same NAME (many-to-one is legal)."""
    load_projects = _load_projects()
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True, exist_ok=True)
    data = {
        "projects": {
            "/abs/repo1": "NRV",
            "/abs/repo2": "NRV",
            "/abs/repo3": "ALF",
        }
    }
    (alfred / "projects.json").write_text(json.dumps(data), encoding="utf-8")
    result = load_projects()
    assert result["/abs/repo1"] == "NRV"
    assert result["/abs/repo2"] == "NRV"
    assert result["/abs/repo3"] == "ALF"


# ── resolve_subproject ────────────────────────────────────────────────────────


def test_resolve_subproject_returns_name_for_mapped_root(tmp_path):
    """resolve_subproject(root) returns the NAME when root is in projects.json."""
    resolve_subproject = _resolve_subproject()
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True, exist_ok=True)
    ext_repo = tmp_path / "ext_repo"
    ext_repo.mkdir()
    (alfred / "projects.json").write_text(
        json.dumps({"projects": {str(ext_repo.resolve()): "NRV"}}),
        encoding="utf-8",
    )
    assert resolve_subproject(ext_repo) == "NRV"


def test_resolve_subproject_returns_none_for_unmapped(tmp_path):
    """resolve_subproject(root) returns None for a root not in projects.json."""
    resolve_subproject = _resolve_subproject()
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True, exist_ok=True)
    ext_repo = tmp_path / "ext_repo"
    ext_repo.mkdir()
    # No projects.json → no mapping
    assert resolve_subproject(ext_repo) is None


def test_resolve_subproject_handles_symlink(tmp_path):
    """resolve_subproject resolves symlinks on both sides before comparing."""
    resolve_subproject = _resolve_subproject()
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True, exist_ok=True)
    real_repo = tmp_path / "real_repo"
    real_repo.mkdir()
    link_repo = tmp_path / "link_repo"
    link_repo.symlink_to(real_repo)
    # Register with the canonical real path
    (alfred / "projects.json").write_text(
        json.dumps({"projects": {str(real_repo.resolve()): "NRV"}}),
        encoding="utf-8",
    )
    # Passing the symlink must still resolve to "NRV"
    assert resolve_subproject(link_repo) == "NRV"


def test_resolve_subproject_no_projects_json_returns_none(tmp_path):
    """resolve_subproject returns None when projects.json is absent (no crash)."""
    resolve_subproject = _resolve_subproject()
    # isolate_home gives a fresh home; don't create .alfred
    ext_repo = tmp_path / "ext_repo"
    ext_repo.mkdir()
    assert resolve_subproject(ext_repo) is None
