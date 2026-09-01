"""FXA-2330: user-level Project SOP Registry.

A machine-wide catalog of every project whose PRJ layer `af` has seen, kept
as one ordinary USR-layer document (``~/.alfred/USR-9000-REF-Project-SOP-
Registry.md``) so the whole map is readable via a normal ``af read``.

Row key is ``(prefix, resolved root)``. The document is regenerated from a
fixed template on every write, but ``parse_registry`` accepts any
table-shaped row, so rows for projects that are not part of the current scan
(hand-added or simply visited from elsewhere) survive regeneration; only
``--prune`` (dead roots) or an upsert on the same key removes them.

Pure core logic: no Click (CHG-2295 contract); the commands layer owns the
non-blocking warning wrapper and the CLI surface.
"""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

# Fixed, well-known slot: the registry must be addressable without
# discovery (`af read USR-9000`), and sequential auto-numbering never
# organically reaches the 90xx range (FXA-2330 §What-1).
REGISTRY_FILENAME = "USR-9000-REF-Project-SOP-Registry.md"

# | PRJ | Root | Docs | Last Seen |
# Root: POSIX (/…) or Windows drive-letter (C:\… or C:/…). Pipes inside a
# root are stored Markdown-escaped as \| so they cannot split the table
# cell (render escapes, parse unescapes — symmetric, PR #338 R1). The root
# body therefore admits any non-pipe/non-backslash char or any backslash
# escape pair, and stops at the first BARE pipe — the cell boundary.
_ROOT_BODY = r"(?:/|[A-Za-z]:[\\/])(?:[^|\\]|\\.)*"
_ROW_RE = re.compile(
    r"^\|\s*([A-Z]{2,4})\s*\|\s*("
    + _ROOT_BODY
    + r")\s*\|\s*(\d+)\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|$"
)


class RegistrySlotConflictError(Exception):
    """USR-9000 is occupied by a pre-existing, non-registry document.

    Raised by ``save_registry`` before any write: a foreign doc with the
    registry filename would be destroyed, and a different ``USR-9000-*``
    filename would create a duplicate prefix+ACID that fails layer
    validation on every later scan (PR #338 R1 P1).
    """


@dataclass(frozen=True)
class RegistryEntry:
    """One registry row: a (prefix, root) pair with corpus size and recency."""

    prefix: str
    root: str
    doc_count: int
    last_seen: str


def registry_path(usr_home: Path | None = None) -> Path:
    """Return the registry document path (default: ``~/.alfred/``)."""
    base = usr_home if usr_home is not None else Path.home() / ".alfred"
    return base / REGISTRY_FILENAME


def today_str() -> str:
    """ISO date for last-seen stamps (indirection point for tests/clocks)."""
    return date.today().isoformat()


def parse_registry(text: str) -> list[RegistryEntry]:
    """Extract table-shaped rows from the registry document.

    Best-effort: prose, headers, and separator lines are ignored; nothing
    raises on arbitrary input (a hand-mangled file degrades to fewer rows,
    never to a crash — the catalog self-heals on the next write).
    """
    entries: list[RegistryEntry] = []
    for line in text.splitlines():
        m = _ROW_RE.match(line.strip())
        if m:
            prefix, root, count, seen = m.groups()
            entries.append(
                RegistryEntry(
                    prefix=prefix,
                    root=root.replace("\\|", "|").rstrip(),
                    doc_count=int(count),
                    last_seen=seen,
                )
            )
    return entries


def render_registry(entries: list[RegistryEntry], *, today: str) -> str:
    """Render the full registry document (header + table)."""
    lines = [
        "# REF-9000: Project SOP Registry",
        "",
        "**Applies to:** USR layer (machine-wide)",
        f"**Last updated:** {today}",
        f"**Last reviewed:** {today}",
        "**Status:** Active",
        "",
        "---",
        "",
        "Auto-maintained by `af` (FXA-2330): one row per (PRJ prefix, project",
        "root) seen by `af guide/list/read/status`. The whole machine's project",
        "SOP map. Manage with `af register` / `af projects --prune`;",
        "hand-edited table rows survive regeneration. Doc id: USR-9000",
        "",
        "| PRJ | Root | Docs | Last Seen |",
        "|-----|------|------|-----------|",
    ]
    for e in _sorted(entries):
        root_cell = e.root.replace("|", "\\|")
        lines.append(f"| {e.prefix} | {root_cell} | {e.doc_count} | {e.last_seen} |")
    lines += [
        "",
        "---",
        "",
        "## Change History",
        "",
        "| Date | Change | By |",
        "|------|--------|----|",
        f"| {today} | Rows upserted in place above (auto) | af |",
    ]
    return "\n".join(lines) + "\n"


