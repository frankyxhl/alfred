# core/phases.py — Formal phase contract shared between ascii_graph and mermaid renderers.
#
# This module formalises what was an implicit list[dict] contract in PR 3.
# The TypedDict definitions provide compile-time type checking and documentation.

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from fx_alfred.core.workflow import LoopSignature


class StepDict(TypedDict):
    """A single step within a phase.

    Attributes:
        index: 1-based within-SOP step index.
        text: Step text (already gate-markers-cleaned per PR 2).
        gate: True if this step is a gate (⚠️).
    """

    index: int
    text: str
    gate: bool


class LoopDict(TypedDict):
    """Intra-SOP loop declaration.

    Attributes:
        id: Loop identifier (e.g., "review-retry").
        from_step: Within-SOP 1-based index of the step that jumps back.
        to_step: Within-SOP 1-based index of the loop target.
        max_iterations: Maximum number of loop iterations.
        condition: Condition text for the loop.
    """

    id: str
    from_step: int
    to_step: int
    max_iterations: int
    condition: str


class _PhaseRequired(TypedDict):
    """Required keys for PhaseDict — always present.

    Note: ``loops`` is typed as ``list[LoopSignature]`` because the runtime
    producer (``workflow.parse_workflow_loops``) always yields dataclass
    instances, not plain dicts.  ``LoopDict`` is retained above as a
    documentation-only shape mirror used by earlier design notes.
    """

    sop_id: str
    steps: list[StepDict]
    loops: list[LoopSignature]


class PhaseDict(_PhaseRequired, total=False):
    """A single phase in the composition.

    Required keys (sop_id, steps, loops) are yielded by
    ``_build_mermaid_phases`` in plan_cmd. Optional provenance is added
    by the --task composition layer.

    Attributes:
        sop_id: Full PREFIX-ACID form (e.g., "COR-1602").
        steps: List of steps in this phase.
        loops: List of intra-SOP loops.
        provenance: How this SOP was selected ("always" | "auto" | "explicit").
    """

    provenance: str  # Optional - added by plan_cmd for ASCII rendering
