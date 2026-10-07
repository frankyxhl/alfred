"""End-to-end scenarios for cross-project `af search --all`."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest


pytestmark = [pytest.mark.cli, pytest.mark.integration]


@dataclass(frozen=True)
class ScenarioProjects:
    root_a: Path
    root_b: Path
    unregistered: Path


@dataclass(frozen=True)
class BrokenScenarioProjects:
    root_a: Path
    root_b: Path
    root_c: Path
    unregistered: Path


def _run_af(*arguments: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("af")
    assert executable is not None, "the real af executable must be on PATH"
    source_root = Path(__file__).resolve().parents[1] / "src"
    environment = os.environ.copy()
    environment["HOME"] = str(Path.home())
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(source_root), environment.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    return subprocess.run(
        [executable, *arguments],
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )


def _write_project(root: Path, marker: str, *, zebra_marker: str | None = None) -> None:
    rules = root / "rules"
    rules.mkdir(parents=True)
    (rules / "STW-0001-SOP-Shared-Prefix.md").write_text(
        f"# Shared Prefix\n{marker}\n",
        encoding="utf-8",
    )
    zebra_content = "# Zebra Document\nzebra\n"
    if zebra_marker is not None:
        zebra_content = f"# Zebra Document\nzebra\n{zebra_marker}\n"
    (rules / "STW-0002-SOP-Zebra.md").write_text(zebra_content, encoding="utf-8")


@pytest.fixture
def scenario(tmp_path: Path) -> ScenarioProjects:
    base = Path(tmp_path).resolve()
    projects = ScenarioProjects(
        root_a=base / "project-a",
        root_b=base / "project-b",
        unregistered=base / "unregistered",
    )
    _write_project(
        projects.root_a,
        "A-only-search-target",
        zebra_marker="A-local-zebra-target",
    )
    _write_project(projects.root_b, "B-only-search-target")
    projects.unregistered.mkdir()

    for project_root in (projects.root_a, projects.root_b):
        registered = _run_af("register", cwd=project_root)
        assert registered.returncode == 0, registered.stderr + registered.stdout

    return projects


def test_s1_default_stays_local(scenario: ScenarioProjects) -> None:
    result = _run_af("search", "zebra", cwd=scenario.root_a)

    assert result.returncode == 0
    assert "A-local-zebra-target" in result.stdout
    assert "B-only-search-target" not in result.stdout


def test_s2_all_finds_every_registered_project(scenario: ScenarioProjects) -> None:
    result = _run_af(
        "search",
        "zebra",
        "--all",
        cwd=scenario.unregistered,
    )

    assert result.returncode == 0
    assert str(scenario.root_a) in result.stdout
    assert str(scenario.root_b) in result.stdout


def test_s3_pkg_hits_appear_once(scenario: ScenarioProjects) -> None:
    result = _run_af(
        "search",
        "Workflow Routing",
        "--all",
        cwd=scenario.unregistered,
    )

    assert result.returncode == 0
    package_hits = [
        line for line in result.stdout.splitlines() if line.startswith("COR-1103  PKG")
    ]
    assert len(package_hits) == 1


def test_s4_same_prefix_projects_stay_distinct(scenario: ScenarioProjects) -> None:
    result = _run_af(
        "search",
        "B-only-search-target",
        "--all",
        cwd=scenario.unregistered,
    )

    assert result.returncode == 0
    project_hits = [
        line for line in result.stdout.splitlines() if line.startswith("STW-0001  PRJ")
    ]
    assert len(project_hits) == 1
    assert str(scenario.root_b) in result.stdout
    assert "B-only-search-target" in result.stdout


def test_s5_json_carries_project_root(scenario: ScenarioProjects) -> None:
    result = _run_af(
        "search",
        "zebra",
        "--all",
        "--json",
        cwd=scenario.unregistered,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    prj_hits = [entry for entry in payload["results"] if entry["source"] == "prj"]
    other_hits = [entry for entry in payload["results"] if entry["source"] != "prj"]

    assert prj_hits
    assert {entry["project_root"] for entry in prj_hits} == {
        str(scenario.root_a),
        str(scenario.root_b),
    }
    assert all(entry.get("project_root") in (None, "") for entry in other_hits)


def test_s6_dead_project_is_skipped_not_fatal(
    scenario: ScenarioProjects,
    tmp_path: Path,
) -> None:
    dead_root = Path(tmp_path).resolve() / "project-dead"
    _write_project(dead_root, "# Unreachable\nzebra\n")
    registered = _run_af("register", cwd=dead_root)
    assert registered.returncode == 0
    shutil.rmtree(dead_root)

    result = _run_af("search", "zebra", "--all", cwd=scenario.unregistered)
    combined_output = result.stdout + result.stderr
    dead_root_warnings = [
        line for line in combined_output.splitlines() if str(dead_root) in line
    ]

    assert result.returncode == 0
    assert str(scenario.root_a) in combined_output
    assert str(scenario.root_b) in combined_output
    assert len(dead_root_warnings) == 1


@pytest.fixture
def broken_scenario(tmp_path: Path) -> BrokenScenarioProjects:
    base = Path(tmp_path).resolve()
    projects = BrokenScenarioProjects(
        root_a=base / "project-a",
        root_b=base / "project-b",
        root_c=base / "project-c",
        unregistered=base / "unregistered",
    )
    _write_project(
        projects.root_a,
        "A-only-broken-target",
        zebra_marker="A-local-zebra-target",
    )
    _write_project(projects.root_b, "B-only-broken-target")
    _write_project(projects.root_c, "C-only-broken-target")
    projects.unregistered.mkdir()

    for project_root in (
        projects.root_a,
        projects.root_b,
        projects.root_c,
    ):
        registered = _run_af("register", cwd=project_root)
        assert registered.returncode == 0, registered.stderr + registered.stdout

    duplicate_acid_one = projects.root_b / "rules" / "FJO-6034-SOP-Duplicate-One.md"
    duplicate_acid_two = projects.root_b / "rules" / "FJO-6034-SOP-Duplicate-Two.md"
    duplicate_acid_one.write_text("# Duplicate One\n", encoding="utf-8")
    duplicate_acid_two.write_text("# Duplicate Two\n", encoding="utf-8")
    (projects.root_c / "rules").chmod(0o000)

    return projects


def test_s7_broken_projects_do_not_crash_all(
    broken_scenario: BrokenScenarioProjects,
) -> None:
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("root ignores directory permissions")
    try:
        result = _run_af(
            "search",
            "zebra",
            "--all",
            cwd=broken_scenario.unregistered,
        )
    finally:
        (broken_scenario.root_c / "rules").chmod(0o755)

    combined_output = result.stdout + result.stderr
    output_lines = combined_output.splitlines()
    validation_warnings = [
        line
        for line in output_lines
        if str(broken_scenario.root_b) in line and "FJO-6034" in line
    ]
    permission_warnings = [
        line
        for line in output_lines
        if str(broken_scenario.root_c) in line
        and ("PermissionError" in line or "Permission denied" in line)
    ]

    assert result.returncode == 0
    assert "A-local-zebra-target" in result.stdout
    assert len(validation_warnings) == 1
    assert len(permission_warnings) == 1
    assert "Traceback" not in combined_output


def test_s8_default_json_has_v130_keys(scenario: ScenarioProjects) -> None:
    result = _run_af("search", "zebra", "--json", cwd=scenario.root_a)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert len(payload["results"]) == 1
    assert set(payload["results"][0]) == {
        "doc_id",
        "title",
        "source",
        "snippet",
    }
    assert str(scenario.root_b) not in result.stdout


def test_s9_all_json_adds_project_root(scenario: ScenarioProjects) -> None:
    result = _run_af(
        "search",
        "zebra",
        "--all",
        "--json",
        cwd=scenario.unregistered,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    expected_keys = {
        "doc_id",
        "title",
        "source",
        "project_root",
        "snippet",
    }
    assert len(payload["results"]) == 2
    assert set(payload["results"][0]) == expected_keys
    assert set(payload["results"][1]) == expected_keys
