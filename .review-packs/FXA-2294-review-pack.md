# FXA-2294 Review Pack — Fence-Aware extract_section

## Review request

You are reviewing a bugfix diff for the fx-alfred CLI (Python 3.10+, Click). Score it with the COR-1610 code rubric pinned below. Review the DIFF as the unit; cross-reference full files in the repo when needed (src/fx_alfred/core/parser.py, src/fx_alfred/core/steps.py, tests/).

## Bug being fixed

`core/parser.py::extract_section` terminated sections at the first `^#{1,level}\s+` match — including `#`-prefixed lines INSIDE fenced code blocks (bash comments at column 0). Result: `af plan COR-1612` rendered 1 of 8 authored steps; 10 real SOPs across PKG/USR/PRJ layers had silently truncated Steps sections. Downstream `steps.py` already had CommonMark fence tracking (PR #59 hardening), but the upstream truncation ran first.

## Fix design

1. New shared helper `parser.iter_lines_with_fence_state(text)` — yields (line, fenced) with CommonMark fence rules hoisted verbatim from steps.py: opener = run of >=3 backticks/tildes (after lstrip); closer = same char, run >= opener length; opener/interior/closer lines all flagged fenced.
2. `extract_section` rewritten on top of it: BOTH the section-heading match and the next-heading boundary search ignore fenced lines. Deliberate semantic change: a heading-shaped line inside a fence can no longer ANCHOR a section start either.
3. `steps.py`: the two duplicated fence loops (`parse_top_level_step_indices`, `has_top_level_substep_lines`) now delegate to the shared helper; `_fence_run_length` moved to parser.py. Behavior unchanged.

NOT in scope (do not deduct per COR-1610 rule 4): workflow.py's third inline fence loop (correct code, follow-up dedupe); plan renderer's loose nested-numbered-list matching (pre-existing); a validate rule for step-count parity (separate CHG); CHANGELOG (release-commit-only convention).

## Verification evidence (already executed — verify claims against the diff, rerun if you can)

- RED: 7 new tests failed on pre-fix code (truncation reproduced at parser, steps, and CLI levels); 105 existing tests in those files passed.
- GREEN: full suite 944 passed in 3.87s (was 935 pre-change; +9 new tests).
- ruff check + ruff format --check: clean. pyright src/: 0 errors. af validate: 284 docs, 0 issues.
- Post-fix: `af plan COR-1612` renders all 8 authored top-level steps; layer-wide rescan: 0 truncated Steps sections (was 10).

## Pinned rubric — COR-1610 (use EXACTLY these dimensions and weights)

| Dimension | Weight | What to check |
|-----------|--------|---------------|
| Correctness | 25% | Logic correct? Handles edge cases? No regressions? |
| Test Coverage | 25% | All new behavior has tests? Tests test behavior not implementation? |
| Code Style | 15% | Consistent with existing codebase? Linter clean? |
| Security | 15% | No injection, no secrets, no unsafe operations? |
| Simplicity | 20% | Minimal code for the task? No over-engineering? No premature abstraction? |

Scoring rules (COR-1610): deductions must cite file:line; 10 = zero improvements possible; distinguish blocking vs advisory; do NOT deduct for out-of-scope issues; cross-reference actual source files; verify test results before scoring; weighted average rounded to ONE decimal; 8.9 = FIX, 9.0 = PASS.

Required output format:

### Decision Matrix

| Dimension | Weight | Score | Deductions |
|-----------|--------|-------|------------|
| Correctness | 25% | X/10 | file:line — specific issue |
| Test Coverage | 25% | X/10 | ... |
| Code Style | 15% | X/10 | ... |
| Security | 15% | X/10 | ... |
| Simplicity | 20% | X/10 | ... |

**Weighted Average: X.X/10 — [PASS/FIX]**

Then a short findings list: each finding labeled BLOCKING or ADVISORY with file:line.
Sanity-check your arithmetic: recompute the weighted average from the table before printing it.

## The diff (vs main)

diff --git a/src/fx_alfred/core/parser.py b/src/fx_alfred/core/parser.py
index af81253..777ddea 100644
--- a/src/fx_alfred/core/parser.py
+++ b/src/fx_alfred/core/parser.py
@@ -7,6 +7,7 @@ body, Change History) and reconstructs them preserving original formatting.
 from __future__ import annotations
 
 import re
