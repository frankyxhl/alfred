"""End-to-end scenarios for cross-project list and read."""

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


@dataclass(frozen=True)
class MappedScenarioProjects:
    home: Path
    root_a: Path
    root_b: Path
    unregistered: Path


def _run_af(
    *arguments: str,
    cwd: Path,
    home: Path,
) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("af")
    assert executable is not None, "the real af executable must be on PATH"
    source_root = Path(__file__).resolve().parents[1] / "src"
    environment = os.environ.copy()
    environment["HOME"] = str(home)
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


def _write_document(root: Path, filename: str, heading: str, marker: str) -> None:
    document = root / "rules" / filename
    document.parent.mkdir(parents=True, exist_ok=True)
    document.write_text(
        f"# {heading}\n\n**Title:** {heading}\n\n---\n\n{marker}\n",
        encoding="utf-8",
    )


def _write_mapped_document(
    home: Path,
    name: str,
    heading: str,
    marker: str,
    *,
    nested: bool,
) -> None:
    document = home / ".alfred" / name / "STW-0001-SOP-Shared.md"
    if nested:
        document = document.parent / "nested" / document.name
    document.parent.mkdir(parents=True, exist_ok=True)
    document.write_text(
        f"# {heading}\n\n**Title:** {heading}\n\n---\n\n{marker}\n",
        encoding="utf-8",
    )


def _write_local_ambiguity_project(root: Path) -> Path:
    """Create one flat project with two prefixes sharing an uncolliding ACID."""
    _write_document(root, "ABC-3411-SOP-Local.md", "ABC-3411: Local", "abc local")
    _write_document(root, "STW-3411-SOP-Local.md", "STW-3411: Local", "stw local")
    return root


@pytest.fixture
def scenario(tmp_path: Path) -> ScenarioProjects:
    base = tmp_path.resolve()
    projects = ScenarioProjects(
        root_a=base / "project-a",
        root_b=base / "project-b",
        unregistered=base / "unregistered",
    )

    _write_document(
        projects.root_a,
        "ABC-0001-SOP-Alpha.md",
        "ABC-0001: Alpha Document",
        "alpha",
    )
    _write_document(
        projects.root_a,
        "STW-0001-SOP-Alpha.md",
        "STW-0001: Shared Alpha",
        "alpha",
    )
    _write_document(
        projects.root_b,
        "STW-0001-SOP-Bravo.md",
        "STW-0001: Shared Bravo",
        "bravo",
    )
    _write_document(
        projects.root_b,
        "XYZ-0002-SOP-Bravo.md",
        "XYZ-0002: Bravo Document",
        "bravo",
    )
    projects.unregistered.mkdir()

    for project_root in (projects.root_a, projects.root_b):
        registered = _run_af("register", cwd=project_root, home=base)
        assert registered.returncode == 0, registered.stderr + registered.stdout

    return projects


@pytest.fixture
def mapped_scenario(tmp_path: Path) -> MappedScenarioProjects:
    home = tmp_path.resolve()
    projects = MappedScenarioProjects(
        home=home,
        root_a=home / "mapped-project-a",
        root_b=home / "mapped-project-b",
        unregistered=home / "unregistered",
    )
    _write_mapped_document(
        home, "map-a", "STW-0001: Mapped Alpha", "mapped alpha", nested=False
    )
    _write_mapped_document(
        home, "map-b", "STW-0001: Mapped Bravo", "mapped bravo", nested=True
    )
    projects.root_a.mkdir()
    projects.root_b.mkdir()
    projects.unregistered.mkdir()
    mapping = {
        "projects": {
            str(projects.root_a.resolve()): "map-a",
            str(projects.root_b.resolve()): "map-b",
        }
    }
    (home / ".alfred" / "projects.json").write_text(
        json.dumps(mapping), encoding="utf-8"
    )
    for project_root in (projects.root_a, projects.root_b):
        registered = _run_af("register", cwd=project_root, home=home)
        assert registered.returncode == 0, registered.stderr + registered.stdout
    return projects


