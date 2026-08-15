"""Regression guard for bundled Workflow-loops declarations (FXA-2326).

Locks in the outcome of the COR-1005 retrofit campaign (PRs #320–#323): every
bundled document that declares ``Workflow loops:`` must keep (a) a
parser-visible Steps section with the expected contiguous step count and (b)
its exact loop signatures, in declaration order.

Why order matters: ``af plan --todo`` currently collapses multiple loops
sharing a ``from`` step to the *last* declaration (issue #324), so COR-1617
deliberately lists ``iterate-round`` after ``replan-blocker``. A reorder would
silently hide the primary loop from checklist output.

Why step counts matter: COR-1617 shipped for months with a fenced step list
(``af plan`` extracted zero steps) and COR-1802's old ``### Step N —``
headings made the planner extract phantom sub-list steps — both regressions
this guard would have caught on the first CI run.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fx_alfred.core.parser import MalformedDocumentError, parse_metadata
from fx_alfred.core.steps import extract_steps_section, parse_top_level_step_indices
from fx_alfred.core.workflow import parse_workflow_loops

pytestmark = pytest.mark.docs

_RULES = Path(__file__).resolve().parents[1] / "src" / "fx_alfred" / "rules"

# doc filename -> (expected top-level step count,
#                  [(loop id, from, to, max_iterations), ...] in declaration order)
EXPECTED: dict[str, tuple[int, list[tuple[str, int, int | str, int]]]] = {
    "COR-1005-SOP-Engineer-Workflow-Loops.md": (
        8,
        [("fix-authoring", 7, 5, 3)],
    ),
    "COR-1602-SOP-Workflow-Multi-Model-Parallel-Review.md": (
        8,
        [("review-retry", 7, 3, 3)],
    ),
    "COR-1600-SOP-Workflow-Direct-Review-Loop.md": (
        8,
        [("revise-resend", 6, 5, 5)],
    ),
    "COR-1601-SOP-Workflow-Leader-Mediated-Review-Loop.md": (
        8,
        [("revise-cycle", 7, 4, 5)],
    ),
    "COR-1612-SOP-Respond-To-PR-Review-Comments.md": (
        8,
        [("fix-round", 6, 1, 10)],
    ),
    "COR-1615-SOP-GitHub-App-PR-Review-Bot-Loop.md": (
        12,
        [("restart-on-push", 11, 1, 10), ("poll-wait", 8, 6, 10)],
    ),
    "COR-1802-SOP-Build-Weighted-Decision-Matrix.md": (
        8,
        [("anchor-rework", 4, 2, 2), ("recalibrate", 5, 2, 2)],
    ),
    "COR-1617-SOP-Multi-Agent-Workflow-Loop.md": (
        12,
        # iterate-round MUST stay last (issue #324 --todo collapse mitigation).
        [("replan-blocker", 9, 4, 2), ("iterate-round", 9, 8, 13)],
    ),
}


@pytest.mark.parametrize("filename", sorted(EXPECTED))
def test_loop_declaration_signature(filename: str) -> None:
    """Each loop-declaring doc keeps its exact loop signatures, in order."""
    parsed = parse_metadata((_RULES / filename).read_text(encoding="utf-8"))
    expected_loops = EXPECTED[filename][1]
    actual = [
        (loop.id, loop.from_step, loop.to_step, loop.max_iterations)
        for loop in parse_workflow_loops(parsed)
    ]
    assert actual == expected_loops


@pytest.mark.parametrize("filename", sorted(EXPECTED))
def test_steps_extraction_count(filename: str) -> None:
    """Each loop-declaring doc keeps a parser-visible, contiguous Steps section."""
    parsed = parse_metadata((_RULES / filename).read_text(encoding="utf-8"))
    section = extract_steps_section(parsed.body)
    assert section is not None, f"{filename}: no parser-recognised Steps section"
    expected_count = EXPECTED[filename][0]
    indices = parse_top_level_step_indices(section)
    assert indices == frozenset(range(1, expected_count + 1)), (
        f"{filename}: extracted step indices {sorted(indices)} != 1..{expected_count}"
    )


def test_expected_covers_every_declaring_doc() -> None:
    """No bundled doc declares Workflow loops without being pinned here."""
    declaring: set[str] = set()
    for p in sorted(_RULES.glob("*.md")):
        try:
            parsed = parse_metadata(p.read_text(encoding="utf-8"))
        except MalformedDocumentError:
            # Non-COR-format bundled files (e.g. INIT.md) cannot declare loops.
            continue
        if any(
            mf.key == "Workflow loops" and mf.value.strip()
            for mf in parsed.metadata_fields
        ):
            declaring.add(p.name)
    assert declaring == set(EXPECTED)
