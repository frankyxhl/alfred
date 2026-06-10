"""Shared step-parsing helpers for SOP bodies.

Extracted from commands/plan_cmd.py to avoid commands -> commands imports
when validate_cmd.py needs the same parser (FXA-2218 CHG Commit 1).
"""

from __future__ import annotations

import re

from fx_alfred.core.parser import extract_section, iter_lines_with_fence_state
from fx_alfred.core.phases import StepDict

# Heading search order for the steps section. SOPs historically used one
# of several heading names before ``## Steps`` was standardised; the
# planner accepts all of them, and cross-SOP validation (PR #59 Codex P2)
# must agree with that — otherwise D3 would reject a SOP the planner can
# render.
_STEP_HEADINGS = ("Steps", "Rule", "Rules", "Concepts")


def extract_steps_section(body: str) -> str | None:
    """Return the body of the first recognised steps-like section, else ``None``.

    Matches the planner's section-resolution logic (``plan_cmd._STEP_HEADINGS``)
    exactly so validation and rendering agree on what counts as a Steps
    section.
    """
    for heading in _STEP_HEADINGS:
        section = extract_section(body, heading)
        if section is not None:
            return section
    return None


def _parse_steps_for_json(section_text: str) -> list[StepDict]:
    """Extract steps as structured data for JSON output.

    Returns list of StepDict shapes. Plain steps have keys
    ``{"index", "text", "gate"}``; sub-stepped siblings (FXA-2226 Path B)
    additionally carry ``"sub_branch"`` set to the suffix letter (``"a"``,
    ``"b"``, ...). Gate is true if step ends with "✓" or contains "[GATE]".

    Path B convention: plain steps OMIT the ``sub_branch`` key entirely;
    it is never set to ``None`` or any sentinel.
    """
    steps: list[StepDict] = []
    for line in section_text.split("\n"):
        stripped = line.strip()
        m = re.match(r"^(?:###\s+)?(\d+)([a-z])?\.\s+(.+)", stripped)
        if m:
            index = int(m.group(1))
            sub_branch = m.group(2)  # None for plain; "a"/"b"/... for sub-steps
            text = m.group(3)
            gate = text.endswith("✓") or "[GATE]" in text
            step: StepDict = {"index": index, "text": text, "gate": gate}
            if sub_branch is not None:
                step["sub_branch"] = sub_branch
            steps.append(step)
    return steps


# Flush-left top-level step matcher — matches only lines that begin at column
# zero (no leading whitespace). Indented numbered sub-items and numbered
# lines inside indented code fences are **not** counted, keeping this
# consistent with `workflow._parse_step_indices`. Shared via this module so
# validate_cmd can use the same definition of "top-level step" (PR #59 P1).
# FXA-2226 Path B: regex extended to also match sub-step lines like ``3a.`` so
# ``parse_top_level_step_indices`` injects the parent integer (3) from each
# sibling. The optional ``[a-z]?`` is OUTSIDE the int-capturing group, so the
# captured group always yields a pure integer for ``int()`` casting.
_TOP_LEVEL_STEP_RE = re.compile(r"^(?:###\s+)?(\d+)[a-z]?\.\s+")


def parse_top_level_step_indices(section_text: str) -> frozenset[int]:
    """Return the set of top-level step indices declared in a Steps section.

    Only lines flush-left (no leading whitespace) that match
    ``^(?:###\\s+)?\\d+\\.\\s+`` contribute. Sub-items (indented) are
    ignored via the flush-left regex; **fenced code blocks** are skipped
    via ``parser.iter_lines_with_fence_state`` so numbered lines inside
    ``` / ~~~ fences don't count as steps (PR #59 Codex review P2 #4;
    CommonMark opener/closer rules per P2 #7 + P2 #8 live in the shared
    helper since CHG-2294).

    Used by ``validate_loops`` (intra-SOP) and by ``af validate`` D3
    (cross-SOP) so both enforce the same notion of "existing step".
    """
    indices: set[int] = set()
    for line, fenced in iter_lines_with_fence_state(section_text):
        if fenced:
            continue
        m = _TOP_LEVEL_STEP_RE.match(line)
        if m:
            indices.add(int(m.group(1)))
    return frozenset(indices)


# Flush-left top-level sub-step matcher — same shape as `_TOP_LEVEL_STEP_RE`
# but requires the trailing letter, so it matches ONLY sub-step lines like
# `3a.` (not plain `3.`). Used by `has_top_level_substep_lines` for the
# FXA-2226 Path B renderer-readiness gate.
_TOP_LEVEL_SUBSTEP_RE = re.compile(r"^(?:###\s+)?(\d+)([a-z])\.\s+")


def has_top_level_substep_lines(section_text: str) -> bool:
    """Return True if the Steps section contains any flush-left top-level
    sub-step line (e.g. ``3a.``) outside of fenced code blocks.

    Used by the FXA-2226 Path B plan-time gate to detect undeclared sub-step
    surface (sub-step lines authored directly in ``## Steps`` without the
    ``Workflow branches:`` metadata field). Mirrors the flush-left + fence
    tracking discipline of :func:`parse_top_level_step_indices` so the gate
    cannot be falsely tripped by indented or fenced ``3a.`` lines (Codex
    PR #68 R4 inline review).
    """
    return any(
        not fenced and _TOP_LEVEL_SUBSTEP_RE.match(line)
        for line, fenced in iter_lines_with_fence_state(section_text)
    )
