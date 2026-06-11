# FXA-2299 Review Pack — Workflow Fence Loop Dedup

## Review request

Review this refactor diff with the COR-1610 rubric pinned below. Unit = branch diff vs main. Cross-reference src/fx_alfred/core/workflow.py, parser.py, steps.py at HEAD.

## What & why

CHG-2294 consolidated CommonMark fence tracking into `parser.iter_lines_with_fence_state` for extract_section + both steps.py parsers, deferring workflow.py's two inline copies (located by the FXA-2294 R1 panel at workflow.py:439-460 and 546-566 — branch validation's sub-step scan and Rule-5 sibling-contiguity scan). Three implementations of one discipline = a future rule fix lands in one place and silently misses others (the exact failure shape of the original CHG-2294 bug). This completes the consolidation.

REFACTOR CONTRACT — zero behavior change: both sites now iterate the shared tracker and `continue` on fenced lines; each keeps its own permissive step-line regex `^(?:###\s+)?(\d+)([a-z])?\.\s+` matched on the RAW line. CRITICAL semantic point for your review: the renderers' `iter_step_lines` was deliberately NOT used — it applies heading-form preference (CHG-2294 R2), which is rendering-side semantics; validation must keep counting BOTH step forms so loop/branch references stay valid. Also the local regex deliberately differs from steps._STEP_LINE_RE (no `(.+)` text-capture requirement).

New guard in tests/test_architecture.py: the implementation fingerprint `fence_char` may appear only in core/parser.py (RED on pre-change code; GREEN now).

Verified: net -32 lines in workflow.py (11+/43-); 982 tests pass with ALL existing workflow/branch/loop tests unmodified (the behavior-preservation proof); ruff/format/pyright/af validate clean.

NOT in scope (no deductions per COR-1610 rule 4): migrating these sites to iter_step_lines (semantics change); unifying the local regex with _STEP_LINE_RE; renderer/plan_cmd surfaces; behavior changes of any kind.

## Pinned rubric — COR-1610

| Dimension | Weight |
|-----------|--------|
| Correctness | 25% |
| Test Coverage | 25% |
| Code Style | 15% |
| Security | 15% |
| Simplicity | 20% |

Rules: deductions cite file:line; BLOCKING vs ADVISORY; no out-of-scope deductions; verify tests before scoring; weighted average rounded to one decimal; >= 9.0 PASS. Recompute arithmetic before printing. Required output: Decision Matrix + weighted average + verdict + findings.

Special attention: (a) verify the two replaced loops are EXACTLY behavior-equivalent to the shared tracker for these inputs — including the subtle original detail that site 1's old loop only counted `position` for matched step lines (confirm the new code preserves position semantics); (b) is the fence_char fingerprint guard a reasonable mechanism, or too coupled to an identifier name? (c) confirm iter_step_lines would have been WRONG here (heading-form preference changing validation outcomes for COR-1612/COR-1200-shaped docs).

## The diff (vs main)

