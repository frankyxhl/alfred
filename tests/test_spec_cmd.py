"""Tests for af create --spec and af update --spec (FXA-2143)."""

import pytest
from click.testing import CliRunner

from fx_alfred.cli import cli


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def spec_project(tmp_path):
    """Create a minimal project with rules/ directory."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    return tmp_path


# ─────────────────────────────────────────────────────────────────────────────
# Test: create with valid spec
# ─────────────────────────────────────────────────────────────────────────────


def test_create_spec_valid(spec_project, monkeypatch):
    """Create with YAML spec passes af validate."""
    monkeypatch.chdir(spec_project)

    # Write spec file
    spec_file = spec_project / "spec.yaml"
    spec_file.write_text(
        """type: SOP
prefix: TST
acid: "2100"
title: Release Build Workflow
metadata:
  Applies to: TST project
  Status: Draft
  Last updated: "2026-03-22"
  Last reviewed: "2026-03-22"
sections:
  What Is It?: Covers release.
  Why: Ensures quality.
  When to Use: Before releases.
  When NOT to Use: For hotfixes.
  Steps:
    - Prepare branch
    - Run tests
"""
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "--spec", str(spec_file)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, f"Output: {result.output}"

    # File should be created
    created = spec_project / "rules" / "TST-2100-SOP-Release-Build-Workflow.md"
    assert created.exists()

    # Validate should pass
    validate_result = runner.invoke(
        cli,
        ["validate", "--root", str(spec_project)],
        catch_exceptions=False,
    )
    assert validate_result.exit_code == 0, f"Validate output: {validate_result.output}"
    assert "0 issues found" in validate_result.output


# ─────────────────────────────────────────────────────────────────────────────
# Test: create spec invalid status
# ─────────────────────────────────────────────────────────────────────────────


def test_create_spec_invalid_status(spec_project, monkeypatch):
    """Status 'InProgress' rejected for SOP."""
    monkeypatch.chdir(spec_project)

    spec_file = spec_project / "spec.yaml"
    spec_file.write_text(
        """type: SOP
prefix: TST
acid: "2100"
title: Bad Status
metadata:
  Applies to: TST project
  Status: InProgress
  Last updated: "2026-03-22"
  Last reviewed: "2026-03-22"
sections:
  What Is It?: Test
  Why: Test
  When to Use: Test
  When NOT to Use: Test
  Steps:
    - Step 1
"""
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "--spec", str(spec_file)],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert (
        "Status 'InProgress' not allowed for SOP; allowed: Draft, Active, Deprecated"
        in result.output
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test: create spec missing required section
# ─────────────────────────────────────────────────────────────────────────────


def test_create_spec_missing_required_section(spec_project, monkeypatch):
    """Missing 'Why' section rejected for SOP."""
    monkeypatch.chdir(spec_project)

    spec_file = spec_project / "spec.yaml"
    spec_file.write_text(
        """type: SOP
prefix: TST
acid: "2100"
title: Missing Section
metadata:
  Applies to: TST project
  Status: Draft
  Last updated: "2026-03-22"
  Last reviewed: "2026-03-22"
sections:
  What Is It?: Test
  When to Use: Test
  When NOT to Use: Test
  Steps:
    - Step 1
"""
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "--spec", str(spec_file)],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "Required section 'Why' missing for SOP" in result.output


# ─────────────────────────────────────────────────────────────────────────────
# Test: create spec invalid doc type
# ─────────────────────────────────────────────────────────────────────────────


def test_create_spec_invalid_doc_type(spec_project, monkeypatch):
    """Unknown document type 'FOO' rejected."""
    monkeypatch.chdir(spec_project)

    spec_file = spec_project / "spec.yaml"
    spec_file.write_text(
        """type: FOO
prefix: TST
acid: "2100"
title: Bad Type
metadata:
  Applies to: TST project
  Status: Draft
  Last reviewed: "2026-03-22"
