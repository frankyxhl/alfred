"""Architecture guard tests (CHG-2295).

Enforces the "core/ is framework-agnostic" contract from CLAUDE.md
§Key Design Patterns: Click may only be imported by the commands layer.
Before CHG-2295, compose.py was the lone violator (4 raise sites); this
test keeps the contract enforced rather than aspirational.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_CORE_DIR = Path(__file__).parent.parent / "src" / "fx_alfred" / "core"
_CLICK_IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+click\b")


def test_core_modules_do_not_import_click() -> None:
    """No module under core/ may import Click (CHG-2295 A1)."""
    offenders: list[str] = []
    # rglob so future core/ subpackages cannot evade the guard
    # (FXA-2295 R1 convergent advisory: glm + minimax).
    for py in sorted(_CORE_DIR.rglob("*.py")):
        for lineno, line in enumerate(
            py.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if _CLICK_IMPORT_RE.match(line):
                offenders.append(f"{py.name}:{lineno}: {line.strip()}")
    assert offenders == [], (
        "core/ must stay Click-free (raise domain exceptions; commands/ "
        f"converts at the CLI boundary). Violations: {offenders}"
    )


_SRC_ROOT = Path(__file__).parent.parent / "src" / "fx_alfred"

# Assignment/annotation/comparison sites of the fence-state variables
# (`fence_char = ...`, `fence_len: int`, `== fence_char:`) — NOT prose
# mentions in comments/docstrings ("the old fence_char loops"). The
# `(char|len)` alternation also catches partial renames that keep either
# state variable (FXA-2299 R1 convergent advisory: deepseek false-fire
# risk + minimax rename-evasion risk).
_FENCE_STATE_RE = re.compile(r"\bfence_(char|len)\b\s*[:=]")


def test_fence_tracking_implementation_lives_only_in_parser() -> None:
    """Inline CommonMark fence-state loops were consolidated onto
    parser.iter_lines_with_fence_state (CHG-2294 → CHG-2299). The
    implementation fingerprint (``fence_char``/``fence_len`` state
    variables) may appear only in core/parser.py, so duplicated fence
    loops cannot silently reappear and diverge from the shared rules
    (CHG-2299 A1)."""
    offenders: list[str] = []
    for py in sorted(_SRC_ROOT.rglob("*.py")):
        if py.name == "parser.py":
            continue
        for lineno, line in enumerate(
            py.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if _FENCE_STATE_RE.search(line):
                offenders.append(f"{py.relative_to(_SRC_ROOT)}:{lineno}")
    assert offenders == [], (
        "fence tracking must go through parser.iter_lines_with_fence_state "
        f"(one implementation, one set of rules). Inline copies at: {offenders}"
    )


_COMMANDS_DIR = _SRC_ROOT / "commands"


def _commands_violations(predicate, skip_helpers: bool = False) -> list[str]:
    offenders: list[str] = []
    for py in sorted(_COMMANDS_DIR.rglob("*.py")):
        if skip_helpers and py.name == "_helpers.py":
            continue
        for lineno, line in enumerate(
            py.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if predicate(line):
                offenders.append(f"{py.name}:{lineno}")
    return offenders


def test_commands_emit_json_through_helper() -> None:
    """All --json output goes through _helpers.emit_json so formatting
    (indent=2, ensure_ascii=False) cannot fork into dialects again —
    bare json.dumps escaped CJK document titles (CHG-2301 A1)."""
    offenders = _commands_violations(
        lambda line: "json.dumps(" in line, skip_helpers=True
    )
    assert offenders == [], (
        f"use _helpers.emit_json instead of raw json.dumps: {offenders}"
    )


def test_commands_use_ctx_exit_not_sys_exit() -> None:
    """Commands exit through Click's ctx.exit, not sys.exit (CHG-2301)."""
    offenders = _commands_violations(lambda line: "sys.exit(" in line)
    assert offenders == [], f"use ctx.exit in commands/: {offenders}"


def test_commands_use_named_schema_version_constants() -> None:
    """No magic '"schema_version": "1"' literals — envelopes reference a
    named constant (_helpers.SCHEMA_VERSION, or their schema family's own
    core constant) so version bumps cannot miss call sites (CHG-2301)."""
    offenders = _commands_violations(
        lambda line: '"schema_version": "1"' in line, skip_helpers=True
    )
    assert offenders == [], f"use a named SCHEMA_VERSION constant: {offenders}"


# Pre-CHG-2302 oversized functions, pinned at their current sizes — a
# RATCHET: they may shrink but not grow, and new functions get the 150
# cap. Decomposing them is recorded follow-up work (CHG-2302 §Out of
# Scope). Maintainers: when one of these shrinks, LOWER its cap to the
# new size (or delete the entry once it fits under 150) so the ratchet
# never goes slack.
_GRANDFATHERED_FUNCTION_LINES = {
    "create_cmd.py:create_cmd": 230,
    "update_cmd.py:update_cmd": 283,
    "validate_cmd.py:validate_cmd": 326,
}


def test_commands_functions_stay_decomposed() -> None:
    """No function in commands/ may exceed 150 lines (CHG-2302).

    Operationalizes the plan_cmd decomposition: the pre-change main
    function had grown to 376 lines of nested mode branching, absorbing
    every plan feature since FXA-2134. 150 leaves ~1.4x headroom over
    the largest post-decomposition function (_emit_json_output, 108).
    Three pre-existing functions are grandfathered at their current
    sizes (ratchet — see _GRANDFATHERED_FUNCTION_LINES)."""
    import ast

    offenders: list[str] = []
    for py in sorted(_COMMANDS_DIR.rglob("*.py")):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                length = (node.end_lineno or node.lineno) - node.lineno + 1
                cap = _GRANDFATHERED_FUNCTION_LINES.get(f"{py.name}:{node.name}", 150)
                if length > cap:
                    offenders.append(
                        f"{py.name}:{node.name} ({length} lines > cap {cap})"
                    )
    assert offenders == [], (
        f"decompose oversized command functions (CHG-2302): {offenders}"
    )
