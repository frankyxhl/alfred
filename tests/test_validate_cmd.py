"""Tests for af validate command."""

from click.testing import CliRunner

from fx_alfred.cli import cli


def _write_valid_document(path, prefix, acid, type_code, title, status="Active"):
    """Write a valid Alfred document to path."""
    content = f"""# {type_code}-{acid}: {title}

**Applies to:** All projects
**Last updated:** 2026-03-14
**Last reviewed:** 2026-03-14
**Status:** {status}

---

## What Is It?

This is a valid document.

## Why

This section explains why.

## When to Use

Use when needed.

## When NOT to Use

Do not use when not needed.

## Steps

1. Step one.
2. Step two.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-14 | Initial version | Frank |
"""
    path.write_text(content)


def test_validate_valid_documents_exit_0(tmp_path):
    """Valid documents should result in exit code 0 and '0 issues found'."""
    # Create a valid project with valid documents
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    # Write two valid documents
    _write_valid_document(
        rules_dir / "SOP-1000-SOP-Create-SOP.md",
        "SOP",
        "1000",
        "SOP",
        "Create SOP",
    )
    _write_valid_document(
        rules_dir / "PRP-2000-PRP-Another-Doc.md",
        "PRP",
        "2000",
        "PRP",
        "Another Doc",
        status="Draft",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "0 issues found" in result.output


def test_validate_h1_type_code_mismatch(tmp_path):
    """H1 type_code mismatch should be detected and reported."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    # Valid document
    _write_valid_document(
        rules_dir / "SOP-1000-SOP-Create-SOP.md",
        "SOP",
        "1000",
        "SOP",
        "Create SOP",
    )

    # Document with H1 type_code mismatch
    # Filename has type_code=SOP, but H1 has type_code=SSM
    mismatched_content = """# SSM-2000: Another Doc

**Applies to:** All projects
**Last updated:** 2026-03-14
**Last reviewed:** 2026-03-14
**Status:** Active

---

## What Is It?

This document has mismatched H1.

## Why

This section explains why.

## When to Use

Use when needed.

## When NOT to Use

Do not use when not needed.

## Steps

1. Step one.
2. Step two.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-14 | Initial version | Frank |
"""
    (rules_dir / "SOP-2000-SOP-Another-Doc.md").write_text(mismatched_content)

    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])

    # Should have issues
    assert "1 issues found" in result.output
    # Should report the H1 mismatch
    assert "SOP-2000" in result.output
    assert "H1" in result.output


def test_validate_missing_metadata_field(tmp_path):
    """Missing required metadata field should be detected."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    # Document missing 'Last reviewed' field
    missing_metadata_content = """# SOP-1000: Missing Metadata

**Applies to:** All projects
**Last updated:** 2026-03-14
**Status:** Active

---

## What Is It?

This document is missing 'Last reviewed'.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-14 | Initial version | Frank |
"""
    (rules_dir / "SOP-1000-SOP-Missing-Metadata.md").write_text(
        missing_metadata_content
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])

    # Should have issues
    assert "SOP-1000" in result.output
    assert "Last reviewed" in result.output


def test_validate_invalid_change_history_table(tmp_path):
    """Invalid Change History table structure should be detected."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    # Document with missing 'By' column in Change History
    invalid_history_content = """# SOP-1000: Invalid History

**Applies to:** All projects
**Last updated:** 2026-03-14
**Last reviewed:** 2026-03-14
**Status:** Active

---

## What Is It?

This document has invalid Change History.

---

## Change History

| Date | Change |
|------|--------|
| 2026-03-14 | Initial version |
"""
    (rules_dir / "SOP-1000-SOP-Invalid-History.md").write_text(invalid_history_content)

    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])

    # Should have issues
    assert "SOP-1000" in result.output
    assert "Change History" in result.output


def test_validate_malformed_document_reported_as_issue(tmp_path):
    """MalformedDocumentError should be reported as issue, not crash."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    # Document that will fail to parse (no separator ---)
    malformed_content = """# SOP-1000: Malformed Doc

**Applies to:** All projects
**Last updated:** 2026-03-14
**Last reviewed:** 2026-03-14
**Status:** Active

## What Is It?

This document has no separator.
"""
    (rules_dir / "SOP-1000-SOP-Malformed-Doc.md").write_text(malformed_content)

    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])

    # Should not crash - should report issue
    assert "SOP-1000" in result.output
    assert "Malformed" in result.output or "missing" in result.output.lower()


def test_validate_cor_in_non_pkg_layer(tmp_path):
    """COR document in PRJ layer should be reported as issue."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    # COR document in PRJ layer (should only be in PKG)
    cor_content = """# COR-9999: Bad Layer Doc

**Applies to:** All projects
**Last updated:** 2026-03-14
**Last reviewed:** 2026-03-14
**Status:** Active

---

## What Is It?