sections:
  What Is It?: Test
"""
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "--spec", str(spec_file)],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    # Types are sorted alphabetically in the error message
    assert "Unknown document type 'FOO'" in result.output
    assert "valid:" in result.output


# ─────────────────────────────────────────────────────────────────────────────
# Test: create spec dry run
# ─────────────────────────────────────────────────────────────────────────────


def test_create_spec_dry_run(spec_project, monkeypatch):
    """Dry run prints content without writing file."""
    monkeypatch.chdir(spec_project)

    spec_file = spec_project / "spec.yaml"
    spec_file.write_text(
        """type: SOP
prefix: TST
acid: "2100"
title: Dry Run Test
metadata:
  Applies to: TST project
  Status: Draft
  Last updated: "2026-03-22"
  Last reviewed: "2026-03-22"
sections:
  What Is It?: Test
  Why: Test
  When to Use: Test
  When NOT to Use: Test
  Steps:
    - Step 1
"""
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "--spec", str(spec_file), "--dry-run"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "Dry run" in result.output
    # File should NOT be created
    assert not (spec_project / "rules" / "TST-2100-SOP-Dry-Run-Test.md").exists()


# ─────────────────────────────────────────────────────────────────────────────
# Test: create existing CLI still works
# ─────────────────────────────────────────────────────────────────────────────


def test_create_existing_cli_still_works(spec_project, monkeypatch):
    """af create sop --prefix TST --acid 2100 --title "My SOP" still works."""
    monkeypatch.chdir(spec_project)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--acid", "2100", "--title", "My SOP"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert (spec_project / "rules" / "TST-2100-SOP-My-SOP.md").exists()


# ─────────────────────────────────────────────────────────────────────────────
# Test: update spec patch metadata
# ─────────────────────────────────────────────────────────────────────────────


def test_update_spec_patch_metadata(spec_project, monkeypatch):
    """Patch metadata preserves unchanged sections."""
    monkeypatch.chdir(spec_project)

    # Create initial document
    rules = spec_project / "rules"
    doc = rules / "TST-2100-SOP-Test-Document.md"
    doc.write_text(
        """# SOP-2100: Test Document

**Applies to:** Old value
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---

## What Is It?

Original content.

## Why

Original why.

## When to Use

When to use content.

## When NOT to Use

When not to use content.

## Steps

1. Original step

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
"""
    )

    # Create patch spec
    spec_file = spec_project / "patch.yaml"
    spec_file.write_text(
        """metadata:
  Applies to: New value
  Status: Active
"""
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--spec", str(spec_file)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, f"Output: {result.output}"

    # Read updated content
    content = doc.read_text()
    assert "**Applies to:** New value" in content
    assert "**Status:** Active" in content
    # Unchanged sections preserved
    assert "Original content." in content
    assert "Original why." in content


# ─────────────────────────────────────────────────────────────────────────────
# Test: update spec patch sections
# ─────────────────────────────────────────────────────────────────────────────


def test_update_spec_patch_sections(spec_project, monkeypatch):
    """Patch sections preserves unchanged sections."""
    monkeypatch.chdir(spec_project)

    # Create initial document
    rules = spec_project / "rules"
    doc = rules / "TST-2100-SOP-Test-Document.md"
    doc.write_text(
        """# SOP-2100: Test Document

**Applies to:** All
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---

## What Is It?

Original content.

## Why

Original why.

## When to Use

When to use content.

## When NOT to Use

When not to use content.

## Steps

1. Original step

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
"""
    )

    # Create patch spec
    spec_file = spec_project / "patch.yaml"
    spec_file.write_text(
        """sections:
  Steps:
    - Updated step 1
    - Updated step 2
