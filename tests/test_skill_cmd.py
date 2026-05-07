"""Tests for af skill command (FXA-2236)."""

from __future__ import annotations

import pytest


import json
from pathlib import Path

from click.testing import CliRunner

from fx_alfred.cli import cli


pytestmark = pytest.mark.cli


def _doc_content(
    type_code: str,
    acid: str,
    title: str,
    *,
    tags: str | None = None,
    task_tags: str | None = None,
    body: str = "Release packaging helper.",
) -> str:
    lines = [
        f"# {type_code}-{acid}: {title}",
        "",
        "**Applies to:** TST project",
        "**Last updated:** 2026-05-05",
        "**Last reviewed:** 2026-05-05",
        "**Status:** Active",
    ]
    if tags is not None:
        lines.append(f"**Tags:** {tags}")
    if task_tags is not None:
        lines.append(f"**Task tags:** {task_tags}")
    lines.extend(
        [
            "",
            "---",
            "",
            "## What Is It?",
            "",
            body,
            "",
            "---",
            "",
            "## Change History",
            "",
            "| Date | Change | By |",
            "|------|--------|----|",
            "| 2026-05-05 | Initial version | Test |",
        ]
    )
    return "\n".join(lines) + "\n"


def _project_doc(
    root: Path,
    prefix: str,
    acid: str,
    type_code: str,
    file_title: str,
    *,
    h1_title: str | None = None,
    tags: str | None = None,
    task_tags: str | None = None,
    body: str = "Release packaging helper.",
) -> Path:
    path = root / "rules" / f"{prefix}-{acid}-{type_code}-{file_title}.md"
    path.write_text(
        _doc_content(
            type_code,
            acid,
            h1_title or file_title.replace("-", " "),
            tags=tags,
            task_tags=task_tags,
            body=body,
        )
    )
    return path


def _user_doc(
    prefix: str,
    acid: str,
    type_code: str,
    file_title: str,
    *,
    h1_title: str | None = None,
    tags: str | None = None,
    task_tags: str | None = None,
) -> Path:
    user_dir = Path.home() / ".alfred"
    user_dir.mkdir(exist_ok=True)
    path = user_dir / f"{prefix}-{acid}-{type_code}-{file_title}.md"
    path.write_text(
        _doc_content(
            type_code,
            acid,
            h1_title or file_title.replace("-", " "),
            tags=tags,
            task_tags=task_tags,
        )
    )
    return path


def test_skill_list_returns_only_marked_ref_or_sop(sample_project):
    _project_doc(
        sample_project,
        "TST",
        "5001",
        "REF",
        "Skill-Release",
        h1_title="Skill: Release",
        tags="Skill, release",
        task_tags="release",
    )
    _project_doc(
        sample_project,
        "TST",
        "5002",
        "SOP",
        "Task-Tagged-Only",
        task_tags="release",
    )
    _project_doc(
        sample_project,
        "TST",
        "5003",
        "PRP",
        "Skill-But-Wrong-Type",
        tags="skill",
    )

    result = CliRunner().invoke(cli, ["--root", str(sample_project), "skill", "list"])

    assert result.exit_code == 0
    assert "TST-5001" in result.output
    assert "TST-5002" not in result.output
    assert "TST-5003" not in result.output


def test_skill_list_title_skill_without_tag_is_not_classified(sample_project):
    _project_doc(
        sample_project,
        "TST",
        "5001",
        "REF",
        "Skill-Release",
        h1_title="Skill: Release",
    )

    result = CliRunner().invoke(cli, ["--root", str(sample_project), "skill", "list"])

    assert result.exit_code == 0
    assert "TST-5001" not in result.output


