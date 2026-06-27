"""Drift guard for the COR-1402 no-formal-SOP canonical literal (FXA-2312).

Pins the exact declaration string across every surface that teaches the
COR-1402 cadence so a wording change on any one surface immediately fails CI,
preventing the class of silent regression that caused a 6-round serial review
loop during FXA-2312 development.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.docs

_REPO = Path(__file__).resolve().parents[1]

CANONICAL = "📋 COR-1402 Declare Active Process → no formal task SOP"

_SURFACES = [
    _REPO / "src" / "fx_alfred" / "rules" / "INIT.md",
    _REPO / "src" / "fx_alfred" / "rules" / "COR-1402-SOP-Declare-Active-Process.md",
    _REPO / "src" / "fx_alfred" / "commands" / "plan_cmd.py",
    _REPO / "src" / "fx_alfred" / "commands" / "setup_cmd.py",
    _REPO / "src" / "fx_alfred" / "commands" / "guide_cmd.py",
    _REPO / "CLAUDE.md",
    _REPO / "skills" / "alfred" / "alfred-contract.md",
    _REPO / "skills" / "alfred" / "claude" / "SKILL.md",
    _REPO / "skills" / "alfred" / "agents" / "AGENTS.md",
    _REPO / "skills" / "alfred" / "copilot" / "copilot-instructions.md",
]

_OLD_SHORT_FORM = "📋 COR-1402 → no formal task SOP"


def _old_form_candidates() -> list[Path]:
    """Walk the four search scopes and return candidate files."""
    fx = _REPO / "src" / "fx_alfred"
    files: list[Path] = []
    files.extend(fx.rglob("*.py"))
    files.extend((fx / "rules").glob("*.md"))
    files.extend((_REPO / "skills").rglob("*.md"))
    files.append(_REPO / "CLAUDE.md")
    return sorted(set(files))


def test_canonical_literal_present_in_all_surfaces() -> None:
    """CANONICAL string appears (substring, UTF-8) in every teaching surface."""
    missing = [
        str(path)
        for path in _SURFACES
        if CANONICAL not in path.read_text(encoding="utf-8")
    ]
    assert missing == [], (
        f"CANONICAL literal missing from {len(missing)} surface(s):\n"
        + "\n".join(f"  {p}" for p in missing)
    )


def test_no_old_shortform_anywhere() -> None:
    """The OLD short form (without 'Declare Active Process') must not appear."""
    hits = [
        str(path)
        for path in _old_form_candidates()
        if _OLD_SHORT_FORM in path.read_text(encoding="utf-8")
    ]
    assert hits == [], (
        f"Old short form {_OLD_SHORT_FORM!r} found in {len(hits)} file(s):\n"
        + "\n".join(f"  {p}" for p in hits)
    )