This COR document is in the wrong layer.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-14 | Initial version | Frank |
"""
    (rules_dir / "COR-9999-SOP-Bad-Layer-Doc.md").write_text(cor_content)

    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])

    # Validate command should report COR-in-wrong-layer as a validate issue
    # (not as a ClickException from the scanner)
    assert result.exit_code != 0
    assert "COR-9999" in result.output
    assert "COR document found in non-PKG layer (prj)" in result.output
    assert "issues found" in result.output


def test_validate_missing_change_history(tmp_path):
    """Document without Change History section should be reported as issue."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    # Document without any Change History section
    no_history_content = """# SOP-1000: No History

**Applies to:** All projects
**Last updated:** 2026-03-14
**Last reviewed:** 2026-03-14
**Status:** Active

---

## What Is It?

This document has no Change History section.

---
"""
    (rules_dir / "SOP-1000-SOP-No-History.md").write_text(no_history_content)

    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])

    assert result.exit_code != 0
    assert "SOP-1000" in result.output
    assert "Missing Change History table" in result.output


def test_validate_h1_acid_mismatch(tmp_path):
    """H1 ACID that doesn't match filename ACID should be reported."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    # Filename has ACID 2000, but H1 has ACID 9999
    acid_mismatch_content = """# SOP-9999: Mismatched ACID

**Applies to:** All projects
**Last updated:** 2026-03-14
**Last reviewed:** 2026-03-14
**Status:** Active

---

## What Is It?

This document has ACID mismatch between H1 and filename.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-14 | Initial version | Frank |
"""
    (rules_dir / "SOP-2000-SOP-Mismatched-ACID.md").write_text(acid_mismatch_content)

    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])

    assert result.exit_code != 0
    assert "SOP-2000" in result.output
    assert "H1 ACID '9999' does not match filename ACID '2000'" in result.output


def test_validate_exit_code_1_on_issues(tmp_path):
    """Exit code should be 1 when issues are found."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    # Document with an issue (missing metadata)
    invalid_content = """# SOP-1000: Invalid Doc

**Applies to:** All projects
**Last updated:** 2026-03-14
**Status:** Active

---

## What Is It?

Missing Last reviewed.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-14 | Initial version | Frank |
"""
    (rules_dir / "SOP-1000-SOP-Invalid-Doc.md").write_text(invalid_content)

    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])

    # Should exit with code 1 when issues found
    assert result.exit_code == 1
    assert "issues found" in result.output


# ── CHG-2122 tests: per-type required fields, Status validation, ACID=0000 ──


def test_validate_sop_status_active_no_issue(tmp_path):
    """SOP with Status: Active should report no status issue."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    _write_valid_document(
        rules_dir / "SOP-1000-SOP-Good-Status.md",
        "SOP",
        "1000",
        "SOP",
        "Good Status",
        status="Active",
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "0 issues found" in result.output


def test_validate_sop_status_invalid_reports_issue(tmp_path):
    """SOP with Status: InvalidValue should report invalid status issue."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    _write_valid_document(
        rules_dir / "SOP-1000-SOP-Bad-Status.md",
        "SOP",
        "1000",
        "SOP",
        "Bad Status",
        status="InvalidValue",
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "Invalid Status" in result.output
    assert "InvalidValue" in result.output


def test_validate_prp_status_draft_no_issue(tmp_path):
    """PRP with Status: Draft should report no status issue."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    _write_valid_document(
        rules_dir / "PRP-2000-PRP-Draft-Proposal.md",
        "PRP",
        "2000",
        "PRP",
        "Draft Proposal",
        status="Draft",
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "0 issues found" in result.output


def test_validate_chg_status_in_progress_no_issue(tmp_path):
    """CHG with Status: In Progress should report no issue (space in value OK)."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    _write_valid_document(
        rules_dir / "CHG-3000-CHG-In-Progress-Change.md",
        "CHG",
        "3000",
        "CHG",
        "In Progress Change",
        status="In Progress",
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "0 issues found" in result.output


def test_validate_chg_status_annotation_reports_issue(tmp_path):
    """CHG with Status containing parentheses should report annotation issue."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    _write_valid_document(
        rules_dir / "CHG-3000-CHG-Annotated-Status.md",
        "CHG",
        "3000",
        "CHG",
        "Annotated Status",
        status="Draft (revised after review)",
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "Invalid Status" in result.output
    assert "Draft (revised after review)" in result.output


def test_validate_ref_status_active_no_issue(tmp_path):
    """REF with Status: Active should report no issue (PLN override gives REF Status)."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    _write_valid_document(
        rules_dir / "REF-4000-REF-Reference-Doc.md",
        "REF",
        "4000",
        "REF",
        "Reference Doc",
        status="Active",
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "0 issues found" in result.output


def test_validate_chg_missing_applies_to_reports_issue(tmp_path):
    """CHG missing Applies to should report per-type required field issue."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    # Write a CHG document missing "Applies to"
    content = """# CHG-3000: Missing Applies To

**Last updated:** 2026-03-14
**Last reviewed:** 2026-03-14
**Status:** Proposed

---

## What Is It?

