# core/phases.py — Formal phase contract shared between ascii_graph and mermaid renderers.
#
# This module formalises what was an implicit list[dict] contract in PR 3.
# The TypedDict definitions provide compile-time type checking and documentation.

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from fx_alfred.core.workflow import BranchSignature, LoopSignature


class _StepRequired(TypedDict):
    """Required keys for StepDict — always present."""

    index: int
    text: str
    gate: bool


class StepDict(_StepRequired, total=False):
    """A single step within a phase.

    Attributes:
        index: 1-based within-SOP step index. For sub-stepped siblings
            (e.g. `3a`, `3b`), all siblings share the parent integer (3).
        text: Step text (already gate-markers-cleaned per PR 2).
        gate: True if this step is a gate (⚠️).
        sub_branch: Optional single letter (`"a"`, `"b"`, ...) for branch
            siblings under FXA-2226 ``Workflow branches:`` schema. The key
            is OMITTED for plain steps (Path B convention; never set to
            ``None`` or any sentinel). Use ``step.get("sub_branch", "")`` for
            deterministic format string concatenation.
    """

    sub_branch: str


class LoopDict(TypedDict):
    """Loop declaration (documentation-only shape mirror of ``LoopSignature``).

    Attributes:
        id: Loop identifier (e.g., "review-retry").
        from_step: Within-SOP 1-based index of the step that jumps back.
        to_step: Int for intra-SOP loops, or ``"PREFIX-ACID.step"`` string for
            cross-SOP loops (FXA-2218).
        max_iterations: Maximum number of loop iterations.
        condition: Condition text for the loop.
    """

    id: str
    from_step: int
    to_step: int | str
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
        branches: List of forward-branch declarations (FXA-2227 Path B).
            Optional; absent for legacy SOPs without ``Workflow branches:``.
    """

    provenance: str  # Optional - added by plan_cmd for ASCII rendering
    branches: list[BranchSignature]  # Optional — FXA-2227 Path B