@pytest.fixture
def broken_scenario(tmp_path: Path) -> BrokenScenarioProjects:
    base = tmp_path.resolve()
    projects = BrokenScenarioProjects(
        root_a=base / "project-a",
        root_b=base / "project-b",
        root_c=base / "project-c",
        unregistered=base / "unregistered",
    )

    _write_document(
        projects.root_a,
        "ABC-0001-SOP-Alpha.md",
        "ABC-0001: Alpha Document",
        "alpha",
    )
    _write_document(
        projects.root_b,
        "BRO-0001-SOP-Broken.md",
        "BRO-0001: Broken Project",
        "bravo",
    )
    _write_document(
        projects.root_c,
        "CHX-0001-SOP-Cleanup.md",
        "CHX-0001: Cleanup Document",
        "charlie",
    )
    projects.unregistered.mkdir()

    for project_root in (projects.root_a, projects.root_b, projects.root_c):
        registered = _run_af("register", cwd=project_root, home=base)
        assert registered.returncode == 0, registered.stderr + registered.stdout

    _write_document(
        projects.root_b,
        "BRO-0001-SOP-Duplicate.md",
        "BRO-0001: Broken Duplicate",
        "duplicate",
    )
    shutil.rmtree(projects.root_c)

    return projects


def test_s1_list_stays_local_by_default(
    scenario: ScenarioProjects,
    tmp_path: Path,
) -> None:
    result = _run_af("list", cwd=scenario.root_a, home=tmp_path)

    assert result.returncode == 0
    assert "ABC-0001" in result.stdout
    assert "STW-0001" in result.stdout
    assert "XYZ-0002" not in result.stdout
    assert str(scenario.root_b) not in result.stdout


def test_s2_list_all_shows_every_registered_project(
    scenario: ScenarioProjects,
    tmp_path: Path,
) -> None:
    result = _run_af("list", "--all", cwd=scenario.unregistered, home=tmp_path)

    assert result.returncode == 0
    for project_root in (scenario.root_a, scenario.root_b):
        assert str(project_root) in result.stdout
    for document_id in ("ABC-0001", "STW-0001", "XYZ-0002"):
        assert document_id in result.stdout
    assert result.stdout.count("COR-1103") == 1