+from collections.abc import Iterator
 from dataclasses import dataclass, field
 
 
@@ -294,28 +295,89 @@ def parse_tags(value: str) -> list[str]:
     return [t.strip().lower() for t in value.split(",") if t.strip()]
 
 
+def _fence_run_length(stripped: str, ch: str) -> int:
+    """Return the length of the leading run of ``ch`` in ``stripped`` (0 if none)."""
+    run = 0
+    while run < len(stripped) and stripped[run] == ch:
+        run += 1
+    return run
+
+
+def iter_lines_with_fence_state(text: str) -> Iterator[tuple[str, bool]]:
+    """Yield ``(line, fenced)`` for each line of ``text``.
+
+    ``fenced`` is True for fence opener lines, fence closer lines, and every
+    line in between — i.e. lines that markdown structure matching (headings,
+    step numbers) must ignore.
+
+    Fence matching follows CommonMark rules (same discipline as the step
+    parsers in ``core/steps.py``, PR #59 reviews P2 #4/#7/#8):
+
+    - Opener is a run of 3 or more backtick or tilde characters.
+    - Closer must use the **same character** AND be a run of **at least
+      as many** characters as the opener.
+    """
+    fence_char: str | None = None  # '`' or '~' or None
+    fence_len = 0
+    for line in text.split("\n"):
+        stripped = line.lstrip()
+        if fence_char is not None:
+            # Inside a fence — closer must be the same char with len >= opener.
+            if stripped and stripped[0] == fence_char:
+                run = _fence_run_length(stripped, fence_char)
+                if run >= fence_len:
+                    fence_char = None
+                    fence_len = 0
+            yield line, True
+            continue
+        # Outside any fence — check for an opener (≥3 run of ` or ~).
+        if stripped and stripped[0] in ("`", "~"):
+            ch = stripped[0]
+            run = _fence_run_length(stripped, ch)
+            if run >= 3:
+                fence_char = ch
+                fence_len = run
+                yield line, True
+                continue
+        yield line, False
+
+
 def extract_section(body: str, heading: str) -> str | None:
     """Extract a section from document body by heading name.
 
     Searches for ``## {heading}`` or ``### {heading}`` (line-start anchored).
     Returns text from after the heading until the next heading of same or higher
     level, or end of body.  Returns ``None`` if no matching heading is found.
+
+    Lines inside fenced code blocks are ignored for both the heading match
+    and the boundary search, so column-0 ``#`` lines in code samples (e.g.
+    bash comments) neither start nor terminate a section (CHG-2294).
     """
+    annotated = list(iter_lines_with_fence_state(body))
     # Try ## first, then ###
     for prefix in ("##", "###"):
-        pattern = rf"^{re.escape(prefix)}\s+{re.escape(heading)}\s*$"
-        match = re.search(pattern, body, re.MULTILINE)
-        if match:
-            # Determine heading level (number of '#')
-            level = len(prefix)
-            start = match.end()
-            # Find next heading of same or higher level
-            next_heading = re.search(
-                rf"^#{{{1},{level}}}\s+", body[start:], re.MULTILINE
-            )
-            if next_heading:
-                section = body[start : start + next_heading.start()]
-            else:
-                section = body[start:]
-            return section.strip()
+        heading_re = re.compile(rf"^{re.escape(prefix)}\s+{re.escape(heading)}\s*$")
+        start_idx = next(
+            (
+                i
+                for i, (line, fenced) in enumerate(annotated)
+                if not fenced and heading_re.match(line)
+            ),
+            None,
+        )
+        if start_idx is None:
+            continue
+        # Find next heading of same or higher level (number of '#')
+        level = len(prefix)
+        boundary_re = re.compile(rf"^#{{1,{level}}}\s+")
+        end_idx = next(
+            (
+                j
+                for j in range(start_idx + 1, len(annotated))
+                if not annotated[j][1] and boundary_re.match(annotated[j][0])
+            ),
+            len(annotated),
+        )
+        section = "\n".join(line for line, _ in annotated[start_idx + 1 : end_idx])
+        return section.strip()
     return None
