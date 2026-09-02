"""Direct unit tests for `af issue` violation rendering."""

import pytest

from fx_alfred.commands.issue_cmd import _render


pytestmark = pytest.mark.unit


def test_render_missing_section():
    v = {"rule": "missing-section", "line": 0, "match": "What Is It?"}
    assert _render(v) == "✗ Missing required section: ## What Is It?"


def test_render_no_acceptance_criteria():
    v = {"rule": "no-acceptance-criteria", "line": 0, "match": "Acceptance"}
    assert _render(v) == '✗ Section "## Acceptance" has no checkbox (- [ ]) item'


def test_render_unknown_rule_raises():
    with pytest.raises(AssertionError, match="unknown violation rule"):
        _render({"rule": "bogus", "line": 0, "match": "x"})
