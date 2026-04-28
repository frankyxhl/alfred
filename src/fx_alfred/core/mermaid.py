"""Mermaid flowchart rendering for composed af plan output (FXA-2205 PR3).

Produces a ``flowchart TD`` string from composed SOP phases.  Pure text —
no external dependencies.

Design decisions:
- Node id format: ``S{phase}_{step}`` (underscore, Mermaid-safe).
- Node label format: ``[SOP-ID step-text]`` for rectangles,
  ``{SOP-ID step-text}`` for diamonds (gate steps).
- Step text is truncated to 60 characters (with ``...`` suffix) to keep
  diagram nodes readable.  60 was chosen as a balance between information
  density and Mermaid renderer width — most steps fit in ~40 chars, and
  truncation only triggers on unusually verbose step descriptions.
- Special characters (brackets, braces, quotes) in step text are stripped
  to avoid breaking Mermaid syntax.  Mermaid has limited escape support,
  so removal is safer than escaping.
- Loop conditions longer than 40 characters are replaced with ``yes`` to
  keep edge labels legible.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from fx_alfred.core.workflow import LoopSignature

if TYPE_CHECKING:
    from fx_alfred.core.phases import PhaseDict, StepDict

# Maximum label length before truncation (chars).
_MAX_LABEL_LEN = 60

# Maximum loop condition label length before fallback to "yes".
_MAX_CONDITION_LEN = 40

# Characters that break Mermaid node label syntax or add visual noise.
# Includes * to strip markdown bold/italic formatting from SOP step text.
_MERMAID_UNSAFE_RE = re.compile(r'[\[\]{}()"\'`#;|<>*]')


def _sanitize_label(text: str) -> str:
    """Strip Mermaid-unsafe characters and truncate to ``_MAX_LABEL_LEN``."""
    clean = _MERMAID_UNSAFE_RE.sub("", text)
    clean = clean.strip()
    if len(clean) > _MAX_LABEL_LEN:
        clean = clean[: _MAX_LABEL_LEN - 3] + "..."
    return clean


def _sanitize_condition(condition: str) -> str:
    """Sanitize a loop condition label for Mermaid edge text."""
    clean = _MERMAID_UNSAFE_RE.sub("", condition).strip()
    if len(clean) > _MAX_CONDITION_LEN:
        return "yes"
    return clean


def _node_id(phase: int, step: int) -> str:
    """Build Mermaid-safe node identifier ``S{phase}_{step}``."""
    return f"S{phase}_{step}"


def render_mermaid(phases: list[PhaseDict]) -> str:
    """Render a Mermaid ``flowchart TD`` string from composed phases.

    Parameters
    ----------
    phases:
        List of phase dicts, each with keys:
        - ``sop_id`` (str): SOP identifier, e.g. ``"COR-1602"``.
        - ``steps`` (list[dict]): each ``{"index": int, "text": str, "gate": bool}``.
        - ``loops`` (list[LoopSignature]): loop metadata for this phase.

    Returns
    -------
    str
        Bare ``flowchart TD\\n  ...`` with no fence markers.
    """
    if not phases:
        return "flowchart TD"

    lines: list[str] = ["flowchart TD"]

    # Detect any cross-SOP loop across the whole composition so we can emit
    # exactly one omission comment (FXA-2218 Commit 5 — Mermaid is ASCII-only
    # for cross-SOP edges in this release).
    has_cross_sop_loop = any(
        not isinstance(lp.to_step, int)
        for phase in phases
        for lp in phase.get("loops", [])
    )
    if has_cross_sop_loop:
        lines.append(
            "  %% (cross-SOP loops omitted — Mermaid layout is ASCII-only in this release)"
        )

    prev_last_node_id: str | None = None

    for phase_idx, phase in enumerate(phases, start=1):
        sop_id: str = phase["sop_id"]
        steps: list[StepDict] = phase["steps"]
        loops: list[LoopSignature] = phase.get("loops", [])

        if not steps:
            continue

        # (No per-step dict here — iterating `loops` directly below avoids
        # silently dropping a loop when two share the same from_step, e.g.
        # one intra-SOP retry plus one cross-SOP escalation from the same
        # gate step. PR #59 Codex review P2.)

        # Build node definitions and forward edges
        prev_node_id: str | None = None

        for step in steps:
            step_idx: int = step["index"]
            text: str = step["text"]
            gate: bool = step["gate"]

            # Empty default keeps legacy plain steps byte-identical to pre-Phase-7.
            nid = f"{_node_id(phase_idx, step_idx)}{step.get('sub_branch', '')}"
            label = _sanitize_label(f"{sop_id} {text}")

            # Choose shape: diamond for gates, rectangle for regular steps
            if gate:
                node_def = f"{nid}{{{label}}}"
            else:
                node_def = f"{nid}[{label}]"

            if prev_node_id is not None:
                # Forward edge from previous step
                lines.append(f"  {prev_node_id} --> {node_def}")
            elif prev_last_node_id is not None:
                # Phase-to-phase transition edge
                lines.append(f"  {prev_last_node_id} --> {node_def}")
            else:
                # First node in the entire graph — just define it
                lines.append(f"  {node_def}")

            prev_node_id = nid

        # Record last node of this phase for phase-to-phase edge
        if prev_node_id is not None:
            prev_last_node_id = prev_node_id

        # Build int→first-sibling-letter map for this phase so loop edges
        # can anchor to a real node when from_step/to_step is a sub-stepped
        # integer (FXA-2227 Phase 7 phantom-node fix).  Only the first
        # occurrence of each integer with a sub_branch key is recorded.
        int_to_first_sibling_letter: dict[int, str] = {}
        for step in steps:
            idx = step["index"]
            letter = step.get("sub_branch", "")
            if letter and idx not in int_to_first_sibling_letter:
                int_to_first_sibling_letter[idx] = letter

        # Integers that have a plain (non-sub-branched) step.  When a plain
        # node co-exists with sub-stepped siblings at the same integer, a loop
        # targeting that integer should land on the plain node, not the first
        # sibling (Codex P2 fix).
        has_plain_step: set[int] = {
            step["index"] for step in steps if "sub_branch" not in step
        }

        def _suffix_for(int_step: int) -> str:
            if int_step in has_plain_step:
                return ""  # plain node exists — preserve explicit endpoint
            return int_to_first_sibling_letter.get(int_step, "")

        # Dashed back-edges for every intra-SOP loop (cross-SOP loops —
        # string `to_step` — are skipped; Mermaid layout is ASCII-only in
        # FXA-2218; see PRP Component 4). A user-facing omission comment
        # is emitted by the caller once per composition if any cross-SOP
        # loop exists. Iterate `loops` directly so multiple loops from the
        # same source step all render (PR #59 Codex review P2 fix).
        for lp in loops:
            if not isinstance(lp.to_step, int):
                continue
            from_nid = f"{_node_id(phase_idx, lp.from_step)}{_suffix_for(lp.from_step)}"
            to_nid = f"{_node_id(phase_idx, lp.to_step)}{_suffix_for(lp.to_step)}"
            cond = _sanitize_condition(lp.condition)
            lines.append(f"  {from_nid} -. {cond} .-> {to_nid}")

    return "\n".join(lines)
