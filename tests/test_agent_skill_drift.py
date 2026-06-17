"""Drift guards for the cross-platform agent-skill bundle (FXA-2305).

`skills/alfred/` ships one canonical contract (`alfred-contract.md`) wrapped
by three native carriers — Claude Code `SKILL.md`, the shared `AGENTS.md`
(Codex / droid / opencode), and GitHub Copilot `copilot-instructions.md`.
The carriers are static files, so these tests pin them to the single source
of truth: each carrier's sentinel-delimited region must equal the canonical
contract, the Claude frontmatter must carry a usable trigger description, and
every `af` command named in the contract must still exist in the CLI.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from fx_alfred.core.normalize import strip_trailing_whitespace

pytestmark = pytest.mark.docs

_REPO = Path(__file__).parent.parent
_SKILL_DIR = _REPO / "skills" / "alfred"
_CONTRACT = _SKILL_DIR / "alfred-contract.md"

_START = "<!-- alfred-contract:start -->"
_END = "<!-- alfred-contract:end -->"

# (carrier path relative to skills/alfred, human label)
_CARRIERS = [
    ("claude/SKILL.md", "Claude Code SKILL.md"),
    ("agents/AGENTS.md", "shared AGENTS.md"),
    ("copilot/copilot-instructions.md", "Copilot copilot-instructions.md"),
]


def _normalize(text: str) -> str:
    """Canonical comparison form: rstrip each line, then strip the block.

    Matches the normalization specified in FXA-2305 §Scope so carriers
    cannot re-indent the shared body without failing the guard.
    """
    return "\n".join(strip_trailing_whitespace(text.splitlines())).strip()


def _extract_region(text: str, label: str) -> str:
    """Return the text strictly between the start and end sentinels."""
    assert _START in text, f"{label}: missing start sentinel {_START!r}"
    assert _END in text, f"{label}: missing end sentinel {_END!r}"
    assert text.index(_START) < text.index(_END), (
        f"{label}: end sentinel precedes start sentinel"
    )
    after_start = text.split(_START, 1)[1]
    region = after_start.split(_END, 1)[0]
    return region


def _lazy_subcommands() -> list[str]:
    cli_src = (_REPO / "src" / "fx_alfred" / "cli.py").read_text(encoding="utf-8")
    return re.findall(r'"([a-z]+)":\s*"fx_alfred\.commands\.', cli_src)


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Parse a leading YAML-ish `---` frontmatter block into a flat dict.

    Only simple `key: value` scalars are needed here, so we avoid a YAML
    dependency the rest of the suite does not use.
    """
    assert text.startswith("---"), "SKILL.md must open with a `---` frontmatter block"
    # Frontmatter values use an em-dash (U+2014), never a literal "---", so
    # splitting on the first two "---" delimiters cleanly isolates the block.
    _, fm, _body = text.split("---", 2)
    out: dict[str, str] = {}
    for line in fm.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            out[key.strip()] = value.strip()
    return out


def test_skill_dir_exists() -> None:
    assert _SKILL_DIR.is_dir(), f"missing skill bundle directory: {_SKILL_DIR}"
    assert _CONTRACT.is_file(), f"missing canonical contract: {_CONTRACT}"


@pytest.mark.parametrize("rel,label", _CARRIERS)
def test_carrier_matches_canonical_contract(rel: str, label: str) -> None:
    """Each carrier's sentinel region equals the canonical contract."""
    contract = _normalize(_CONTRACT.read_text(encoding="utf-8"))
    carrier_path = _SKILL_DIR / rel
    assert carrier_path.is_file(), f"missing carrier: {carrier_path}"
    region = _normalize(
        _extract_region(carrier_path.read_text(encoding="utf-8"), label)
    )
    assert region == contract, (
        f"{label} sentinel region has drifted from alfred-contract.md — "
        f"regenerate it from the canonical source."
    )


def test_claude_frontmatter_has_trigger_description() -> None:
    """Claude SKILL.md needs name=alfred and a trigger-phrase description."""
    skill = (_SKILL_DIR / "claude" / "SKILL.md").read_text(encoding="utf-8")
    fm = _parse_frontmatter(skill)
    assert fm.get("name") == "alfred", f"expected name: alfred, got {fm.get('name')!r}"
    description = fm.get("description", "")
    assert len(description) >= 40, (
        f"description too short ({len(description)} chars) — Claude's on-demand "
        f"match needs a substantive description"
    )
    # Accepted trigger phrases: "use [this] [skill] at/when/before/for/to …"
    # or "at the start of …" — anchoring the skill to a concrete situation.
    trigger = re.compile(
        r"use (this )?(skill )?(at|when|before|for|to)\b|at the start of",
        re.IGNORECASE,
    )
    assert trigger.search(description), (
        f"description lacks a use-trigger phrase: {description!r}"
    )


def test_contract_only_references_real_commands() -> None:
    """Every `af <cmd>` named in the contract is a registered CLI command."""
    contract = _CONTRACT.read_text(encoding="utf-8")
    assert "1.19" in contract, "contract missing the af >= 1.19 version floor (D8)"
    referenced = set(re.findall(r"\baf ([a-z]+)\b", contract))
    assert referenced, "no `af <cmd>` references found in the contract"
    known = set(_lazy_subcommands())
    assert known, (
        "no CLI subcommands parsed from cli.py — registration pattern changed?"
    )
    unknown = sorted(referenced - known)
    assert unknown == [], f"contract references unknown af commands: {unknown}"
