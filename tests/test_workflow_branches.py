"""Tests for FXA-2226 Workflow branches: schema parser.

Schema:

    Workflow branches:
      - from: 2
        to:
          - {id: 3a, label: pass}
          - {id: 3b, label: fail}
          - {id: 3c, label: escalate}

Parsed to:

    [BranchSignature(
        from_step=2,
        to=[
            BranchTarget(parent=3, branch="a", label="pass"),
            BranchTarget(parent=3, branch="b", label="fail"),
            BranchTarget(parent=3, branch="c", label="escalate"),
        ],
    )]
"""

from __future__ import annotations

import textwrap

from fx_alfred.core.parser import parse_metadata
from fx_alfred.core.workflow import (
    BranchSignature,
    BranchTarget,
    parse_workflow_branches,
    parse_workflow_loops,
)


def _doc(yaml_branches: str) -> str:
    """Build a minimal SOP-shaped document with the given Workflow branches: value."""
    return textwrap.dedent(
        f"""\
        # SOP-9999: Test

        **Status:** Active
        **Workflow branches:** {yaml_branches}

        ---

        ## Steps

        1. Decision setup
        2. Audit Ledger Gate
        3a. Pass branch
        3b. Fail branch
        3c. Escalate branch
        4. After

        ## Change History

        | Date | Change | By |
        |------|--------|----|
        | 2026-04-27 | Initial | Test |
        """
    )


def test_parse_simple_3way() -> None:
    """3-way branch parses to expected BranchSignature/BranchTarget shape."""
    body = _doc(
        "[{from: 2, to: [{id: 3a, label: pass}, {id: 3b, label: fail}, {id: 3c, label: escalate}]}]"
    )
    parsed = parse_metadata(body)
    branches = parse_workflow_branches(parsed)
    assert branches == [
        BranchSignature(
            from_step=2,
            to=(
                BranchTarget(parent=3, branch="a", label="pass"),
                BranchTarget(parent=3, branch="b", label="fail"),
                BranchTarget(parent=3, branch="c", label="escalate"),
            ),
        )
    ]


def test_parse_2way() -> None:
    """2-way branch."""
    body = _doc("[{from: 5, to: [{id: 6a, label: 'no'}, {id: 6b, label: 'yes'}]}]")
    parsed = parse_metadata(body)
    branches = parse_workflow_branches(parsed)
    assert len(branches) == 1
    sig = branches[0]
    assert sig.from_step == 5
    assert sig.to == (
        BranchTarget(parent=6, branch="a", label="no"),
        BranchTarget(parent=6, branch="b", label="yes"),
    )


def test_parse_branches_absent() -> None:
    """SOP without `Workflow branches:` returns []."""
    body = textwrap.dedent(
        """\
        # SOP-9999: Test

        **Status:** Active

        ---

        ## Steps

        1. First
        2. Second
        """
    )
    parsed = parse_metadata(body)
    assert parse_workflow_branches(parsed) == []


def test_branches_legacy_loops_unchanged() -> None:
    """SOPs without `Workflow branches:` parse loops byte-identically."""
    body = textwrap.dedent(
        """\
        # SOP-9999: Test

        **Status:** Active
        **Workflow loops:** [{id: retry, from: 3, to: 1, max_iterations: 3, condition: failed}]

        ---

        ## Steps

        1. Setup
        2. Validate
        3. Decision

        ## Change History

        | Date | Change | By |
        |------|--------|----|
        | 2026-04-27 | Initial | Test |
        """
    )
    parsed = parse_metadata(body)
    loops = parse_workflow_loops(parsed)
    assert len(loops) == 1
    assert loops[0].id == "retry"
    assert loops[0].from_step == 3
    assert loops[0].to_step == 1
    # Branches absent → empty.
    assert parse_workflow_branches(parsed) == []
