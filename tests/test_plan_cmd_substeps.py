"""Tests for FXA-2226 Phase 3 — plan_cmd.py todo[].index format extension.

Phase 3 extends the dotted ``todo[].index`` format from
``"phase.step"`` (e.g. ``"1.1"``) to ``"phase.stepLetter"`` (e.g.
``"2.3a"``) for sub-stepped plans. The change is at
``plan_cmd.py:286`` and ``:352``: the format string adds
``step.get('sub_branch', '')`` so plain steps emit unchanged and
sub-steps emit with the suffix appended.

Plain plans must remain byte-identical to v1.7.1 for the
``todo[].index`` field (legacy compatibility).
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from fx_alfred.cli import cli


def _create_sop_with_branches(rules_dir: Path) -> Path:
    """Create a SOP that uses Workflow branches: schema (sub-stepped)."""
    filename = "TST-9001-SOP-Branchy.md"
    content = """# TST-9001: Branchy

**Applies to:** Test
**Status:** Active
**Workflow branches:** [{from: 2, to: [{id: 3a, label: pass}, {id: 3b, label: fail}]}]
---
## What Is It?
A test SOP exercising Workflow branches.
## Steps
1. Setup
2. Decision
3a. Pass branch
3b. Fail branch
4. Continue
"""
    filepath = rules_dir / filename
    filepath.write_text(content)
    return filepath


def _create_sop_legacy(rules_dir: Path) -> Path:
    filename = "TST-9002-SOP-Legacy.md"
    content = """# TST-9002: Legacy

**Applies to:** Test
**Status:** Active
---
## What Is It?
A test SOP without branches.
## Steps
1. Alpha
2. Bravo
3. Charlie
"""
    filepath = rules_dir / filename
    filepath.write_text(content)
    return filepath


def test_todo_index_substep_format_in_json(sample_project, monkeypatch):
    """Sub-stepped plan emits todo[].index = '<phase>.3a' for sub-steps.

    Bypasses the renderer-readiness gate (Path B intermediate-state guardrail)
    because this test verifies the format extension that ships in CHG-2227.
    """
    rules_dir = sample_project / "rules"
    _create_sop_with_branches(rules_dir)
    monkeypatch.chdir(sample_project)
    monkeypatch.setattr("fx_alfred.commands.plan_cmd._BRANCHES_RENDERER_READY", True)
    result = CliRunner().invoke(cli, ["plan", "TST-9001", "--todo", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    todo = data.get("todo", [])
    indices = [item.get("index") for item in todo]
    # Plain steps share `phase.N` form; sub-steps share `phase.Na` form.
    assert any(idx.endswith(".3a") for idx in indices), (
        f"expected at least one '*.3a' index, got {indices}"
    )
    assert any(idx.endswith(".3b") for idx in indices)
    # All indices remain strings (Path B contract).
    assert all(isinstance(idx, str) for idx in indices)


def test_todo_index_legacy_unchanged_in_json(sample_project, monkeypatch):
    """All-integer SOP emits todo[].index identical to pre-CHG format."""
    rules_dir = sample_project / "rules"
    _create_sop_legacy(rules_dir)
    monkeypatch.chdir(sample_project)
    result = CliRunner().invoke(cli, ["plan", "TST-9002", "--todo", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    todo = data.get("todo", [])
    indices = [item.get("index") for item in todo]
    # Legacy SOPs: every index matches `^\d+\.\d+$` exactly (no suffix).
    import re

    legacy_pattern = re.compile(r"^\d+\.\d+$")
    for idx in indices:
        assert legacy_pattern.match(idx), (
            f"legacy plan emitted non-legacy index {idx!r} — Path B byte-identity violated"
        )


def test_phases_steps_index_int_unchanged(sample_project, monkeypatch):
    """phases[].steps[].index remains int (Path B contract)."""
    rules_dir = sample_project / "rules"
    _create_sop_with_branches(rules_dir)
    monkeypatch.chdir(sample_project)
    monkeypatch.setattr("fx_alfred.commands.plan_cmd._BRANCHES_RENDERER_READY", True)
    result = CliRunner().invoke(cli, ["plan", "TST-9001", "--todo", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    phases = data.get("phases", [])
    assert phases
    for ph in phases:
        for step in ph.get("steps", []):
            assert isinstance(step["index"], int), (
                f"Path B violated: phases[].steps[].index must stay int, got {type(step['index']).__name__}"
            )


def test_plan_blocked_by_gate_when_branches_present(sample_project, monkeypatch):
    """Per PR #68 Gemini F2: `af plan` must reject branchy SOPs while gate is closed.

    Otherwise the renderer-readiness gate is `af validate`-only and `af plan`
    silently emits sub-stepped surface (`"index": "1.3a"`, ASCII collisions)
    before CHG-2227 ships. The test fixture's `_BRANCHES_RENDERER_READY` is
    False at module level (Path B default), so this should fail with a
    ClickException directing the author to wait for CHG-2227.
    """
    rules_dir = sample_project / "rules"
    _create_sop_with_branches(rules_dir)
    monkeypatch.chdir(sample_project)
    # NO monkeypatch of the flag — exercise the default-closed gate.
    result = CliRunner().invoke(cli, ["plan", "TST-9001", "--todo", "--json"])
    assert result.exit_code != 0, (
        "Expected af plan to reject Workflow branches: while gate closed; "
        f"got exit 0 with output:\n{result.output}"
    )
    assert "CHG-2227" in result.output


def test_plan_gate_fires_on_empty_workflow_branches_field(sample_project, monkeypatch):
    """Per Codex PR #68 R2 review: ``Workflow branches: []`` triggers the
    plan-time gate too.

    Pre-fix, the plan_cmd.py gate only fired when `parse_workflow_branches`
    returned a non-empty list — an SOP authoring `Workflow branches: []`
    would sneak past. Spec: MUST NOT author the field at all.
    """
    rules_dir = sample_project / "rules"
    filename = "TST-9003-SOP-EmptyBranches.md"
    content = """# TST-9003: Empty Branches

