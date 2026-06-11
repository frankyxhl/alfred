# FXA-2296 Review Pack — Validate Unknown-Type Warning

## Review request

Review this feature diff for the fx-alfred CLI with the COR-1610 rubric pinned below. The unit is the full branch diff vs main. Cross-reference files at HEAD.

## What & why

`af validate` silently tolerated unknown filename TYPE codes: `DocType('XYZ')` raised ValueError, handlers fell back to base-field checks and SKIPPED Status-value validation entirely (validate_cmd.py had two independent `except ValueError` fallbacks). A typo'd type (SPO for SOP) bypassed the type contract with zero feedback. Live evidence: FXA-2271-CTX-Alfred-Glossary.md (CTX not in DocType enum / COR-0002 / CLI type list) validated with no signal — found in the 2026-06-10 trinity-reviewed project review.

The change: one DocType membership check per document (replacing both fallbacks) emits a per-doc WARNING. Text mode: `~`-prefixed lines + summary appends ", N warning(s)" ONLY when N > 0 — zero-warning corpora print byte-identical output (existing "0 issues found" substring assertions throughout the suite stay valid). JSON: additive "warnings" key on every result, always present; "valid" still governed by errors only; schema_version stays "1" (additive field). Warnings NEVER affect exit code — deliberate: corpus has one CTX doc today and `af validate` runs in CI/smoke flows; an error would break them. Legitimizing CTX requires an upstream COR-0002 (PKG read-only) change — explicitly out of scope.

Verified on the real corpus: 286 documents, 0 issues, exactly 1 warning (FXA-2271 CTX), exit 0.

NOT in scope (do not deduct per COR-1610 rule 4): adding CTX to DocType; warning-as-error or exit-code changes; af create/fmt behavior; suppression/allowlist mechanisms; other backlog items.

## Pinned rubric — COR-1610 (use EXACTLY these dimensions and weights)

| Dimension | Weight | What to check |
|-----------|--------|---------------|
| Correctness | 25% | Logic correct? Handles edge cases? No regressions? |
| Test Coverage | 25% | All new behavior has tests? Tests test behavior not implementation? |
| Code Style | 15% | Consistent with existing codebase? Linter clean? |
| Security | 15% | No injection, no secrets, no unsafe operations? |
| Simplicity | 20% | Minimal code for the task? No over-engineering? No premature abstraction? |

Rules (COR-1610): deductions cite file:line; distinguish BLOCKING vs ADVISORY; do NOT deduct for out-of-scope; verify test results before scoring; weighted average rounded to ONE decimal; 8.9 = FIX, 9.0 = PASS. Recompute arithmetic from your own table before printing.

Required output: Decision Matrix + weighted average + PASS/FIX + findings labeled BLOCKING/ADVISORY with file:line.

Special attention requested: (a) the text-mode output interleaving — a doc with BOTH issues and warnings would print its doc_id heading twice (once in the issues loop, once in the warnings loop); is that acceptable output design or worth merging? (b) is `"valid": true` with non-empty warnings the right JSON semantic? (c) any doc shape where the warning could fire spuriously or fail to fire?

## Verification evidence (executed)

- TDD: 3 RED tests first (warning text+exit 0; warn-once + status-skip; JSON warnings key) + 1 baseline lock (zero-warning summary unchanged), then GREEN. 975 tests pass (971 → 975). ruff check/format clean; pyright 0 errors.
- Real corpus: `af validate` → "286 documents checked, 0 issues found, 1 warning." exit 0; the warning names FXA-2271 / CTX.

## The diff (vs main)

diff --git a/src/fx_alfred/commands/validate_cmd.py b/src/fx_alfred/commands/validate_cmd.py
index 7d08991..e97b091 100644
--- a/src/fx_alfred/commands/validate_cmd.py
+++ b/src/fx_alfred/commands/validate_cmd.py
@@ -100,8 +100,9 @@ Checks:
   - Status value validation against allowed values per type
   - Change History table has Date, Change, By columns
   - COR-* documents only in PKG layer
+  - Unknown TYPE codes emit a warning (type-specific checks skipped)
 
