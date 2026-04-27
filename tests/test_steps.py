"""Tests for core/steps.py — including FXA-2226 sub-step parsing (Path B).

Sub-steps are authored as `3a.`, `3b.`, etc. and parse to StepDict
with int `index` (the parent integer, e.g. 3) plus optional `sub_branch`
key holding the suffix letter.

Path B convention: plain steps OMIT the `sub_branch` key entirely
(it is never set to None or any sentinel).
"""

from __future__ import annotations

from fx_alfred.core.steps import (
    _parse_steps_for_json,
    parse_top_level_step_indices,
)


def test_extract_step_substep_format() -> None:
    """`3a. Foo` parses to StepDict(index=3, sub_branch="a", text="Foo")."""
    section = "1. First\n2. Second\n3a. Branch A\n3b. Branch B\n4. After\n"
    steps = _parse_steps_for_json(section)
    indices_branches = [(s["index"], s.get("sub_branch")) for s in steps]
    assert indices_branches == [
        (1, None),
        (2, None),
        (3, "a"),
        (3, "b"),
        (4, None),
    ]
    # Plain steps must OMIT sub_branch entirely (not None) — Path B convention.
    plain = steps[0]
    assert "sub_branch" not in plain
    # Sub-stepped entries DO carry sub_branch.
    assert "sub_branch" in steps[2]
    assert steps[2]["sub_branch"] == "a"


def test_legacy_int_steps_unchanged() -> None:
    """Existing all-integer fixtures parse identically (no sub_branch keys)."""
    section = "1. Alpha\n2. Bravo\n3. Charlie\n"
    steps = _parse_steps_for_json(section)
    for s in steps:
        assert "sub_branch" not in s, f"plain step has unexpected sub_branch: {s}"
    assert [s["index"] for s in steps] == [1, 2, 3]


def test_substep_with_gate() -> None:
    """`3a. Foo [GATE]` detects gate AND preserves sub_branch."""
    section = "1. Plain\n3a. With gate [GATE]\n3b. Without\n"
    steps = _parse_steps_for_json(section)
    assert steps[0] == {"index": 1, "text": "Plain", "gate": False}
    assert steps[1]["index"] == 3
    assert steps[1]["sub_branch"] == "a"
    assert steps[1]["gate"] is True
    assert steps[2]["sub_branch"] == "b"
    assert steps[2]["gate"] is False


def test_parse_top_level_step_indices_with_bare_parent() -> None:
    """SOP `1, 2, 3, 3a, 3b, 4` (with bare parent) → {1, 2, 3, 4}."""
    section = "1. A\n2. B\n3. Decision\n3a. Branch a\n3b. Branch b\n4. Continue\n"
    indices = parse_top_level_step_indices(section)
    assert indices == frozenset({1, 2, 3, 4})


def test_parse_top_level_step_indices_substeps_only() -> None:
    """SOP `1, 2, 3a, 3b, 4` (no bare parent) ALSO → {1, 2, 3, 4}.

    The parser injects parent integer 3 from each sub-step line.
    """
    section = "1. A\n2. B\n3a. Branch a\n3b. Branch b\n4. Continue\n"
    indices = parse_top_level_step_indices(section)
    assert indices == frozenset({1, 2, 3, 4})


def test_parse_top_level_step_indices_legacy_unchanged() -> None:
    """All-integer fixture returns plain frozenset[int] unchanged from v1.7.1."""
    section = "1. A\n2. B\n3. C\n"
    indices = parse_top_level_step_indices(section)
    assert indices == frozenset({1, 2, 3})
