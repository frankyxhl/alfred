# FXA-2294 Review Pack — R2 delta (renderer alignment)

## Context

R1 of this PR (fence-aware extract_section) passed your panel 9.8/9.8/10.0 with zero blocking. AFTER that verdict, the GitHub codex bot raised a P1: with sections no longer truncated, the plan-step RENDERERS' loose stripped-line matching corrupts checklists — `af plan COR-1612` emitted 21 items for 8 authored steps, with duplicate `1.` indices (flush-left bare numbered body lists under `### N.` step headings). This R2 review covers ONLY the delta commit fa229c0 that fixes it. The R1 surface is already approved; re-litigate it only if the delta breaks it.

## R2 design

New shared `steps.iter_step_lines(section_text)` feeding BOTH renderers (`steps._parse_steps_for_json` — JSON/todo modes; `plan_cmd._parse_numbered_items` — text mode):
1. Flush-left only — indented nested numbered items are body content (matches `parse_top_level_step_indices` / PR #68 R4 gate discipline).
2. Fence-aware — numbered lines inside ```/~~~ fences are body content (via R1's `iter_lines_with_fence_state`).
3. Heading-form preference — if a section authors ANY flush-left `### N.` step line, ONLY heading-form lines render; all-bare sections keep the legacy bare-form convention. Empirical basis: exactly 2 of 62 SOPs corpus-wide mix forms (COR-1612, COR-1200); in both, every bare line is body content (verified by reading them).
4. Validation side (`parse_top_level_step_indices`, loop/branch target resolution) intentionally UNCHANGED (permissive superset) — corpus-wide invariant "rendered ⊆ indexed" verified, 0 violations: every rendered step still validates; no SOP's loop/branch references break.

## Verification evidence (executed)

- TDD: 7 RED tests first (3 indented/fenced + 1 legacy guard, then 3 heading-form), GREEN after; suite 961 passed in 3.75s (957 → 961).
- `af plan COR-1612` → exactly 8 items (the authored steps, no duplicates; was 21). `af plan COR-1200` → exactly 7.
- ruff check + format: clean. pyright: 0 errors. `af validate`: 284 docs, 0 issues.
- Existing tests: ZERO broke across both R2 phases — no test relied on the loose behavior.

## Score with the pinned COR-1610 rubric

| Dimension | Weight |
|-----------|--------|
| Correctness | 25% |
| Test Coverage | 25% |
| Code Style | 15% |
| Security | 15% |
| Simplicity | 20% |

Rules: deductions cite file:line; do NOT deduct for out-of-scope (workflow.py inline fence loops, CHANGELOG, validate step-parity rule — all deferred per CHG); verify tests before scoring; weighted average rounded to one decimal; >= 9.0 PASS. Required output: Decision Matrix table + weighted average + PASS/FIX + findings labeled BLOCKING/ADVISORY. Recompute your arithmetic before printing.

Special attention requested (the risky semantic): the heading-form preference rule in `iter_step_lines` (src/fx_alfred/core/steps.py). Is the rule sound? Any corpus shape it could misrender? Check the docstring's claims against the code.

## The R2 delta diff (aebc479..fa229c0)

diff --git a/src/fx_alfred/commands/plan_cmd.py b/src/fx_alfred/commands/plan_cmd.py
index 730e5b3..4a7734c 100644
--- a/src/fx_alfred/commands/plan_cmd.py
+++ b/src/fx_alfred/commands/plan_cmd.py
@@ -3,7 +3,6 @@
 from __future__ import annotations
 
 import json
-import re
 
 import click
 
@@ -124,18 +123,17 @@ def _extract_steps_section(body: str) -> str | None:
 def _parse_numbered_items(section_text: str) -> list[str]:
     """Extract numbered items from section text.
 
-    Matches both ``1. text`` and ``### 1. text`` formats.
+    Matches both ``1. text`` and ``### 1. text`` formats, plus ``3a. text``
+    (FXA-2226 Path B sub-steps). Only flush-left, unfenced lines count
+    (CHG-2294 R2): indented nested numbered items and numbered lines inside
+    fenced code blocks are step-body content, not steps.
     """
-    items: list[str] = []
-    for line in section_text.split("\n"):
-        stripped = line.strip()
-        # Match "### 1. text", "1. text", "3a. text" (FXA-2226 Path B sub-step)
-        m = re.match(r"^(?:###\s+)?(\d+)([a-z])?\.\s+(.+)", stripped)
-        if m:
-            number = m.group(1)
-            sub_branch = m.group(2) or ""
-            items.append(f"{number}{sub_branch}. {m.group(3)}")
-    return items
+    from fx_alfred.core.steps import iter_step_lines
+
+    return [
+        f"{index}{sub_branch or ''}. {text}"
+        for index, sub_branch, text in iter_step_lines(section_text)
+    ]
 
 
 # _parse_steps_for_json relocated to fx_alfred.core.steps (FXA-2218 Commit 1);
diff --git a/src/fx_alfred/core/steps.py b/src/fx_alfred/core/steps.py
index 5d9fd49..bf0eb56 100644
--- a/src/fx_alfred/core/steps.py
+++ b/src/fx_alfred/core/steps.py
@@ -7,6 +7,7 @@ when validate_cmd.py needs the same parser (FXA-2218 CHG Commit 1).
 from __future__ import annotations
 
 import re
+from collections.abc import Iterator
 
 from fx_alfred.core.parser import extract_section, iter_lines_with_fence_state
 from fx_alfred.core.phases import StepDict
@@ -33,6 +34,59 @@ def extract_steps_section(body: str) -> str | None:
     return None
 
 
+# Flush-left step-line matcher WITH text capture — the rendering-side
+# sibling of `_TOP_LEVEL_STEP_RE` below. Matched against the RAW line
+# (no strip), so indented nested numbered items in step bodies are body
+# content, not steps (CHG-2294 R2; same notion of "step" as
+# `parse_top_level_step_indices` and the PR #68 R4 gate discipline).
+_STEP_LINE_RE = re.compile(r"^(?:###\s+)?(\d+)([a-z])?\.\s+(.+)")
+
+
+def iter_step_lines(section_text: str) -> Iterator[tuple[int, str | None, str]]:
+    """Yield ``(index, sub_branch, text)`` for each rendered step line.
+
+    A candidate step line is flush-left (column 0), outside any fenced
+    code block, and matches ``^(?:###\\s+)?(\\d+)([a-z])?\\.\\s+(.+)``.
+    ``sub_branch`` is ``None`` for plain steps, or the suffix letter for
+    FXA-2226 Path B sub-steps (``"a"``, ``"b"``, ...). ``text`` is
+    right-stripped.
+
+    Heading-form preference (CHG-2294 R2): if the section contains any
+    ``### N.`` heading-form step line, ONLY heading-form lines are steps —
+    bare flush-left numbered lines are then step-body content (e.g.
+    COR-1612 authors category action lists flush-left under its ### steps).
+    Sections with no heading-form lines keep the legacy convention: bare
+    flush-left numbered lines ARE the steps. Corpus check at change time:
+    exactly 2 of 62 SOPs mix forms (COR-1612, COR-1200); in both, every
+    bare line is body content.
+
+    Rendering-side only: `parse_top_level_step_indices` (loop/branch
+    validation) intentionally stays permissive — it counts both forms, so
+    every index that renders here also validates there.
+
+    Shared by the JSON renderer (`_parse_steps_for_json`) and the text
+    renderer (`plan_cmd._parse_numbered_items`) so both agree on one
+    notion of a rendered step.
+    """
+    candidates: list[tuple[bool, int, str | None, str]] = []
+    has_heading_form = False
+    for line, fenced in iter_lines_with_fence_state(section_text):
+        if fenced:
+            continue
+        m = _STEP_LINE_RE.match(line)
+        if not m:
+            continue
+        heading_form = line.startswith("#")
+        has_heading_form = has_heading_form or heading_form
+        candidates.append(
+            (heading_form, int(m.group(1)), m.group(2), m.group(3).rstrip())
+        )
+    for heading_form, index, sub_branch, text in candidates:
+        if has_heading_form and not heading_form:
+            continue
+        yield index, sub_branch, text
+
+
 def _parse_steps_for_json(section_text: str) -> list[StepDict]:
     """Extract steps as structured data for JSON output.
 
@@ -43,20 +97,17 @@ def _parse_steps_for_json(section_text: str) -> list[StepDict]:
 
     Path B convention: plain steps OMIT the ``sub_branch`` key entirely;
     it is never set to ``None`` or any sentinel.
+
+    Only flush-left, unfenced step lines count (CHG-2294 R2; see
+    :func:`iter_step_lines`).
     """
     steps: list[StepDict] = []
-    for line in section_text.split("\n"):
-        stripped = line.strip()
-        m = re.match(r"^(?:###\s+)?(\d+)([a-z])?\.\s+(.+)", stripped)
-        if m:
-            index = int(m.group(1))
-            sub_branch = m.group(2)  # None for plain; "a"/"b"/... for sub-steps
-            text = m.group(3)
-            gate = text.endswith("✓") or "[GATE]" in text
-            step: StepDict = {"index": index, "text": text, "gate": gate}
-            if sub_branch is not None:
-                step["sub_branch"] = sub_branch
-            steps.append(step)
+    for index, sub_branch, text in iter_step_lines(section_text):
+        gate = text.endswith("✓") or "[GATE]" in text
+        step: StepDict = {"index": index, "text": text, "gate": gate}
+        if sub_branch is not None:
+            step["sub_branch"] = sub_branch
+        steps.append(step)
     return steps
 
 
diff --git a/tests/test_plan_cmd.py b/tests/test_plan_cmd.py
index b914cbd..5eccf0d 100644
--- a/tests/test_plan_cmd.py
+++ b/tests/test_plan_cmd.py
@@ -12,6 +12,7 @@ from fx_alfred.cli import cli
 from fx_alfred.commands.plan_cmd import (
     _build_mermaid_phases,
     _format_phase,
+    _parse_numbered_items,
     _parse_steps_for_json,
 )
 from fx_alfred.core.document import Document
@@ -2444,3 +2445,106 @@ echo hello
     assert "First step" in result.output
     assert "Second step" in result.output
     assert "Third step" in result.output
+
+
+def test_parse_numbered_items_excludes_nested_and_fenced_lines():
+    """Text renderer matches the flush-left + fence-aware step notion (CHG-2294 R2)."""
+    section = (
+        "### 1. First step\n"
+        "\n"
+        "  1. nested option one\n"
+        "  2. nested option two\n"
+        "\n"
+        "```bash\n"
+        "# fenced comment\n"
+        "3. fenced pseudo-step\n"
+        "```\n"
+        "\n"
+        "### 2. Second step\n"
+    )
+    assert _parse_numbered_items(section) == ["1. First step", "2. Second step"]
+
+
+def test_plan_renders_exactly_authored_top_level_steps(sample_project, monkeypatch):
+    """COR-1612-shaped SOP: nested lists + fenced numbered lines must not
+    inflate the checklist; exactly the authored steps render (CHG-2294 R2)."""
+    rules_dir = sample_project / "rules"
+    content = """# TST-5010: Nested Body Steps
+
+**Applies to:** Test
+**Status:** Active
+---
+## What Is It?
+SOP with nested numbered lists and fenced numbered lines in step bodies.
+## Steps
+### 1. First step
+
+Choose one:
+
+  1. nested option one
+  2. nested option two
+
+```bash
+# comment
+2. fenced pseudo-step
+```
+
+### 2. Second step
+### 3. Third step
+"""
+    (rules_dir / "TST-5010-SOP-Nested-Body-Steps.md").write_text(content)
+
+    monkeypatch.chdir(sample_project)
+    runner = CliRunner()
+    result = runner.invoke(cli, ["plan", "TST-5010"], catch_exceptions=False)
+    assert result.exit_code == 0
+    checklist = [
+        line for line in result.output.splitlines() if line.startswith("- [ ]")
+    ]
+    assert checklist == [
+        "- [ ] 1. First step",
+        "- [ ] 2. Second step",
+        "- [ ] 3. Third step",
+    ]
+
+
+def test_plan_heading_form_steps_suppress_flush_left_body_lists(
+    sample_project, monkeypatch
+):
+    """COR-1612's real shape: flush-left bare numbered lists under ### N.
+    steps are body content; exactly the authored steps render (CHG-2294 R2)."""
+    rules_dir = sample_project / "rules"
+    content = """# TST-5011: Mixed Form Steps
+
+**Applies to:** Test
+**Status:** Active
+---
+## What Is It?
+SOP with heading-form steps and flush-left bare numbered body lists.
+## Steps
+### 1. First step
+
+**Blocking:**
+1. Fix the code
+
+**Advisory:**
+1. If adopting: fix the code
+2. If declining: reply with reasoning
+
+### 2. Second step
+### 3. Third step
+"""
+    (rules_dir / "TST-5011-SOP-Mixed-Form-Steps.md").write_text(content)
+
+    monkeypatch.chdir(sample_project)
+    runner = CliRunner()
+    result = runner.invoke(cli, ["plan", "TST-5011"], catch_exceptions=False)
+    assert result.exit_code == 0
+    checklist = [
+        line for line in result.output.splitlines() if line.startswith("- [ ]")
+    ]
+    assert checklist == [
+        "- [ ] 1. First step",
+        "- [ ] 2. Second step",
+        "- [ ] 3. Third step",
+    ]
diff --git a/tests/test_steps.py b/tests/test_steps.py
index d0bcd59..32765af 100644
--- a/tests/test_steps.py
+++ b/tests/test_steps.py
@@ -107,3 +107,80 @@ echo hello
     section = extract_steps_section(body)
     assert section is not None
     assert parse_top_level_step_indices(section) == frozenset({1, 2, 3})
+
+
+_NESTED_AND_FENCED_SECTION = """\
+### 1. First step
+
+Options inside the step body:
+
+  1. nested option one
+  2. nested option two
+
+```bash
+# fenced pseudo-step
+3. not a real step
+```
+
+### 2. Second step
+### 3. Third step
+"""
+
+
+def test_parse_steps_for_json_excludes_nested_and_fenced_lines() -> None:
+    """Renderer counts only flush-left, unfenced step lines (CHG-2294 R2).
+
+    Same notion of "step" as parse_top_level_step_indices: indented
+    nested numbered items and numbered lines inside fences are body
+    content, not steps.
+    """
+    steps = _parse_steps_for_json(_NESTED_AND_FENCED_SECTION)
+    assert [s["index"] for s in steps] == [1, 2, 3]
+    assert [s["text"] for s in steps] == ["First step", "Second step", "Third step"]
+
+
+def test_parse_steps_for_json_keeps_flush_left_substeps() -> None:
+    """Flush-left Path B sub-steps still render; indented ones do not."""
+    section = "1. Plain\n3a. Branch A\n  3b. indented impostor\n"
+    steps = _parse_steps_for_json(section)
+    assert [(s["index"], s.get("sub_branch")) for s in steps] == [
+        (1, None),
+        (3, "a"),
+    ]
+
+
+def test_heading_form_steps_suppress_bare_body_lists() -> None:
+    """When a section authors ### N. heading-form steps, flush-left bare
+    numbered lines are body content (COR-1612 shape, CHG-2294 R2)."""
+    section = (
+        "### 1. First step\n"
+        "\n"
+        "**Blocking:**\n"
+        "1. Fix the code\n"
+        "\n"
+        "**Advisory:**\n"
+        "1. If adopting: fix\n"
+        "2. If declining: reply\n"
+        "\n"
+        "### 2. Second step\n"
+        "### 3. Third step\n"
+    )
+    steps = _parse_steps_for_json(section)
+    assert [s["index"] for s in steps] == [1, 2, 3]
+    assert [s["text"] for s in steps] == ["First step", "Second step", "Third step"]
+
+
+def test_all_bare_sections_keep_legacy_step_form() -> None:
+    """Sections with no heading-form lines render bare flush-left steps."""
+    section = (
+        "1. Leader identifies artifact\n2. Leader dispatches\n3. Reviewers analyze\n"
+    )
+    steps = _parse_steps_for_json(section)
+    assert [s["index"] for s in steps] == [1, 2, 3]
+
+
+def test_heading_form_substeps_count_as_heading_form() -> None:
+    """### 3a. sub-step lines participate in heading-form preference."""
+    section = "### 1. Plain\n### 3a. Branch A\n1. bare body item\n"
+    steps = _parse_steps_for_json(section)
+    assert [(s["index"], s.get("sub_branch")) for s in steps] == [(1, None), (3, "a")]