**Applies to:** Test
**Status:** Active
**Workflow branches:** []
---
## What Is It?
A test SOP authoring an empty Workflow branches: list.
## Steps
1. Setup
2. Done
"""
    (rules_dir / filename).write_text(content)
    monkeypatch.chdir(sample_project)
    # NO monkeypatch of the flag — exercise default-closed gate.
    result = CliRunner().invoke(cli, ["plan", "TST-9003", "--todo", "--json"])
    assert result.exit_code != 0, (
        f"Expected af plan to reject empty Workflow branches: field; "
        f"got exit 0:\n{result.output}"
    )
    assert "CHG-2227" in result.output


def test_plan_gate_fires_on_undeclared_substep_lines(sample_project, monkeypatch):
    """Per Codex PR #68 R3 inline review: gate must also fire when an author
    writes `3a./3b.` lines directly in ## Steps WITHOUT the Workflow branches:
    metadata field.

    Pre-fix, the gate fired only on metadata field presence. An author could
    bypass it by writing sub-step lines in the body — Phase 1's
    `_parse_steps_for_json` would extract `sub_branch="a"` from `3a.`, and
    Phase 3's `dotted` format would emit `"1.3a"` in `todo[].index`,
    leaking Path B surface before the renderer ships.
    """
    rules_dir = sample_project / "rules"
    filename = "TST-9004-SOP-UndeclaredSubsteps.md"
    content = """# TST-9004: Undeclared Substeps

**Applies to:** Test
**Status:** Active
---
## What Is It?
A test SOP with sub-step lines in body but no Workflow branches: metadata.
## Steps
1. Setup
2. Decision
3a. Bypass-attempt branch a
3b. Bypass-attempt branch b
4. After
"""
    (rules_dir / filename).write_text(content)
    monkeypatch.chdir(sample_project)
    # NO monkeypatch of the flag — exercise default-closed gate.
    result = CliRunner().invoke(cli, ["plan", "TST-9004", "--todo", "--json"])
    assert result.exit_code != 0, (
        f"Expected af plan to reject undeclared sub-step lines; "
        f"got exit 0:\n{result.output}"
    )
    assert "CHG-2227" in result.output


def test_plan_gate_does_not_trip_on_indented_substep_line(sample_project, monkeypatch):
    """Per Codex PR #68 R4 inline review: indented `3a.` lines (sub-items
    nested under another step) MUST NOT trip the gate.

    `has_top_level_substep_lines` scans flush-left only; sub-items at any
    indent level are ignored. This SOP has no real sub-step surface, so
    `af plan` should succeed despite the `3a.` text.
    """
    rules_dir = sample_project / "rules"
    filename = "TST-9005-SOP-IndentedSubstep.md"
    content = """# TST-9005: Indented Substep