def _sorted(entries: list[RegistryEntry]) -> list[RegistryEntry]:
    """Canonical row order: (root, prefix) — stable diffs across writes."""
    return sorted(entries, key=lambda e: (e.root, e.prefix))


def load_registry(path: Path) -> list[RegistryEntry]:
    """Load entries from the registry file.

    A genuinely missing file is the normal empty state → ``[]``. Any other
    read failure (permissions, I/O error) PROPAGATES: silently converting an
    unreadable catalog to empty would let the next save wipe every other
    project's rows (PR #338 R1 P2).
    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    return parse_registry(text)


def _slot_conflict(path: Path) -> Path | None:
    """Return the occupying file if USR-9000 is taken by a non-registry doc.

    Conflict cases (PR #338 R1 P1): (a) any other ``USR-9000-*.md`` beside
    the registry path — writing ours would create a duplicate prefix+ACID
    that fails layer validation; (b) the registry path itself holding a
    foreign document (no table rows, no FXA-2330 marker) — writing would
    destroy it. Our own previously-rendered registry never conflicts.
    """
    if path.exists():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return path  # unreadable occupant — never overwrite blind
        if parse_registry(text) or "FXA-2330" in text:
            return None
        return path
    for other in sorted(path.parent.glob("USR-9000-*.md")):
        if other != path:
            return other
    return None


def save_registry(path: Path, entries: list[RegistryEntry], *, today: str) -> None:
    """Atomically write the registry document (tempfile + os.replace)."""
    conflict = _slot_conflict(path)
    if conflict is not None:
        raise RegistrySlotConflictError(
            f"{conflict.name} already occupies the USR-9000 slot; "
            "move or renumber it before af can maintain the project registry"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    content = render_registry(entries, today=today)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".md.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_name, str(path))
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def upsert(
    entries: list[RegistryEntry],
    *,
    root: Path,
    prefix_counts: dict[str, int],
    today: str,
) -> tuple[list[RegistryEntry], bool]:
    """Upsert one project (all its prefixes) into the registry.

    *root* is canonicalized with ``Path.resolve()`` (FXA-2314-style
    normalization) so symlinked visits don't fork rows. Prefixes of the same
    root that no longer appear in *prefix_counts* drop out (their docs are
    gone); rows belonging to other projects pass through untouched.

    Returns ``(new_entries, changed)`` — ``changed`` is False when the table
    content is identical, letting callers skip the write entirely.
    """
    resolved = str(Path(root).resolve())
    incoming = {
        prefix: count for prefix, count in sorted(prefix_counts.items()) if count > 0
    }

    kept: list[RegistryEntry] = []
    for e in entries:
        if e.root == resolved:
            continue  # this project's rows are regenerated below
        kept.append(e)

    new_rows = [
        RegistryEntry(prefix=prefix, root=resolved, doc_count=count, last_seen=today)
        for prefix, count in incoming.items()
    ]
    new_entries = _sorted(kept + new_rows)
    changed = new_entries != _sorted(entries)
    return new_entries, changed


def prune_missing_roots(
    entries: list[RegistryEntry],
) -> tuple[list[RegistryEntry], list[RegistryEntry]]:
    """Split entries into (kept, removed) by root-directory existence.

    Only a DEFINITIVE missing path is pruned (ENOENT, or a parent component
    that is a file). Any other stat error — unavailable network mount,
    parent without search permission — is inconclusive, and the entry is
    KEPT: pruning on a transient condition would silently drop a live
    project from the catalog (PR #338 R1 P2).
    """
    kept: list[RegistryEntry] = []
    removed: list[RegistryEntry] = []
    for e in entries:
        try:
            os.stat(e.root)
            kept.append(e)
        except FileNotFoundError:
            removed.append(e)
        except NotADirectoryError:
            removed.append(e)  # a parent component is a file — cannot be a root
        except OSError:
            kept.append(e)  # inconclusive — never prune on transient errors
    return kept, removed