def test_skill_list_task_json_scores_and_match_reasons(sample_project):
    _project_doc(
        sample_project,
        "TST",
        "5001",
        "REF",
        "Skill-Release-To-PyPI",
        h1_title="Skill: Release To PyPI",
        tags="skill, packaging",
        task_tags="release, pypi",
        body="Build and publish a package release.",
    )

    result = CliRunner().invoke(
        cli,
        [
            "--root",
            str(sample_project),
            "skill",
            "list",
            "--task",
            "release pypi",
            "--json",
        ],
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["schema_version"] == "1"
    assert len(data["results"]) == 1
    item = data["results"][0]
    assert item["id"] == "TST-5001"
    assert item["source"]["layer"] == "PRJ"
    assert item["score"] > 0
    assert "task_tags:release" in item["match_reasons"]


def test_skill_list_without_task_defaults_all_layers_and_null_scores(sample_project):
    _project_doc(
        sample_project,
        "TST",
        "5001",
        "REF",
        "Skill-Project",
        h1_title="Skill: Project",
        tags="skill",
    )
    _user_doc(
        "USR",
        "5002",
        "REF",
        "Skill-User",
        h1_title="Skill: User",
        tags="skill",
    )

    result = CliRunner().invoke(
        cli, ["--root", str(sample_project), "skill", "list", "--json"]
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    layers = [item["source"]["layer"] for item in data["results"]]
    assert "PRJ" in layers
    assert "USR" in layers
    assert all(item["score"] is None for item in data["results"])
    assert all(item["match_reasons"] == [] for item in data["results"])


def test_skill_list_layer_filter_returns_only_selected_layer(sample_project):
    _project_doc(
        sample_project,
        "TST",
        "5001",
        "REF",
        "Skill-Project",
        h1_title="Skill: Project",
        tags="skill",
    )
    _user_doc(
        "USR",
        "5002",
        "REF",
        "Skill-User",
        h1_title="Skill: User",
        tags="skill",
    )

    result = CliRunner().invoke(
        cli,
        ["--root", str(sample_project), "skill", "list", "--layer", "PRJ", "--json"],
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert [item["id"] for item in data["results"]] == ["TST-5001"]
    assert all(item["source"]["layer"] == "PRJ" for item in data["results"])


def test_skill_read_resolves_full_id(sample_project):
    _project_doc(
        sample_project,
        "TST",
        "5001",
        "REF",
        "Skill-Release-To-PyPI",
        h1_title="Skill: Release To PyPI",
        tags="skill, release, pypi",
    )

    result = CliRunner().invoke(
        cli,
        ["--root", str(sample_project), "skill", "read", "TST-5001", "--json"],
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["document"]["id"] == "TST-5001"


def test_skill_read_resolves_slug_and_json_content(sample_project):
    _project_doc(
        sample_project,
        "TST",
        "5001",
        "REF",
        "Skill-Release-To-PyPI",
        h1_title="Skill: Release To PyPI",
        tags="skill, release, pypi",
        task_tags="release",
    )

    result = CliRunner().invoke(
        cli,
        [
            "--root",
            str(sample_project),
            "skill",
            "read",
            "skill-release-to-pypi",
            "--json",
        ],
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["schema_version"] == "1"
    assert data["document"]["id"] == "TST-5001"
    assert data["document"]["tags"] == ["skill", "release", "pypi"]
    assert data["content"].startswith("# REF-5001")


def test_skill_read_acid_only_ambiguity_errors(sample_project):
    _project_doc(
        sample_project,
        "TST",
        "5007",
        "REF",
        "Skill-One",
        h1_title="Skill: One",
        tags="skill",
    )
    _project_doc(
        sample_project,
        "ABC",
        "5007",
        "REF",
        "Skill-Two",
        h1_title="Skill: Two",
        tags="skill",
    )

    result = CliRunner().invoke(
        cli, ["--root", str(sample_project), "skill", "read", "5007"]
    )

    assert result.exit_code != 0
    assert "ambiguous" in result.output.lower()


def test_skill_read_not_found_errors(sample_project):
    result = CliRunner().invoke(
        cli,
        ["--root", str(sample_project), "skill", "read", "missing-skill"],
    )

    assert result.exit_code != 0
    assert "No skill found: missing-skill" in result.output


def test_skill_commands_do_not_import_agent_helpers(sample_project):
    helper_dir = sample_project / ".alfred"
    helper_dir.mkdir()
    (helper_dir / "agent_helpers.py").write_text('raise RuntimeError("imported")\n')
    _project_doc(
        sample_project,
        "TST",
        "5001",
        "REF",
        "Skill-Release",
        h1_title="Skill: Release",
        tags="skill",
    )

    result = CliRunner().invoke(cli, ["--root", str(sample_project), "skill", "list"])

    assert result.exit_code == 0
    assert "TST-5001" in result.output
    assert "imported" not in result.output
