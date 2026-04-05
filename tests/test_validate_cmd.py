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
    invalid_docs = [r for r in output["results"] if not r["valid"]]
    assert len(invalid_docs) > 0
    assert invalid_docs[0]["doc_id"] == "SOP-1000"