A change request missing Applies to.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-14 | Initial version | Frank |
"""
    (rules_dir / "CHG-3000-CHG-Missing-Applies-To.md").write_text(content)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "Applies to" in result.output


def test_validate_sop_missing_status_reports_issue(tmp_path):
    """SOP missing Status field should report per-type required field issue."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    # Write a SOP document without Status field
    content = """# SOP-1000: No Status Field

**Applies to:** All projects
**Last updated:** 2026-03-14
**Last reviewed:** 2026-03-14

---

## What Is It?

A SOP missing the Status field.

## Why

This section explains why.

## When to Use

Use when needed.

## When NOT to Use

Do not use when not needed.

## Steps

1. Step one.
2. Step two.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-14 | Initial version | Frank |
"""
    (rules_dir / "SOP-1000-SOP-No-Status-Field.md").write_text(content)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "Status" in result.output


def test_validate_acid_0000_h1_exempt(tmp_path):
    """ACID=0000 document with non-standard H1 should skip H1 check."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    # Index document with non-standard H1 (no TYP-ACID: Title format)
    content = """# Document Index

**Applies to:** All projects
**Last updated:** 2026-03-14
**Last reviewed:** 2026-03-14
**Status:** Active

---

## What Is It?

This is the document index.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-14 | Initial version | Frank |
"""
    (rules_dir / "FXA-0000-REF-Document-Index.md").write_text(content)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    # H1 check should be skipped for ACID=0000
    assert "H1 does not match" not in result.output


def test_validate_acid_0000_metadata_still_validated(tmp_path):
    """ACID=0000 document should still validate metadata (only H1 exempt)."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    # Index document missing required metadata field
    content = """# Document Index

**Applies to:** All projects
**Last updated:** 2026-03-14
**Status:** Active

---

## What Is It?

This index is missing Last reviewed.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-14 | Initial version | Frank |
"""
    (rules_dir / "FXA-0000-REF-Document-Index.md").write_text(content)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    # Metadata should still be validated even for ACID=0000
    assert result.exit_code == 1
    assert "Last reviewed" in result.output


# -- CHG-2132 tests: SOP required section checking --


def _write_sop_with_body(path, acid, body_text, status="Active"):
    """Write a SOP document with custom body text for section testing."""
    content = f"""# SOP-{acid}: Test SOP

**Applies to:** All projects
**Last updated:** 2026-03-14
**Last reviewed:** 2026-03-14
**Status:** {status}

---

{body_text}

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-14 | Initial version | Frank |
"""
    path.write_text(content)


def test_validate_sop_all_sections_present_no_issue(tmp_path):
    """SOP with all 5 required sections in body should pass."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    body = """## What Is It?

A complete SOP.

## Why

This explains why.

## When to Use

Use when needed.

## When NOT to Use

Do not use when not needed.

## Steps

1. Step one.
2. Step two."""
    _write_sop_with_body(rules_dir / "SOP-1000-SOP-Complete.md", "1000", body)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "0 issues found" in result.output


def test_validate_sop_missing_why_reports_issue(tmp_path):
    """SOP missing '## Why' section should report issue."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    body = """## What Is It?

A SOP without Why.

## When to Use

Use when needed.

## When NOT to Use

Do not use when not needed.

## Steps

1. Step one.
2. Step two."""
    _write_sop_with_body(rules_dir / "SOP-1000-SOP-Missing-Why.md", "1000", body)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "SOP missing required section: '## Why'" in result.output


def test_validate_sop_missing_when_to_use_reports_issue(tmp_path):
    """SOP missing '## When to Use' section should report issue."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    body = """## What Is It?

A SOP without When to Use.

## Why

This explains why.

## When NOT to Use

Do not use when not needed.

## Steps

1. Step one.
2. Step two."""
    _write_sop_with_body(
        rules_dir / "SOP-1000-SOP-Missing-When-To-Use.md", "1000", body
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "SOP missing required section: '## When to Use'" in result.output


def test_validate_sop_missing_when_not_to_use_reports_issue(tmp_path):
    """SOP missing '## When NOT to Use' section should report issue."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    body = """## What Is It?

A SOP without When NOT to Use.

## Why

This explains why.

## When to Use

Use when needed.

## Steps

1. Step one.
2. Step two."""
    _write_sop_with_body(
        rules_dir / "SOP-1000-SOP-Missing-When-Not-To-Use.md", "1000", body
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "SOP missing required section: '## When NOT to Use'" in result.output


def test_validate_sop_with_prerequisites_no_examples_reports_issue(tmp_path):
    """SOP with Prerequisites section but no Examples should report issue."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    body = """## What Is It?

A SOP with Prerequisites.

## Why

This explains why.

## When to Use

Use when needed.

## When NOT to Use

Do not use when not needed.

## Prerequisites

- Item one
- Item two

## Steps

1. Step one.
2. Step two."""
    _write_sop_with_body(
        rules_dir / "SOP-1000-SOP-Prerequisites-No-Examples.md", "1000", body
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "SOP missing required section: '## Examples'" in result.output


def test_validate_sop_with_many_steps_no_examples_reports_issue(tmp_path):
    """SOP with more than 5 steps but no Examples should report issue."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    body = """## What Is It?

