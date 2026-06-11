"""Docs drift guards for the project CLAUDE.md agent runbook (CHG-2297).

CLAUDE.md is the per-session instruction surface for agents working in
this repo. These tests pin the mechanically-checkable claims so the
runbook cannot silently diverge from the code again (the 2026-06-10
review found 6 undocumented commands, 19 undocumented modules, a stale
version, and broken smoke-command paths).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.docs

_REPO = Path(__file__).parent.parent
_CLAUDE_MD = (_REPO / "CLAUDE.md").read_text(encoding="utf-8")


def _lazy_subcommands() -> list[str]:
    cli_src = (_REPO / "src" / "fx_alfred" / "cli.py").read_text(encoding="utf-8")
    return re.findall(r'"([a-z]+)":\s*"fx_alfred\.commands\.', cli_src)


def test_every_cli_command_is_documented() -> None:
    """Every command registered in cli.py appears as `af <name>` in CLAUDE.md."""
    commands = _lazy_subcommands()
    assert commands, "no commands parsed from cli.py — parser broken?"
    missing = [c for c in commands if f"af {c}" not in _CLAUDE_MD]
    assert missing == [], f"CLI commands missing from CLAUDE.md: {missing}"


@pytest.mark.parametrize("package", ["commands", "core"])
def test_every_module_is_documented(package: str) -> None:
    """Every commands/*.py and core/*.py module appears in CLAUDE.md."""
    pkg_dir = _REPO / "src" / "fx_alfred" / package
    modules = sorted(
        p.name for p in pkg_dir.glob("*.py") if p.stem not in ("__init__",)
    )
    assert modules, f"no modules found under {package}/ — path broken?"
    missing = [m for m in modules if m not in _CLAUDE_MD]
    assert missing == [], f"{package}/ modules missing from CLAUDE.md: {missing}"


def test_no_dead_fx_alfred_root_path() -> None:
    """The nonexistent `Projects/alfred/fx_alfred` path must not reappear
    (it broke the documented session-start smoke commands)."""
    assert "Projects/alfred/fx_alfred" not in _CLAUDE_MD


def test_no_hardcoded_package_version() -> None:
    """CLAUDE.md must not pin `fx-alfred vX.Y.Z` — that drift class is
    removed in favor of `af --version` / pyproject.toml pointers."""
    assert not re.search(r"fx-alfred v\d+\.\d+", _CLAUDE_MD)
