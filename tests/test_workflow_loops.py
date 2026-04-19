"""Tests for core/workflow.py — loop metadata parsing and validation."""

import pytest

from fx_alfred.core.parser import MetadataField, ParsedDocument
from fx_alfred.core.workflow import (
    LoopSignature,
    parse_workflow_loops,
    validate_loops,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_parsed(fields: list[tuple[str, str]], body: str = "") -> ParsedDocument:
    """Build a minimal ParsedDocument with the given metadata fields and body."""
    metadata_fields = [
        MetadataField(
            key=key,
            value=value,
            prefix_style="bold",
            raw_line=f"**{key}:** {value}",
        )
        for key, value in fields
    ]
    return ParsedDocument(
        h1_line="# SOP-0000: Test",
        metadata_fields=metadata_fields,
        body=body,
    )


# ---------------------------------------------------------------------------
# parse_workflow_loops — basic cases
# ---------------------------------------------------------------------------


def test_parse_returns_empty_when_field_absent():
    """parse_workflow_loops returns [] when Workflow loops field is absent."""
    parsed = _make_parsed([("Status", "Active")])
    assert parse_workflow_loops(parsed) == []


def test_parse_returns_empty_when_field_empty_string():
    """parse_workflow_loops returns [] when Workflow loops is empty string."""
    parsed = _make_parsed([("Workflow loops", "")])
    assert parse_workflow_loops(parsed) == []


def test_parse_returns_empty_when_field_whitespace_only():
    """parse_workflow_loops returns [] when Workflow loops is whitespace."""
    parsed = _make_parsed([("Workflow loops", "   ")])
    assert parse_workflow_loops(parsed) == []


def test_parse_single_loop():
    """parse_workflow_loops parses a well-formed single-loop inline YAML."""
    parsed = _make_parsed(
        [
            (
                "Workflow loops",
                "[{id: review-retry, from: 7, to: 3, max_iterations: 3, condition: 'iteration is on'}]",
            )
        ]
    )
    loops = parse_workflow_loops(parsed)
    assert len(loops) == 1
    loop = loops[0]
    assert loop.id == "review-retry"
    assert loop.from_step == 7
    assert loop.to_step == 3
    assert loop.max_iterations == 3
    assert loop.condition == "iteration is on"


def test_parse_multiple_loops():
    """parse_workflow_loops parses multiple loops in one SOP."""
    parsed = _make_parsed(
        [
            (
                "Workflow loops",
                "[{id: loop-a, from: 5, to: 2, max_iterations: 2, condition: 'x'}, "
                "{id: loop-b, from: 8, to: 4, max_iterations: 1, condition: 'y'}]",
            )
        ]
    )
    loops = parse_workflow_loops(parsed)
    assert len(loops) == 2
    assert loops[0].id == "loop-a"
    assert loops[1].id == "loop-b"


def test_parse_yaml_null_returns_empty():
    """parse_workflow_loops returns [] when YAML parses to null."""
    parsed = _make_parsed([("Workflow loops", "null")])
    assert parse_workflow_loops(parsed) == []


def test_parse_rejects_invalid_yaml_syntax():
    """parse_workflow_loops raises on invalid YAML syntax."""
    # Unclosed bracket causes YAML parse error
    parsed = _make_parsed([("Workflow loops", "[{id: x, from: 5, to: 2")])
    from fx_alfred.core.parser import MalformedDocumentError

    with pytest.raises(MalformedDocumentError) as exc_info:
        parse_workflow_loops(parsed)
    assert "invalid YAML" in str(exc_info.value)


# ---------------------------------------------------------------------------
# parse_workflow_loops — error cases (MalformedDocumentError)
# ---------------------------------------------------------------------------


def test_parse_rejects_non_list():
    """parse_workflow_loops raises when value is not a YAML list."""
    parsed = _make_parsed([("Workflow loops", "{id: x, from: 1, to: 2}")])
    from fx_alfred.core.parser import MalformedDocumentError

    with pytest.raises(MalformedDocumentError) as exc_info:
        parse_workflow_loops(parsed)
    assert "expected a YAML list" in str(exc_info.value)


def test_parse_rejects_scalar():
    """parse_workflow_loops raises when value is a scalar (not a list)."""
    parsed = _make_parsed([("Workflow loops", "42")])
    from fx_alfred.core.parser import MalformedDocumentError

    with pytest.raises(MalformedDocumentError) as exc_info:
        parse_workflow_loops(parsed)
    assert "expected a YAML list" in str(exc_info.value)


def test_parse_rejects_entry_not_dict():
    """parse_workflow_loops raises when a list entry is not a dict."""
    parsed = _make_parsed([("Workflow loops", "[42, 'string']")])
    from fx_alfred.core.parser import MalformedDocumentError

    with pytest.raises(MalformedDocumentError) as exc_info:
        parse_workflow_loops(parsed)
    assert "expected a mapping" in str(exc_info.value)


def test_parse_rejects_missing_id():
    """parse_workflow_loops raises when 'id' key is missing."""
    parsed = _make_parsed(
        [("Workflow loops", "[{from: 5, to: 2, max_iterations: 1, condition: 'x'}]")]
    )
    from fx_alfred.core.parser import MalformedDocumentError

    with pytest.raises(MalformedDocumentError) as exc_info:
        parse_workflow_loops(parsed)
    assert "missing required key 'id'" in str(exc_info.value)


def test_parse_rejects_missing_from():
    """parse_workflow_loops raises when 'from' key is missing."""
    parsed = _make_parsed(
        [("Workflow loops", "[{id: x, to: 2, max_iterations: 1, condition: 'x'}]")]
    )
    from fx_alfred.core.parser import MalformedDocumentError

    with pytest.raises(MalformedDocumentError) as exc_info:
        parse_workflow_loops(parsed)
    assert "missing required key 'from'" in str(exc_info.value)


def test_parse_rejects_missing_to():
    """parse_workflow_loops raises when 'to' key is missing."""
    parsed = _make_parsed(
        [("Workflow loops", "[{id: x, from: 5, max_iterations: 1, condition: 'x'}]")]
    )
    from fx_alfred.core.parser import MalformedDocumentError

    with pytest.raises(MalformedDocumentError) as exc_info:
        parse_workflow_loops(parsed)
    assert "missing required key 'to'" in str(exc_info.value)


def test_parse_rejects_missing_max_iterations():
    """parse_workflow_loops raises when 'max_iterations' key is missing."""
    parsed = _make_parsed(
        [("Workflow loops", "[{id: x, from: 5, to: 2, condition: 'x'}]")]
    )
    from fx_alfred.core.parser import MalformedDocumentError

    with pytest.raises(MalformedDocumentError) as exc_info:
        parse_workflow_loops(parsed)
    assert "missing required key 'max_iterations'" in str(exc_info.value)


def test_parse_rejects_missing_condition():
    """parse_workflow_loops raises when 'condition' key is missing."""
    parsed = _make_parsed(
        [("Workflow loops", "[{id: x, from: 5, to: 2, max_iterations: 1}]")]
    )
    from fx_alfred.core.parser import MalformedDocumentError

    with pytest.raises(MalformedDocumentError) as exc_info:
        parse_workflow_loops(parsed)
    assert "missing required key 'condition'" in str(exc_info.value)


def test_parse_rejects_non_string_id():
    """parse_workflow_loops raises when 'id' is not a string."""
    parsed = _make_parsed(
        [
            (
                "Workflow loops",
                "[{id: 42, from: 5, to: 2, max_iterations: 1, condition: 'x'}]",
            )
        ]
    )
    from fx_alfred.core.parser import MalformedDocumentError

    with pytest.raises(MalformedDocumentError) as exc_info:
        parse_workflow_loops(parsed)
    assert "'id' must be a non-empty string" in str(exc_info.value)


def test_parse_rejects_empty_string_id():
    """parse_workflow_loops raises when 'id' is an empty string."""
    parsed = _make_parsed(
        [
            (
                "Workflow loops",
                "[{id: '', from: 5, to: 2, max_iterations: 1, condition: 'x'}]",
            )
        ]
    )
    from fx_alfred.core.parser import MalformedDocumentError

    with pytest.raises(MalformedDocumentError) as exc_info:
        parse_workflow_loops(parsed)
    assert "'id' must be a non-empty string" in str(exc_info.value)


def test_parse_rejects_non_int_from():
    """parse_workflow_loops raises when 'from' is not an integer."""
    parsed = _make_parsed(
        [
            (
                "Workflow loops",
                "[{id: x, from: 'five', to: 2, max_iterations: 1, condition: 'x'}]",
            )
        ]
    )
    from fx_alfred.core.parser import MalformedDocumentError

    with pytest.raises(MalformedDocumentError) as exc_info:
        parse_workflow_loops(parsed)
    assert "'from' must be an integer" in str(exc_info.value)


def test_parse_rejects_bool_from():
    """parse_workflow_loops raises when 'from' is a bool (int subclass)."""
    parsed = _make_parsed(
        [
            (
                "Workflow loops",
                "[{id: x, from: true, to: 2, max_iterations: 1, condition: 'x'}]",
            )
        ]
    )
    from fx_alfred.core.parser import MalformedDocumentError

    with pytest.raises(MalformedDocumentError) as exc_info:
        parse_workflow_loops(parsed)
    assert "'from' must be an integer" in str(exc_info.value)


def test_parse_rejects_non_int_to():
    """parse_workflow_loops raises when 'to' is not an integer."""
    parsed = _make_parsed(
        [
            (
                "Workflow loops",
                "[{id: x, from: 5, to: 'two', max_iterations: 1, condition: 'x'}]",
            )
        ]
    )
    from fx_alfred.core.parser import MalformedDocumentError

    with pytest.raises(MalformedDocumentError) as exc_info:
        parse_workflow_loops(parsed)
    assert "'to' must be an integer" in str(exc_info.value)


def test_parse_rejects_bool_to():
    """parse_workflow_loops raises when 'to' is a bool."""
    parsed = _make_parsed(
        [
            (
                "Workflow loops",
                "[{id: x, from: 5, to: false, max_iterations: 1, condition: 'x'}]",
            )
        ]
    )
    from fx_alfred.core.parser import MalformedDocumentError

    with pytest.raises(MalformedDocumentError) as exc_info:
        parse_workflow_loops(parsed)
    assert "'to' must be an integer" in str(exc_info.value)


def test_parse_rejects_non_int_max_iterations():
    """parse_workflow_loops raises when 'max_iterations' is not an integer."""
    parsed = _make_parsed(
        [
            (
                "Workflow loops",
                "[{id: x, from: 5, to: 2, max_iterations: 'three', condition: 'x'}]",
            )
        ]
    )
    from fx_alfred.core.parser import MalformedDocumentError

    with pytest.raises(MalformedDocumentError) as exc_info:
        parse_workflow_loops(parsed)
    assert "'max_iterations' must be an integer" in str(exc_info.value)


def test_parse_rejects_bool_max_iterations():
    """parse_workflow_loops raises when 'max_iterations' is a bool."""
    parsed = _make_parsed(
        [
            (
                "Workflow loops",
                "[{id: x, from: 5, to: 2, max_iterations: true, condition: 'x'}]",
            )
        ]
    )
    from fx_alfred.core.parser import MalformedDocumentError

    with pytest.raises(MalformedDocumentError) as exc_info:
        parse_workflow_loops(parsed)
    assert "'max_iterations' must be an integer" in str(exc_info.value)


def test_parse_rejects_empty_condition():
    """parse_workflow_loops raises when 'condition' is empty string."""
    parsed = _make_parsed(
        [
            (
                "Workflow loops",
                "[{id: x, from: 5, to: 2, max_iterations: 1, condition: ''}]",
            )
        ]
    )
    from fx_alfred.core.parser import MalformedDocumentError

    with pytest.raises(MalformedDocumentError) as exc_info:
        parse_workflow_loops(parsed)
    assert "'condition' must be a non-empty string" in str(exc_info.value)


def test_parse_rejects_whitespace_only_condition():
    """parse_workflow_loops raises when 'condition' is whitespace only."""
    parsed = _make_parsed(
        [
            (
                "Workflow loops",
                "[{id: x, from: 5, to: 2, max_iterations: 1, condition: '   '}]",
            )
        ]
    )
    from fx_alfred.core.parser import MalformedDocumentError

    with pytest.raises(MalformedDocumentError) as exc_info:
        parse_workflow_loops(parsed)
    assert "'condition' must be a non-empty string" in str(exc_info.value)


# ---------------------------------------------------------------------------
# validate_loops — valid cases
# ---------------------------------------------------------------------------


def test_validate_valid_back_edge():
    """validate_loops accepts from > to with both in range."""
    body = """---

## Steps

1. First
2. Second
3. Third
4. Fourth
5. Fifth
"""
    parsed = _make_parsed([], body=body)
    loop = LoopSignature(
        id="test-loop",
        from_step=5,
        to_step=2,
        max_iterations=3,
        condition="x",
    )
    errors = validate_loops(parsed, [loop])
    assert errors == []


def test_validate_accepts_from_equals_to_minus_one():
    """validate_loops accepts from = to + 1 (adjacent back-edge)."""
    body = """---

## Steps

1. First
2. Second
3. Third
"""
    parsed = _make_parsed([], body=body)
    loop = LoopSignature(
        id="adjacent-loop",
        from_step=3,
        to_step=2,
        max_iterations=1,
        condition="x",
    )
    errors = validate_loops(parsed, [loop])
    assert errors == []


# ---------------------------------------------------------------------------
# validate_loops — error cases
# ---------------------------------------------------------------------------


def test_validate_rejects_from_equals_to():
    """validate_loops rejects from == to (zero-length loop)."""
    body = """---

## Steps

1. First
2. Second
3. Third
"""
    parsed = _make_parsed([], body=body)
    loop = LoopSignature(
        id="zero-length",
        from_step=2,
        to_step=2,
        max_iterations=3,
        condition="x",
    )
    errors = validate_loops(parsed, [loop])
    assert len(errors) == 1
    assert "must be greater than" in errors[0].msg
    assert errors[0].loop_id == "zero-length"


def test_validate_rejects_from_less_than_to():
    """validate_loops rejects from < to (forward jump, not a back-edge)."""
    body = """---

## Steps

1. First
2. Second
3. Third
4. Fourth
"""
    parsed = _make_parsed([], body=body)
    loop = LoopSignature(
        id="forward-jump",
        from_step=2,
        to_step=4,
        max_iterations=1,
        condition="x",
    )
    errors = validate_loops(parsed, [loop])
    assert len(errors) == 1
    assert "must be greater than" in errors[0].msg
    assert errors[0].loop_id == "forward-jump"


def test_validate_rejects_max_iterations_zero():
    """validate_loops rejects max_iterations == 0."""
    body = """---

## Steps

1. First
2. Second
"""
    parsed = _make_parsed([], body=body)
    loop = LoopSignature(
        id="zero-iter",
        from_step=2,
        to_step=1,
        max_iterations=0,
        condition="x",
    )
    errors = validate_loops(parsed, [loop])
    assert len(errors) == 1
    assert "must be a positive integer" in errors[0].msg


def test_validate_rejects_max_iterations_negative():
    """validate_loops rejects max_iterations < 0."""
    body = """---

## Steps

1. First
2. Second
"""
    parsed = _make_parsed([], body=body)
    loop = LoopSignature(
        id="neg-iter",
        from_step=2,
        to_step=1,
        max_iterations=-1,
        condition="x",
    )
    errors = validate_loops(parsed, [loop])
    assert len(errors) == 1
    assert "must be a positive integer" in errors[0].msg


def test_validate_rejects_from_not_in_steps_high():
    """validate_loops rejects from > all step indices (not an existing step)."""
    body = """---

## Steps

1. First
2. Second
3. Third
"""
    parsed = _make_parsed([], body=body)
    loop = LoopSignature(
        id="from-out",
        from_step=99,
        to_step=2,
        max_iterations=1,
        condition="x",
    )
    errors = validate_loops(parsed, [loop])
    assert any("does not reference an existing step" in e.msg for e in errors)
    assert any(e.loop_id == "from-out" for e in errors)


def test_validate_rejects_from_not_in_steps_low():
    """validate_loops rejects from < 1 (no such step)."""
    body = """---

## Steps

1. First
2. Second
"""
    parsed = _make_parsed([], body=body)
    loop = LoopSignature(
        id="from-low",
        from_step=0,
        to_step=1,
        max_iterations=1,
        condition="x",
    )
    errors = validate_loops(parsed, [loop])
    assert any("does not reference an existing step" in e.msg for e in errors)


def test_validate_rejects_to_not_in_steps_high():
    """validate_loops rejects to > all step indices."""
    body = """---

## Steps

1. First
2. Second
"""
    parsed = _make_parsed([], body=body)
    loop = LoopSignature(
        id="to-out",
        from_step=2,
        to_step=99,
        max_iterations=1,
        condition="x",
    )
    errors = validate_loops(parsed, [loop])
    assert any("does not reference an existing step" in e.msg for e in errors)


def test_validate_rejects_to_not_in_steps_low():
    """validate_loops rejects to < 1 (no such step)."""
    body = """---

## Steps

1. First
2. Second
"""
    parsed = _make_parsed([], body=body)
    loop = LoopSignature(
        id="to-low",
        from_step=2,
        to_step=0,
        max_iterations=1,
        condition="x",
    )
    errors = validate_loops(parsed, [loop])
    assert any("does not reference an existing step" in e.msg for e in errors)


def test_validate_no_steps_section_skips_range_check():
    """validate_loops gracefully skips membership checks when no Steps section."""
    parsed = _make_parsed([], body="---\n\n## Other Section\n\nSome text.")
    loop = LoopSignature(
        id="no-steps",
        from_step=100,
        to_step=50,
        max_iterations=5,
        condition="x",
    )
    errors = validate_loops(parsed, [loop])
    # Should NOT have membership errors (step indices are None)
    assert not any("does not reference an existing step" in e.msg for e in errors)
    # But from > to is still validated
    # from=100 > to=50, so it's valid as a back-edge
    assert errors == []


def test_validate_multiple_errors_on_one_loop():
    """validate_loops reports both structural and range errors."""
    body = """---

## Steps

1. First
2. Second
"""
    parsed = _make_parsed([], body=body)
    loop = LoopSignature(
        id="multi-error",
        from_step=99,  # out of range
        to_step=99,  # out of range AND from <= to (not a back-edge)
        max_iterations=0,  # non-positive
        condition="x",
    )
    errors = validate_loops(parsed, [loop])
    # Should have: from <= to, max_iterations <= 0, from out of range, to out of range
    assert len(errors) >= 2


def test_validate_multiple_loops_independent():
    """validate_loops validates each loop independently."""
    body = """---

## Steps

1. First
2. Second
3. Third
"""
    parsed = _make_parsed([], body=body)
    loop1 = LoopSignature(
        id="good-loop",
        from_step=3,
        to_step=1,
        max_iterations=2,
        condition="x",
    )
    loop2 = LoopSignature(
        id="bad-loop",
        from_step=2,
        to_step=2,  # zero-length
        max_iterations=1,
        condition="y",
    )
    errors = validate_loops(parsed, [loop1, loop2])
    assert len(errors) == 1
    assert errors[0].loop_id == "bad-loop"


# ---------------------------------------------------------------------------
# Cross-SOP independence
# ---------------------------------------------------------------------------


def test_validate_cross_sop_independence():
    """validate_loops on SOP-A should not reference SOP-B's loop id."""
    body_a = """---

## Steps

1. First
2. Second
3. Third
"""
    body_b = """---

## Steps

1. Alpha
2. Beta
3. Gamma
4. Delta
"""
    parsed_a = _make_parsed([], body=body_a)
    parsed_b = _make_parsed([], body=body_b)

    loop_a = LoopSignature(
        id="loop-a",
        from_step=3,
        to_step=1,
        max_iterations=2,
        condition="x",
    )
    loop_b = LoopSignature(
        id="loop-b",
        from_step=4,
        to_step=2,
        max_iterations=1,
        condition="y",
    )

    errors_a = validate_loops(parsed_a, [loop_a])
    errors_b = validate_loops(parsed_b, [loop_b])

    assert errors_a == []
    assert errors_b == []
    # No cross-contamination
    assert all("loop-b" not in e.msg for e in errors_a)
    assert all("loop-a" not in e.msg for e in errors_b)


# ---------------------------------------------------------------------------
# Step counting edge cases
# ---------------------------------------------------------------------------


def test_step_counting_with_substeps():
    """Step-index parsing ignores bullet sub-items but collects all numbered top-level steps."""
    body = """---

## Steps

1. First
2. Second
   - Sub-item A
   - Sub-item B
3. Third
### 4. Fourth (with prefix)
5. Fifth
"""
    parsed = _make_parsed([], body=body)
    # A loop referencing existing steps should validate cleanly.
    loop = LoopSignature(
        id="test-loop",
        from_step=5,
        to_step=2,
        max_iterations=1,
        condition="x",
    )
    errors = validate_loops(parsed, [loop])
    assert errors == []


def test_gap_step_index_rejected():
    """A gap in the numbered steps means intermediate indices don't exist.

    With body ``1. First / 3. Third / 10. Tenth`` the step index set is
    ``{1, 3, 10}``. A loop referencing an existing pair like from=10, to=3
    is valid; a loop referencing step 2 (absent) must be rejected.
    """
    body = """---

## Steps

1. First
3. Third (skipped 2)
10. Tenth
"""
    parsed = _make_parsed([], body=body)

    # Valid: both endpoints are existing steps
    good_loop = LoopSignature(
        id="gap-existing",
        from_step=10,
        to_step=3,
        max_iterations=1,
        condition="x",
    )
    assert validate_loops(parsed, [good_loop]) == []

    # Invalid: to=2 does not exist in the gapped Steps body
    bad_loop = LoopSignature(
        id="gap-missing",
        from_step=3,
        to_step=2,
        max_iterations=1,
        condition="x",
    )
    errors = validate_loops(parsed, [bad_loop])
    assert len(errors) == 1
    assert errors[0].loop_id == "gap-missing"
    assert (
        "step 2" not in errors[0].msg
        or "does not reference an existing step" in errors[0].msg
    )
    # Error message must cite the missing index and report the observed set
    assert "'to' (2)" in errors[0].msg
    assert "does not reference an existing step" in errors[0].msg
    # Message includes the set of found indices; sorted textual check
    assert "1, 3, 10" in errors[0].msg


def test_indented_sub_items_not_counted_as_steps():
    """Indented numbered sub-items must not inflate the step index set.

    A nested numbered list beneath a top-level step (flush-left convention
    broken by indentation) is NOT a top-level step.
    """
    body = """---

## Steps

1. Top-level one
2. Top-level two
   1. Indented sub-step A
   2. Indented sub-step B
3. Top-level three
"""
    parsed = _make_parsed([], body=body)

    # Referencing only the genuine top-level indices must pass.
    loop = LoopSignature(
        id="top-level-only",
        from_step=3,
        to_step=1,
        max_iterations=1,
        condition="x",
    )
    assert validate_loops(parsed, [loop]) == []


def test_code_block_numbered_lines_not_counted_as_steps():
    """Numbered lines inside a fenced code block must not be counted as steps.

    Because the regex is applied to the raw (un-stripped) line, any numbered
    item inside an indented code fence is flush-left-broken and ignored.
    The step index set is exactly the flush-left top-level numbered lines.
    """
    body = """---

## Steps

1. Top-level one
2. Top-level two (with code block)

   ```
   1. Inside code block, not a step
   2. Also inside code block
   ```

3. Top-level three
"""
    parsed = _make_parsed([], body=body)

    # A loop over the real flush-left steps must validate cleanly.
    loop = LoopSignature(
        id="code-block-test",
        from_step=3,
        to_step=1,
        max_iterations=1,
        condition="x",
    )
    assert validate_loops(parsed, [loop]) == []

    # And directly assert the parsed step index set.
    from fx_alfred.core.workflow import _parse_step_indices

    indices = _parse_step_indices(parsed)
    assert indices == frozenset({1, 2, 3})


# ---------------------------------------------------------------------------
# Integration test with real PKG SOP
# ---------------------------------------------------------------------------


def test_parse_cor_1602_loop():
    """Integration test: parse COR-1602's Workflow loops metadata."""
    from importlib import resources
    from fx_alfred.core.parser import parse_metadata

    # PKG layer is bundled in fx_alfred/rules/
    pkg_rules = resources.files("fx_alfred").joinpath("rules")
    cor_1602_path = pkg_rules.joinpath(
        "COR-1602-SOP-Workflow-Multi-Model-Parallel-Review.md"
    )

    content = cor_1602_path.read_text()
    parsed = parse_metadata(content)
    loops = parse_workflow_loops(parsed)

    # After backfill, should have exactly one loop
    # This test will fail until the backfill is done
    assert len(loops) >= 1, "COR-1602 should have at least one loop after backfill"

    loop = loops[0]
    assert loop.id == "review-retry"
    assert loop.from_step == 7
    assert loop.to_step == 3
    assert loop.max_iterations == 3
    assert "iteration" in loop.condition.lower()

    # Validate the loop
    errors = validate_loops(parsed, loops)
    assert errors == [], f"COR-1602 loop validation failed: {errors}"


# ---------------------------------------------------------------------------
# Cross-SOP loops (FXA-2218) — parser + LoopSignature helpers + validate_loops
# ---------------------------------------------------------------------------


def test_cross_sop_ref_regex_accepts_valid_form():
    """CROSS_SOP_REF matches PREFIX-ACID.step form."""
    from fx_alfred.core.workflow import CROSS_SOP_REF

    m = CROSS_SOP_REF.match("COR-1500.3")
    assert m is not None
    assert m.group("prefix") == "COR"
    assert m.group("acid") == "1500"
    assert m.group("step") == "3"


def test_cross_sop_ref_regex_rejects_malformed():
    """CROSS_SOP_REF rejects lower-case prefix, missing step, no prefix, wrong ACID width."""
    from fx_alfred.core.workflow import CROSS_SOP_REF

    assert CROSS_SOP_REF.match("cor-1500.3") is None  # lower-case prefix
    assert CROSS_SOP_REF.match("COR-1500") is None  # missing .step
    assert CROSS_SOP_REF.match("1500.3") is None  # no prefix
    assert CROSS_SOP_REF.match("COR-150.3") is None  # 3-digit ACID
    assert CROSS_SOP_REF.match("COR-15000.3") is None  # 5-digit ACID
    assert CROSS_SOP_REF.match("COR-1500.") is None  # empty step
    assert CROSS_SOP_REF.match("27") is None  # plain int-string


def test_parse_accepts_cross_sop_to_reference():
    """parse_workflow_loops accepts a string 'to' matching PREFIX-ACID.step form."""
    parsed = _make_parsed(
        [
            (
                "Workflow loops",
                '[{id: review-retry, from: 3, to: "COR-1500.3", '
                'max_iterations: 3, condition: "if review fails"}]',
            )
        ]
    )
    loops = parse_workflow_loops(parsed)
    assert len(loops) == 1
    assert loops[0].from_step == 3
    assert loops[0].to_step == "COR-1500.3"


def test_parse_rejects_cross_sop_malformed_ref():
    """parse_workflow_loops rejects a string 'to' that does not match CROSS_SOP_REF."""
    from fx_alfred.core.parser import MalformedDocumentError

    parsed = _make_parsed(
        [
            (
                "Workflow loops",
                '[{id: bad, from: 3, to: "not-a-ref", '
                'max_iterations: 3, condition: "oops"}]',
            )
        ]
    )
    with pytest.raises(MalformedDocumentError, match="cross-SOP reference"):
        parse_workflow_loops(parsed)


def test_parse_rejects_quoted_digit_string_as_to():
    """parse_workflow_loops rejects 'to: "27"' — use int 27 for intra-SOP."""
    from fx_alfred.core.parser import MalformedDocumentError

    parsed = _make_parsed(
        [
            (
                "Workflow loops",
                '[{id: bad, from: 3, to: "27", '
                'max_iterations: 3, condition: "quoted digits"}]',
            )
        ]
    )
    with pytest.raises(MalformedDocumentError, match="cross-SOP reference"):
        parse_workflow_loops(parsed)


def test_loop_signature_is_cross_sop():
    """is_cross_sop() returns True for string to_step, False for int."""
    intra = LoopSignature(
        id="a", from_step=5, to_step=3, max_iterations=2, condition="x"
    )
    cross = LoopSignature(
        id="b", from_step=5, to_step="COR-1500.3", max_iterations=2, condition="y"
    )
    assert intra.is_cross_sop() is False
    assert cross.is_cross_sop() is True


def test_loop_signature_cross_sop_target_parses_components():
    """cross_sop_target() returns (prefix, acid, step_idx) tuple for cross-SOP refs."""
    cross = LoopSignature(
        id="b", from_step=5, to_step="COR-1500.3", max_iterations=2, condition="y"
    )
    target = cross.cross_sop_target()
    assert target == ("COR", "1500", 3)


def test_loop_signature_cross_sop_target_none_for_intra():
    """cross_sop_target() returns None for intra-SOP (int to_step) loops."""
    intra = LoopSignature(
        id="a", from_step=5, to_step=3, max_iterations=2, condition="x"
    )
    assert intra.cross_sop_target() is None


def test_validate_loops_skips_back_edge_direction_for_cross_sop():
    """validate_loops does not enforce from > to for cross-SOP loops."""
    parsed = _make_parsed(
        [],
        body="## Steps\n\n1. A\n2. B\n3. C\n",
    )
    # Cross-SOP loop — from_step could be < to_step number because they refer
    # to different SOPs. No back-edge direction error should fire.
    cross = LoopSignature(
        id="cx", from_step=2, to_step="COR-1500.99", max_iterations=2, condition="y"
    )
    errors = validate_loops(parsed, [cross])
    assert errors == []


def test_validate_loops_skips_membership_check_for_cross_sop():
    """validate_loops does not check cross-SOP to_step against local step indices."""
    parsed = _make_parsed(
        [],
        body="## Steps\n\n1. A\n2. B\n",
    )
    # Local SOP has steps {1, 2}; cross-SOP target step 99 is fine here
    # because it's checked in a different layer (af validate D3).
    cross = LoopSignature(
        id="cx", from_step=2, to_step="COR-1500.99", max_iterations=2, condition="y"
    )
    errors = validate_loops(parsed, [cross])
    assert errors == []


def test_validate_loops_still_checks_from_step_membership_for_cross_sop():
    """validate_loops still enforces from_step membership for cross-SOP loops
    — only to_step-dependent checks are skipped (PR #59 Codex review P1 #3)."""
    parsed = _make_parsed(
        [],
        body="## Steps\n\n1. A\n2. B\n3. C\n",
    )
    # Cross-SOP loop with from_step=99 (does not exist locally). Must be
    # rejected even though to_step is a cross-SOP string.
    cross = LoopSignature(
        id="cx",
        from_step=99,
        to_step="COR-1500.1",
        max_iterations=2,
        condition="y",
    )
    errors = validate_loops(parsed, [cross])
    assert len(errors) == 1
    assert "'from' (99)" in errors[0].msg
    assert "does not reference an existing step" in errors[0].msg
    assert "{1, 2, 3}" in errors[0].msg


def test_validate_loops_still_checks_max_iterations_for_cross_sop():
    """validate_loops still enforces max_iterations > 0 for cross-SOP loops."""
    parsed = _make_parsed(
        [],
        body="## Steps\n\n1. A\n",
    )
    cross = LoopSignature(
        id="cx", from_step=1, to_step="COR-1500.3", max_iterations=0, condition="y"
    )
    errors = validate_loops(parsed, [cross])
    assert len(errors) == 1
    assert "max_iterations" in errors[0].msg