A SOP with many steps.

## Why

This explains why.

## When to Use

Use when needed.

## When NOT to Use

Do not use when not needed.

## Steps

1. Step one.
2. Step two.
3. Step three.
4. Step four.
5. Step five.
6. Step six."""
    _write_sop_with_body(
        rules_dir / "SOP-1000-SOP-Many-Steps-No-Examples.md", "1000", body
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "SOP missing required section: '## Examples'" in result.output


def test_validate_sop_with_substeps_counted_for_examples_rule(tmp_path):
    """Per PR #68 R2 review F4: sub-step lines (`3a.`, `3b.`) must count
    toward the > 5 → require ## Examples heuristic.

    Pre-fix, the regex `^\\d+\\.` undercounted branchy SOPs: a 3-plain +
    3-substep SOP (6 step-equivalents) was counted as 3 and silently
    bypassed the rule.
    """
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    body = """## What Is It?

A SOP with branches.

## Why

Branches need testing.

## When to Use

When deciding.

## When NOT to Use

Never.

## Steps

1. Setup
2. Decision
3a. Pass branch
3b. Fail branch
3c. Escalate branch
4. After"""
    _write_sop_with_body(rules_dir / "SOP-1000-SOP-Substep-Count.md", "1000", body)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    # 6 numbered lines (1, 2, 3a, 3b, 3c, 4) — exceeds threshold of 5.
    # Should require ## Examples.
    assert result.exit_code == 1
    assert "SOP missing required section: '## Examples'" in result.output


def test_validate_sop_few_steps_no_examples_no_issue(tmp_path):
    """SOP with 5 or fewer steps and no Examples should pass."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    body = """## What Is It?

A simple SOP.

## Why

This explains why.

## When to Use

Use when needed.

## When NOT to Use

Do not use when not needed.

## Steps

1. Step one.
2. Step two.
3. Step three."""
    _write_sop_with_body(rules_dir / "SOP-1000-SOP-Few-Steps.md", "1000", body)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "0 issues found" in result.output


def test_validate_non_sop_skips_section_check(tmp_path):
    """Non-SOP document should skip section checking."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    # PRP document with only one section (no SOP sections)
    content = """# PRP-2000: Minimal PRP

**Applies to:** All projects
**Last updated:** 2026-03-14
**Last reviewed:** 2026-03-14
**Status:** Draft

---

## What Is It?

This is a PRP with no SOP sections.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-14 | Initial version | Frank |
"""
    (rules_dir / "PRP-2000-PRP-Minimal.md").write_text(content)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "SOP missing" not in result.output


# -- FXA-2132 code review: substring match false positive --


def test_validate_sop_section_in_prose_not_heading(tmp_path):
    """## Why appearing in prose (not as heading) should still report missing."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    # Body has "## Why" embedded in a paragraph (not at line start) but NOT as
    # an actual markdown heading on its own line.  The validator must detect
    # that the real heading is absent.
    body = """## What Is It?

A SOP that mentions ## Why in the middle of a sentence but does not
have it as a real heading.

## When to Use

Use when needed.

## When NOT to Use

Do not use when not needed.

## Steps

1. Step one.
2. Step two."""
    _write_sop_with_body(rules_dir / "SOP-1000-SOP-Prose-Why.md", "1000", body)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "SOP missing required section: '## Why'" in result.output


def test_validate_sop_section_in_prose_prerequisites(tmp_path):
    """## Prerequisites in prose should not count as having that section."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    # Body mentions "## Prerequisites" inside prose, but has no real heading.
    # Since there's no real ## Prerequisites heading, ## Examples should NOT
    # be required by the conditional logic.
    body = """## What Is It?

A SOP that talks about ## Prerequisites in a paragraph.

## Why

This explains why.

## When to Use

Use when needed.

## When NOT to Use

Do not use when not needed.

## Steps

1. Step one.
2. Step two."""
    _write_sop_with_body(rules_dir / "SOP-1000-SOP-Prose-Prereq.md", "1000", body)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    # No ## Examples should be required because ## Prerequisites is NOT a real heading
    assert result.exit_code == 0
    assert "0 issues found" in result.output


def test_validate_sop_section_in_prose_examples(tmp_path):
    """## Examples in prose should not satisfy the Examples requirement."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    # Has real ## Prerequisites heading -> ## Examples required.
    # But ## Examples only appears in prose, not as a heading.
    body = """## What Is It?

A SOP that mentions ## Examples in a sentence but not as heading.

## Why

This explains why.

## When to Use

Use when needed.

## When NOT to Use

Do not use when not needed.

## Prerequisites

- Item one

## Steps

1. Step one.
2. Step two."""
    _write_sop_with_body(rules_dir / "SOP-1000-SOP-Prose-Examples.md", "1000", body)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "SOP missing required section: '## Examples'" in result.output


# -- FXA-2132 code review: end-of-line anchor fix for prefix matches --


def test_validate_sop_prefix_heading_why_this_matters(tmp_path):
    """## Why This Matters should NOT satisfy ## Why requirement."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    body = """## What Is It?

