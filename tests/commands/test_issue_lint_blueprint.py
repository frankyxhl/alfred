"""Tests for `af issue lint` blueprint structural check (issue #219).

The check derives required sections from the repo's own
``.github/ISSUE_TEMPLATE/blueprint.md`` (relative to the resolved --root) and
flags bodies missing a required section or lacking a checkbox under
``## Acceptance Criteria``. When the template is absent the check is skipped
and only the TBD-phrase rule applies (byte-for-byte unchanged behavior).
"""

import json

import pytest

from click.testing import CliRunner
from fx_alfred.cli import cli

pytestmark = pytest.mark.cli

# Mirrors the real blueprint's required H2 sections; "(optional)" is excluded.
TEMPLATE = """\
---
name: Blueprint
about: task ticket
---

## Work Type

## Problem / Goal

## Context

## Expected Outcome

## Acceptance Criteria

## Reproduction Steps / Task Plan

## Priority

## Requester / Owner

## Out of Scope (optional)
"""

REQUIRED = [
    "Work Type",
    "Problem / Goal",
    "Context",
    "Expected Outcome",
    "Acceptance Criteria",
    "Reproduction Steps / Task Plan",
    "Priority",
    "Requester / Owner",
]


def _make_root(tmp_path, with_template=True):
    if with_template:
        tpl = tmp_path / ".github" / "ISSUE_TEMPLATE" / "blueprint.md"
        tpl.parent.mkdir(parents=True)
        tpl.write_text(TEMPLATE)
    return tmp_path


def _section_block(h: str) -> str:
    if h == "Acceptance Criteria":
        return f"## {h}\n\n- [ ] first criterion\n"
    return f"## {h}\n\ncontent\n"


def _body_from(headings) -> str:
    return "\n".join(_section_block(h) for h in headings)


def _complete_body(extra="") -> str:
    body = _body_from(REQUIRED)
    return f"{body}\n{extra}" if extra else body


def _run(tmp_path, body_text, root, *extra_args):
    body = tmp_path / "body.md"
    body.write_text(body_text)
    runner = CliRunner()
    return runner.invoke(
        cli, ["issue", "lint", str(body), "--root", str(root), *extra_args]
    )


# ---------------------------------------------------------------------------
# AC: complete body passes
# ---------------------------------------------------------------------------


def test_complete_body_passes(tmp_path):
    root = _make_root(tmp_path)
    result = _run(tmp_path, _complete_body(), root)
    assert result.exit_code == 0
    assert "PASS (0 violations)" in result.output


# ---------------------------------------------------------------------------
# AC: missing required section(s)
# ---------------------------------------------------------------------------


def test_missing_one_section_fails(tmp_path):
    root = _make_root(tmp_path)
    body = _body_from([h for h in REQUIRED if h != "Context"])
    result = _run(tmp_path, body, root)
    assert result.exit_code == 1
    assert "Context" in result.output
    assert "FAIL" in result.output


def test_missing_multiple_sections_reports_each(tmp_path):
    root = _make_root(tmp_path)
    # Body with only two sections present
    body = "## Work Type\nx\n\n## Priority\nP2\n"
    result = _run(tmp_path, body, root, "--json")
    data = json.loads(result.output)
    missing = [v for v in data["violations"] if v["rule"] == "missing-section"]
    names = {v["match"] for v in missing}
    # Everything required except the two present must be reported
    assert "Context" in names
    assert "Acceptance Criteria" in names
    assert "Work Type" not in names
    assert "Priority" not in names


# ---------------------------------------------------------------------------
# AC: Acceptance Criteria with no checkbox
# ---------------------------------------------------------------------------


def test_acceptance_criteria_without_checkbox_fails(tmp_path):
    root = _make_root(tmp_path)
    body = _complete_body().replace("- [ ] first criterion", "just prose, no checkbox")
    result = _run(tmp_path, body, root, "--json")
    assert result.exit_code == 1
    data = json.loads(result.output)
    rules = {v["rule"] for v in data["violations"]}
    assert "no-acceptance-criteria" in rules
    # The section IS present, so it must not also be reported as missing
    missing = {v["match"] for v in data["violations"] if v["rule"] == "missing-section"}
    assert "Acceptance Criteria" not in missing


def test_acceptance_criteria_with_checkbox_ok(tmp_path):
    root = _make_root(tmp_path)
    result = _run(tmp_path, _complete_body(), root, "--json")
    data = json.loads(result.output)
    assert data["result"] == "PASS"


# ---------------------------------------------------------------------------
# AC: optional sections are not required
# ---------------------------------------------------------------------------


def test_optional_section_absence_is_ok(tmp_path):
    root = _make_root(tmp_path)
    # _complete_body has no "Out of Scope" — it's optional, so still PASS
    result = _run(tmp_path, _complete_body(), root)
    assert result.exit_code == 0
    assert "Out of Scope" not in result.output


# ---------------------------------------------------------------------------
# AC: template absent → check skipped, TBD-only behavior
# ---------------------------------------------------------------------------


def test_no_template_skips_structural_check(tmp_path):
    root = _make_root(tmp_path, with_template=False)
    # A body that would fail every structural rule, but has no TBD phrase
    result = _run(tmp_path, "just a sentence, no sections at all\n", root)
    assert result.exit_code == 0
    assert "PASS (0 violations)" in result.output


def test_no_template_still_catches_tbd(tmp_path):
    root = _make_root(tmp_path, with_template=False)
    result = _run(tmp_path, "implementer chooses the parser\n", root)
    assert result.exit_code == 1
    assert "FAIL" in result.output