"""
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--spec", str(spec_file)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, f"Output: {result.output}"

    # Read updated content
    content = doc.read_text()
    assert "Updated step 1" in content
    assert "Updated step 2" in content
    # Unchanged sections preserved
    assert "Original why." in content
    assert "Original content." in content


# ─────────────────────────────────────────────────────────────────────────────
# Test: update spec invalid status
# ─────────────────────────────────────────────────────────────────────────────


def test_update_spec_invalid_status(spec_project, monkeypatch):
    """Invalid Status in patch rejected."""
    monkeypatch.chdir(spec_project)

    # Create initial document
    rules = spec_project / "rules"
    doc = rules / "TST-2100-SOP-Test-Document.md"
    doc.write_text(
        """# SOP-2100: Test Document

**Applies to:** All
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---

## What Is It?

Test

## Why

Test

## When to Use

Test

## When NOT to Use

Test

## Steps

1. Test

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
"""
    )

    # Create patch spec with invalid status
    spec_file = spec_project / "patch.yaml"
    spec_file.write_text(
        """metadata:
  Status: InProgress
"""
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--spec", str(spec_file)],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert (
        "Status 'InProgress' not allowed for SOP; allowed: Draft, Active, Deprecated"
        in result.output
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test: update spec dry run
# ─────────────────────────────────────────────────────────────────────────────


def test_update_spec_dry_run(spec_project, monkeypatch):
    """Dry run does not write file."""
    monkeypatch.chdir(spec_project)

    # Create initial document
    rules = spec_project / "rules"
    doc = rules / "TST-2100-SOP-Test-Document.md"
    original_content = """# SOP-2100: Test Document

**Applies to:** Old value
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---

## What Is It?

Original content.

## Why

Original why.

## When to Use

When to use content.

## When NOT to Use

When not to use content.

## Steps

1. Original step

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
"""
    doc.write_text(original_content)

    # Create patch spec
    spec_file = spec_project / "patch.yaml"
    spec_file.write_text(
        """metadata:
  Status: Active
"""
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--spec", str(spec_file), "--dry-run"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "Dry run" in result.output
    # File should not be modified
    assert doc.read_text() == original_content


# ─────────────────────────────────────────────────────────────────────────────
# Test: create spec missing required metadata field
# ─────────────────────────────────────────────────────────────────────────────


def test_create_spec_missing_required_metadata(spec_project, monkeypatch):
    """Missing 'Applies to' metadata field rejected."""
    monkeypatch.chdir(spec_project)

    spec_file = spec_project / "spec.yaml"
    spec_file.write_text(
        """type: SOP
prefix: TST
acid: "2100"
title: Missing Metadata
metadata:
  Status: Draft
  Last updated: "2026-03-22"
  Last reviewed: "2026-03-22"
sections:
  What Is It?: Test
  Why: Test
  When to Use: Test
  When NOT to Use: Test
  Steps:
    - Step 1
"""
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "--spec", str(spec_file)],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "Required metadata field 'Applies to' missing for SOP" in result.output


# ─────────────────────────────────────────────────────────────────────────────
# Test: update spec adds new metadata field
# ─────────────────────────────────────────────────────────────────────────────


def test_update_spec_adds_new_metadata_field(spec_project, monkeypatch):
    """Spec can add a new metadata field not currently in the document."""
    monkeypatch.chdir(spec_project)

    rules = spec_project / "rules"
    doc = rules / "TST-2100-SOP-Test-Document.md"
    doc.write_text(
        """# SOP-2100: Test Document

**Applies to:** All
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---

## What Is It?

Original content.

## Why

Original why.

## When to Use

When to use content.

## When NOT to Use

When not to use content.

## Steps

1. Original step

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
"""
    )

    spec_file = spec_project / "patch.yaml"
    spec_file.write_text(
        """metadata:
  Custom field: new value