diff --git a/src/fx_alfred/core/steps.py b/src/fx_alfred/core/steps.py
index c570f43..5d9fd49 100644
--- a/src/fx_alfred/core/steps.py
+++ b/src/fx_alfred/core/steps.py
@@ -8,7 +8,7 @@ from __future__ import annotations
 
 import re
 
-from fx_alfred.core.parser import extract_section
+from fx_alfred.core.parser import extract_section, iter_lines_with_fence_state
 from fx_alfred.core.phases import StepDict
 
 # Heading search order for the steps section. SOPs historically used one
@@ -72,56 +72,24 @@ def _parse_steps_for_json(section_text: str) -> list[StepDict]:
 _TOP_LEVEL_STEP_RE = re.compile(r"^(?:###\s+)?(\d+)[a-z]?\.\s+")
 
 
-def _fence_run_length(stripped: str, ch: str) -> int:
-    """Return the length of the leading run of ``ch`` in ``stripped`` (0 if none)."""
-    run = 0
-    while run < len(stripped) and stripped[run] == ch:
-        run += 1
-    return run
-
-
 def parse_top_level_step_indices(section_text: str) -> frozenset[int]:
     """Return the set of top-level step indices declared in a Steps section.
 
     Only lines flush-left (no leading whitespace) that match
     ``^(?:###\\s+)?\\d+\\.\\s+`` contribute. Sub-items (indented) are
-    ignored via the flush-left regex; **fenced code blocks** are tracked
-    explicitly so numbered lines inside ``` / ~~~ fences don't count as
-    steps (PR #59 Codex review P2 #4).
-
-    Fence matching follows CommonMark rules:
-
-    - Opener is a run of 3 or more backtick or tilde characters.
-    - Closer must use the **same character** AND be a run of **at least
-      as many** characters as the opener.
-    - So a 4-backtick fence is not closed by a 3-backtick line inside;
-      and a backtick fence is not closed by a tilde line (PR #59 Codex
-      reviews P2 #7 + P2 #8).
+    ignored via the flush-left regex; **fenced code blocks** are skipped
+    via ``parser.iter_lines_with_fence_state`` so numbered lines inside
+    ``` / ~~~ fences don't count as steps (PR #59 Codex review P2 #4;
+    CommonMark opener/closer rules per P2 #7 + P2 #8 live in the shared
+    helper since CHG-2294).
 
     Used by ``validate_loops`` (intra-SOP) and by ``af validate`` D3
     (cross-SOP) so both enforce the same notion of "existing step".
     """
     indices: set[int] = set()
-    fence_char: str | None = None  # '`' or '~' or None
-    fence_len = 0
-    for line in section_text.split("\n"):
-        stripped = line.lstrip()
-        if fence_char is not None:
-            # Inside a fence — closer must be the same char with len >= opener.
-            if stripped and stripped[0] == fence_char:
-                run = _fence_run_length(stripped, fence_char)
-                if run >= fence_len:
-                    fence_char = None
-                    fence_len = 0
+    for line, fenced in iter_lines_with_fence_state(section_text):
+        if fenced:
             continue
