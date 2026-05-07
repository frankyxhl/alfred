"""User preferences I/O for ~/.alfred/preferences.yaml (FXA-2274).

Framework-agnostic: raises PreferencesError on schema/parse failures.
The command layer (commands/star_cmd.py) converts PreferencesError to
click.ClickException at the CLI boundary.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import yaml


_HEADER_COMMENT = "# Managed by `af star`; safe to edit by hand.\n"


class PreferencesError(ValueError):
    """Raised when ~/.alfred/preferences.yaml is malformed or has wrong shape."""


def preferences_path() -> Path:
    """Path to the user's preferences file (depends on Path.home())."""
    return Path.home() / ".alfred" / "preferences.yaml"


def load_preferences() -> dict[str, Any]:
    """Read preferences.yaml. Returns {} when file is missing.

    Raises PreferencesError on parse failure or wrong top-level shape.
    """
    path = preferences_path()
    if not path.exists():
        return {}
    raw = path.read_text()
    if not raw.strip():
        return {}
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise PreferencesError(f"malformed YAML in {path}: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise PreferencesError(
            f"{path}: top-level must be a mapping, got {type(data).__name__}"
        )
    return data


def _atomic_write(path: Path, content: str) -> None:
    """Write content to path via tempfile + os.replace (no .tmp leftover)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=".preferences.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def _serialise(data: dict[str, Any]) -> str:
    body = yaml.safe_dump(data, sort_keys=True, default_flow_style=False)
    return _HEADER_COMMENT + body


def get_starred_docs() -> list[str]:
    """Return the user's starred document IDs (sorted, deduplicated).

    Returns [] when the file is missing or starred_docs key is absent.
    Raises PreferencesError when the key exists but is not a list.
    """
    data = load_preferences()
    if "starred_docs" not in data:
        return []
    value = data["starred_docs"]
    if value is None:
        return []
    if not isinstance(value, list):
        raise PreferencesError(
            f"{preferences_path()}: 'starred_docs' must be a list, got "
            f"{type(value).__name__}"
        )
    return sorted({str(v) for v in value})


def add_starred_doc(canonical_id: str) -> tuple[bool, list[str]]:
    """Add `canonical_id` to starred_docs. Returns (added, sorted_list).

    `canonical_id` must already be in canonical form (e.g., "COR-1202").
    Idempotent. Preserves any other top-level keys in preferences.yaml.
    """
    data = load_preferences()
    existing_raw = data.get("starred_docs")
    if existing_raw is None:
        existing: list[str] = []
    elif isinstance(existing_raw, list):
        existing = [str(v) for v in existing_raw]
    else:
        raise PreferencesError(
            f"{preferences_path()}: 'starred_docs' must be a list, got "
            f"{type(existing_raw).__name__}"
        )

    if canonical_id in existing:
        return False, sorted(set(existing))
    new_list = sorted(set(existing + [canonical_id]))
    data["starred_docs"] = new_list
    _atomic_write(preferences_path(), _serialise(data))
    return True, new_list


def remove_starred_doc(canonical_id: str) -> tuple[bool, list[str]]:
    """Remove `canonical_id` from starred_docs. Returns (removed, sorted_list).

    Idempotent: returns (False, current_list) when not present.
    """
    data = load_preferences()
    existing_raw = data.get("starred_docs")
    if existing_raw is None:
        return False, []
    if not isinstance(existing_raw, list):
        raise PreferencesError(
            f"{preferences_path()}: 'starred_docs' must be a list, got "
            f"{type(existing_raw).__name__}"
        )
    existing = [str(v) for v in existing_raw]
    if canonical_id not in existing:
        return False, sorted(set(existing))
    new_list = sorted({v for v in existing if v != canonical_id})
    data["starred_docs"] = new_list
    _atomic_write(preferences_path(), _serialise(data))
    return True, new_list