"""
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--spec", str(spec_file)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, f"Output: {result.output}"

    content = doc.read_text()
    assert "**Custom field:** new value" in content


# ─────────────────────────────────────────────────────────────────────────────
# Test: update spec missing section raises error
# ─────────────────────────────────────────────────────────────────────────────


def test_update_spec_missing_section_raises_error(spec_project, monkeypatch):
    """Spec sections referencing a non-existent section raises an error."""
    monkeypatch.chdir(spec_project)

    rules = spec_project / "rules"
    doc = rules / "TST-2100-SOP-Test-Document.md"
    doc.write_text(
        """# SOP-2100: Test Document

**Applies to:** All
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---

## What Is It?

Original content.

## Why

Original why.

## When to Use

When to use content.

## When NOT to Use

When not to use content.

## Steps

1. Original step

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
"""
    )

    spec_file = spec_project / "patch.yaml"
    spec_file.write_text(
        """sections:
  Nonexistent Section: some content
"""
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--spec", str(spec_file)],
    )
    assert result.exit_code != 0
    assert "not found in document" in result.output


# ─────────────────────────────────────────────────────────────────────────────
# REGRESSION TEST: Bug A - idempotent section update should not error
# ─────────────────────────────────────────────────────────────────────────────


def test_update_spec_idempotent_section_update_succeeds(spec_project, monkeypatch):
    """Updating a section with identical content should succeed, not error.

    Bug A: _replace_section_in_body returned only str, comparing with original
    body would fail when update was idempotent (same content). Fixed by
    returning tuple[str, bool] to explicitly indicate whether section was found.
    """
    monkeypatch.chdir(spec_project)

    rules = spec_project / "rules"
    doc = rules / "TST-2100-SOP-Test-Document.md"
    doc.write_text(
        """# SOP-2100: Test Document

**Applies to:** All
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---

## What Is It?

Original content.

## Why

Original why.

## When to Use

When to use content.

## When NOT to Use

When not to use content.

## Steps

1. Original step

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
"""
    )

    # Patch with IDENTICAL content to What Is It? section
    spec_file = spec_project / "patch.yaml"
    spec_file.write_text(
        """sections:
  What Is It?: Original content.
"""
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--spec", str(spec_file)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, f"Output: {result.output}"
    # Content should be unchanged
    assert "Original content." in doc.read_text()


# ─────────────────────────────────────────────────────────────────────────────
# REGRESSION TEST: Bug B - new metadata field inherits existing prefix_style
# ─────────────────────────────────────────────────────────────────────────────


def test_update_spec_new_field_inherits_prefix_style(spec_project, monkeypatch):
    """New metadata field should infer prefix_style from existing fields.

    Bug B: prefix_style was hardcoded to 'bold' when adding new fields via spec.
    Fixed by inferring from first existing metadata field's prefix_style.
    """
    monkeypatch.chdir(spec_project)

    rules = spec_project / "rules"
    doc = rules / "TST-2100-SOP-Test-Document.md"
    # Use list style for existing fields (valid prefix_style values: "bold", "list")
    doc.write_text(
        """# SOP-2100: Test Document

- **Applies to:** All
- **Last updated:** 2026-01-01
- **Last reviewed:** 2026-01-01
- **Status:** Draft

---

## What Is It?

Original content.

## Why

Original why.

## When to Use

When to use content.

## When NOT to Use

When not to use content.

## Steps

1. Original step

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
"""
    )

    spec_file = spec_project / "patch.yaml"
    spec_file.write_text(
        """metadata:
  Custom field: new value
"""
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--spec", str(spec_file)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, f"Output: {result.output}"

    content = doc.read_text()
    # New field should use list style, not bold
    assert "- **Custom field:** new value" in content
    assert "**Custom field:**" not in content or "- **Custom field:**" in content


# ─────────────────────────────────────────────────────────────────────────────
# ROUND 4: Issue 1 — Malformed YAML raises user-friendly error
# ─────────────────────────────────────────────────────────────────────────────


def test_update_spec_malformed_yaml_raises_error(spec_project, monkeypatch):
    """Malformed YAML in spec file produces a user-friendly ClickException, not a raw traceback."""
    monkeypatch.chdir(spec_project)

    rules = spec_project / "rules"
    doc = rules / "TST-2100-SOP-Test-Document.md"
    doc.write_text(
        """# SOP-2100: Test Document

