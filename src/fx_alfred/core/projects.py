"""FXA-2314: projects.json loader and subproject resolver.

Provides two public functions:

- ``load_projects()`` — reads ``~/.alfred/projects.json`` once (no module-level
  cache) and returns a validated ``{absolute-path-string: leaf-name}`` dict.
- ``resolve_subproject(root, mapping)`` — resolves symlinks on both sides and
  returns the NAME for the given root, or None if not registered.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def load_projects(projects_json_path: Path | None = None) -> dict[str, str]:
    """Load and validate ``~/.alfred/projects.json``.

    Returns a ``{path_string: name}`` mapping.  On every error condition the
    function degrades gracefully:

    - Missing file or missing ``~/.alfred/`` → ``{}`` (silent).
    - Malformed JSON or wrong top-level shape → ``{}`` + one stderr warning.
    - Relative key → entry skipped + one stderr warning per entry.
    - Invalid value (``.``, ``..``, contains a path separator, or empty) →
      entry skipped + one stderr warning per entry.

    No module-level cache: the file is re-read on every call so callers that
    invoke the function multiple times within a long-lived process always see
    the current state (and tests never see stale data).
    """
    if projects_json_path is None:
        projects_json_path = Path.home() / ".alfred" / "projects.json"

    if not projects_json_path.exists():
        return {}

    try:
        data = json.loads(projects_json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(
            f"Warning: projects.json is malformed and will be ignored ({exc})",
            file=sys.stderr,
        )
        return {}

    if not isinstance(data, dict):
        return {}

    projects = data.get("projects")
    if not isinstance(projects, dict):
        return {}

    result: dict[str, str] = {}
    for key, value in projects.items():
        # Key must be an absolute path string.
        if not isinstance(key, str) or not Path(key).is_absolute():
            print(
                f"Warning: projects.json key {key!r} is not an absolute path; skipping.",
                file=sys.stderr,
            )
            continue

        # Value must be a non-empty single-component leaf name.
        if (
            not isinstance(value, str)
            or not value
            or value in (".", "..")
            or "/" in value
            or "\\" in value
        ):
            print(
                f"Warning: projects.json value {value!r} for key {key!r} is not a valid "
                "subproject name (must be a non-empty leaf name, not '.' or '..'); skipping.",
                file=sys.stderr,
            )
            continue

        result[key] = value

    return result


def resolve_subproject(root: Path, mapping: dict[str, str] | None = None) -> str | None:
    """Return the subproject NAME for *root*, or ``None`` if not registered.

    Both *root* and every key in *mapping* are normalised with
    ``Path.resolve()`` before comparison so that symlinked paths, trailing
    slashes, and ``..`` segments all reduce to the same canonical form.

    When *mapping* is ``None``, :func:`load_projects` is called automatically.
    Callers that have already loaded the mapping should pass it explicitly to
    avoid a redundant file read.
    """
    if mapping is None:
        mapping = load_projects()

    resolved_root = str(root.resolve())
    for key, name in mapping.items():
        if str(Path(key).resolve()) == resolved_root:
            return name
    return None