-        # Outside any fence — check for an opener (≥3 run of ` or ~).
-        if stripped and stripped[0] in ("`", "~"):
-            ch = stripped[0]
-            run = _fence_run_length(stripped, ch)
-            if run >= 3:
-                fence_char = ch
-                fence_len = run
-                continue
         m = _TOP_LEVEL_STEP_RE.match(line)
         if m:
             indices.add(int(m.group(1)))
@@ -146,24 +114,7 @@ def has_top_level_substep_lines(section_text: str) -> bool:
     cannot be falsely tripped by indented or fenced ``3a.`` lines (Codex
     PR #68 R4 inline review).
     """
-    fence_char: str | None = None
-    fence_len = 0
-    for line in section_text.split("\n"):
-        stripped = line.lstrip()
-        if fence_char is not None:
-            if stripped and stripped[0] == fence_char:
-                run = _fence_run_length(stripped, fence_char)
-                if run >= fence_len:
-                    fence_char = None
-                    fence_len = 0
-            continue
-        if stripped and stripped[0] in ("`", "~"):
-            ch = stripped[0]
-            run = _fence_run_length(stripped, ch)
-            if run >= 3:
-                fence_char = ch
-                fence_len = run
-                continue
-        if _TOP_LEVEL_SUBSTEP_RE.match(line):
-            return True
-    return False
+    return any(
+        not fenced and _TOP_LEVEL_SUBSTEP_RE.match(line)
+        for line, fenced in iter_lines_with_fence_state(section_text)
+    )
diff --git a/tests/test_parser.py b/tests/test_parser.py
index 20a0200..8e04bfb 100644
--- a/tests/test_parser.py
+++ b/tests/test_parser.py
@@ -3,7 +3,7 @@
 import pytest
 
 
-from fx_alfred.core.parser import H1_PATTERN, parse_metadata
+from fx_alfred.core.parser import H1_PATTERN, extract_section, parse_metadata
 
 
 pytestmark = pytest.mark.unit
@@ -53,3 +53,100 @@ def test_parse_metadata_change_history_heading_without_table():
     assert parsed.history_header == ""
     assert parsed.history_rows == []
     assert "Change History" in parsed.body
+
+
+# --- extract_section fence-awareness (CHG-2294) ---
+
+
+_FENCED_BASH_COMMENT_BODY = """\
+intro text
+
+## Steps
+
+Step one:
+
+```bash
+# a column-0 bash comment must not terminate the section
+echo hello
+```
+
+More steps here.
+
+## Next Section
+
+other content
+"""
+
+
+def test_extract_section_basic_boundaries():
+    """Baseline: section runs from after its heading to the next heading."""
+    body = "## Steps\n\nalpha\n\n## Next\n\nbeta\n"
+    assert extract_section(body, "Steps") == "alpha"
+    assert extract_section(body, "Next") == "beta"
+    assert extract_section(body, "Absent") is None
+
+
+def test_extract_section_h3_fallback():
+    """Baseline: falls back to ### when no ## heading matches."""
+    body = "## Outer\n\n### Steps\n\ngamma\n\n### After\n\ndelta\n"
+    assert extract_section(body, "Steps") == "gamma"
+
+
+def test_extract_section_ignores_bash_comment_inside_backtick_fence():
+    """A `# comment` at column 0 inside ``` fences is not a section boundary."""
+    section = extract_section(_FENCED_BASH_COMMENT_BODY, "Steps")
+    assert section is not None
+    assert "More steps here." in section
+    assert "other content" not in section  # still stops at the real heading
+
+
+def test_extract_section_ignores_heading_lookalike_inside_fence():
+    """A `## Fake` line inside a fence is not a section boundary."""
+    body = (
+        "## Steps\n\nbefore\n\n"
+        "```\n## Fake Heading\n```\n\n"
+        "after\n\n## Real Next\n\nnope\n"
+    )
+    section = extract_section(body, "Steps")
+    assert section is not None
+    assert "before" in section
+    assert "after" in section
+    assert "nope" not in section
+
+
+def test_extract_section_tilde_fence():
+    """Tilde fences (~~~) shield their content like backtick fences."""
+    body = "## Steps\n\none\n\n~~~sh\n# fenced comment\n~~~\n\ntwo\n\n## End\n\nx\n"
+    section = extract_section(body, "Steps")
+    assert section is not None
+    assert "two" in section
+    assert "x" not in section
+
+
+def test_extract_section_fence_closer_must_match_opener_length():
+    """A shorter fence run does not close a longer opener (CommonMark)."""
+    body = (
+        "## Steps\n\nstart\n\n"
+        "````md\n"
+        "```\n"
+        "# still inside the 4-backtick fence\n"
+        "```\n"
+        "# also still inside\n"
+        "````\n\n"
+        "end\n\n## Tail\n\ny\n"
+    )
+    section = extract_section(body, "Steps")
+    assert section is not None
+    assert "end" in section
+    assert "y" not in section
+
+
+def test_extract_section_heading_inside_fence_is_not_section_start():
+    """A heading-shaped line inside a fence cannot anchor a section."""
+    body = (
+        "intro\n\n"
+        "```\n## Steps\nfenced sample, not a real section\n```\n\n"
+        "## Steps\n\nreal content\n\n## After\n\nz\n"
+    )
+    section = extract_section(body, "Steps")
+    assert section == "real content"
diff --git a/tests/test_plan_cmd.py b/tests/test_plan_cmd.py
index af17e3b..b914cbd 100644
--- a/tests/test_plan_cmd.py
+++ b/tests/test_plan_cmd.py
@@ -2412,3 +2412,35 @@ Test.
         _build_mermaid_phases(phase_info)
 
     assert "TST-9902" in str(exc_info.value.format_message())
+
+
+def test_plan_keeps_steps_after_fenced_bash_comment(sample_project, monkeypatch):
+    """Steps after a fenced block with a column-0 comment must render (CHG-2294)."""
+    rules_dir = sample_project / "rules"
+    content = """# TST-5009: Fenced Steps
+
+**Applies to:** Test
+**Status:** Active
+---
+## What Is It?
+SOP whose first step embeds a bash block with a column-0 comment.
+## Steps
+1. First step
+
+```bash
+# a comment that must not terminate the section
+echo hello
+```
+
+2. Second step
+3. Third step
+"""
+    (rules_dir / "TST-5009-SOP-Fenced-Steps.md").write_text(content)
+
+    monkeypatch.chdir(sample_project)
+    runner = CliRunner()
+    result = runner.invoke(cli, ["plan", "TST-5009"], catch_exceptions=False)
+    assert result.exit_code == 0
+    assert "First step" in result.output
+    assert "Second step" in result.output
+    assert "Third step" in result.output
diff --git a/tests/test_steps.py b/tests/test_steps.py
index a981ce1..d0bcd59 100644
--- a/tests/test_steps.py
+++ b/tests/test_steps.py
@@ -15,6 +15,7 @@ import pytest
 
 from fx_alfred.core.steps import (
     _parse_steps_for_json,
+    extract_steps_section,
     parse_top_level_step_indices,
 )
 
@@ -85,3 +86,24 @@ def test_parse_top_level_step_indices_legacy_unchanged() -> None:
     section = "1. A\n2. B\n3. C\n"
     indices = parse_top_level_step_indices(section)
     assert indices == frozenset({1, 2, 3})
+
+
+def test_step_indices_survive_fenced_bash_comment_in_section_extraction() -> None:
+    """End-to-end: extract_steps_section + index parsing keep steps that
+    follow a fenced code block containing a column-0 comment (CHG-2294)."""
+    body = """\
+## Steps
+
+1. First step
+
+```bash
+# a comment that must not truncate the section
+echo hello
+```
+
+2. Second step
+3. Third step
+"""
+    section = extract_steps_section(body)
+    assert section is not None
+    assert parse_top_level_step_indices(section) == frozenset({1, 2, 3})
