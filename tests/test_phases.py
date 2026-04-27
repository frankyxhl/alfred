"""Tests for core/phases.py — including FXA-2226 StepDict refactor.

StepDict moves from a single TypedDict(total=True) to the
`_StepRequired + total=False` subclass pattern matching the
existing `_PhaseRequired + PhaseDict(total=False)` precedent at
`phases.py:47-75`. New optional `sub_branch: str` lives on the
total=False subclass.
"""

from __future__ import annotations

from fx_alfred.core.phases import StepDict


def test_stepdict_required_keys_only() -> None:
    """A plain StepDict with only required keys type-checks and is valid at runtime."""
    s: StepDict = {"index": 1, "text": "First", "gate": False}
    assert s["index"] == 1
    assert s["text"] == "First"
    assert s["gate"] is False
    # sub_branch is OPTIONAL — must NOT be present on plain steps.
    assert "sub_branch" not in s


def test_stepdict_with_sub_branch() -> None:
    """A sub-stepped StepDict carries the optional sub_branch field."""
    s: StepDict = {
        "index": 3,
        "text": "Branch A",
        "gate": False,
        "sub_branch": "a",
    }
    assert s.get("sub_branch") == "a"


def test_stepdict_get_returns_none_for_absent_sub_branch() -> None:
    """Plain steps' sub_branch is genuinely absent (not None) — .get() returns None default."""
    s: StepDict = {"index": 1, "text": "Plain", "gate": False}
    # `.get("sub_branch")` returns None because the key is absent.
    assert s.get("sub_branch") is None
    # But the key itself must NOT be present (Path B convention).
    assert "sub_branch" not in s
    # `step.get("sub_branch", "")` returns "" for plain steps (used by plan_cmd format).
    assert s.get("sub_branch", "") == ""
