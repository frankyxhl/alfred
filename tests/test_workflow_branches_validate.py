"""Tests for FXA-2226 Phase 2 — validate_branches + renderer-readiness gate.

The gate (`_BRANCHES_RENDERER_READY = False`) blocks production SOPs from
authoring `Workflow branches:` until CHG-2227 ships the renderer. CHG-2227
Phase 8a flips the flag to `True` as a separately-reviewable commit.
"""

from __future__ import annotations

import textwrap

import pytest

from fx_alfred.core.parser import MalformedDocumentError, parse_metadata
from fx_alfred.core.workflow import (
    parse_workflow_branches,
    validate_branches,
    _BRANCHES_RENDERER_READY,
)


def _doc(yaml_branches: str, steps_section: str) -> str:
    # Build without textwrap.dedent — interpolating multiline `steps_section`
    # defeats common-prefix detection.
    return (
        "# SOP-9999: Test\n"
        "\n"
        "**Status:** Active\n"
        f"**Workflow branches:** {yaml_branches}\n"
        "\n"
        "---\n"
        "\n"
        "## Steps\n"
        "\n"
        f"{steps_section}\n"
        "## Change History\n"
        "\n"
        "| Date | Change | By |\n"
        "|------|--------|----|\n"
        "| 2026-04-27 | Initial | Test |\n"
    )


def test_renderer_readiness_gate_default_blocks() -> None:
    """Default `_BRANCHES_RENDERER_READY = False` makes ANY Workflow branches:
    SOP fail validation with a clear message instructing authors to wait for
    CHG-2227.
    """
    assert _BRANCHES_RENDERER_READY is False, (
        "CHG-2226 ships with the gate CLOSED; CHG-2227 Phase 8a flips it open"
    )

    body = _doc(
        "[{from: 2, to: [{id: 3a, label: pass}, {id: 3b, label: fail}]}]",
        "1. Setup\n2. Decision\n3a. A path\n3b. B path\n4. After\n",
    )
    parsed = parse_metadata(body)
    branches = parse_workflow_branches(parsed)
    errors = validate_branches(parsed, branches)
    assert len(errors) >= 1
    assert any("renderer support is not yet shipped" in e.msg for e in errors)
    assert any("CHG-2227" in e.msg for e in errors)


def test_branches_from_must_be_plain_int_not_substep_only() -> None:
    """Per PR #68 Codex F1: `from: 2` requires a BARE `2.` line in ## Steps.

    A SOP with `2a.`/`2b.` lines but no plain `2.` line should NOT satisfy
    `from: 2` — even though `_parse_step_indices` injects parent integer 2
    from the sub-step lines (Phase 1 design). Path B keeps step_indices
    int-stable, but the `from` validator must only accept *plain* integer
    parents.

    Note: this fixture is somewhat artificial because in practice any
    branchy SOP authored as `Workflow branches: from: 2` would have a
    bare `2.` decision step. The defensive check guards against the
    silent false-negative class.
    """
    body = _doc(
        "[{from: 2, to: [{id: 3a, label: pass}, {id: 3b, label: fail}]}]",
        "1. Setup\n2a. ORPHAN-as-from\n2b. ORPHAN\n3a. Pass\n3b. Fail\n",
    )
    parsed = parse_metadata(body)
    branches = parse_workflow_branches(parsed)
    errors = validate_branches(parsed, branches, _gate_open_for_test=True)
    # Should reject `from: 2` because there's no bare `2.` line — only `2a/2b`.
    assert any("from = 2" in e.msg for e in errors)


def test_branches_from_must_exist() -> None:
    """`from` referencing a nonexistent step rejected."""
    body = _doc(
        "[{from: 99, to: [{id: 100a, label: x}, {id: 100b, label: y}]}]",
        "1. A\n2. B\n",
    )
    parsed = parse_metadata(body)
    branches = parse_workflow_branches(parsed)
    errors = validate_branches(parsed, branches, _gate_open_for_test=True)
    assert any("from" in e.msg and "99" in e.msg for e in errors)


def test_branches_to_must_exist() -> None:
    """`to.id` referencing a non-existent sub-step rejected."""
    body = _doc(
        "[{from: 2, to: [{id: 3a, label: pass}, {id: 3z, label: fail}]}]",
        "1. A\n2. B\n3a. Has it\n4. After\n",  # no 3z
    )
    parsed = parse_metadata(body)
    branches = parse_workflow_branches(parsed)
    errors = validate_branches(parsed, branches, _gate_open_for_test=True)
    assert any("3z" in e.msg for e in errors)