A SOP with wrong heading.

## Why This Matters

This is not the same as ## Why.

## When to Use

Use when needed.

## When NOT to Use

Do not use when not needed.

## Steps

1. Step one.
2. Step two."""
    _write_sop_with_body(rules_dir / "SOP-1000-SOP-Why-This-Matters.md", "1000", body)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "SOP missing required section: '## Why'" in result.output


def test_validate_sop_prefix_heading_prerequisites_setup(tmp_path):
    """## Prerequisites Setup should NOT trigger Examples requirement."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    body = """## What Is It?

A SOP with Prerequisites Setup (not Prerequisites).

## Why

This explains why.

## When to Use

Use when needed.

## When NOT to Use

Do not use when not needed.

## Prerequisites Setup

This is not the same as ## Prerequisites.

## Steps

1. Step one.
2. Step two."""
    _write_sop_with_body(rules_dir / "SOP-1000-SOP-Prereq-Setup.md", "1000", body)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    # ## Prerequisites Setup should NOT be treated as ## Prerequisites
    # So ## Examples should NOT be required
    assert result.exit_code == 0
    assert "0 issues found" in result.output


def test_validate_sop_prefix_heading_examples_notes(tmp_path):
    """## Examples Notes should NOT satisfy Examples requirement."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    body = """## What Is It?

A SOP with Examples Notes heading but not Examples.

## Why

This explains why.

## When to Use

Use when needed.

## When NOT to Use

Do not use when not needed.

## Prerequisites

- Item one

## Steps

1. Step one.
2. Step two.

## Examples Notes

This is not the same as ## Examples."""
    _write_sop_with_body(rules_dir / "SOP-1000-SOP-Examples-Notes.md", "1000", body)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "SOP missing required section: '## Examples'" in result.output


# -- FXA-2204 tests: workflow metadata validation for SOP docs --


def _write_sop_with_workflow(
    path,
    acid,
    wf_input="",
    wf_output="",
    wf_requires="",
    wf_provides="",
):
    """Write a valid SOP document with optional workflow metadata."""
    wf_lines = ""
    if wf_input:
        wf_lines += f"\n**Workflow input:** {wf_input}"
    if wf_output:
        wf_lines += f"\n**Workflow output:** {wf_output}"
    if wf_requires:
        wf_lines += f"\n**Workflow requires:** {wf_requires}"
    if wf_provides:
        wf_lines += f"\n**Workflow provides:** {wf_provides}"

    content = f"""# SOP-{acid}: Workflow Test

**Applies to:** Test
**Last updated:** 2026-03-14
**Last reviewed:** 2026-03-14
**Status:** Active{wf_lines}

---

## What Is It?

A test SOP for workflow validation.

## Why

Testing.

## When to Use

Testing.

## When NOT to Use

Not testing.

## Steps

1. Step one.
2. Step two.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-14 | Initial version | Test |
"""
    path.write_text(content)


def test_validate_valid_workflow_metadata_passes(tmp_path):
    """SOP with valid workflow metadata should report no issues."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    _write_sop_with_workflow(
        rules_dir / "SOP-3001-SOP-Valid-Workflow.md",
        "3001",
        wf_input="proposal:none",
        wf_output="proposal:draft",
        wf_requires="repo:clean",
        wf_provides="proposal:draft, proposal:editable",
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "0 issues found" in result.output


def test_validate_bad_token_format_reported(tmp_path):
    """SOP with invalid token format in workflow metadata should report error."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    _write_sop_with_workflow(
        rules_dir / "SOP-3002-SOP-Bad-Token.md",
        "3002",
        wf_input="BAD TOKEN!",
        wf_output="proposal:draft",
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "SOP-3002" in result.output
    assert "invalid token format" in result.output
    assert "BAD TOKEN!" in result.output


def test_validate_partial_signature_reported(tmp_path):
    """SOP with only Workflow input (no output) should report error."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    _write_sop_with_workflow(
        rules_dir / "SOP-3003-SOP-Partial-Sig.md",
        "3003",
        wf_input="proposal:none",
        wf_output="",
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "SOP-3003" in result.output
    assert "Workflow output is missing" in result.output


def test_validate_duplicate_provides_token_reported(tmp_path):
    """SOP with duplicate token in Workflow provides should report error."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    _write_sop_with_workflow(
        rules_dir / "SOP-3004-SOP-Dup-Provides.md",
        "3004",
        wf_input="proposal:none",
        wf_output="proposal:draft",
        wf_provides="proposal:draft, proposal:draft",
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "SOP-3004" in result.output
    assert "duplicate entry" in result.output
    assert "proposal:draft" in result.output


