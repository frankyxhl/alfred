"""Shared step-parsing helpers for SOP bodies.

Extracted from commands/plan_cmd.py to avoid commands -> commands imports
when validate_cmd.py needs the same parser (FXA-2218 CHG Commit 1).
"""

from __future__ import annotations

import re

from fx_alfred.core.parser import extract_section
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

    Returns list of {"index": int, "text": str, "gate": bool}.
    Gate is true if step ends with "✓" or contains "[GATE]".
    """
    steps: list[StepDict] = []
    for line in section_text.split("\n"):
        stripped = line.strip()
        m = re.match(r"^(?:###\s+)?(\d+)\.\s+(.+)", stripped)
        if m:
            index = int(m.group(1))
            text = m.group(2)
            gate = text.endswith("✓") or "[GATE]" in text
            steps.append({"index": index, "text": text, "gate": gate})
    return steps


# Flush-left top-level step matcher — matches only lines that begin at column
# zero (no leading whitespace). Indented numbered sub-items and numbered
# lines inside indented code fences are **not** counted, keeping this
# consistent with `workflow._parse_step_indices`. Shared via this module so
# validate_cmd can use the same definition of "top-level step" (PR #59 P1).
_TOP_LEVEL_STEP_RE = re.compile(r"^(?:###\s+)?(\d+)\.\s+")


def parse_top_level_step_indices(section_text: str) -> frozenset[int]:
    """Return the set of top-level step indices declared in a Steps section.

    Only lines flush-left (no leading whitespace) that match
    ``^(?:###\\s+)?\\d+\\.\\s+`` contribute. Sub-items (indented) are
    ignored via the flush-left regex; **fenced code blocks** are tracked
    explicitly so numbered lines inside ``` / ~~~ fences don't count as
    steps (PR #59 Codex review P2 #4).

    Used by ``validate_loops`` (intra-SOP) and by ``af validate`` D3
    (cross-SOP) so both enforce the same notion of "existing step".
    """
    indices: set[int] = set()
    in_fence = False
    for line in section_text.split("\n"):
        stripped = line.lstrip()
        # Toggle fence state on lines that begin with ``` or ~~~ (at any
        # indent — indented code fences are still fences for our purposes).
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = _TOP_LEVEL_STEP_RE.match(line)
        if m:
            indices.add(int(m.group(1)))
    return frozenset(indices)
