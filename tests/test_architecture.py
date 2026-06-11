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