def test_validate_no_workflow_metadata_no_issue(tmp_path):
    """SOP without workflow metadata should pass (it's optional)."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    _write_sop_with_workflow(
        rules_dir / "SOP-3005-SOP-No-Workflow.md",
        "3005",
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "0 issues found" in result.output


def test_validate_json_output_exits_1_on_issues(tmp_path):
    """JSON output path should also exit with code 1 when issues exist."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    # Document with missing "Last reviewed" metadata
    invalid_content = """# SOP-1000: Invalid Doc

**Applies to:** All projects
**Last updated:** 2026-03-14
**Status:** Active

---

## What Is It?

Missing Last reviewed.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-14 | Initial version | Frank |
"""
    (rules_dir / "SOP-1000-SOP-Invalid-Doc.md").write_text(invalid_content)

    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--json", "--root", str(tmp_path)])

    assert result.exit_code == 1
    # JSON output should contain the invalid document
    import json

    output = json.loads(result.output)
    invalid_doc_ids = [r["doc_id"] for r in output["results"] if not r["valid"]]
    assert "SOP-1000" in invalid_doc_ids


def test_validate_history_header_early_return_arms():
    """_validate_history_header returns the documented diagnostic on malformed input.

    Exercises two early-return arms that user-visible behaviour depends on:
    - len(lines) < 2 (validate_cmd.py:60): header text is empty / single-line only.
    - not header_line (validate_cmd.py:70): multiple lines but no line starts with `|`.

    Pins the exact diagnostic strings so a regression that replaces them with an
    empty list (silently accepting malformed documents) is caught. Closes coverage
    gap at validate_cmd.py:60, 70.
    """
    from fx_alfred.commands.validate_cmd import _validate_history_header

    # Arm 1: empty input — .strip().split("\n") yields [""] (len == 1 < 2).
    assert _validate_history_header("") == [
        "Change History table header is missing or incomplete"
    ]

    # Arm 2: >= 2 lines but no line starts with `|`.
    assert _validate_history_header("Trailing text only\nMore text\n") == [
        "Change History table header is missing"
    ]


# ---------------------------------------------------------------------------
# FXA-2218 D2 + D3 — Cross-SOP Workflow loops validation
# ---------------------------------------------------------------------------


def _write_sop_with_cross_sop_loop(path, prefix, acid, title, to_ref):
    """Write an SOP with a cross-SOP Workflow loop referencing `to_ref`.

    Body has 3 numbered steps; from_step=3, to_step=to_ref, max=3.
    """
    content = f"""# SOP-{acid}: {title}

**Applies to:** Test
**Last updated:** 2026-04-19
**Last reviewed:** 2026-04-19
**Status:** Active
**Workflow loops:** [{{id: cx, from: 3, to: "{to_ref}", max_iterations: 3, condition: "if fail"}}]

---

## What Is It?

Test.

## Why

Test.

## When to Use

Test.

## When NOT to Use

Test.

## Steps

1. A
2. B
3. C

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-19 | Initial | — |
"""
    path.write_text(content)


def test_validate_cross_sop_target_missing(tmp_path):
    """D2: af validate reports cross-SOP loop pointing to nonexistent SOP."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    _write_sop_with_cross_sop_loop(
        rules_dir / "TST-2100-SOP-Source.md",
        "TST",
        "2100",
        "Source",
        to_ref="TST-9999.1",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "TST-9999" in result.output
    assert "no such SOP in corpus" in result.output


def test_validate_cross_sop_step_out_of_range(tmp_path):
    """D3: af validate reports cross-SOP step index beyond target's step count."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    # Target TST-2200 has 2 numbered steps; source references .99 (out of range).
    _write_valid_document(
        rules_dir / "TST-2200-SOP-Target.md",
        "TST",
        "2200",
        "SOP",
        "Target",
    )
    _write_sop_with_cross_sop_loop(
        rules_dir / "TST-2100-SOP-Source.md",
        "TST",
        "2100",
        "Source",
        to_ref="TST-2200.99",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])

    assert result.exit_code == 1
    # D3 now reports by index membership (PR #59 Codex P1) — diagnostic
    # lists the actual step indices found, not a count.
    assert "step index 99" in result.output
    assert "does not reference an existing step" in result.output
    assert "{1, 2}" in result.output


def test_validate_cross_sop_happy_path(tmp_path):
    """D2+D3 green when cross-SOP target exists and step index is in range."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    # Target TST-2200 has 2 steps; source references .1 (in range).
    _write_valid_document(
        rules_dir / "TST-2200-SOP-Target.md",
        "TST",
        "2200",
        "SOP",
        "Target",
    )
    _write_sop_with_cross_sop_loop(
        rules_dir / "TST-2100-SOP-Source.md",
        "TST",
        "2100",
        "Source",
        to_ref="TST-2200.1",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "0 issues found" in result.output


# ---------------------------------------------------------------------------
# PR #59 review fixes — sparse step numbering + non-SOP target filtering
# ---------------------------------------------------------------------------


def _write_sop_with_sparse_steps(path, prefix, acid, title):
    """Write an SOP whose ## Steps section has SPARSE numbering (1, 3, 5)."""
    content = f"""# SOP-{acid}: {title}

**Applies to:** Test
**Last updated:** 2026-04-19
**Last reviewed:** 2026-04-19
**Status:** Active

---

## What Is It?

Test.

## Why

Test.

## When to Use

Test.

## When NOT to Use

Test.

## Steps

1. A
3. C
5. E

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-19 | Initial | — |
"""
    path.write_text(content)