**Applies to:** All
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---

## What Is It?

Content.

## Why

Why content.

## When to Use

When content.

## When NOT to Use

When not content.

## Steps

1. Step

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
"""
    )

    spec_file = spec_project / "bad.yaml"
    spec_file.write_text("metadata: [unterminated\n")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--spec", str(spec_file)],
    )
    assert result.exit_code != 0
    assert "Invalid YAML" in result.output


def test_create_spec_malformed_yaml_raises_error(spec_project, monkeypatch):
    """Malformed YAML in spec file for create produces a user-friendly ClickException."""
    monkeypatch.chdir(spec_project)

    spec_file = spec_project / "bad.yaml"
    spec_file.write_text("metadata: [unterminated\n")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "--spec", str(spec_file)],
    )
    assert result.exit_code != 0
    assert "Invalid YAML" in result.output


# ─────────────────────────────────────────────────────────────────────────────
# ROUND 4: Issue 2 — Nested spec payloads validated as mappings
# ─────────────────────────────────────────────────────────────────────────────


def test_update_spec_metadata_not_mapping_raises_error(spec_project, monkeypatch):
    """Spec with 'metadata' as a list raises a user-friendly error."""
    monkeypatch.chdir(spec_project)

    rules = spec_project / "rules"
    doc = rules / "TST-2100-SOP-Test-Document.md"
    doc.write_text(
        """# SOP-2100: Test Document

**Applies to:** All
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---

## What Is It?

Content.

## Why

Why content.

## When to Use

When content.

## When NOT to Use

When not content.

## Steps

1. Step

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
"""
    )

    spec_file = spec_project / "bad_meta.yaml"
    spec_file.write_text("metadata:\n  - Applies to\n  - Status\n")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--spec", str(spec_file)],
    )
    assert result.exit_code != 0
    assert "must be a mapping" in result.output


# ─────────────────────────────────────────────────────────────────────────────
# ROUND 4: Issue 3 — create --spec enforces acid/area mutual exclusivity
# ─────────────────────────────────────────────────────────────────────────────


def test_create_spec_acid_and_area_raises_error(spec_project, monkeypatch):
    """Spec containing both 'acid' and 'area' raises a user-friendly error."""
    monkeypatch.chdir(spec_project)

    spec_file = spec_project / "both.yaml"
    spec_file.write_text(
        """type: SOP
prefix: TST
acid: "2100"
area: "21"
title: Conflicting ACID and Area
metadata:
  Applies to: TST project
  Status: Draft
  Last updated: "2026-03-22"
  Last reviewed: "2026-03-22"
sections:
  What Is It?: Test
  Why: Test
  When to Use: Test
  When NOT to Use: Test
  Steps:
    - Step 1
"""
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "--spec", str(spec_file)],
    )
    assert result.exit_code != 0
    assert "acid" in result.output.lower() and "area" in result.output.lower()


# ─────────────────────────────────────────────────────────────────────────────
# ROUND 5: Issue 1 — CLI --field/--status overrides spec metadata
# ─────────────────────────────────────────────────────────────────────────────


def test_update_spec_cli_overrides_spec_field(spec_project, monkeypatch):
    """When both --field and spec metadata set the same key, CLI wins."""
    monkeypatch.chdir(spec_project)

    rules = spec_project / "rules"
    doc = rules / "TST-2100-SOP-Test-Document.md"
    doc.write_text(
        """# SOP-2100: Test Document

**Applies to:** All
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---

## What Is It?

Content.

## Why

Why content.

## When to Use

When content.

## When NOT to Use

When not content.

## Steps

