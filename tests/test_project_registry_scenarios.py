"""End-to-end tests for explicit Project SOP Registry behavior."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from fx_alfred.core.registry import (
    REGISTRY_FILENAME,
    RegistryEntry,
    save_registry,
)


pytestmark = [pytest.mark.cli, pytest.mark.integration]


AF_EXECUTABLE = Path(sys.executable).with_name("af")
PROJECT_FILES = {
    "ALF-0000-REF-Document-Index.md": "# ALF Index",
    "ALF-2201-PRP-AF-CLI-Tool.md": "# AF CLI",
    "ALF-2202-SOP-Another-Doc.md": "# Another Doc",
}


def run_af(
    arguments: list[str], cwd: Path, home: Path
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["HOME"] = str(home)
    environment["NO_COLOR"] = "1"
    return subprocess.run(
        [str(AF_EXECUTABLE), *arguments],
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def make_project(home: Path, name: str = "project") -> Path:
    project = home / name
    rules = project / "rules"
    rules.mkdir(parents=True)
    for filename, body in PROJECT_FILES.items():
        (rules / filename).write_text(body, encoding="utf-8")
    return project


def make_linked_worktree(home: Path) -> tuple[Path, Path]:
    project = make_project(home, "git-project")
    worktree = home / "project-worktree"

    def run_git(arguments: list[str]) -> None:
        subprocess.run(
            ["git", *arguments],
            cwd=project,
            capture_output=True,
            text=True,
            check=True,
        )

    run_git(["init", "--initial-branch=main"])
    run_git(["config", "user.name", "Alfred Tests"])
    run_git(["config", "user.email", "alfred-tests@example.invalid"])
    run_git(["add", "rules"])
    run_git(["commit", "-m", "initial project"])
    run_git(["worktree", "add", str(worktree)])
    return project, worktree


def registered_roots(home: Path) -> list[str]:
    result = run_af(["projects", "--json"], cwd=home, home=home)
    assert result.returncode == 0, result.stderr
    return [row["root"] for row in json.loads(result.stdout)]


def registry_bytes_or_none(registry: Path) -> bytes | None:
    return registry.read_bytes() if registry.exists() else None


def seed_registry(home: Path, entries: list[RegistryEntry]) -> None:
    save_registry(
        home / ".alfred" / REGISTRY_FILENAME,
        entries,
        today="2026-10-01",
    )


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def test_s1_reads_do_not_register(isolated_home: Path) -> None:
    """Read commands must expose a project without writing the registry."""
    project = make_project(isolated_home)
    registry = isolated_home / ".alfred" / REGISTRY_FILENAME
    registry_before = registry_bytes_or_none(registry)

    for arguments in (
        ["guide"],
        ["list"],
        ["read", "ALF-2201"],
        ["status"],
    ):
        result = run_af(arguments, cwd=project, home=isolated_home)
        assert result.returncode == 0, result.stderr

    registry_after = registry_bytes_or_none(registry)
    assert registry_after == registry_before

    projects_json = run_af(["projects", "--json"], cwd=project, home=isolated_home)
    assert projects_json.returncode == 0, projects_json.stderr
    assert json.loads(projects_json.stdout) == []


def test_s2_register_is_idempotent(isolated_home: Path) -> None:
    """Repeated explicit registration keeps one row per project root."""
    project = make_project(isolated_home)

    first = run_af(["register"], cwd=project, home=isolated_home)
    assert first.returncode == 0, first.stderr
    assert registered_roots(isolated_home) == [str(project.resolve())]

    second = run_af(["register"], cwd=project, home=isolated_home)
    assert second.returncode == 0, second.stderr
    assert registered_roots(isolated_home) == [str(project.resolve())]


def test_s3_register_rejects_linked_worktree(isolated_home: Path) -> None:
    """Register a linked worktree's main repository instead of the link."""
    main_project, worktree = make_linked_worktree(isolated_home)

    result = run_af(["register"], cwd=worktree, home=isolated_home)
    assert result.returncode != 0
    assert "worktree" in result.stderr.lower()
    assert "main repo" in result.stderr.lower()
    assert registered_roots(isolated_home) == []

    main_result = run_af(["register"], cwd=main_project, home=isolated_home)
    assert main_result.returncode == 0, main_result.stderr
    assert registered_roots(isolated_home) == [str(main_project.resolve())]


def test_s4_prune_removes_worktree_and_dead_roots(isolated_home: Path) -> None:
    """Prune removes both dead roots and live linked-worktree roots."""
    live = make_project(isolated_home, "live-project")
    _, worktree = make_linked_worktree(isolated_home)
    dead = isolated_home / "dead-project"

    seed_registry(
        isolated_home,
        [
            RegistryEntry("OLD", str(dead), 3, "2026-01-01"),
            RegistryEntry("WT", str(worktree), 3, "2026-01-01"),
        ],
    )
    registration = run_af(["register"], cwd=live, home=isolated_home)
    assert registration.returncode == 0, registration.stderr

    first_prune = run_af(["projects", "--prune"], cwd=live, home=isolated_home)
    assert first_prune.returncode == 0, first_prune.stderr
    assert re.search(r"(?i)\bremoved\s+2\b", first_prune.stdout)
    assert registered_roots(isolated_home) == [str(live.resolve())]

    second_prune = run_af(["projects", "--prune"], cwd=live, home=isolated_home)
    assert second_prune.returncode == 0, second_prune.stderr
    assert re.search(r"(?i)\bremoved\s+0\b", second_prune.stdout)
    assert registered_roots(isolated_home) == [str(live.resolve())]


def test_s5_projects_json_after_prune(isolated_home: Path) -> None:
    """JSON project output contains exactly the surviving ordinary roots."""
    unregistered_cwd = make_project(isolated_home, "unregistered-cwd")
    _, worktree = make_linked_worktree(isolated_home)
    dead = isolated_home / "dead-project"
    seed_registry(
        isolated_home,
        [
            RegistryEntry("OLD", str(dead), 3, "2026-01-01"),
            RegistryEntry("WT", str(worktree), 3, "2026-01-01"),
        ],
    )

    prune = run_af(["projects", "--prune"], cwd=unregistered_cwd, home=isolated_home)
    assert prune.returncode == 0, prune.stderr
    projects_json = run_af(
        ["projects", "--json"], cwd=unregistered_cwd, home=isolated_home
    )
    assert projects_json.returncode == 0, projects_json.stderr
    payload = json.loads(projects_json.stdout)
    assert payload == []