-Exit code 0 if clean, 1 if issues found.
+Exit code 0 if clean, 1 if issues found. Warnings never affect the exit code.
 """
 
 
@@ -120,6 +121,10 @@ def validate_cmd(ctx: click.Context, output_json: bool):
         docs = _scan_all_layers(root)
 
     issues_by_doc: dict[str, list[str]] = {}
+    # CHG-2296: non-fatal findings. Warnings never affect the exit code;
+    # they surface degraded validation (e.g. unknown TYPE codes) that was
+    # previously silent.
+    warnings_by_doc: dict[str, list[str]] = {}
 
     # Corpus-wide lookup table for cross-SOP reference resolution (FXA-2218 D2/D3).
     # Only SOPs are valid cross-SOP targets — filter out PRP/CHG/REF/etc. so a
@@ -132,6 +137,21 @@ def validate_cmd(ctx: click.Context, output_json: bool):
     for doc in docs:
         doc_id = f"{doc.prefix}-{doc.acid}"
         issues: list[str] = []
+        warnings: list[str] = []
+
+        # CHG-2296: single membership check replaces the per-lookup
+        # ValueError fallbacks. Unknown TYPE codes get base-field checks
+        # only; warn so typos (SPO for SOP) no longer pass silently.
+        doc_type: DocType | None
+        try:
+            doc_type = DocType(doc.type_code)
+        except ValueError:
+            doc_type = None
+            warnings.append(
+                f"Unknown document type '{doc.type_code}' — type-specific "
+                "validation skipped (known types: "
+                f"{', '.join(t.value for t in DocType)})"
+            )
 
         # Check 0: COR documents must only exist in PKG layer
         if doc.prefix == "COR" and doc.source != "pkg":
@@ -186,13 +206,11 @@ def validate_cmd(ctx: click.Context, output_json: bool):
             found_fields = {mf.key for mf in parsed.metadata_fields}
 
             # Look up required fields for this document type
-            try:
+            if doc_type is not None:
                 required = set(
-                    REQUIRED_METADATA.get(
-                        DocType(doc.type_code), list(_BASE_REQUIRED_FIELDS)
-                    )
+                    REQUIRED_METADATA.get(doc_type, list(_BASE_REQUIRED_FIELDS))
                 )
-            except ValueError:
+            else:
                 required = _BASE_REQUIRED_FIELDS
             missing = required - found_fields
             for field in sorted(missing):
@@ -204,12 +222,11 @@ def validate_cmd(ctx: click.Context, output_json: bool):
             )
             if status_field is not None:
                 status_val = status_field.value
-                try:
-                    allowed: set[str] | None = set(
-                        ALLOWED_STATUSES.get(DocType(doc.type_code), [])
-                    )
-                except ValueError:
-                    allowed = None
+                allowed: set[str] | None = (
+                    set(ALLOWED_STATUSES.get(doc_type, []))
+                    if doc_type is not None
+                    else None
+                )
                 if allowed is not None:
                     if "(" in status_val or ")" in status_val:
                         issues.append(
@@ -363,30 +380,25 @@ def validate_cmd(ctx: click.Context, output_json: bool):
 
         if issues:
             issues_by_doc[doc_id] = issues
+        if warnings:
+            warnings_by_doc[doc_id] = warnings
 
     total_issues = sum(len(i) for i in issues_by_doc.values())
+    total_warnings = sum(len(w) for w in warnings_by_doc.values())
 
     # Build results for JSON output
     if output_json:
         results = []
         for doc in docs:
             doc_id = f"{doc.prefix}-{doc.acid}"
-            if doc_id in issues_by_doc:
-                results.append(
-                    {
-                        "doc_id": doc_id,
-                        "valid": False,
-                        "errors": issues_by_doc[doc_id],
-                    }
-                )
-            else:
-                results.append(
-                    {
-                        "doc_id": doc_id,
-                        "valid": True,
-                        "errors": [],
-                    }
-                )
+            results.append(
+                {
+                    "doc_id": doc_id,
+                    "valid": doc_id not in issues_by_doc,
+                    "errors": issues_by_doc.get(doc_id, []),
+                    "warnings": warnings_by_doc.get(doc_id, []),
+                }
+            )
 
         result = {
             "schema_version": "1",
@@ -400,7 +412,17 @@ def validate_cmd(ctx: click.Context, output_json: bool):
             for issue in doc_issues:
                 click.echo(f"  - {issue}")
 
-        click.echo(f"{len(docs)} documents checked, {total_issues} issues found.")
+        # Report warnings (CHG-2296) — `~` prefix distinguishes from `-` issues
+        for doc_id, doc_warnings in warnings_by_doc.items():
+            click.echo(f"{doc_id}:")
+            for warning in doc_warnings:
+                click.echo(f"  ~ {warning}")
+
+        summary = f"{len(docs)} documents checked, {total_issues} issues found."
+        if total_warnings:
+            plural = "s" if total_warnings != 1 else ""
+            summary = summary[:-1] + f", {total_warnings} warning{plural}."
+        click.echo(summary)
 
     # Exit with code 1 if issues found
     if total_issues > 0:
diff --git a/tests/test_validate_cmd.py b/tests/test_validate_cmd.py
index e42642a..4ecd778 100644
--- a/tests/test_validate_cmd.py
+++ b/tests/test_validate_cmd.py
@@ -2035,3 +2035,84 @@ Test.
     assert result.exit_code == 1
     assert "step index 3" in result.output
     assert "{1, 2}" in result.output
+
+
+# ── Unknown TYPE code warnings (CHG-2296) ──────────────────────────────────
+
+
+def test_unknown_type_emits_warning_exit_0(tmp_path):
+    """A structurally-valid doc with an unknown TYPE warns but passes (A1)."""
+    rules_dir = tmp_path / "rules"
+    rules_dir.mkdir()
+    _write_valid_document(
+        rules_dir / "TST-9001-XYZ-Weird-Doc.md", "TST", "9001", "XYZ", "Weird Doc"
+    )
+
+    runner = CliRunner()
+    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
+    assert result.exit_code == 0
+    assert "Unknown document type 'XYZ'" in result.output
+    assert "SOP, PRP, CHG, ADR, REF, PLN, INC" in result.output
+    assert "0 issues found" in result.output
+    assert "1 warning" in result.output
+
+
+def test_unknown_type_warns_once_and_still_skips_status_check(tmp_path):
+    """One warning per doc; Status validation stays skipped for unknown
+    types — no false Status issues (A2)."""
+    rules_dir = tmp_path / "rules"
+    rules_dir.mkdir()
+    _write_valid_document(
+        rules_dir / "TST-9002-XYZ-Odd-Status.md",
+        "TST",
+        "9002",
+        "XYZ",
+        "Odd Status",
+        status="Totally Made Up",
+    )
+
+    runner = CliRunner()
+    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
+    assert result.exit_code == 0
+    assert result.output.count("Unknown document type 'XYZ'") == 1
+    assert "Invalid Status" not in result.output
+
+
+def test_unknown_type_warning_in_json_output(tmp_path):
+    """JSON mode: warnings key populated for unknown type, empty for known;
+    valid stays true (A3)."""
+    import json as json_mod
+
+    rules_dir = tmp_path / "rules"
+    rules_dir.mkdir()
+    _write_valid_document(
+        rules_dir / "TST-9003-XYZ-Weird-Doc.md", "TST", "9003", "XYZ", "Weird Doc"
+    )
+    _write_valid_document(
+        rules_dir / "TST-9004-SOP-Normal-Doc.md", "TST", "9004", "SOP", "Normal Doc"
+    )
+
+    runner = CliRunner()
+    result = runner.invoke(cli, ["validate", "--root", str(tmp_path), "--json"])
+    assert result.exit_code == 0
+    payload = json_mod.loads(result.output)
+    by_id = {r["doc_id"]: r for r in payload["results"]}
+    weird = by_id["TST-9003"]
+    assert weird["valid"] is True
+    assert len(weird["warnings"]) == 1
+    assert "Unknown document type 'XYZ'" in weird["warnings"][0]
+    assert by_id["TST-9004"]["warnings"] == []
+
+
+def test_no_warnings_keeps_summary_line_unchanged(tmp_path):
+    """Zero-warning corpora print the summary exactly as before (A4)."""
+    rules_dir = tmp_path / "rules"
+    rules_dir.mkdir()
+    _write_valid_document(
+        rules_dir / "TST-9005-SOP-Normal-Doc.md", "TST", "9005", "SOP", "Normal Doc"
+    )
+
+    runner = CliRunner()
+    result = runner.invoke(cli, ["validate", "--root", str(tmp_path)])
+    assert result.exit_code == 0
+    assert "warning" not in result.output.lower()
