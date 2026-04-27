"""Validate command for af CLI -- validates all documents."""

import json
import re
import sys
from importlib import resources
from pathlib import Path

import click

from fx_alfred.context import get_root, root_option
from fx_alfred.core.schema import (
    ALLOWED_STATUSES,
    REQUIRED_METADATA,
    REQUIRED_SECTIONS,
    DocType,
)
from fx_alfred.core.document import Document
from fx_alfred.core.parser import H1_PATTERN, MalformedDocumentError, parse_metadata
from fx_alfred.core.scanner import (
    LayerValidationError,
    _scan_path_dir,
    _scan_pkg_dir,
    scan_documents,
)
from fx_alfred.core.steps import (
    extract_steps_section,
    parse_top_level_step_indices,
)
from fx_alfred.core.workflow import (
    parse_workflow_branches,
    parse_workflow_loops,
    parse_workflow_signature,
    validate_branches,
    validate_workflow_signature,
)

# Base required metadata fields (fallback for unknown types)
_BASE_REQUIRED_FIELDS = {"Applies to", "Last updated", "Last reviewed"}

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
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def validate_cmd(ctx: click.Context, output_json: bool):
    """Validate all documents for structural correctness."""
    root = get_root(ctx)
    try:
        docs = scan_documents(root)
    except LayerValidationError:
        # Layer violations found -- re-scan without validation so we can
        # report them as per-document issues instead of aborting.
        docs = _scan_all_layers(root)

    issues_by_doc: dict[str, list[str]] = {}

    # Corpus-wide lookup table for cross-SOP reference resolution (FXA-2218 D2/D3).
    # Only SOPs are valid cross-SOP targets — filter out PRP/CHG/REF/etc. so a
    # `Workflow loops.to = "FXA-2217.3"` pointing at a PRP doesn't falsely
    # resolve (PR #59 Codex review P2).
    docs_by_id: dict[tuple[str, str], Document] = {
        (d.prefix, d.acid): d for d in docs if d.type_code == "SOP"
    }

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
                match = H1_PATTERN.match(h1_line)
                if match:
                    h1_type_code = match.group("type_code")
                    h1_acid = match.group("acid")
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
            try:
                required = set(
                    REQUIRED_METADATA.get(
                        DocType(doc.type_code), list(_BASE_REQUIRED_FIELDS)
                    )
                )
            except ValueError:
                required = _BASE_REQUIRED_FIELDS
            missing = required - found_fields
            for field in sorted(missing):
                issues.append(f"Missing required metadata field: '{field}'")

            # Validate Status value if present
            status_field = next(
                (mf for mf in parsed.metadata_fields if mf.key == "Status"), None
            )
            if status_field is not None:
                status_val = status_field.value
                try:
                    allowed: set[str] | None = set(
                        ALLOWED_STATUSES.get(DocType(doc.type_code), [])
                    )
                except ValueError:
                    allowed = None
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

            # Validate Tags field format (if present)
            tag_field = next(
                (mf for mf in parsed.metadata_fields if mf.key == "Tags"), None
            )
            if tag_field is not None:
                raw_parts = [t.strip() for t in tag_field.value.split(",")]
                if any(not part for part in raw_parts):
                    issues.append("Tags field contains empty tag values")
                lowered = [t.lower() for t in raw_parts if t]
                if len(lowered) != len(set(lowered)):
                    issues.append("Tags field contains duplicate tags")

            # Validate Change History table header
            if parsed.history_header:
                history_issues = _validate_history_header(parsed.history_header)
                issues.extend(history_issues)
            else:
                issues.append("Missing Change History table")

            # Check 6: SOP required sections (skip PKG layer COR-* docs)
            if doc.type_code == "SOP" and doc.source != "pkg" and parsed.body:
                body_text = parsed.body
                required_sections = [
                    f"## {name}" for name in REQUIRED_SECTIONS.get(DocType.SOP, [])
                ]
                for section in required_sections:
                    if not re.search(
                        rf"^{re.escape(section)}\s*$", body_text, re.MULTILINE
                    ):
                        issues.append(f"SOP missing required section: '{section}'")

                # Conditional: Examples required if Prerequisites or > 5 Steps
                has_prerequisites = bool(
                    re.search(r"^## Prerequisites\s*$", body_text, re.MULTILINE)
                )
                has_steps = bool(re.search(r"^## Steps", body_text, re.MULTILINE))
                steps_section = body_text.split("## Steps")[-1] if has_steps else ""
                next_heading = steps_section.find("\n## ")
                if next_heading > 0:
                    steps_section = steps_section[:next_heading]
                step_count = len(re.findall(r"^\d+\.", steps_section, re.MULTILINE))

                if (has_prerequisites or step_count > 5) and not re.search(
                    r"^## Examples\s*$", body_text, re.MULTILINE
                ):
                    issues.append(
                        "SOP missing required section: '## Examples' "
                        "(has Prerequisites or > 5 Steps)"
                    )

            # Check 7: Workflow metadata validation (SOP only, optional)
            if doc.type_code == "SOP":
                sig = parse_workflow_signature(parsed)
                if sig is not None:
                    wf_errors = validate_workflow_signature(sig)
                    issues.extend(wf_errors)

                # Check 8b: Workflow branches (FXA-2226 Path B). Parse + validate.
                # Until CHG-2227 Phase 8a flips the renderer-readiness gate,
                # any production SOP authoring this field is rejected.
                try:
                    branches = parse_workflow_branches(parsed)
                except MalformedDocumentError as exc:
                    issues.append(str(exc))
                    branches = []
                for berr in validate_branches(parsed, branches):
                    issues.append(berr.msg)

                # Check 8: Cross-SOP workflow loop references (FXA-2218 D2/D3)
                # For each Workflow loops entry whose `to` is a cross-SOP ref,
                # verify the target SOP exists in the corpus and the step
                # index is within range of the target's numbered steps.
                loops = parse_workflow_loops(parsed)
                for i, loop in enumerate(loops):
                    target = loop.cross_sop_target()
                    if target is None:
                        continue
                    t_prefix, t_acid, t_step = target
                    target_doc = docs_by_id.get((t_prefix, t_acid))
                    if target_doc is None:
                        issues.append(
                            f"Workflow loops[{i}].to references "
                            f"{t_prefix}-{t_acid} — no such SOP in corpus"
                        )
                        continue
                    # D3 — step index in range against target SOP's Steps section
                    try:
                        target_content = target_doc.resolve_resource().read_text()
                        target_parsed = parse_metadata(target_content)
                    except Exception:
                        issues.append(
                            f"Workflow loops[{i}].to = {loop.to_step!r} "
                            f"— could not read target SOP {t_prefix}-{t_acid}"
                        )
                        continue
                    # Use the same heading-selection logic as plan rendering
                    # so D3 and plan agree on what counts as a "Steps"
                    # section (PR #59 Codex review P2 #2).
                    steps_section = extract_steps_section(target_parsed.body)
                    if steps_section is None:
                        issues.append(
                            f"Workflow loops[{i}].to = {loop.to_step!r} "
                            f"— target SOP {t_prefix}-{t_acid} has no Steps section"
                        )
                        continue
                    # Validate by index membership using flush-left top-level
                    # step parsing (consistent with workflow.validate_loops
                    # for intra-SOP refs). SOP step numbering can be sparse
                    # and sub-items / code-fence lines must not count as
                    # steps (PR #59 Codex reviews P1 #1 + #2).
                    target_step_indices = parse_top_level_step_indices(steps_section)
                    if t_step not in target_step_indices:
                        found_desc = (
                            "{"
                            + ", ".join(str(i) for i in sorted(target_step_indices))
                            + "}"
                            if target_step_indices
                            else "{}"
                        )
                        issues.append(
                            f"Workflow loops[{i}].to = {loop.to_step!r} "
                            f"— step index {t_step} does not reference an "
                            f"existing step in {t_prefix}-{t_acid}'s Steps "
                            f"section (found: {found_desc})"
                        )
        except MalformedDocumentError as e:
            # Report parsing error as an issue, don't crash
            issues.append(f"Malformed document: {e}")

        if issues:
            issues_by_doc[doc_id] = issues

    total_issues = sum(len(i) for i in issues_by_doc.values())

    # Build results for JSON output
    if output_json:
        results = []
        for doc in docs:
            doc_id = f"{doc.prefix}-{doc.acid}"
            if doc_id in issues_by_doc:
                results.append(
                    {
                        "doc_id": doc_id,
                        "valid": False,
                        "errors": issues_by_doc[doc_id],
                    }
                )
            else:
                results.append(
                    {
                        "doc_id": doc_id,
                        "valid": True,
                        "errors": [],
                    }
                )

        result = {
            "schema_version": "1",
            "results": results,
        }
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # Report issues (text output)
        for doc_id, doc_issues in issues_by_doc.items():
            click.echo(f"{doc_id}:")
            for issue in doc_issues:
                click.echo(f"  - {issue}")

        click.echo(f"{len(docs)} documents checked, {total_issues} issues found.")

    # Exit with code 1 if issues found
    if total_issues > 0:
        sys.exit(1)