**Applies to:** Test
**Status:** Active
---
## What Is It?
A test SOP with `3a.` text appearing only as an indented sub-item.
## Steps
1. Setup
2. Decision
3. Discuss the format. Maybe label paths:
    3a. like this (indented sub-item, not a top-level step)
    3b. or this
4. Continue
"""
    (rules_dir / filename).write_text(content)
    monkeypatch.chdir(sample_project)
    # Default-closed gate; should NOT fire because the only `3a./3b.` lines
    # are indented (sub-items, not top-level).
    result = CliRunner().invoke(cli, ["plan", "TST-9005", "--todo", "--json"])
    assert result.exit_code == 0, (
        f"Indented sub-item lines should NOT trip the gate; got exit "
        f"{result.exit_code}:\n{result.output}"
    )


def test_plan_gate_does_not_trip_on_fenced_substep_line(sample_project, monkeypatch):
    """Per Codex PR #68 R4 inline review: `3a.` lines inside fenced code
    blocks MUST NOT trip the gate (they're examples, not authored steps).
    """
    rules_dir = sample_project / "rules"
    filename = "TST-9006-SOP-FencedSubstep.md"
    content = """# TST-9006: Fenced Substep

**Applies to:** Test
**Status:** Active
---
## What Is It?
A test SOP demonstrating substep syntax inside a code fence (example only).
## Steps
1. Setup
2. Decision
3. Show what FXA-2226 substep syntax looks like:
```
3a. Pass branch
3b. Fail branch
```
4. Continue
"""
    (rules_dir / filename).write_text(content)
    monkeypatch.chdir(sample_project)
    result = CliRunner().invoke(cli, ["plan", "TST-9006", "--todo", "--json"])
    assert result.exit_code == 0, (
        f"Fenced sub-step example should NOT trip the gate; got exit "
        f"{result.exit_code}:\n{result.output}"
    )


def test_plan_human_branchy_renders_substeps(sample_project, monkeypatch):
    """Per PR #68 Gemini F3: `af plan --human` must NOT silently drop 3a/3b.

    Pre-fix, `_parse_numbered_items` regex was `^(?:###\\s+)?(\\d+)\\.\\s+`
    which only matched plain `3.` lines, dropping `3a/3b`. Test asserts the
    human output for a branchy SOP includes both sub-step entries.
    """
    rules_dir = sample_project / "rules"
    _create_sop_with_branches(rules_dir)
    monkeypatch.chdir(sample_project)
    monkeypatch.setattr("fx_alfred.commands.plan_cmd._BRANCHES_RENDERER_READY", True)
    result = CliRunner().invoke(cli, ["plan", "TST-9001", "--human"])
    assert result.exit_code == 0, result.output
    # Sub-step lines must appear in the human checklist (preceded by "3a." / "3b.").
    assert "3a." in result.output, (
        f"--human output silently dropped sub-step 3a:\n{result.output}"
    )
    assert "3b." in result.output


def test_phases_steps_sub_branch_emitted(sample_project, monkeypatch):
    """phases[].steps[].sub_branch is emitted ONLY for sub-stepped entries."""
    rules_dir = sample_project / "rules"
    _create_sop_with_branches(rules_dir)
    monkeypatch.chdir(sample_project)
    monkeypatch.setattr("fx_alfred.commands.plan_cmd._BRANCHES_RENDERER_READY", True)
    result = CliRunner().invoke(cli, ["plan", "TST-9001", "--todo", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    phases = data.get("phases", [])
    assert phases
    seen_sub_branches: list[str] = []
    seen_plain_steps_with_no_sub_branch = 0
    for ph in phases:
        for step in ph.get("steps", []):
            if "sub_branch" in step:
                seen_sub_branches.append(step["sub_branch"])
            else:
                seen_plain_steps_with_no_sub_branch += 1
    # Branchy SOP: should have at least 'a' and 'b' sub_branch entries.
    assert sorted(seen_sub_branches) == ["a", "b"], (
        f"expected sub_branches ['a','b'], got {seen_sub_branches}"
    )
    # Plain steps must NOT carry sub_branch key (Path B convention).
    assert seen_plain_steps_with_no_sub_branch >= 1