def test_s3_list_all_json_carries_project_root(
    scenario: ScenarioProjects,
    tmp_path: Path,
) -> None:
    result = _run_af(
        "list",
        "--all",
        "--json",
        cwd=scenario.unregistered,
        home=tmp_path,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    project_entries = [entry for entry in payload if entry["source"] == "prj"]
    package_entries = [entry for entry in payload if entry["source"] == "pkg"]

    assert project_entries
    assert {entry["project_root"] for entry in project_entries} == {
        str(scenario.root_a),
        str(scenario.root_b),
    }
    assert {entry["prefix"] for entry in project_entries} == {"ABC", "STW", "XYZ"}
    package_ids = [(entry["prefix"], entry["acid"]) for entry in package_entries]
    assert len(package_ids) == len(set(package_ids))


def test_s4_read_all_reads_a_single_match(
    scenario: ScenarioProjects,
    tmp_path: Path,
) -> None:
    result = _run_af(
        "read",
        "XYZ-0002",
        "--all",
        cwd=scenario.unregistered,
        home=tmp_path,
    )

    assert result.returncode == 0
    assert "XYZ-0002" in result.stdout
    assert "bravo" in result.stdout


def test_s5_read_all_reports_ambiguous_candidates(
    scenario: ScenarioProjects,
    tmp_path: Path,
) -> None:
    result = _run_af(
        "read",
        "STW-0001",
        "--all",
        cwd=scenario.unregistered,
        home=tmp_path,
    )

    assert result.returncode != 0
    assert str(scenario.root_a) in result.stderr
    assert str(scenario.root_b) in result.stderr
    assert "--root" in result.stderr
    assert "PREFIX-ACID" not in result.stderr
    assert "STW-0001" in result.stderr
    assert "alpha" not in result.stdout
    assert "bravo" not in result.stdout
    assert "# STW-0001" not in result.stdout


def test_read_all_local_acid_ambiguity_advises_prefix_acid(
    tmp_path: Path,
) -> None:
    base = tmp_path.resolve()
    project = _write_local_ambiguity_project(base / "local-project")
    outside = base / "outside"
    outside.mkdir()
    registered = _run_af("register", cwd=project, home=base)
    assert registered.returncode == 0, registered.stderr + registered.stdout

    result = _run_af("read", "3411", "--all", cwd=outside, home=base)

    assert result.returncode != 0
    assert result.stderr.splitlines()[1:3] == [
        f"  ABC-3411 at {project.resolve()}",
        f"  STW-3411 at {project.resolve()}",
    ]
    assert "Use PREFIX-ACID to be precise" in result.stderr
    assert result.stderr.count("ABC-3411") == 1
    assert result.stderr.count("STW-3411") == 1


def test_local_acid_ambiguity_advises_prefix_acid(tmp_path: Path) -> None:
    project = _write_local_ambiguity_project(tmp_path / "local-project")

    result = _run_af("read", "3411", cwd=project, home=tmp_path)

    assert result.returncode != 0
    assert result.stderr == (
        "Error: Ambiguous ACID 3411. Multiple matches: ABC-3411, STW-3411. "
        "Use PREFIX-ACID to be precise.\n"
    )


def test_read_all_ambiguity_names_mapped_project_roots(
    mapped_scenario: MappedScenarioProjects,
) -> None:
    result = _run_af(
        "read",
        "STW-0001",
        "--all",
        cwd=mapped_scenario.unregistered,
        home=mapped_scenario.home,
    )

    assert result.returncode != 0
    assert result.stderr.splitlines()[1:3] == [
        f"  STW-0001 at {mapped_scenario.root_a.resolve()}",
        f"  STW-0001 at {mapped_scenario.root_b.resolve()}",
    ]


def test_listed_mapped_root_a_reads_its_direct_document(
    mapped_scenario: MappedScenarioProjects,
) -> None:
    result = _run_af(
        "--root",
        str(mapped_scenario.root_a),
        "read",
        "STW-0001",
        cwd=mapped_scenario.unregistered,
        home=mapped_scenario.home,
    )

    assert result.returncode == 0, result.stderr
    assert "mapped alpha" in result.stdout


def test_listed_mapped_root_b_reads_its_nested_document(
    mapped_scenario: MappedScenarioProjects,
) -> None:
    result = _run_af(
        "--root",
        str(mapped_scenario.root_b),
        "read",
        "STW-0001",
        cwd=mapped_scenario.unregistered,
        home=mapped_scenario.home,
    )

    assert result.returncode == 0, result.stderr
    assert "mapped bravo" in result.stdout


def test_s6_explicit_root_resolves_the_ambiguity(
    scenario: ScenarioProjects,
    tmp_path: Path,
) -> None:
    result = _run_af(
        "read",
        "STW-0001",
        "--root",
        str(scenario.root_b),
        cwd=scenario.root_b,
        home=tmp_path,
    )

    assert result.returncode == 0
    assert "bravo" in result.stdout
    assert "alpha" not in result.stdout
    assert result.stderr == ""


def test_s7_read_all_reports_a_missing_document_cleanly(
    scenario: ScenarioProjects,
    tmp_path: Path,
) -> None:
    result = _run_af(
        "read",
        "NOPE-9999",
        "--all",
        cwd=scenario.unregistered,
        home=tmp_path,
    )

    assert result.returncode != 0
    assert "No document found: NOPE-9999" in result.stderr
    assert result.stdout == ""
    assert "Traceback" not in result.stderr


def test_s8_broken_projects_do_not_crash_list_or_read_all(
    broken_scenario: BrokenScenarioProjects,
    tmp_path: Path,
) -> None:
    list_result = _run_af(
        "list",
        "--all",
        cwd=broken_scenario.unregistered,
        home=tmp_path,
    )

    assert list_result.returncode == 0
    assert str(broken_scenario.root_a) in list_result.stdout
    assert "ABC-0001" in list_result.stdout
    assert str(broken_scenario.root_b) not in list_result.stdout
    assert str(broken_scenario.root_c) not in list_result.stdout

    validation_warnings = [
        line
        for line in list_result.stderr.splitlines()
        if str(broken_scenario.root_b) in line and "BRO-0001" in line
    ]
    missing_warnings = [
        line
        for line in list_result.stderr.splitlines()
        if str(broken_scenario.root_c) in line
    ]
    assert len(validation_warnings) == 1
    assert len(missing_warnings) == 1
    assert "Traceback" not in list_result.stderr

    read_result = _run_af(
        "read",
        "ABC-0001",
        "--all",
        cwd=broken_scenario.unregistered,
        home=tmp_path,
    )

    assert read_result.returncode == 0
    assert "ABC-0001" in read_result.stdout
    assert "alpha" in read_result.stdout
    assert "bravo" not in read_result.stdout

    read_validation_warnings = [
        line
        for line in read_result.stderr.splitlines()
        if str(broken_scenario.root_b) in line and "BRO-0001" in line
    ]
    read_missing_warnings = [
        line
        for line in read_result.stderr.splitlines()
        if str(broken_scenario.root_c) in line
    ]
    assert len(read_validation_warnings) == 1
    assert len(read_missing_warnings) == 1
    assert "Traceback" not in read_result.stderr


@pytest.mark.parametrize("cwd_kind", ["root", "subdirectory", "symlink"])
def test_s9_search_all_counts_registered_current_project_once(
    scenario: ScenarioProjects,
    tmp_path: Path,
    cwd_kind: str,
) -> None:
    if cwd_kind == "subdirectory":
        cwd = scenario.root_a / "nested"
        cwd.mkdir()
    elif cwd_kind == "symlink":
        cwd = tmp_path.resolve() / "project-a-link"
        cwd.symlink_to(scenario.root_a, target_is_directory=True)
    else:
        cwd = scenario.root_a

    result = _run_af("search", "alpha", "--all", "--json", cwd=cwd, home=tmp_path)

    assert result.returncode == 0
    assert result.stderr == ""
    results = json.loads(result.stdout)["results"]
    assert (
        len(
            [
                item
                for item in results
                if item["doc_id"] == "ABC-0001"
                and item["project_root"] == str(scenario.root_a)
            ]
        )
        == 1
    )
    assert (
        len(
            [
                item
                for item in results
                if item["doc_id"] == "STW-0001"
                and item["project_root"] == str(scenario.root_a)
            ]
        )
        == 1
    )
    assert not any(item["project_root"] == str(scenario.root_b) for item in results)


@pytest.mark.parametrize("cwd_kind", ["root", "subdirectory", "symlink"])
def test_s9_list_all_counts_registered_current_project_once(
    scenario: ScenarioProjects,
    tmp_path: Path,
    cwd_kind: str,
) -> None:
    if cwd_kind == "subdirectory":
        cwd = scenario.root_a / "nested"
        cwd.mkdir()
    elif cwd_kind == "symlink":
        cwd = tmp_path.resolve() / "project-a-link"
        cwd.symlink_to(scenario.root_a, target_is_directory=True)
    else:
        cwd = scenario.root_a

    result = _run_af("list", "--all", "--json", cwd=cwd, home=tmp_path)

    assert result.returncode == 0
    assert result.stderr == ""
    rows = json.loads(result.stdout)
    for document_id in ("ABC-0001", "STW-0001"):
        assert (
            len(
                [
                    row
                    for row in rows
                    if f"{row['prefix']}-{row['acid']}" == document_id
                    and row["project_root"] == str(scenario.root_a)
                ]
            )
            == 1
        )
    assert (
        len([row for row in rows if row["project_root"] == str(scenario.root_a)]) == 2
    )
    assert (
        len(
            [
                row
                for row in rows
                if f"{row['prefix']}-{row['acid']}" == "STW-0001"
                and row["project_root"] == str(scenario.root_b)
            ]
        )
        == 1
    )


@pytest.mark.parametrize(
    "cwd_kind",
    ["root", "subdirectory", "symlink"],
)
def test_s9_read_all_reads_unique_current_project_document_once(
    scenario: ScenarioProjects,
    tmp_path: Path,
    cwd_kind: str,
) -> None:
    if cwd_kind == "subdirectory":
        cwd = scenario.root_a / "nested"
        cwd.mkdir()
    elif cwd_kind == "symlink":
        cwd = tmp_path.resolve() / "project-a-link"
        cwd.symlink_to(scenario.root_a, target_is_directory=True)
    else:
        cwd = scenario.root_a

    result = _run_af("read", "ABC-0001", "--all", cwd=cwd, home=tmp_path)

    assert result.returncode == 0
    assert "ABC-0001" in result.stdout
    assert "alpha" in result.stdout
    assert result.stderr == ""


def _cwd_for_kind(
    scenario: ScenarioProjects,
    tmp_path: Path,
    cwd_kind: str,
) -> Path:
    if cwd_kind == "subdirectory":
        cwd = scenario.root_a / "nested"
        cwd.mkdir()
    elif cwd_kind == "symlink":
        cwd = tmp_path.resolve() / "project-a-link"
        cwd.symlink_to(scenario.root_a, target_is_directory=True)
    else:
        cwd = scenario.root_a
    return cwd


@pytest.mark.parametrize(
    "cwd_kind",
    ["root", "subdirectory", "symlink"],
)
def test_s9_read_all_reports_ambiguous_shared_document_once_per_project(
    scenario: ScenarioProjects,
    tmp_path: Path,
    cwd_kind: str,
) -> None:
    cwd = _cwd_for_kind(scenario, tmp_path, cwd_kind)

    result = _run_af("read", "STW-0001", "--all", cwd=cwd, home=tmp_path)

    assert result.returncode != 0
    assert result.stdout == ""
    assert "--root" in result.stderr
    assert "PREFIX-ACID" not in result.stderr
    assert result.stderr.count(str(scenario.root_a)) == 1
    assert result.stderr.count(str(scenario.root_b)) == 1
    assert "Traceback" not in result.stderr