def test_branches_to_parent_must_match_from_plus_one() -> None:
    """`from: 2` requires `to` siblings to use parent 3, not 4."""
    body = _doc(
        "[{from: 2, to: [{id: 4a, label: x}, {id: 4b, label: y}]}]",
        "1. A\n2. B\n4a. wrong parent\n4b. wrong parent\n",
    )
    parsed = parse_metadata(body)
    branches = parse_workflow_branches(parsed)
    errors = validate_branches(parsed, branches, _gate_open_for_test=True)
    assert any("from + 1" in e.msg or "must be 3" in e.msg for e in errors)


def test_branches_substep_id_malformed_raises_at_parse() -> None:
    """`3aa` rejected at PARSE time (regex \\d+[a-z], not \\d+[a-z]+)."""
    body = _doc(
        "[{from: 2, to: [{id: 3aa, label: x}, {id: 3b, label: y}]}]",
        "1. A\n2. B\n",
    )
    parsed = parse_metadata(body)
    with pytest.raises(MalformedDocumentError, match=r"3aa"):
        parse_workflow_branches(parsed)


def test_branches_orphan_substep_rejected() -> None:
    """A sub-step in ## Steps not declared in any branches.to is an orphan."""
    body = _doc(
        "[{from: 2, to: [{id: 3a, label: x}]}]",
        "1. A\n2. B\n3a. Declared\n3b. ORPHAN — not in branches.to\n4. After\n",
    )
    parsed = parse_metadata(body)
    branches = parse_workflow_branches(parsed)
    errors = validate_branches(parsed, branches, _gate_open_for_test=True)
    assert any("3b" in e.msg and "orphan" in e.msg.lower() for e in errors)


def test_branches_siblings_must_be_contiguous() -> None:
    """`3a, 4, 3b` (integer step interleaved between siblings) rejected."""
    body = _doc(
        "[{from: 2, to: [{id: 3a, label: x}, {id: 3b, label: y}]}]",
        "1. A\n2. B\n3a. First\n4. WRONG — interleaved\n3b. Second\n",
    )
    parsed = parse_metadata(body)
    branches = parse_workflow_branches(parsed)
    errors = validate_branches(parsed, branches, _gate_open_for_test=True)
    assert any("contiguous" in e.msg.lower() for e in errors)


def test_branches_valid_3way_passes_when_gate_open() -> None:
    """Well-formed 3-way branches pass validation when gate is open."""
    body = _doc(
        "[{from: 2, to: [{id: 3a, label: pass}, {id: 3b, label: fail}, {id: 3c, label: escalate}]}]",
        "1. Setup\n2. Decision\n3a. Pass\n3b. Fail\n3c. Escalate\n4. Continue\n",
    )
    parsed = parse_metadata(body)
    branches = parse_workflow_branches(parsed)
    errors = validate_branches(parsed, branches, _gate_open_for_test=True)
    assert errors == []


def test_gate_fires_on_empty_field_authored() -> None:
    """Per Codex PR #68 R2 review: ``Workflow branches: []`` (or ``null``)
    must trigger the gate too.

    Spec is "MUST NOT author this field until CHG-2227 lands" — authoring an
    empty list still authors the field. Pre-fix, the gate only fired when
    `parse_workflow_branches()` returned a non-empty list, so an SOP could
    sneak past the gate by writing `Workflow branches: []`.
    """
    body = _doc("[]", "1. A\n2. B\n3. C\n")
    parsed = parse_metadata(body)
    branches = parse_workflow_branches(parsed)
    assert branches == []  # parsed-empty
    # Gate should still fire on field presence even though branches=[].
    errors = validate_branches(parsed, branches)
    assert any("renderer support is not yet shipped" in e.msg for e in errors)


def test_branches_legacy_loops_unaffected() -> None:
    """SOPs without Workflow branches: produce no branch errors regardless of gate."""
    body = textwrap.dedent(
        """\
        # SOP-9999: Test

        **Status:** Active
        **Workflow loops:** [{id: retry, from: 3, to: 1, max_iterations: 3, condition: failed}]

        ---

        ## Steps

        1. A
        2. B
        3. C

        ## Change History

        | Date | Change | By |
        |------|--------|----|
        | 2026-04-27 | Initial | Test |
        """
    )
    parsed = parse_metadata(body)
    branches = parse_workflow_branches(parsed)
    assert branches == []
    errors = validate_branches(parsed, branches)
    assert errors == []
