# FXA-2301 Review Pack — JSON Emission / Schema Constants / Exit Idiom Unification

## Review request

Review this consistency-sweep diff with the COR-1610 rubric pinned below. Unit = branch diff vs main (13 command modules + _helpers + 3 guards + CHG doc). Cross-reference at HEAD as needed.

## What & why

2026-06-10 review, commands-layer findings: a CLI whose primary consumers are AGENTS PARSING --json had three JSON dialects — and the bare-dumps family (list/read/status) actively degraded CJK content (ensure_ascii=True escapes the user's Chinese document titles to \uXXXX). Plus 4 hardcoded `"schema_version": "1"` literals + a private duplicate constant, and 2 sys.exit sites amid ctx.exit convention.

Change: (1) `_helpers.emit_json(data)` = `click.echo(json.dumps(data, indent=2, ensure_ascii=False))`; ALL 14 dumps sites migrate. (2) `_helpers.SCHEMA_VERSION = "1"` for the commands-layer envelope; literals + star_cmd's private constant migrate; deliberately NOT migrated: core.skills.SCHEMA_VERSION and core.agent_helpers.SCHEMA_VERSION (separate schema families owned by core) and plan_cmd's COMPUTED schema_ver ("3"/"2"/"1" by payload shape — real semantic versioning). (3) validate + issue-lint sys.exit → ctx.exit (lint gains @click.pass_context). (4) Three guards in tests/test_architecture.py: no raw json.dumps outside _helpers, no sys.exit in commands/, no schema_version magic literals.

Deliberate behavior delta (documented in CHG): list/read/status gain indent + raw UTF-8; agent/where gain indent; issue gains ensure_ascii=False; majority family byte-identical; exit codes numerically identical.

KEY EVIDENCE: zero existing tests modified — every JSON test already asserted via json.loads, so the suite passing unmodified (998) proves semantic equivalence. Live verification: af search "跨" --json renders raw 跨; issue lint exit codes pass=0/fail=1 confirmed.

NOT in scope (no deductions per COR-1610 rule 4): adding schema_version to envelopes lacking one (list/read/status — schema additions are separate CHGs); plan_cmd's computed versioning; core-layer envelope constants; machine-readable error envelopes.

## Pinned rubric — COR-1610

| Dimension | Weight |
|-----------|--------|
| Correctness | 25% |
| Test Coverage | 25% |
| Code Style | 15% |
| Security | 15% |
| Simplicity | 20% |

Rules: deductions cite file:line; BLOCKING vs ADVISORY; no out-of-scope deductions; verify tests before scoring; weighted average rounded to one decimal; >= 9.0 PASS. Recompute arithmetic before printing. Required output: Decision Matrix + weighted average + verdict + findings.

Special attention: (a) sweep completeness — any json emission or exit path the guards miss (click.echo of hand-built JSON strings, SystemExit raises, print())? (b) the issue-lint pass_context addition — any Click behavior change (option order, help output, group context)? (c) is keeping plan_cmd's computed schema_ver + core-owned constants the right boundary, or should the panel push for full unification?

## The diff (vs main)

diff --git a/src/fx_alfred/commands/_helpers.py b/src/fx_alfred/commands/_helpers.py
index 0c97e68..1e76dd7 100644
--- a/src/fx_alfred/commands/_helpers.py
+++ b/src/fx_alfred/commands/_helpers.py
@@ -1,6 +1,7 @@
 """Shared helpers for CLI commands — wraps core functions with Click error handling."""
 
 import importlib
+import json
 import os
 import tempfile
 from pathlib import Path
@@ -19,6 +20,21 @@ from fx_alfred.core.scanner import (
 )
 from fx_alfred.core.schema import ALLOWED_STATUSES, DocType
 
+# Commands-layer JSON envelope version (CHG-2301). Schema families owned
+# by core keep their own constants (core.skills / core.agent_helpers);
+# plan_cmd versions its payload shape independently.
+SCHEMA_VERSION = "1"
+
+
+def emit_json(data: Any) -> None:
+    """Emit ``data`` as the canonical CLI JSON form (CHG-2301).
+
+    indent=2 for human inspection, ensure_ascii=False so CJK content
+    renders as written. All command --json output goes through here
+    (enforced by tests/test_architecture.py).
+    """
+    click.echo(json.dumps(data, indent=2, ensure_ascii=False))
+
 
 def scan_or_fail(ctx: click.Context) -> list[Document]:
     """Scan documents, converting LayerValidationError to ClickException."""
diff --git a/src/fx_alfred/commands/agent_cmd.py b/src/fx_alfred/commands/agent_cmd.py
index 265aaf6..2befb3e 100644
--- a/src/fx_alfred/commands/agent_cmd.py
+++ b/src/fx_alfred/commands/agent_cmd.py
@@ -1,9 +1,10 @@
 from __future__ import annotations
 
-import json
 
 import click
 
+from fx_alfred.commands._helpers import emit_json
+
 from fx_alfred.context import get_root, root_option
 from fx_alfred.core.agent_helpers import (
     AgentArgError,
@@ -16,7 +17,7 @@ from fx_alfred.core.agent_helpers import (
 
 
 def _emit_json(envelope: dict) -> None:
-    click.echo(json.dumps(envelope, ensure_ascii=False))
+    emit_json(envelope)
 
 
 @click.group("agent")
diff --git a/src/fx_alfred/commands/guide_cmd.py b/src/fx_alfred/commands/guide_cmd.py
index 0503479..cef5875 100644
--- a/src/fx_alfred/commands/guide_cmd.py
+++ b/src/fx_alfred/commands/guide_cmd.py
@@ -1,8 +1,6 @@
-import json
-
 import click
 
-from fx_alfred.commands._helpers import scan_or_fail
+from fx_alfred.commands._helpers import SCHEMA_VERSION, emit_json, scan_or_fail
 from fx_alfred.context import root_option
 from fx_alfred.core.parser import MalformedDocumentError, parse_metadata
 from fx_alfred.core.schema import ROUTING_ROLE_METADATA_KEY, ROUTING_ROLE_VALUE
@@ -101,10 +99,10 @@ def guide_cmd(ctx: click.Context, output_json: bool):
 
     if output_json:
         result = {
-            "schema_version": "1",
+            "schema_version": SCHEMA_VERSION,
             "routing_docs": routing_docs,
         }
-        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
+        emit_json(result)
     else:
         click.echo(
             "Run this at session start for routing context."
diff --git a/src/fx_alfred/commands/issue_cmd.py b/src/fx_alfred/commands/issue_cmd.py
index 1a2f18d..6276e14 100644
--- a/src/fx_alfred/commands/issue_cmd.py
+++ b/src/fx_alfred/commands/issue_cmd.py
@@ -2,12 +2,13 @@
 
 from __future__ import annotations
 
-import json
 import sys
 from pathlib import Path
 
 import click
 
+from fx_alfred.commands._helpers import emit_json
+
 # Phase 1: TBD-phrase rule (same list as COR-1506 §Hard Cap Trigger B).
 # Order is significant — when two phrases appear on the same line, the one
 # earlier in this list is reported first.
@@ -58,7 +59,8 @@ def issue_cmd() -> None:
     type=click.Path(dir_okay=False, allow_dash=True),
 )
 @click.option("--json", "as_json", is_flag=True, help="Output violations as JSON.")
-def lint_cmd(body_file: str, as_json: bool) -> None:
+@click.pass_context
+def lint_cmd(ctx: click.Context, body_file: str, as_json: bool) -> None:
     """Lint a GitHub issue body for known anti-patterns.
 
     Phase 1: detects TBD-after-PR-review phrases (see #168 §Hard Cap Trigger B).
@@ -76,15 +78,12 @@ def lint_cmd(body_file: str, as_json: bool) -> None:
     violations = _check_tbd_phrases(text)
 
     if as_json:
-        click.echo(
-            json.dumps(
-                {
-                    "result": "PASS" if not violations else "FAIL",
-                    "violation_count": len(violations),
-                    "violations": violations,
-                },
-                indent=2,
-            )
+        emit_json(
+            {
+                "result": "PASS" if not violations else "FAIL",
+                "violation_count": len(violations),
+                "violations": violations,
+            }
         )
     else:
         for v in violations:
@@ -95,4 +94,4 @@ def lint_cmd(body_file: str, as_json: bool) -> None:
         else:
             click.echo("Lint result: PASS (0 violations)")
 
-    sys.exit(1 if violations else 0)
+    ctx.exit(1 if violations else 0)
diff --git a/src/fx_alfred/commands/list_cmd.py b/src/fx_alfred/commands/list_cmd.py
index 87d0583..770b8a2 100644
--- a/src/fx_alfred/commands/list_cmd.py
+++ b/src/fx_alfred/commands/list_cmd.py
@@ -1,8 +1,6 @@
-import json
-
 import click
 
-from fx_alfred.commands._helpers import scan_or_fail
+from fx_alfred.commands._helpers import emit_json, scan_or_fail
 from fx_alfred.context import root_option
 from fx_alfred.core.source import SOURCE_LABELS
 
@@ -80,7 +78,7 @@ def list_cmd(
             }
             for doc in docs
         ]
-        click.echo(json.dumps(output))
+        emit_json(output)
     else:
         for doc in docs:
             label = SOURCE_LABELS.get(doc.source, "???")
diff --git a/src/fx_alfred/commands/plan_cmd.py b/src/fx_alfred/commands/plan_cmd.py
index 4e3e56d..593572d 100644
--- a/src/fx_alfred/commands/plan_cmd.py
+++ b/src/fx_alfred/commands/plan_cmd.py
@@ -2,11 +2,10 @@
 
 from __future__ import annotations
 
-import json
 
 import click
 
-from fx_alfred.commands._helpers import find_or_fail, scan_or_fail
+from fx_alfred.commands._helpers import emit_json, find_or_fail, scan_or_fail
 from fx_alfred.context import root_option
 from fx_alfred.core.document import Document
 from fx_alfred.core.parser import (
@@ -865,7 +864,7 @@ def plan_cmd(
         if with_skills:
             result["recommended_skills"] = recommended_skills or []
 
-        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
+        emit_json(result)
         return
 
     # ── Second pass: render phased output (default behavior) ──
diff --git a/src/fx_alfred/commands/read_cmd.py b/src/fx_alfred/commands/read_cmd.py
index fddc9f3..e82ef75 100644
--- a/src/fx_alfred/commands/read_cmd.py
+++ b/src/fx_alfred/commands/read_cmd.py
@@ -1,8 +1,6 @@
-import json
-
 import click
 
-from fx_alfred.commands._helpers import find_or_fail, scan_or_fail
+from fx_alfred.commands._helpers import emit_json, find_or_fail, scan_or_fail
 from fx_alfred.context import root_option
 
 
@@ -35,6 +33,6 @@ def read_cmd(ctx: click.Context, identifier: str, json_output: bool):
             "source": doc.source,
             "content": content,
         }
-        click.echo(json.dumps(output))
+        emit_json(output)
     else:
         click.echo(content)
diff --git a/src/fx_alfred/commands/search_cmd.py b/src/fx_alfred/commands/search_cmd.py
index d3493cf..5c90323 100644
--- a/src/fx_alfred/commands/search_cmd.py
+++ b/src/fx_alfred/commands/search_cmd.py
@@ -1,10 +1,8 @@
 """Search command for af CLI -- searches document contents."""
 
-import json
-
 import click
 
-from fx_alfred.commands._helpers import scan_or_fail
+from fx_alfred.commands._helpers import SCHEMA_VERSION, emit_json, scan_or_fail
 from fx_alfred.context import root_option
 from fx_alfred.core.source import SOURCE_LABELS
 
@@ -75,10 +73,10 @@ def search_cmd(ctx: click.Context, pattern: str, output_json: bool):
 
     if output_json:
         result = {
-            "schema_version": "1",
+            "schema_version": SCHEMA_VERSION,
             "query": pattern,
             "results": results,
         }
-        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
+        emit_json(result)
     elif not matches_found:
         click.echo("No matches found.")
diff --git a/src/fx_alfred/commands/skill_cmd.py b/src/fx_alfred/commands/skill_cmd.py
index 099aa71..66e83a0 100644
--- a/src/fx_alfred/commands/skill_cmd.py
+++ b/src/fx_alfred/commands/skill_cmd.py
@@ -1,10 +1,9 @@
 from __future__ import annotations
 
-import json
 
 import click
 
-from fx_alfred.commands._helpers import scan_or_fail
+from fx_alfred.commands._helpers import emit_json, scan_or_fail
 from fx_alfred.context import root_option
 from fx_alfred.core.skills import (
     SCHEMA_VERSION,
@@ -42,12 +41,7 @@ def skill_list_cmd(
     results = list_skills(docs, task=task, layer=layer)
 
     if json_output:
-        click.echo(
-            json.dumps(
-                {"schema_version": SCHEMA_VERSION, "results": results},
-                ensure_ascii=False,
-            )
-        )
+        emit_json({"schema_version": SCHEMA_VERSION, "results": results})
         return
 
     if not results:
@@ -85,15 +79,12 @@ def skill_read_cmd(
         raise click.ClickException(str(exc)) from exc
 
     if json_output:
-        click.echo(
-            json.dumps(
-                {
-                    "schema_version": SCHEMA_VERSION,
-                    "document": skill_metadata(doc),
-                    "content": content,
-                },
-                ensure_ascii=False,
-            )
+        emit_json(
+            {
+                "schema_version": SCHEMA_VERSION,
+                "document": skill_metadata(doc),
+                "content": content,
+            }
         )
         return
 
diff --git a/src/fx_alfred/commands/star_cmd.py b/src/fx_alfred/commands/star_cmd.py
index cd47580..333003f 100644
--- a/src/fx_alfred/commands/star_cmd.py
+++ b/src/fx_alfred/commands/star_cmd.py
@@ -2,11 +2,15 @@
 
 from __future__ import annotations
 
-import json
 
 import click
 
-from fx_alfred.commands._helpers import find_or_fail, scan_or_fail
+from fx_alfred.commands._helpers import (
+    SCHEMA_VERSION,
+    emit_json,
+    find_or_fail,
+    scan_or_fail,
+)
 from fx_alfred.context import root_option
 from fx_alfred.core.preferences import (
     PreferencesError,
@@ -16,9 +20,6 @@ from fx_alfred.core.preferences import (
 )
 
 
-SCHEMA_VERSION = "1"
-
-
 def _canonical_from_doc(doc) -> str:
     """Build a canonical PREFIX-ACID string from a Document."""
     return f"{doc.prefix}-{doc.acid}"
@@ -141,14 +142,12 @@ def starred_cmd(ctx: click.Context, json_output: bool) -> None:
     missing = sorted(s for s in starred if s not in resolvable)
 
     if json_output:
-        click.echo(
-            json.dumps(
-                {
-                    "schema_version": SCHEMA_VERSION,
-                    "starred_docs": starred,
-                    "missing": missing,
-                }
-            )
+        emit_json(
+            {
+                "schema_version": SCHEMA_VERSION,
+                "starred_docs": starred,
+                "missing": missing,
+            }
         )
         return
 
diff --git a/src/fx_alfred/commands/status_cmd.py b/src/fx_alfred/commands/status_cmd.py
index 4082751..c8fb98a 100644
--- a/src/fx_alfred/commands/status_cmd.py
+++ b/src/fx_alfred/commands/status_cmd.py
@@ -1,9 +1,8 @@
-import json
 from collections import Counter
 
 import click
 
-from fx_alfred.commands._helpers import scan_or_fail
+from fx_alfred.commands._helpers import emit_json, scan_or_fail
 from fx_alfred.context import root_option
 from fx_alfred.core.source import SOURCE_LABELS, SOURCE_ORDER
 
@@ -20,11 +19,7 @@ def status_cmd(ctx: click.Context, json_output: bool):
 
     if not docs:
         if json_output:
-            click.echo(
-                json.dumps(
-                    {"total": 0, "by_source": {}, "by_type": {}, "by_prefix": {}}
-                )
-            )
+            emit_json({"total": 0, "by_source": {}, "by_type": {}, "by_prefix": {}})
         else:
             click.echo("No documents found.")
         return
@@ -40,7 +35,7 @@ def status_cmd(ctx: click.Context, json_output: bool):
             "by_type": dict(by_type),
             "by_prefix": dict(by_prefix),
         }
-        click.echo(json.dumps(output))
+        emit_json(output)
     else:
         click.echo(f"Total: {len(docs)} documents\n")
         click.echo("By source:")
diff --git a/src/fx_alfred/commands/validate_cmd.py b/src/fx_alfred/commands/validate_cmd.py
index 67a43d7..e91536e 100644
--- a/src/fx_alfred/commands/validate_cmd.py
+++ b/src/fx_alfred/commands/validate_cmd.py
@@ -1,13 +1,13 @@
 """Validate command for af CLI -- validates all documents."""
 
-import json
 import re
-import sys
 from importlib import resources
 from pathlib import Path
 
 import click
 
+from fx_alfred.commands._helpers import SCHEMA_VERSION, emit_json
+
 from fx_alfred.context import get_root, root_option
 from fx_alfred.core.schema import (
     ALLOWED_STATUSES,
@@ -401,10 +401,10 @@ def validate_cmd(ctx: click.Context, output_json: bool):
             )
 
         result = {
-            "schema_version": "1",
+            "schema_version": SCHEMA_VERSION,
             "results": results,
         }
-        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
+        emit_json(result)
     else:
         # Report issues and warnings (text output) — one heading per doc,
         # `-` issue lines then `~` warning lines beneath it (CHG-2296; R1
@@ -434,4 +434,4 @@ def validate_cmd(ctx: click.Context, output_json: bool):
 
     # Exit with code 1 if issues found
     if total_issues > 0:
-        sys.exit(1)
+        ctx.exit(1)
diff --git a/src/fx_alfred/commands/where_cmd.py b/src/fx_alfred/commands/where_cmd.py
index 44fa681..c9b6736 100644
--- a/src/fx_alfred/commands/where_cmd.py
+++ b/src/fx_alfred/commands/where_cmd.py
@@ -1,11 +1,15 @@
 """af where command — print the file path of a document."""
 
-import json
 from pathlib import Path
 
 import click
 
-from fx_alfred.commands._helpers import find_or_fail, scan_or_fail
+from fx_alfred.commands._helpers import (
+    SCHEMA_VERSION,
+    emit_json,
+    find_or_fail,
+    scan_or_fail,
+)
 from fx_alfred.context import root_option
 
 
@@ -33,12 +37,12 @@ def where_cmd(ctx, identifier: str, output_json: bool) -> None:
 
     if output_json:
         result = {
-            "schema_version": "1",
+            "schema_version": SCHEMA_VERSION,
             "doc_id": f"{doc.prefix}-{doc.acid}",
             "path": str(file_path),
             "source": doc.source,
             "filename": file_path.name,
         }
-        click.echo(json.dumps(result, ensure_ascii=False))
+        emit_json(result)
     else:
         click.echo(str(file_path))
diff --git a/tests/test_architecture.py b/tests/test_architecture.py
index 6c2a7b3..ff21d3b 100644
--- a/tests/test_architecture.py
+++ b/tests/test_architecture.py
@@ -67,3 +67,47 @@ def test_fence_tracking_implementation_lives_only_in_parser() -> None:
         "fence tracking must go through parser.iter_lines_with_fence_state "
         f"(one implementation, one set of rules). Inline copies at: {offenders}"
     )
+
+
+_COMMANDS_DIR = _SRC_ROOT / "commands"
+
+
+def _commands_violations(predicate, skip_helpers: bool = False) -> list[str]:
+    offenders: list[str] = []
+    for py in sorted(_COMMANDS_DIR.rglob("*.py")):
+        if skip_helpers and py.name == "_helpers.py":
+            continue
+        for lineno, line in enumerate(
+            py.read_text(encoding="utf-8").splitlines(), start=1
+        ):
+            if predicate(line):
+                offenders.append(f"{py.name}:{lineno}")
+    return offenders
+
+
+def test_commands_emit_json_through_helper() -> None:
+    """All --json output goes through _helpers.emit_json so formatting
+    (indent=2, ensure_ascii=False) cannot fork into dialects again —
+    bare json.dumps escaped CJK document titles (CHG-2301 A1)."""
+    offenders = _commands_violations(
+        lambda line: "json.dumps(" in line, skip_helpers=True
+    )
+    assert offenders == [], (
+        f"use _helpers.emit_json instead of raw json.dumps: {offenders}"
+    )
+
+
+def test_commands_use_ctx_exit_not_sys_exit() -> None:
+    """Commands exit through Click's ctx.exit, not sys.exit (CHG-2301)."""
+    offenders = _commands_violations(lambda line: "sys.exit(" in line)
+    assert offenders == [], f"use ctx.exit in commands/: {offenders}"
+
+
+def test_commands_use_named_schema_version_constants() -> None:
+    """No magic '"schema_version": "1"' literals — envelopes reference a
+    named constant (_helpers.SCHEMA_VERSION, or their schema family's own
+    core constant) so version bumps cannot miss call sites (CHG-2301)."""
+    offenders = _commands_violations(
+        lambda line: '"schema_version": "1"' in line, skip_helpers=True
+    )
+    assert offenders == [], f"use a named SCHEMA_VERSION constant: {offenders}"
