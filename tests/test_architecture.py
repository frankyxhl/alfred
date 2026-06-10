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
    for py in sorted(_CORE_DIR.glob("*.py")):
        for lineno, line in enumerate(
            py.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if _CLICK_IMPORT_RE.match(line):
                offenders.append(f"{py.name}:{lineno}: {line.strip()}")
    assert offenders == [], (
        "core/ must stay Click-free (raise domain exceptions; commands/ "
        f"converts at the CLI boundary). Violations: {offenders}"
    )