diff --git a/src/fx_alfred/core/workflow.py b/src/fx_alfred/core/workflow.py
index b1fc533..d8c91ac 100644
--- a/src/fx_alfred/core/workflow.py
+++ b/src/fx_alfred/core/workflow.py
@@ -430,35 +430,20 @@ def validate_branches(
     # Pull the actual ## Steps lines (in document order) for sub-step
     # presence and contiguity checks.
     from fx_alfred.core.parser import extract_section as _extract_section
+    from fx_alfred.core.parser import iter_lines_with_fence_state
 
     section = _extract_section(parsed.body, "Steps") if parsed.body else None
     sub_steps_in_order: list[tuple[int, str]] = []  # [(parent, branch), ...]
     plain_step_positions: dict[int, int] = {}  # int_index -> first occurrence
     if section is not None:
         position = 0  # logical position counting ALL parsed step lines
-        fence_char: str | None = None
-        fence_len = 0
-        for raw in section.split("\n"):
-            stripped = raw.lstrip()
-            # Skip fenced code blocks (mirrors parse_top_level_step_indices).
-            if fence_char is not None:
-                if stripped and stripped[0] == fence_char:
-                    run = 0
-                    while run < len(stripped) and stripped[run] == fence_char:
-                        run += 1
-                    if run >= fence_len:
-                        fence_char = None
-                        fence_len = 0
+        # Fenced lines are skipped via the shared CommonMark tracker
+        # (CHG-2299; same discipline as parse_top_level_step_indices).
+        # Validation-side matching stays permissive — both "3." and
+        # "### 3." forms count; no heading-form preference here.
+        for raw, fenced in iter_lines_with_fence_state(section):
+            if fenced:
                 continue
-            if stripped and stripped[0] in ("`", "~"):
-                ch = stripped[0]
-                run = 0
-                while run < len(stripped) and stripped[run] == ch:
-                    run += 1
-                if run >= 3:
-                    fence_char = ch
-                    fence_len = run
-                    continue
             # Match either "3." (plain) or "3a." (sub-step).
             m = re.match(r"^(?:###\s+)?(\d+)([a-z])?\.\s+", raw)
             if not m:
@@ -543,28 +528,11 @@ def validate_branches(
             # last declared sibling.
             unified: list[tuple[str, int, str | None]] = []
             if section is not None:
-                fence_char = None
-                fence_len = 0
-                for raw in section.split("\n"):
-                    stripped = raw.lstrip()
-                    if fence_char is not None:
-                        if stripped and stripped[0] == fence_char:
-                            run = 0
-                            while run < len(stripped) and stripped[run] == fence_char:
-                                run += 1
-                            if run >= fence_len:
-                                fence_char = None
-                                fence_len = 0
+                # Shared fence tracker (CHG-2299); permissive matching as
+                # in the sub-step scan above.
+                for raw, fenced in iter_lines_with_fence_state(section):
+                    if fenced:
                         continue
-                    if stripped and stripped[0] in ("`", "~"):
-                        ch = stripped[0]
-                        run = 0
-                        while run < len(stripped) and stripped[run] == ch:
-                            run += 1
-                        if run >= 3:
-                            fence_char = ch
-                            fence_len = run
-                            continue
                     m = re.match(r"^(?:###\s+)?(\d+)([a-z])?\.\s+", raw)
                     if not m:
                         continue
diff --git a/tests/test_architecture.py b/tests/test_architecture.py
index a2d914c..5846234 100644
--- a/tests/test_architecture.py
+++ b/tests/test_architecture.py
@@ -34,3 +34,27 @@ def test_core_modules_do_not_import_click() -> None:
         "core/ must stay Click-free (raise domain exceptions; commands/ "
         f"converts at the CLI boundary). Violations: {offenders}"
     )
+
+
+_SRC_ROOT = Path(__file__).parent.parent / "src" / "fx_alfred"
+
+
+def test_fence_tracking_implementation_lives_only_in_parser() -> None:
+    """Inline CommonMark fence-state loops were consolidated onto
+    parser.iter_lines_with_fence_state (CHG-2294 → CHG-2299). The
+    implementation fingerprint ``fence_char`` may appear only in
+    core/parser.py, so duplicated fence loops cannot silently reappear
+    and diverge from the shared rules (CHG-2299 A1)."""
+    offenders: list[str] = []
+    for py in sorted(_SRC_ROOT.rglob("*.py")):
+        if py.name == "parser.py":
+            continue
+        for lineno, line in enumerate(
+            py.read_text(encoding="utf-8").splitlines(), start=1
+        ):
+            if "fence_char" in line:
+                offenders.append(f"{py.relative_to(_SRC_ROOT)}:{lineno}")
+    assert offenders == [], (
+        "fence tracking must go through parser.iter_lines_with_fence_state "
+        f"(one implementation, one set of rules). Inline copies at: {offenders}"
+    )
