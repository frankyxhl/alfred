"""Validate command for af CLI -- validates all documents."""

import re
import sys
from importlib import resources
from pathlib import Path

import click

from fx_alfred.context import get_root, root_option
from fx_alfred.core.parser import H1_PATTERN, MalformedDocumentError, parse_metadata
from fx_alfred.core.scanner import (
    LayerValidationError,
    _scan_path_dir,
    _scan_pkg_dir,
    scan_documents,
)

# Pattern to extract type_code and ACID from H1 line
_H1_EXTRACT = re.compile(r"^# ([A-Z]{3})-(\d{4}): .+$")

# Base required metadata fields (fallback for unknown types)
_BASE_REQUIRED_FIELDS = {"Applies to", "Last updated", "Last reviewed"}

# Per-type required metadata fields
REQUIRED_FIELDS_BY_TYPE = {
    "SOP": {"Applies to", "Last updated", "Last reviewed", "Status"},
    "PRP": {"Applies to", "Last updated", "Last reviewed", "Status"},
    "CHG": {"Applies to", "Last updated", "Last reviewed", "Status"},
    "ADR": {"Applies to", "Last updated", "Last reviewed", "Status"},
    "REF": {"Applies to", "Last updated", "Last reviewed", "Status"},
    "PLN": {"Applies to", "Last updated", "Last reviewed", "Status"},
    "INC": {"Applies to", "Last updated", "Last reviewed", "Status"},
}

# Allowed Status values per document type
ALLOWED_STATUS = {
    "SOP": {"Active", "Draft", "Deprecated"},
    "PRP": {"Draft", "Approved", "Rejected", "Implemented"},
    "CHG": {"Proposed", "Approved", "In Progress", "Completed", "Rolled Back"},
    "ADR": {"Proposed", "Accepted", "Superseded", "Deprecated"},
    "PLN": {"Draft", "Active", "Completed", "Cancelled"},
    "INC": {"Open", "Resolved", "Monitoring"},
    "REF": {"Active", "Draft", "Deprecated"},
}

# Required Change History columns
REQUIRED_HISTORY_COLUMNS = ["Date", "Change", "By"]


def _scan_all_layers(root: Path):
    """Scan all layers without raising on layer violations.

    Returns the document list even when layer invariants are broken,
    so that validate can report them as issues instead of aborting.
    """
    docs = []
    pkg_rules = resources.files("fx_alfred").joinpath("rules")
    docs.extend(_scan_pkg_dir(pkg_rules))
    user_alfred = Path.home() / ".alfred"
    docs.extend(_scan_path_dir(user_alfred, source="usr", recursive=True))
    rules_path = root / "rules"
    docs.extend(_scan_path_dir(rules_path, source="prj"))
    return docs


def _validate_history_header(header: str) -> list[str]:
    """Validate Change History table header has required columns."""
    issues = []

    # Header format: "## Change History\n| Date | Change | By |\n|---|---|---|"
    lines = header.strip().split("\n")
    if len(lines) < 2:
        return ["Change History table header is missing or incomplete"]

    # Find the table header line (first line starting with |)
    header_line = None
    for line in lines:
        if line.strip().startswith("|"):
            header_line = line.strip()
            break

    if not header_line:
        return ["Change History table header is missing"]

    # Parse the columns from the header
    # Format: | Date | Change | By |
    cells = [c.strip() for c in header_line.split("|") if c.strip()]

    for col in REQUIRED_HISTORY_COLUMNS:
        if col not in cells:
            issues.append(f"Change History table missing required column: '{col}'")

    return issues


_EPILOG = """\
Examples:

  af validate                      # check all documents
  af validate --root myproj        # check specific project

Checks:
  - H1 format matches filename (type, ACID, title) [skip for ACID=0000]
  - Per-type required metadata fields (incl. Status)
  - Status value validation against allowed values per type
  - Change History table has Date, Change, By columns
  - COR-* documents only in PKG layer

Exit code 0 if clean, 1 if issues found.
"""