# ---------------------------------------------------------------------------
# AC: COR-1501 pointer on FAIL (text mode only)
# ---------------------------------------------------------------------------


def test_fail_prints_cor1501_pointer(tmp_path):
    root = _make_root(tmp_path)
    result = _run(tmp_path, "## Work Type\nx\n", root)
    assert result.exit_code == 1
    assert "COR-1501" in result.output


def test_json_has_no_cor1501_pointer_text(tmp_path):
    root = _make_root(tmp_path)
    result = _run(tmp_path, "## Work Type\nx\n", root, "--json")
    # JSON mode must stay machine-parseable: no prose pointer, no ✗ glyphs
    data = json.loads(result.output)
    assert data["result"] == "FAIL"
    assert "✗" not in result.output


def test_tbd_only_fail_has_no_pointer(tmp_path):
    """AC#4: a TBD-only FAIL (no structural violation) prints no COR-1501
    pointer — keeps text output byte-for-byte identical to pre-#219."""
    root = _make_root(tmp_path, with_template=False)
    result = _run(tmp_path, "implementer chooses the lib\n", root)
    assert result.exit_code == 1
    assert "COR-1501" not in result.output


def test_structural_fail_with_tbd_still_prints_pointer(tmp_path):
    """A mixed fail (structural + TBD) still prints the pointer."""
    root = _make_root(tmp_path)
    result = _run(tmp_path, "## Work Type\nimplementer chooses\n", root)
    assert "COR-1501" in result.output


# ---------------------------------------------------------------------------
# AC: structural + TBD violations combine
# ---------------------------------------------------------------------------


def test_structural_and_tbd_combine(tmp_path):
    root = _make_root(tmp_path)
    body = "## Work Type\nimplementer chooses the lib\n"
    result = _run(tmp_path, body, root, "--json")
    data = json.loads(result.output)
    rules = {v["rule"] for v in data["violations"]}
    assert "tbd-phrase" in rules
    assert "missing-section" in rules


# ---------------------------------------------------------------------------
# AC: fence-awareness — headings/checkboxes inside code fences don't count
# ---------------------------------------------------------------------------


def test_fenced_heading_does_not_satisfy_required_section(tmp_path):
    root = _make_root(tmp_path)
    # Real Context section omitted; "## Context" appears only inside a fenced
    # code block → must not count as satisfying the required section.
    body = _body_from([h for h in REQUIRED if h != "Context"])
    body += "\n```markdown\n## Context\nfaux\n```\n"
    result = _run(tmp_path, body, root, "--json")
    data = json.loads(result.output)
    missing = {v["match"] for v in data["violations"] if v["rule"] == "missing-section"}
    assert "Context" in missing


def test_indented_heading_not_counted_as_present(tmp_path):
    """Column-0 discipline: an indented '## Acceptance Criteria' is not a
    real section (matches extract_section's ^## anchor) → missing-section,
    not a false no-acceptance-criteria."""
    root = _make_root(tmp_path)
    body = _body_from([h for h in REQUIRED if h != "Acceptance Criteria"])
    body += "\n  ## Acceptance Criteria\n\n  - [ ] indented\n"
    result = _run(tmp_path, body, root, "--json")
    data = json.loads(result.output)
    missing = {v["match"] for v in data["violations"] if v["rule"] == "missing-section"}
    rules = {v["rule"] for v in data["violations"]}
    assert "Acceptance Criteria" in missing
    assert "no-acceptance-criteria" not in rules


# ---------------------------------------------------------------------------
# AC: auto-discovery (no --root) path — the headline real-user behavior
# ---------------------------------------------------------------------------


def test_autodiscovery_without_root_flag(tmp_path, monkeypatch):
    """Run from inside a repo root (no --root): discover_root falls back to
    cwd, the template is found, and the structural check activates."""
    root = _make_root(tmp_path)
    body = root / "body.md"
    body.write_text("## Work Type\nx\n")
    monkeypatch.chdir(root)
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "lint", str(body)])
    assert result.exit_code == 1
    assert "COR-1501" in result.output


# ---------------------------------------------------------------------------
# AC: template edge cases
# ---------------------------------------------------------------------------


def test_optional_casing_variance_not_required(tmp_path):
    """A heading ending in '(Optional)' (capitalized) is still optional."""
    tpl = tmp_path / ".github" / "ISSUE_TEMPLATE" / "blueprint.md"
    tpl.parent.mkdir(parents=True)
    tpl.write_text("## Work Type\n\n## Extras (Optional)\n")
    body = tmp_path / "body.md"
    body.write_text("## Work Type\ncontent\n")
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "lint", str(body), "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Extras" not in result.output


def test_template_with_no_headings_is_noop(tmp_path):
    """A template with zero '## ' headings imposes no structural requirement."""
    tpl = tmp_path / ".github" / "ISSUE_TEMPLATE" / "blueprint.md"
    tpl.parent.mkdir(parents=True)
    tpl.write_text("Just prose, no sections.\n")
    body = tmp_path / "body.md"
    body.write_text("anything at all\n")
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "lint", str(body), "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "PASS (0 violations)" in result.output


def test_fenced_checkbox_does_not_satisfy_acceptance_criteria(tmp_path):
    root = _make_root(tmp_path)
    # AC section present, but the only "- [ ]" is inside a code fence
    body = _complete_body().replace(
        "## Acceptance Criteria\n\n- [ ] first criterion\n",
        "## Acceptance Criteria\n\n```\n- [ ] fenced, does not count\n```\n",
    )
    result = _run(tmp_path, body, root, "--json")
    data = json.loads(result.output)
    rules = {v["rule"] for v in data["violations"]}
    assert "no-acceptance-criteria" in rules