1. Step

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
"""
    )

    spec_file = spec_project / "patch.yaml"
    spec_file.write_text(
        """metadata:
  Status: Draft
"""
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--field", "Status", "Active", "--spec", str(spec_file)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, f"Output: {result.output}"

    content = doc.read_text()
    # CLI --field Status Active must win over spec Status: Draft
    assert "**Status:** Active" in content


# ─────────────────────────────────────────────────────────────────────────────
# ROUND 5: Issue 2 — Mixed-source acid/area conflict raises error
# ─────────────────────────────────────────────────────────────────────────────


def test_create_spec_cli_acid_with_spec_area_raises_error(spec_project, monkeypatch):
    """--acid on CLI + area in spec raises conflict error."""
    monkeypatch.chdir(spec_project)

    spec_file = spec_project / "mixed.yaml"
    spec_file.write_text(
        """type: SOP
prefix: TST
area: "21"
title: Mixed Conflict
metadata:
  Applies to: TST project
  Status: Draft
  Last updated: "2026-03-22"
  Last reviewed: "2026-03-22"
sections:
  What Is It?: Test
  Why: Test
  When to Use: Test
  When NOT to Use: Test
  Steps:
    - Step 1
"""
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "--spec", str(spec_file), "--acid", "0042"],
    )
    assert result.exit_code != 0
    assert "acid" in result.output.lower() and "area" in result.output.lower()


# ─────────────────────────────────────────────────────────────────────────────
# ROUND 6: Validation-order bug — spec Status validated before CLI merge
# ─────────────────────────────────────────────────────────────────────────────


def _make_sop_doc(rules: object) -> object:
    """Helper: write a minimal valid SOP document and return the Path."""
    doc = rules / "TST-2100-SOP-Test-Document.md"
    doc.write_text(
        """# SOP-2100: Test Document

**Applies to:** All
**Last updated:** 2026-01-01
**Last reviewed:** 2026-01-01
**Status:** Draft

---

## What Is It?

Content.

## Why

Why content.

## When to Use

When content.

## When NOT to Use

When not content.

## Steps

1. Step

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-01-01 | Initial version | Author |
"""
    )
    return doc


def test_update_spec_invalid_status_overridden_by_cli_succeeds(
    spec_project, monkeypatch
):
    """CLI --field Status Active overrides spec Status: InProgress; effective value is valid.

    Round 6 bug: _validate_spec_status fired on the raw spec value BEFORE the
    CLI merge, so even though the effective Status after merge was valid (Active),
    the command raised 'InProgress not allowed for SOP'.  Fix: validate AFTER
    computing field_updates = {**spec_field_updates, **cli_field_updates}.
    """
    monkeypatch.chdir(spec_project)

    rules = spec_project / "rules"
    _make_sop_doc(rules)

    spec_file = spec_project / "patch.yaml"
    spec_file.write_text(
        """metadata:
  Status: InProgress
"""
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--field", "Status", "Active", "--spec", str(spec_file)],
        catch_exceptions=False,
    )
    # CLI override makes effective Status = Active (valid for SOP) — must succeed
    assert result.exit_code == 0, f"Output: {result.output}"

    content = (rules / "TST-2100-SOP-Test-Document.md").read_text()
    assert "**Status:** Active" in content


def test_update_spec_invalid_status_without_override_fails(spec_project, monkeypatch):
    """Spec Status: InProgress with no CLI override still fails with 'not allowed'.

    Complements the previous test: when there is no CLI override, the effective
    Status remains InProgress (invalid for SOP) and the command must reject it.
    """
    monkeypatch.chdir(spec_project)

    rules = spec_project / "rules"
    _make_sop_doc(rules)

    spec_file = spec_project / "patch.yaml"
    spec_file.write_text(
        """metadata:
  Status: InProgress
"""
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["update", "TST-2100", "--spec", str(spec_file)],
    )
    assert result.exit_code != 0
    assert "not allowed" in result.output
