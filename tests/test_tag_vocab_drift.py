"""Single-source-of-truth guard: CONTROLLED_TAGS constant must match FXA-2315.

FXA-2315 "Tag Documents For Filtering" owns the controlled vocabulary.
schema.py's CONTROLLED_TAGS is the machine-readable copy.  This test
parses the SOP and asserts the two are identical so they cannot silently
diverge.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.docs

_REPO = Path(__file__).parent.parent
_SOP_PATH = _REPO / "rules" / "FXA-2315-SOP-Tag-Documents-For-Filtering.md"


def _parse_controlled_tags_from_sop() -> frozenset[str]:
    """Extract every backtick-quoted tag from the controlled-vocabulary section.

    Parsing strategy:
    - Find the **Controlled vocabulary** anchor.
    - Extend the slice to the next blank line or next ## heading after the
      PRJ/USR-only line (so a reflow doesn't drop trailing tags like
      `release`/`commit`).
    - Within the slice, only examine table rows (lines containing '|') and
      lines containing 'PRJ/USR-only'; extract tokens with `([^`]+)` to
      tolerate digits and uppercase.
    """
    text = _SOP_PATH.read_text(encoding="utf-8")

    anchor = "**Controlled vocabulary**"
    start = text.find(anchor)
    assert start != -1, f"Anchor {anchor!r} not found in FXA-2315"

    prj_usr_marker = "PRJ/USR-only"
    marker_pos = text.find(prj_usr_marker, start)
    assert marker_pos != -1, (
        f"Marker {prj_usr_marker!r} not found after anchor in FXA-2315"
    )

    # Extend end to the next blank line or next ## heading after the
    # PRJ/USR-only line (whichever comes first).
    eol_of_marker = text.index("\n", marker_pos) + 1
    rest = text[eol_of_marker:]
    next_blank = rest.find("\n\n")
    next_heading = rest.find("\n##")
    candidates = [pos for pos in (next_blank, next_heading) if pos != -1]
    if candidates:
        end = eol_of_marker + min(candidates) + 1
    else:
        end = len(text)

    slice_ = text[start:end]

    # Only process table rows and the PRJ/USR-only line.
    tags: set[str] = set()
    for line in slice_.splitlines():
        if "|" in line or prj_usr_marker in line:
            tags.update(re.findall(r"`([^`]+)`", line))

    return frozenset(tags)


def test_controlled_tags_match_fxa_2315() -> None:
    """CONTROLLED_TAGS in schema.py must equal the vocabulary parsed from FXA-2315."""
    from fx_alfred.core.schema import CONTROLLED_TAGS

    # Invariant: every member is lowercase and matches ^[a-z][a-z-]*$
    for tag in CONTROLLED_TAGS:
        assert re.match(r"^[a-z][a-z-]*$", tag), (
            f"CONTROLLED_TAGS member {tag!r} violates format constraint "
            r"^[a-z][a-z-]*$ (must start with lowercase letter, only a-z and hyphen)"
        )

    parsed = _parse_controlled_tags_from_sop()
    assert parsed == CONTROLLED_TAGS, (
        f"CONTROLLED_TAGS diverged from FXA-2315.\n"
        f"In schema.py but not SOP: {CONTROLLED_TAGS - parsed}\n"
        f"In SOP but not schema.py: {parsed - CONTROLLED_TAGS}"
    )
