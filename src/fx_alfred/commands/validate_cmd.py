"""Validate command for af CLI -- validates all documents."""

import re
from importlib import resources
from pathlib import Path

import click

from fx_alfred.commands._helpers import SCHEMA_VERSION, emit_json

from fx_alfred.context import get_root, root_option
from fx_alfred.core.schema import (
    ALLOWED_DISPOSITIONS,
    ALLOWED_STATUSES,
    COR_REFERENCE_PATTERN,
    DISPOSITION,
    DISPOSITION_MANDATORY_BIND,
    DISPOSITION_OPTIONAL_OVERLAY,
    INSTANTIATES,
    OVERLAYS,
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


def _metadata_field(parsed, key: str):
    """Return the first metadata field matching key, if present."""
    return next((mf for mf in parsed.metadata_fields if mf.key == key), None)


def _parse_for_validation(doc: Document, content: str):
    """Parse document metadata, handling non-standard ACID=0000 index H1s."""
    if doc.acid == "0000":
        lines = content.split("\n")
        if lines and not H1_PATTERN.match(lines[0]):
            dummy_h1 = f"# {doc.type_code}-{doc.acid}: Index"
            content = dummy_h1 + content[len(lines[0]) :]
    return parse_metadata(content)


def _build_cor_disposition_index(docs: list[Document]) -> dict[str, str | None]:
    """Index PKG COR document Disposition values by COR-NNNN id."""
    index: dict[str, str | None] = {}
    for doc in docs:
        if doc.prefix != "COR" or doc.source != "pkg":
            continue
        doc_id = f"{doc.prefix}-{doc.acid}"
        try:
            content = doc.resolve_resource().read_text(encoding="utf-8")
            parsed = _parse_for_validation(doc, content)
        except Exception:
            index[doc_id] = None
            continue
        disp_field = _metadata_field(parsed, DISPOSITION)
        index[doc_id] = disp_field.value.strip() if disp_field is not None else None
    return index


def _validate_binding_field(
    doc: Document,
    field_name: str,
    raw_value: str,
    cor_dispositions: dict[str, str | None],
    expected_disposition: str,
) -> list[str]:
    """Validate a PRJ/USR binding field against its PKG COR target."""
    issues: list[str] = []
    target_ids = [part.strip() for part in raw_value.split(",")]

    if any(
        not target_id or not re.match(COR_REFERENCE_PATTERN, target_id)
        for target_id in target_ids
    ):
        issues.append(
            f"Invalid {field_name} value '{raw_value.strip()}' — "
            "must be a comma-separated list of COR-NNNN values "
            "(e.g. COR-1622, COR-1623)"
        )
        return issues

    if doc.source not in {"prj", "usr"}:
        issues.append(f"{field_name} field is only allowed on PRJ/USR documents")
        return issues

    for target_id in target_ids:
        if target_id not in cor_dispositions:
            issues.append(
                f"{field_name} target '{target_id}' does not exist in PKG COR documents"
            )
            continue

        target_disposition = cor_dispositions[target_id]
        if target_disposition is None:
            issues.append(f"{field_name} target '{target_id}' has no Disposition value")
        elif target_disposition != expected_disposition:
            issues.append(
                f"{field_name} target '{target_id}' has Disposition "
                f"'{target_disposition}' (expected '{expected_disposition}')"
            )
    return issues


def _validate_governance_fields(
    doc: Document,
    parsed,
    cor_dispositions: dict[str, str | None],
) -> list[str]:
    """Validate COR-204 governance fields: Disposition, Instantiates, Overlays.

    These fields are optional (backward-compatible with existing docs).
    Returns a list of issue strings; empty list means no issues.
    """
    issues: list[str] = []

    # Validate Disposition field value
    disp_field = _metadata_field(parsed, DISPOSITION)
    if disp_field is not None:
        disp_val = disp_field.value.strip()
        if doc.prefix != "COR" or doc.source != "pkg":
            issues.append(
                "Disposition field is only allowed on COR documents in the PKG layer"
            )
        if disp_val not in ALLOWED_DISPOSITIONS:
            issues.append(
                f"Invalid Disposition value '{disp_val}' — "
                f"allowed: {', '.join(sorted(ALLOWED_DISPOSITIONS))}"
            )

    # Validate Instantiates field format and target disposition
    inst_field = _metadata_field(parsed, INSTANTIATES)
    if inst_field is not None:
        issues.extend(
            _validate_binding_field(
                doc,
                INSTANTIATES,
                inst_field.value,
                cor_dispositions,
                DISPOSITION_MANDATORY_BIND,
            )
        )

    # Validate Overlays field format and target disposition
    ovr_field = _metadata_field(parsed, OVERLAYS)
    if ovr_field is not None:
        issues.extend(
            _validate_binding_field(
                doc,
                OVERLAYS,
                ovr_field.value,
                cor_dispositions,
                DISPOSITION_OPTIONAL_OVERLAY,
            )
        )

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
  - Unknown TYPE codes emit a warning (type-specific checks skipped)

Exit code 0 if clean, 1 if issues found. Warnings never affect the exit code.
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
    # CHG-2296: non-fatal findings. Warnings never affect the exit code;
    # they surface degraded validation (e.g. unknown TYPE codes) that was
    # previously silent.
    warnings_by_doc: dict[str, list[str]] = {}

    # Corpus-wide lookup table for cross-SOP reference resolution (FXA-2218 D2/D3).
    # Filter out PRP/CHG/REF/etc. so `Workflow loops.to = "FXA-2217.3"` cannot
    # resolve (PR #59 Codex review P2).
    docs_by_id: dict[tuple[str, str], Document] = {
        (d.prefix, d.acid): d for d in docs if d.type_code == "SOP"
    }
    cor_dispositions = _build_cor_disposition_index(docs)

    for doc in docs:
        doc_id = f"{doc.prefix}-{doc.acid}"
        issues: list[str] = []
        warnings: list[str] = []

        # CHG-2296: single membership check replaces the per-lookup
        # ValueError fallbacks. Unknown TYPE codes get base-field checks
        # only; warn so typos (SPO for SOP) no longer pass silently.
        doc_type: DocType | None
        try:
            doc_type = DocType(doc.type_code)
        except ValueError:
            doc_type = None
            warnings.append(
                f"Unknown document type '{doc.type_code}' — type-specific "
                "validation skipped (known types: "
                f"{', '.join(t.value for t in DocType)})"
            )

        # Check 0: COR documents must only exist in PKG layer
        if doc.prefix == "COR" and doc.source != "pkg":
            issues.append(f"COR document found in non-PKG layer ({doc.source})")

        try:
            content = doc.resolve_resource().read_text(encoding="utf-8")
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
            if doc_type is not None:
                required = set(
                    REQUIRED_METADATA.get(doc_type, list(_BASE_REQUIRED_FIELDS))
                )
            else:
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
                allowed: set[str] | None = (
                    set(ALLOWED_STATUSES.get(doc_type, []))
                    if doc_type is not None
                    else None
                )
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
            issues.extend(_validate_governance_fields(doc, parsed, cor_dispositions))

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
                # FXA-2226 Path B: count both plain steps (`3.`) and sub-steps
                # (`3a.`) toward the > 5 → require ## Examples heuristic. The
                # legacy regex `^\d+\.` undercounted branchy SOPs; per PR #68
                # multi-model code review F4 (Codex 9.1, Gemini 9.6).
                step_count = len(
                    re.findall(r"^\d+[a-z]?\.", steps_section, re.MULTILINE)
                )

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
                        target_content = target_doc.resolve_resource().read_text(
                            encoding="utf-8"
                        )
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
        if warnings:
            warnings_by_doc[doc_id] = warnings

    total_issues = sum(len(i) for i in issues_by_doc.values())
    total_warnings = sum(len(w) for w in warnings_by_doc.values())

    # Build results for JSON output
    if output_json:
        results = []
        for doc in docs:
            doc_id = f"{doc.prefix}-{doc.acid}"
            results.append(
                {
                    "doc_id": doc_id,
                    "valid": doc_id not in issues_by_doc,
                    "errors": issues_by_doc.get(doc_id, []),
                    "warnings": warnings_by_doc.get(doc_id, []),
                }
            )

        result = {
            "schema_version": SCHEMA_VERSION,
            "results": results,
        }
        emit_json(result)
    else:
        # Report issues and warnings (text output) — one heading per doc,
        # `-` issue lines then `~` warning lines beneath it (CHG-2296; R1
        # panel convergent advisory). Iterate in scan order so issue-only
        # corpora print identically to the pre-CHG-2296 output.
        for doc in docs:
            doc_id = f"{doc.prefix}-{doc.acid}"
            doc_issues = issues_by_doc.get(doc_id, [])
            doc_warnings = warnings_by_doc.get(doc_id, [])
            if not doc_issues and not doc_warnings:
                continue
            click.echo(f"{doc_id}:")
            for issue in doc_issues:
                click.echo(f"  - {issue}")
            for warning in doc_warnings:
                click.echo(f"  ~ {warning}")

        warnings_suffix = (
            f", {total_warnings} warning{'' if total_warnings == 1 else 's'}"
            if total_warnings
            else ""
        )
        click.echo(
            f"{len(docs)} documents checked, "
            f"{total_issues} issues found{warnings_suffix}."
        )

    # Exit with code 1 if issues found
    if total_issues > 0:
        ctx.exit(1)
