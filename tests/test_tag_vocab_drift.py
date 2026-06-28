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
    """Extract every backtick-quoted tag from the controlled-vocabulary section."""
    text = _SOP_PATH.read_text(encoding="utf-8")

    anchor = "**Controlled vocabulary**"
    start = text.find(anchor)
    assert start != -1, f"Anchor {anchor!r} not found in FXA-2315"

    prj_usr_marker = "PRJ/USR-only"
    marker_pos = text.find(prj_usr_marker, start)
    assert marker_pos != -1, (
        f"Marker {prj_usr_marker!r} not found after anchor in FXA-2315"
    )

    end = text.index("\n", marker_pos) + 1
    slice_ = text[start:end]

    return frozenset(re.findall(r"`([a-z-]+)`", slice_))


def test_controlled_tags_match_fxa_2315() -> None:
    """CONTROLLED_TAGS in schema.py must equal the vocabulary parsed from FXA-2315."""
    from fx_alfred.core.schema import CONTROLLED_TAGS

    parsed = _parse_controlled_tags_from_sop()
    assert parsed == CONTROLLED_TAGS, (
        f"CONTROLLED_TAGS diverged from FXA-2315.\n"
        f"In schema.py but not SOP: {CONTROLLED_TAGS - parsed}\n"
        f"In SOP but not schema.py: {parsed - CONTROLLED_TAGS}"
    )