def test_validate_cross_sop_accepts_sparse_but_present_index(tmp_path):
    """D3 accepts a cross-SOP ref to a sparse but present step index
    (PR #59 Codex P1 — old range check rejected sparse hits > len)."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    _write_sop_with_sparse_steps(
        rules_dir / "TST-2200-SOP-Target.md", "TST", "2200", "Target"
    )
    # Step 5 — in the sparse set {1, 3, 5}, but > len (which is 3).
    _write_sop_with_cross_sop_loop(
        rules_dir / "TST-2100-SOP-Source.md",
        "TST",
        "2100",
        "Source",
        to_ref="TST-2200.5",
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "0 issues found" in result.output


def test_validate_cross_sop_rejects_sparse_gap_index(tmp_path):
    """D3 rejects a cross-SOP ref to a step that's <= len but NOT in the
    sparse set (PR #59 Codex P1 — old check accepted 2 for {1,3,5})."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    _write_sop_with_sparse_steps(
        rules_dir / "TST-2200-SOP-Target.md", "TST", "2200", "Target"
    )
    _write_sop_with_cross_sop_loop(
        rules_dir / "TST-2100-SOP-Source.md",
        "TST",
        "2100",
        "Source",
        to_ref="TST-2200.2",
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "step index 2" in result.output
    assert "does not reference an existing step" in result.output
    assert "{1, 3, 5}" in result.output


def test_validate_cross_sop_does_not_resolve_non_sop_target(tmp_path):
    """D2 only resolves cross-SOP refs against SOP-type documents; a PRP
    (or any non-SOP) sharing PREFIX-ACID must NOT count (PR #59 Codex P2)."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    _write_valid_document(
        rules_dir / "TST-2200-PRP-Not-A-SOP.md",
        "TST",
        "2200",
        "PRP",
        "Not A SOP",
        status="Draft",
    )
    _write_sop_with_cross_sop_loop(
        rules_dir / "TST-2100-SOP-Source.md",
        "TST",
        "2100",
        "Source",
        to_ref="TST-2200.1",
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "no such SOP in corpus" in result.output


def test_validate_cross_sop_ignores_indented_sub_items(tmp_path):
    """D3 must count only flush-left top-level steps, not indented sub-items
    or numbered lines inside indented blocks (PR #59 Codex P1 #2)."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    # Target SOP has 2 top-level steps (1, 2) plus indented numbered sub-
    # items (1, 2 under step 1). The old `_parse_steps_for_json` would have
    # accepted a ref to step "3" (counting sub-items), "4" etc. Ref to
    # step 3 here must be rejected.
    target_content = """# SOP-2200: Target With Sub Items

**Applies to:** Test
**Last updated:** 2026-04-19
**Last reviewed:** 2026-04-19
**Status:** Active

---

## What Is It?

Test.

## Why

Test.

## When to Use

Test.

## When NOT to Use

Test.

## Steps

1. Top-level A
  1. Sub-step of A
  2. Another sub-step of A
2. Top-level B

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-19 | Initial | — |
"""
    (rules_dir / "TST-2200-SOP-Target.md").write_text(target_content)

    # Reference step 3 — does not exist at top level (only 1, 2 do;
    # sub-items numbered 1, 2 don't count).
    _write_sop_with_cross_sop_loop(
        rules_dir / "TST-2100-SOP-Source.md",
        "TST",
        "2100",
        "Source",
        to_ref="TST-2200.3",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "step index 3" in result.output
    assert "does not reference an existing step" in result.output
    # Diagnostic lists top-level indices only ({1, 2}), not sub-item ones.
    assert "{1, 2}" in result.output


def test_validate_cross_sop_accepts_target_with_legacy_heading(tmp_path):
    """D3 must use the same heading-selection logic as plan rendering. If
    the target SOP uses a legacy heading like '## Rule' or '## Concepts'
    (recognised by the planner), D3 must resolve the section via the
    shared `extract_steps_section()` helper rather than hard-coding the
    literal string 'Steps' (PR #59 Codex review P2 #2).

    Note: the *overall* `af validate` run still fails on a legacy-heading
    SOP because the per-type REQUIRED_SECTIONS check is stricter than the
    planner. This test only asserts D3's specific diagnostic ('has no
    Steps section' for the cross-ref) is NOT emitted when the target has
    a legacy heading. The overall exit code is still 1 for unrelated
    reasons, but that's pre-existing behaviour out of this PR's scope."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    target_content = """# SOP-2200: Legacy Heading SOP

**Applies to:** Test
**Last updated:** 2026-04-19
**Last reviewed:** 2026-04-19
**Status:** Active

---

## What Is It?

Test.

## Why

Test.

## When to Use

Test.

## When NOT to Use

Test.

## Rule

1. Rule one
2. Rule two

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-19 | Initial | — |
"""
    (rules_dir / "TST-2200-SOP-Target.md").write_text(target_content)

    _write_sop_with_cross_sop_loop(
        rules_dir / "TST-2100-SOP-Source.md",
        "TST",
        "2100",
        "Source",
        to_ref="TST-2200.1",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    # The key D3 assertion: the cross-ref target now resolves via the shared
    # heading helper, so D3's "has no Steps section" diagnostic must NOT
    # appear on the SOURCE SOP.
    assert "Workflow loops[0].to" not in result.output or (
        "has no Steps section" not in result.output
    )
    # The cross-ref-specific "no such SOP in corpus" / "out of range"
    # diagnostics must also not fire.
    assert "no such SOP in corpus" not in result.output
    assert "does not reference an existing step" not in result.output


def test_validate_cross_sop_ignores_fenced_code_step_numbers(tmp_path):
    """D3 must not count numbered lines inside fenced code blocks as valid
    steps (PR #59 Codex review P2 #4). Cross-SOP ref to a fence-only
    index must be rejected."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    # Target SOP has 2 real top-level steps (1, 2) plus fenced code
    # containing lines that LOOK like numbered items (3., 4.).
    target_content = """# SOP-2200: Target With Fenced Code

**Applies to:** Test
**Last updated:** 2026-04-19
**Last reviewed:** 2026-04-19
**Status:** Active

---

## What Is It?

Test.

## Why

Test.

## When to Use

Test.

## When NOT to Use

Test.

## Steps

1. Real step one

```python
3. fake step in code
4. another fake step
```

2. Real step two

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-19 | Initial | — |
"""
    (rules_dir / "TST-2200-SOP-Target.md").write_text(target_content)

    # Ref to step 3 — only appears inside the fence, not a real step.
    _write_sop_with_cross_sop_loop(
        rules_dir / "TST-2100-SOP-Source.md",
        "TST",
        "2100",
        "Source",
        to_ref="TST-2200.3",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "step index 3" in result.output
    assert "does not reference an existing step" in result.output
    # Found set is {1, 2}, the fence lines don't contribute.
    assert "{1, 2}" in result.output


def test_validate_cross_sop_fence_delimiter_must_match(tmp_path):
    """D3 must track fence delimiters by type — a ``` fence is NOT closed
    by a literal ~~~ line inside it, and vice versa (PR #59 Codex review
    P2 #7). Before the fix, my simple `in_fence = not in_fence` toggle
    exited the fence prematurely on mismatched delimiters."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    # Target SOP: ```-fenced block contains a literal ~~~ line AND numbered
    # lines. Real top-level steps are {1, 2}. Lines "3." and "4." inside the
    # ```-fence must NOT be counted, even though a mismatched "~~~" appears
    # between them.
    target_content = """# SOP-2200: Mismatched Fence

**Applies to:** Test
**Last updated:** 2026-04-19
**Last reviewed:** 2026-04-19
**Status:** Active

---

## What Is It?

Test.

## Why

Test.

## When to Use

Test.

## When NOT to Use

Test.

## Steps

1. Real step one

```python
3. fake step in code
~~~ not a closer
4. another fake step
```

2. Real step two

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-19 | Initial | — |
"""
    (rules_dir / "TST-2200-SOP-Target.md").write_text(target_content)

    # Ref to step 3 — inside the mismatched-fence block. Must still be
    # rejected (the ~~~ does not close the ``` fence).
    _write_sop_with_cross_sop_loop(
        rules_dir / "TST-2100-SOP-Source.md",
        "TST",
        "2100",
        "Source",
        to_ref="TST-2200.3",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "step index 3" in result.output
    # Found set is still {1, 2} — all fence contents ignored.
    assert "{1, 2}" in result.output


def test_validate_cross_sop_fence_length_must_match_or_exceed(tmp_path):
    """D3 must honor CommonMark fence-length rules: a fence opened with 4
    backticks is NOT closed by 3 backticks inside it (PR #59 Codex review
    P2 #8). Closer must be the same delimiter char AND have length >=
    opener length."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    # Target SOP: ````-fenced block (4 backticks) with a 3-backtick line
    # inside. Real steps are {1, 2}. "3. fake" between the 3-tick line
    # and the 4-tick closer must not count.
    target_content = """# SOP-2200: 4-Tick Fence

**Applies to:** Test
**Last updated:** 2026-04-19
**Last reviewed:** 2026-04-19
**Status:** Active

---

## What Is It?

Test.

## Why

Test.

## When to Use

Test.

## When NOT to Use

Test.

## Steps

1. Real step one

````markdown
3. fake step inside the 4-tick fence
```
4. still inside fence (3-tick line is content)
````

2. Real step two

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-19 | Initial | — |
"""
    (rules_dir / "TST-2200-SOP-Target.md").write_text(target_content)

    _write_sop_with_cross_sop_loop(
        rules_dir / "TST-2100-SOP-Source.md",
        "TST",
        "2100",
        "Source",
        to_ref="TST-2200.3",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "step index 3" in result.output
    assert "{1, 2}" in result.output
