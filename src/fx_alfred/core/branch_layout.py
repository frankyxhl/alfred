"""Branch-group discovery — shared between renderers (FXA-2227 Phase 4+5).

Pure functions that take ``(steps, branches)`` and return identified branch
groups. Renderer-agnostic: returns indices + slices, leaves all formatting
decisions to the caller. Used by:

- ``core.dag_graph`` (nested-layout renderer, Phase 4)
- ``core.ascii_graph`` (flat renderer, Phase 5)

Why a shared module:
- Convergence-detection bugs need fixing in exactly one place.
- The "iterate until exhausted" multi-pass pattern is non-trivial; both
  renderers need the same advance-past-consumed-group semantics.
- Branch ordering invariants (process by ``from_step`` ascending) are
  centralized here so renderers can assume sorted output.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fx_alfred.core.phases import StepDict
    from fx_alfred.core.workflow import BranchSignature


@dataclass(frozen=True)
class BranchGroup:
    """An identified branch group inside a phase's step list.

    Attributes:
        parent_idx: 0-based position in ``steps`` of the parent step (whose
            ``index == branch_signature.from_step``).
        sibling_indices: 0-based positions in ``steps`` of the sibling
            sub-step entries. Always non-empty (a group with zero siblings
            is not a valid branch group and is not produced).
        convergence_idx: 0-based position in ``steps`` of the convergence
            step, or ``None`` for terminal/dangling branches.
        branch_signature: the matching :class:`BranchSignature`.
    """

    parent_idx: int
    sibling_indices: tuple[int, ...]
    convergence_idx: int | None
    branch_signature: "BranchSignature"

    @property
    def end_idx(self) -> int:
        """Index *after* the last step consumed by this group (parent +
        siblings + optional convergence). Use as the upper bound for
        ``skip_indices`` accounting."""
        if self.convergence_idx is not None:
            return self.convergence_idx + 1
        return self.sibling_indices[-1] + 1


def discover_branch_groups(
    steps: list["StepDict"],
    branches: list["BranchSignature"],
) -> list[BranchGroup]:
    """Discover all branch groups in ``steps``, in step order.

    Branches are processed in ``from_step`` ascending order regardless of
    their order in the input list — this prevents a list-order-dependent
    silent-misrender where a later-listed earlier-step branch would have
    its siblings consumed as a previous group's convergence.

    Convergence detection: the next plain (non-sub_branch) step *after*
    the siblings is the convergence — but NOT if that step is itself
    another branch's ``from_step``. Without this guard, two back-to-back
    branches in the same SOP would silently drop the second one.

    Returns groups sorted by ``parent_idx`` ascending. Returns ``[]`` if
    no branches are present or none match the step list.
    """
    if not branches:
        return []
    # Sort by from_step so the "next plain step is another branch's
    # parent" guard works regardless of list order in the input.
    sorted_branches = sorted(branches, key=lambda b: b.from_step)

    groups: list[BranchGroup] = []
    consumed: set[int] = set()
    for bsig in sorted_branches:
        from_step = bsig.from_step
        # Locate parent step (must be plain, not already consumed).
        parent_idx: int | None = None
        for i, s in enumerate(steps):
            if i not in consumed and s["index"] == from_step and "sub_branch" not in s:
                parent_idx = i
                break
        if parent_idx is None:
            continue
        # Walk forward: collect contiguous sub-step siblings.
        sibling_indices: list[int] = []
        i = parent_idx + 1
        while (
            i < len(steps)
            and steps[i].get("sub_branch") is not None
            and steps[i]["index"] == from_step + 1
        ):
            sibling_indices.append(i)
            i += 1
        if not sibling_indices:
            continue
        # Convergence: next plain step, unless it's another branch's parent.
        convergence_idx: int | None = None
        other_branch_starts = {b.from_step for b in sorted_branches if b is not bsig}
        if (
            i < len(steps)
            and "sub_branch" not in steps[i]
            and steps[i]["index"] not in other_branch_starts
        ):
            convergence_idx = i
        group = BranchGroup(
            parent_idx=parent_idx,
            sibling_indices=tuple(sibling_indices),
            convergence_idx=convergence_idx,
            branch_signature=bsig,
        )
        groups.append(group)
        consumed.add(parent_idx)
        consumed.update(sibling_indices)
        if convergence_idx is not None:
            consumed.add(convergence_idx)
    # Result already in from_step order (we sorted); but confirm by
    # parent_idx so callers can rely on positional order.
    groups.sort(key=lambda g: g.parent_idx)
    return groups


# Suppress the F-string-percent-formatting noise: this module's only
# external symbols are BranchGroup + discover_branch_groups.
__all__ = ["BranchGroup", "discover_branch_groups"]
