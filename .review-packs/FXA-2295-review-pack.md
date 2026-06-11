# FXA-2295 Review Pack — Compose Domain Exceptions (de-Click core/)

## Review request

Review this refactor diff for the fx-alfred CLI with the COR-1610 rubric pinned below. The unit is the full branch diff vs main. Cross-reference files at HEAD as needed.

## What & why

`core/compose.py` was the ONLY core/ module importing Click — violating the repo's documented "core/ is framework-agnostic" contract (CLAUDE.md §Key Design Patterns; flagged 🔴 high in the 2026-06-10 trinity-reviewed project evaluation). Every other core module already follows the domain-exception pattern (scanner → LayerValidationError/DocumentNotFoundError/AmbiguousDocumentError, converted by _helpers).

This refactor: (1) introduces `CompositionError(message, exit_code=1)`; (2) swaps the 4 ClickException raise sites (cycle, not-found, ambiguous, zero-match — the last with exit_code=2 per FXA-2205 §C1); (3) converts at the single production boundary (plan_cmd.py, one try/except); (4) adds tests/test_architecture.py — a permanent guard asserting no core/*.py imports Click (regex ^\s*(?:import|from)\s+click\b); (5) corrects compose.py's module docstring which falsely claimed "Pure stdlib. No filesystem access." (it read documents at line 358 and imported Click); (6) migrates 8 unit-test assertion sites in test_compose.py from click.ClickException to CompositionError. CLI-level tests untouched.

REFACTOR CONTRACT — zero observable behavior change. Verified by execution:
- `af plan --task "xyzzy nonexistent task"` → exit 2, identical message
- `af plan --task implement NOPE-9999` → exit 1, "Error: SOP 'NOPE-9999' not found"
- 970 tests pass (965 pre-change + 5 new: 1 architecture guard + 4 CompositionError contract); ruff check/format clean; pyright 0 errors; af validate 285 docs 0 issues.

NOT in scope (do not deduct per COR-1610 rule 4): Kahn queue re-sort inefficiency (compose.py); a `compose_or_fail` helper in _helpers.py (exactly one call site exists today; extraction deferred until a second caller appears — assess whether you agree this is the right simplicity call, but it is a declared decision); other review-backlog items (validate unknown-type warning, CLAUDE.md refresh, CI matrix).

## Pinned rubric — COR-1610 (use EXACTLY these dimensions and weights)

| Dimension | Weight | What to check |
|-----------|--------|---------------|
| Correctness | 25% | Logic correct? Handles edge cases? No regressions? |
| Test Coverage | 25% | All new behavior has tests? Tests test behavior not implementation? |
| Code Style | 15% | Consistent with existing codebase? Linter clean? |
| Security | 15% | No injection, no secrets, no unsafe operations? |
| Simplicity | 20% | Minimal code for the task? No over-engineering? No premature abstraction? |

Rules (COR-1610): deductions cite file:line; 10 = zero improvements possible; distinguish BLOCKING vs ADVISORY; do NOT deduct for out-of-scope; cross-reference actual sources; verify test results before scoring; weighted average rounded to ONE decimal; 8.9 = FIX, 9.0 = PASS. Recompute your arithmetic from your own table before printing.

Required output: Decision Matrix table + weighted average + PASS/FIX + findings labeled BLOCKING/ADVISORY with file:line.

Special attention requested: (a) does the boundary conversion in plan_cmd preserve ALL ClickException semantics Click relies on (message formatting, exit code propagation, stderr routing)? (b) is the architecture guard regex sound (false positives/negatives)? (c) any OTHER core module leaking framework types by a route the guard does not catch?

## The diff (vs main)

diff --git a/src/fx_alfred/commands/plan_cmd.py b/src/fx_alfred/commands/plan_cmd.py
index 4a7734c..4e3e56d 100644
--- a/src/fx_alfred/commands/plan_cmd.py
+++ b/src/fx_alfred/commands/plan_cmd.py
@@ -17,7 +17,7 @@ from fx_alfred.core.parser import (
 )
 from fx_alfred.core.ascii_graph import render_ascii
 from fx_alfred.core.dag_graph import render_dag
-from fx_alfred.core.compose import resolve_sops_from_task
+from fx_alfred.core.compose import CompositionError, resolve_sops_from_task
 from fx_alfred.core.mermaid import render_mermaid
 from fx_alfred.core.phases import PhaseDict
 from fx_alfred.core.schema import TASK_TAGS
@@ -588,9 +588,12 @@ def plan_cmd(
             resolved_ids, composed_from_provenance = resolve_sops_from_task(
                 task_description, all_sops, positional_list
             )
-        except click.ClickException:
-            # Re-raise with proper exit code
-            raise
+        except CompositionError as e:
+            # CLI boundary (CHG-2295): core raises the domain exception;
+            # convert here, preserving message and exit code (2 = zero-match).
+            exc = click.ClickException(str(e))
+            exc.exit_code = e.exit_code
+            raise exc from e
         # Convert resolved IDs back to tuple for processing
         sop_ids = tuple(resolved_ids)
 
diff --git a/src/fx_alfred/core/compose.py b/src/fx_alfred/core/compose.py
index 1a6e2d6..49c0e21 100644
--- a/src/fx_alfred/core/compose.py
+++ b/src/fx_alfred/core/compose.py
@@ -1,8 +1,14 @@
 """Auto-composition helpers for `af plan --task`.
 
-Pure stdlib. No filesystem access. Operates on already-parsed
-Document objects and workflow metadata to resolve SOP ordering
-via tag matching and topological sort.
+Operates on already-parsed Document objects and workflow metadata to
+resolve SOP ordering via tag matching and topological sort. Reads
+document content through ``Document.resolve_resource()`` when building
+workflow edges.
+
+Framework-agnostic (core layer contract, CHG-2295): no Click imports.
+Failures raise :class:`CompositionError`; the commands layer converts it
+to ``click.ClickException`` at the CLI boundary, preserving the carried
+``exit_code``.
 
 FXA-2205 PR4.
 """
@@ -13,8 +19,6 @@ import string
 from collections import deque
 from dataclasses import dataclass
 
-import click
-
 from fx_alfred.core.document import Document
 from fx_alfred.core.scanner import (
     AmbiguousDocumentError,
@@ -24,6 +28,20 @@ from fx_alfred.core.scanner import (
 from fx_alfred.core.parser import parse_metadata
 from fx_alfred.core.workflow import parse_workflow_signature
 
+
+class CompositionError(Exception):
+    """Raised when SOP composition fails (cycle, unknown ID, zero match).
+
+    ``exit_code`` is the CLI exit code the command boundary should use;
+    it defaults to 1, mirroring ``click.ClickException``. The zero-match
+    case in :func:`resolve_sops_from_task` sets 2 (FXA-2205 §C1 contract).
+    """
+
+    def __init__(self, message: str, exit_code: int = 1):
+        super().__init__(message)
+        self.exit_code = exit_code
+
+
 # Verbatim from FXA-2205 §C1
 STOPWORDS: frozenset[str] = frozenset(
     {
@@ -176,7 +194,7 @@ def compose_order(
 
     Deterministic tiebreak: layer priority (PKG → USR → PRJ), then ASCII doc_id.
 
-    Fail-closed on TRUE cycle (raises ClickException with cycle nodes).
+    Fail-closed on TRUE cycle (raises CompositionError with cycle nodes).
 
     Returns ordered list of Document objects.
     """
@@ -252,7 +270,7 @@ def compose_order(
         # Find cycle nodes
         remaining = [d for d in doc_ids if doc_map[d] not in result]
         cycle_nodes = ", ".join(sorted(remaining))
-        raise click.ClickException(f"Workflow cycle detected among: {cycle_nodes}")
+        raise CompositionError(f"Workflow cycle detected among: {cycle_nodes}")
 
     return result
 
@@ -287,9 +305,10 @@ def resolve_sops_from_task(
 
     Raises
     ------
-    click.ClickException:
-        If tag matching produces nothing and no positional IDs given
-        (tag_cands is empty and positional_set is empty), exit code 2.
+    CompositionError:
+        If a positional ID is unknown or ambiguous (exit_code 1), or if
+        tag matching produces nothing and no positional IDs are given
+        (tag_cands empty and positional_set empty — exit_code 2).
     """
     # 1. Tokenize (as set for probing)
     tokens = tokenize(task_description)
@@ -322,9 +341,9 @@ def resolve_sops_from_task(
         try:
             doc = find_document(all_docs, sop_id)
         except DocumentNotFoundError:
-            raise click.ClickException(f"SOP '{sop_id}' not found") from None
+            raise CompositionError(f"SOP '{sop_id}' not found") from None
         except AmbiguousDocumentError as e:
-            raise click.ClickException(str(e)) from None
+            raise CompositionError(str(e)) from None
         normalized_positional.append(f"{doc.prefix}-{doc.acid}")
 
     positional_set = set(normalized_positional)
@@ -337,13 +356,12 @@ def resolve_sops_from_task(
     # wrongly fired when an always-included SOP also had a matching Task tag
     # (because tag_cands ⊆ always_set keeps set equality True).
     if not tag_cands and not positional_set:
-        exc = click.ClickException(
+        raise CompositionError(
             f'--task "{task_description}" matched 0 tagged SOPs. '
             "No routing fallback in v1.\n"
-            "Try: af plan <SOP_ID> ... explicitly, or tag a relevant SOP with `Task tags:`."
+            "Try: af plan <SOP_ID> ... explicitly, or tag a relevant SOP with `Task tags:`.",
+            exit_code=2,
         )
-        exc.exit_code = 2
-        raise exc
 
     # 8. Order via compose_order with workflow edges
     # Build doc map for ordering
diff --git a/tests/test_architecture.py b/tests/test_architecture.py
new file mode 100644
index 0000000..79b83e1
--- /dev/null
+++ b/tests/test_architecture.py
@@ -0,0 +1,34 @@
+"""Architecture guard tests (CHG-2295).
+
+Enforces the "core/ is framework-agnostic" contract from CLAUDE.md
+§Key Design Patterns: Click may only be imported by the commands layer.
+Before CHG-2295, compose.py was the lone violator (4 raise sites); this
+test keeps the contract enforced rather than aspirational.
+"""
+
+from __future__ import annotations
+
+import re
+from pathlib import Path
+
+import pytest
+
+pytestmark = pytest.mark.unit
+
+_CORE_DIR = Path(__file__).parent.parent / "src" / "fx_alfred" / "core"
+_CLICK_IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+click\b")
+
+
+def test_core_modules_do_not_import_click() -> None:
+    """No module under core/ may import Click (CHG-2295 A1)."""
+    offenders: list[str] = []
+    for py in sorted(_CORE_DIR.glob("*.py")):
+        for lineno, line in enumerate(
+            py.read_text(encoding="utf-8").splitlines(), start=1
+        ):
+            if _CLICK_IMPORT_RE.match(line):
+                offenders.append(f"{py.name}:{lineno}: {line.strip()}")
+    assert offenders == [], (
+        "core/ must stay Click-free (raise domain exceptions; commands/ "
+        f"converts at the CLI boundary). Violations: {offenders}"
+    )
diff --git a/tests/test_compose.py b/tests/test_compose.py
index f4c9c36..27fcae3 100644
--- a/tests/test_compose.py
+++ b/tests/test_compose.py
@@ -281,11 +281,9 @@ class TestComposeOrder:
         result_no_edges = compose_order([doc_a, doc_b])
         assert [d.acid for d in result_no_edges] == ["7002", "7009"]
 
-    def test_compose_order_real_cycle_raises_click_exception(self):
-        """True cycle A→B→A in Workflow input/output edges raises ClickException."""
-        import click
-
-        from fx_alfred.core.compose import compose_order
+    def test_compose_order_real_cycle_raises_composition_error(self):
+        """True cycle A→B→A in Workflow input/output edges raises CompositionError."""
+        from fx_alfred.core.compose import CompositionError, compose_order
         from fx_alfred.core.document import Document
 
         doc_a = Document(
@@ -311,7 +309,7 @@ class TestComposeOrder:
             "TST-8002": ("x", "y"),
         }
 
-        with pytest.raises(click.ClickException) as exc_info:
+        with pytest.raises(CompositionError) as exc_info:
             compose_order([doc_a, doc_b], edges)
 
         msg = str(exc_info.value)
@@ -398,10 +396,9 @@ class TestResolveSopsFromTask:
         assert "change-feature" in bg
 
     def test_resolve_empty_task_no_positional_raises_exit_2(self):
-        """Empty tag match + no positional → ClickException exit 2 with diagnostic."""
-        from fx_alfred.core.compose import resolve_sops_from_task
+        """Empty tag match + no positional → CompositionError exit 2 with diagnostic."""
+        from fx_alfred.core.compose import CompositionError, resolve_sops_from_task
         from fx_alfred.core.document import Document
-        import click
 
         # Create only always-included SOP with no matching tags
         always_doc = Document(
@@ -416,7 +413,7 @@ class TestResolveSopsFromTask:
         all_sops = [(always_doc, frozenset(), True)]
 
         # "xyzzy rare unmatched" should match nothing
-        with pytest.raises(click.ClickException) as exc_info:
+        with pytest.raises(CompositionError) as exc_info:
             resolve_sops_from_task("xyzzy rare unmatched", all_sops, [])
 
         assert exc_info.value.exit_code == 2
@@ -646,11 +643,10 @@ class TestComposeOrderWithEdges:
         assert result[1].acid == "6002"
         assert result[2].acid == "6003"
 
-    def test_compose_order_cycle_raises_click_exception(self):
-        """True cycle A→B→A raises ClickException."""
-        from fx_alfred.core.compose import compose_order
+    def test_compose_order_cycle_raises_composition_error(self):
+        """True cycle A→B→A raises CompositionError."""
+        from fx_alfred.core.compose import CompositionError, compose_order
         from fx_alfred.core.document import Document
-        import click
 
         doc_a = Document(
             prefix="TST",
@@ -675,7 +671,7 @@ class TestComposeOrderWithEdges:
             "TST-6002": ("reviewed", "done"),
         }
 
-        with pytest.raises(click.ClickException, match="Workflow cycle detected"):
+        with pytest.raises(CompositionError, match="Workflow cycle detected"):
             compose_order([doc_a, doc_b], workflow_edges)
 
     def test_compose_order_partial_edges(self):
@@ -751,11 +747,9 @@ class TestCoverageFills:
         result = tokenize_ordered("code change code change feature")
         assert result == ["code", "change", "feature"]
 
-    def test_resolve_explicit_id_not_found_raises_clickexception(self):
-        """Unknown positional SOP ID in --task mode → ClickException 'SOP X not found'."""
-        import click
-
-        from fx_alfred.core.compose import resolve_sops_from_task
+    def test_resolve_explicit_id_not_found_raises_composition_error(self):
+        """Unknown positional SOP ID in --task mode → CompositionError 'SOP X not found'."""
+        from fx_alfred.core.compose import CompositionError, resolve_sops_from_task
         from fx_alfred.core.document import Document
 
         doc = Document(
@@ -768,7 +762,7 @@ class TestCoverageFills:
         )
         all_sops = [(doc, frozenset(), True)]
 
-        with pytest.raises(click.ClickException) as exc_info:
+        with pytest.raises(CompositionError) as exc_info:
             resolve_sops_from_task("implement", all_sops, ["BAD-9999"])
 
         assert "BAD-9999" in str(exc_info.value)
@@ -815,10 +809,8 @@ class TestResolveSopsFromTaskBotP2Regression:
         assert "TST-9100" in provenance["always"]
 
     def test_empty_match_still_raises_when_no_tags_and_no_positional(self):
-        """Empty tag match + no positional → ClickException exit 2 (fail-closed preserved)."""
-        import click
-
-        from fx_alfred.core.compose import resolve_sops_from_task
+        """Empty tag match + no positional → CompositionError exit 2 (fail-closed preserved)."""
+        from fx_alfred.core.compose import CompositionError, resolve_sops_from_task
         from fx_alfred.core.document import Document
 
         # SOP with no tags, not always-included.
@@ -836,7 +828,7 @@ class TestResolveSopsFromTaskBotP2Regression:
         ]
 
         # "xyzzy unmatched" matches no tags; no positional → must fail-closed.
-        with pytest.raises(click.ClickException) as exc_info:
+        with pytest.raises(CompositionError) as exc_info:
             resolve_sops_from_task("xyzzy unmatched", all_sops, [])
 
         assert exc_info.value.exit_code == 2
@@ -900,9 +892,7 @@ class TestResolveSopsFromTaskAcidOnlyPositional:
 
     def test_bad_acid_only_still_raises(self):
         """Non-existent ACID-only positional raises 'SOP 'X' not found'."""
-        import click
-
-        from fx_alfred.core.compose import resolve_sops_from_task
+        from fx_alfred.core.compose import CompositionError, resolve_sops_from_task
         from fx_alfred.core.document import Document
 
         doc = Document(
@@ -915,7 +905,7 @@ class TestResolveSopsFromTaskAcidOnlyPositional:
         )
         all_sops = [(doc, frozenset(["implement"]), False)]
 
-        with pytest.raises(click.ClickException) as exc_info:
+        with pytest.raises(CompositionError) as exc_info:
             resolve_sops_from_task("implement", all_sops, ["99999"])
 
         assert "99999" in str(exc_info.value)
@@ -923,9 +913,7 @@ class TestResolveSopsFromTaskAcidOnlyPositional:
 
     def test_bad_full_id_still_raises(self):
         """Non-existent full PREFIX-ACID raises 'SOP 'X' not found'."""
-        import click
-
-        from fx_alfred.core.compose import resolve_sops_from_task
+        from fx_alfred.core.compose import CompositionError, resolve_sops_from_task
         from fx_alfred.core.document import Document
 
         doc = Document(
@@ -938,7 +926,7 @@ class TestResolveSopsFromTaskAcidOnlyPositional:
         )
         all_sops = [(doc, frozenset(["implement"]), False)]
 
-        with pytest.raises(click.ClickException) as exc_info:
+        with pytest.raises(CompositionError) as exc_info:
             resolve_sops_from_task("implement", all_sops, ["BAD-9999"])
 
         assert "BAD-9999" in str(exc_info.value)
@@ -946,9 +934,7 @@ class TestResolveSopsFromTaskAcidOnlyPositional:
 
     def test_ambiguous_acid_raises(self):
         """Same ACID across two prefixes, ACID-only positional → ambiguity error."""
-        import click
-
-        from fx_alfred.core.compose import resolve_sops_from_task
+        from fx_alfred.core.compose import CompositionError, resolve_sops_from_task
         from fx_alfred.core.document import Document
 
         doc_a = Document(
@@ -972,7 +958,7 @@ class TestResolveSopsFromTaskAcidOnlyPositional:
             (doc_b, frozenset(), False),
         ]
 
-        with pytest.raises(click.ClickException) as exc_info:
+        with pytest.raises(CompositionError) as exc_info:
             resolve_sops_from_task("implement", all_sops, ["1500"])
 
         # The message comes from AmbiguousDocumentError.__str__
@@ -980,3 +966,46 @@ class TestResolveSopsFromTaskAcidOnlyPositional:
         msg = str(exc_info.value).lower()
         assert "1500" in msg
         assert "ambiguous" in msg or "multiple" in msg
+
+
+class TestCompositionErrorContract:
+    """CHG-2295: core/compose raises domain CompositionError, not ClickException."""
+
+    def test_cycle_raises_composition_error(self):
+        from fx_alfred.core.compose import CompositionError, compose_order
+        from fx_alfred.core.document import Document
+
+        doc_a = Document.from_filename(
+            "TST-9001-SOP-Cycle-A.md", directory="rules", source="prj"
+        )
+        doc_b = Document.from_filename(
+            "TST-9002-SOP-Cycle-B.md", directory="rules", source="prj"
+        )
+        edges = {
+            "TST-9001": ("from-b", "to-b"),
+            "TST-9002": ("to-b", "from-b"),
+        }
+        with pytest.raises(CompositionError, match="Workflow cycle detected among:"):
+            compose_order([doc_a, doc_b], edges)
+
+    def test_zero_match_raises_composition_error_exit_code_2(self):
+        from fx_alfred.core.compose import CompositionError, resolve_sops_from_task
+
+        with pytest.raises(CompositionError, match="matched 0 tagged SOPs") as exc_info:
+            resolve_sops_from_task("totally unrelated task", [], [])
+        assert exc_info.value.exit_code == 2
+
+    def test_not_found_raises_composition_error_default_exit_code(self):
+        from fx_alfred.core.compose import CompositionError, resolve_sops_from_task
+
+        with pytest.raises(CompositionError, match="SOP 'TST-9999' not found") as ei:
+            resolve_sops_from_task("task", [], ["TST-9999"])
+        assert ei.value.exit_code == 1
+
+    def test_composition_error_is_not_click_exception(self):
+        """The domain exception must not subclass Click types (core stays Click-free)."""
+        import click
+
+        from fx_alfred.core.compose import CompositionError
+
+        assert not issubclass(CompositionError, click.ClickException)
