"""Tests for af validate command."""

from click.testing import CliRunner

from fx_alfred.cli import cli


def _write_valid_document(path, prefix, acid, type_code, title):
    """Write a valid Alfred document to path."""
    content = f"""# {type_code}-{acid}: {title}

**Applies to:** All projects
**Last updated:** 2026-03-14
**Last reviewed:** 2026-03-14

---

## What Is It?

This is a valid document.

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

---

## What Is It?

This document has mismatched H1.

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
