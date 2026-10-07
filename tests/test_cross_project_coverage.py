"""Behaviour coverage for cross-project CI fixes."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from fx_alfred.cli import cli
from fx_alfred.commands._helpers import scan_registered_project_documents
from fx_alfred.core.registry import (
    RegistryEntry,
    prune_missing_roots,
    registry_path,
    save_registry,
)

pytestmark = [pytest.mark.cli]


def _write_project(root: Path, document_id: str, marker: str) -> Path:
    """Create a minimal project whose PRJ layer has one document."""
    rules = root / "rules"
    rules.mkdir(parents=True, exist_ok=True)
    (rules / f"{document_id}-SOP-Coverage.md").write_text(
        f"# {document_id}\n\n{marker}\n",
        encoding="utf-8",
    )
    return root


def _register(runner: CliRunner, root: Path) -> None:
    result = runner.invoke(cli, ["register", "--root", str(root)])
    assert result.exit_code == 0, result.output


def test_scan_registered_project_documents_skips_current_and_warns(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The shared all-command scanner deduplicates cwd, scans and reports."""
    current = _write_project(tmp_path / "current", "CUR-0001", "current marker")
    registered = _write_project(
        tmp_path / "registered", "REG-0001", "registered marker"
    )
    missing = tmp_path / "missing"
    save_registry(
        registry_path(),
        [
            RegistryEntry("CUR", str(current), 1, "2026-10-05"),
            RegistryEntry("REG", str(registered), 1, "2026-10-05"),
            RegistryEntry("GONE", str(missing), 1, "2026-10-05"),
        ],
        today="2026-10-05",
    )

    scanned = scan_registered_project_documents(current.resolve())

    assert [root for root, _ in scanned] == [registered.resolve()]
    document_ids = {doc.prefix + "-" + doc.acid for _, docs in scanned for doc in docs}
    assert "REG-0001" in document_ids
    assert "does not exist" in capsys.readouterr().err


def test_prune_removes_a_worktree_marker_root(tmp_path: Path) -> None:
    """A directory whose `.git` is the worktree marker file is removable."""
    root = tmp_path / "worktree-root"
    root.mkdir()
    (root / ".git").write_text(
        "gitdir: ../main/.git/worktrees/example\n", encoding="utf-8"
    )
    entry = RegistryEntry("WT", str(root), 1, "2026-10-05")

    kept, removed = prune_missing_roots([entry])

    assert kept == []
    assert removed == [entry]


def test_prune_removes_a_root_beneath_a_file(tmp_path: Path) -> None:
    """A non-directory parent is definitive evidence the root is gone."""
    parent = tmp_path / "parent"
    parent.write_text("not a directory\n", encoding="utf-8")
    entry = RegistryEntry("BAD", str(parent / "root"), 1, "2026-10-05")

    kept, removed = prune_missing_roots([entry])

    assert kept == []
    assert removed == [entry]


def test_register_rejects_a_git_worktree_marker(tmp_path: Path) -> None:
    """Registration belongs at the main repository, not a linked worktree."""
    project = _write_project(tmp_path / "worktree-project", "WT-0001", "worktree")
    (project / ".git").write_text(
        "gitdir: ../main/.git/worktrees/example\n", encoding="utf-8"
    )

    result = CliRunner().invoke(cli, ["register", "--root", str(project)])

    assert result.exit_code != 0
    assert "linked git worktree" in result.output
    assert registry_path().exists() is False


def test_list_all_json_names_the_current_registered_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Local PRJ hits and registered PRJ hits both carry JSON roots."""
    runner = CliRunner()
    current = _write_project(tmp_path / "current", "CUR-0001", "current marker")
    registered = _write_project(
        tmp_path / "registered", "REG-0001", "registered marker"
    )
    _register(runner, current)
    _register(runner, registered)
    monkeypatch.chdir(current)

    result = runner.invoke(cli, ["list", "--all", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    project_entries = [entry for entry in payload if entry["source"] == "prj"]
    roots = Counter(
        (entry["project_root"], entry["prefix"] + "-" + entry["acid"])
        for entry in project_entries
    )
    assert roots == Counter(
        {
            (str(current.resolve()), "CUR-0001"): 1,
            (str(registered.resolve()), "REG-0001"): 1,
        }
    )


def test_list_all_plain_output_shows_project_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The human list labels each document with its owning project."""
    runner = CliRunner()
    current = _write_project(tmp_path / "current", "CUR-0001", "current marker")
    registered = _write_project(
        tmp_path / "registered", "REG-0001", "registered marker"
    )
    _register(runner, current)
    _register(runner, registered)
    monkeypatch.chdir(current)

    result = runner.invoke(cli, ["list", "--all"])

    assert result.exit_code == 0, result.output
    _assert_project_label(result.stdout, "CUR-0001", current)
    _assert_project_label(result.stdout, "REG-0001", registered)


def test_read_all_ambiguity_names_registered_candidates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An all-project read resolves duplicate ids by naming both roots."""
    runner = CliRunner()
    current = _write_project(tmp_path / "current", "ABC-0001", "current marker")
    registered = _write_project(
        tmp_path / "registered", "ABC-0001", "registered marker"
    )
    _register(runner, current)
    _register(runner, registered)
    monkeypatch.chdir(current)

    result = runner.invoke(cli, ["read", "ABC-0001", "--all"])

    assert result.exit_code != 0
    assert "Ambiguous document ABC-0001" in result.output
    assert str(current.resolve()) in result.output
    assert str(registered.resolve()) in result.output


def test_search_all_json_from_registered_cwd_reports_resolved_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """JSON project roots are strings equal to each resolved project root."""
    runner = CliRunner()
    current = _write_project(tmp_path / "current", "CUR-0001", "cross-project marker")
    registered = _write_project(
        tmp_path / "registered", "REG-0001", "cross-project marker"
    )
    _register(runner, current)
    _register(runner, registered)
    monkeypatch.chdir(current)

    result = runner.invoke(cli, ["search", "cross-project marker", "--all", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert Counter(
        (entry["doc_id"], entry["project_root"]) for entry in payload["results"]
    ) == Counter(
        {
            ("CUR-0001", str(current.resolve())): 1,
            ("REG-0001", str(registered.resolve())): 1,
        }
    )
    assert all(isinstance(entry["project_root"], str) for entry in payload["results"])


def test_search_all_plain_output_labels_project_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Human search labels both local and registered matches."""
    runner = CliRunner()
    current = _write_project(tmp_path / "current", "CUR-0001", "cross-project marker")
    registered = _write_project(
        tmp_path / "registered", "REG-0001", "cross-project marker"
    )
    _register(runner, current)
    _register(runner, registered)
    monkeypatch.chdir(current)

    result = runner.invoke(cli, ["search", "cross-project marker", "--all"])

    assert result.exit_code == 0, result.output
    _assert_project_label(result.stdout, "CUR-0001", current)
    _assert_project_label(result.stdout, "REG-0001", registered)


def _assert_project_label(output: str, document_id: str, root: Path) -> None:
    lines = output.splitlines()
    index = next(
        (
            i
            for i, line in enumerate(lines[:-1])
            if document_id in line and lines[i + 1].startswith("  Project: ")
        ),
        None,
    )
    assert index is not None, output
    assert lines[index + 1] == f"  Project: {root.resolve()}"