@click.command("validate", epilog=_EPILOG)
@root_option
@click.pass_context
def validate_cmd(ctx: click.Context):
    """Validate all documents for structural correctness."""
    root = get_root(ctx)
    try:
        docs = scan_documents(root)
    except LayerValidationError:
        # Layer violations found -- re-scan without validation so we can
        # report them as per-document issues instead of aborting.
        docs = _scan_all_layers(root)

    issues_by_doc: dict[str, list[str]] = {}

    for doc in docs:
        doc_id = f"{doc.prefix}-{doc.acid}"
        issues: list[str] = []

        # Check 0: COR documents must only exist in PKG layer
        if doc.prefix == "COR" and doc.source != "pkg":
            issues.append(f"COR document found in non-PKG layer ({doc.source})")

        try:
            content = doc.resolve_resource().read_text()
        except Exception:
            issues_by_doc[doc_id] = ["Could not read document"]
            continue

        lines = content.split("\n")
        if not lines:
            issues_by_doc[doc_id] = ["Empty document"]
            continue

        h1_line = lines[0]
        is_index = doc.acid == "0000"

        # Check 1 & 2: H1 format (skip for ACID=0000 index documents)
        if not is_index:
            if not H1_PATTERN.match(h1_line):
                issues.append(f"H1 does not match expected format: {h1_line!r}")
            else:
                # Check 2: type_code and ACID in H1 must match filename
                match = _H1_EXTRACT.match(h1_line)
                if match:
                    h1_type_code = match.group(1)
                    h1_acid = match.group(2)
                    if h1_type_code != doc.type_code:
                        issues.append(
                            f"H1 type_code '{h1_type_code}' does not match "
                            f"filename type_code '{doc.type_code}'"
                        )
                    if h1_acid != doc.acid:
                        issues.append(
                            f"H1 ACID '{h1_acid}' does not match filename ACID '{doc.acid}'"
                        )

        # Check 3: Required metadata fields present
        # Check 4: Change History table structure valid
        # Check 5: Status value validation
        try:
            # For ACID=0000 documents with non-standard H1, substitute a
            # dummy H1 so the parser can extract metadata without failing.
            parse_content = content
            if is_index and not H1_PATTERN.match(h1_line):
                dummy_h1 = f"# {doc.type_code}-{doc.acid}: Index"
                parse_content = dummy_h1 + content[len(h1_line) :]

            parsed = parse_metadata(parse_content)
            found_fields = {mf.key for mf in parsed.metadata_fields}

            # Look up required fields for this document type
            required = REQUIRED_FIELDS_BY_TYPE.get(doc.type_code, _BASE_REQUIRED_FIELDS)
            missing = required - found_fields
            for field in sorted(missing):
                issues.append(f"Missing required metadata field: '{field}'")

            # Validate Status value if present
            status_field = next(
                (mf for mf in parsed.metadata_fields if mf.key == "Status"), None
            )
            if status_field is not None:
                status_val = status_field.value
                allowed = ALLOWED_STATUS.get(doc.type_code)
                if allowed is not None:
                    if "(" in status_val or ")" in status_val:
                        issues.append(
                            f"Invalid Status value '{status_val}' for type "
                            f"{doc.type_code} (allowed: "
                            f"{', '.join(sorted(allowed))})"
                        )
                    elif status_val not in allowed:
                        issues.append(
                            f"Invalid Status value '{status_val}' for type "
                            f"{doc.type_code} (allowed: "
                            f"{', '.join(sorted(allowed))})"
                        )

            # Validate Change History table header
            if parsed.history_header:
                history_issues = _validate_history_header(parsed.history_header)
                issues.extend(history_issues)
            else:
                issues.append("Missing Change History table")
        except MalformedDocumentError as e:
            # Report parsing error as an issue, don't crash
            issues.append(f"Malformed document: {e}")

        if issues:
            issues_by_doc[doc_id] = issues

    # Report issues
    for doc_id, doc_issues in issues_by_doc.items():
        click.echo(f"{doc_id}:")
        for issue in doc_issues:
            click.echo(f"  - {issue}")

    total_issues = sum(len(i) for i in issues_by_doc.values())
    click.echo(f"{len(docs)} documents checked, {total_issues} issues found.")

    # Exit with code 1 if issues found
    if total_issues > 0:
        sys.exit(1)
