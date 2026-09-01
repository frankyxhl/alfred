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
import stat
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from fx_alfred.core.fsmode import resolve_write_mode

# Fixed, well-known slot: the registry must be addressable without
# discovery (`af read USR-9000`), and sequential auto-numbering never
# organically reaches the 90xx range (FXA-2330 §What-1).
REGISTRY_FILENAME = "USR-9000-REF-Project-SOP-Registry.md"

# Structured ownership marker (PR #338 R7 P1): af writes this exact HTML
# comment into every registry it renders, and accepts a file at the slot as
# ITS OWN only when the marker (or the pre-marker legacy template line) is
# present — never on prose mentions of FXA-2330 or parseable rows.
REGISTRY_MARKER = "<!-- af:project-sop-registry v1 -->"
_LEGACY_OWNER_LINE = "Auto-maintained by `af` (FXA-2330)"

# | PRJ | Root | Docs | Last Seen |
# Root: POSIX (/…) or Windows drive-letter (C:\… or C:/…). Pipes inside a
# root are stored Markdown-escaped as \| so they cannot split the table
# cell (render escapes, parse unescapes — symmetric, PR #338 R1). The root
# body therefore admits any non-pipe/non-backslash char or any backslash
# escape pair, and stops at the first BARE pipe — the cell boundary.
_ROOT_BODY = r"(?:/|[A-Za-z]:[\\/]|\\\\)(?:[^|\\]|\\.)*"
_ROW_RE = re.compile(
    r"^\|\s*([A-Z]{2,4})\s*\|\s*("
    + _ROOT_BODY
    + r")\s*\|\s*(\d+)\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|$"
)

# Canonical row form since R4: the root cell is backtick-quoted, so the
# cell boundary is explicit and trailing whitespace that BELONGS to the
# path (a legal POSIX dir name ending in a space/tab) round trips exactly
# instead of being rstripped into a phantom duplicate row (PR #338 R4 P2).
# _ROW_RE (bare) stays as the legacy/hand-written row grammar.
_ROW_RE_BT = re.compile(
    r"^\|\s*([A-Z]{2,4})\s*\|\s*`((?:[^`|\\]|\\.)*)`\s*\|\s*(\d+)\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|$"
)

# Symmetric cell encoding (PR #338 R5/R6 P2): escape backslashes FIRST,
# then pipes, then backticks, so any path — `C:\dir\`, `/tmp/a|b`,
# `/tmp/a\|b`, `/tmp/a`b` — survives the Markdown table round trip.
# Unescape scans left-to-right and only maps known escape pairs; any other
# backslash sequence stays literal (legacy hand rows keep working).


def _encode_cell(root: str) -> str:
    return root.replace("\\", "\\\\").replace("|", "\\|").replace("`", "\\`")


def _decode_cell(cell: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(cell):
        ch = cell[i]
        if ch == "\\" and i + 1 < len(cell) and cell[i + 1] in ("\\", "|", "`"):
            out.append(cell[i + 1])
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


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
        m = _ROW_RE_BT.match(line.strip())
        if m:
            # Backticked (canonical) form: exact root, decoded symmetrically.
            prefix, root, count, seen = m.groups()
            entries.append(
                RegistryEntry(
                    prefix=prefix,
                    root=_decode_cell(root),
                    doc_count=int(count),
                    last_seen=seen,
                )
            )
            continue
        m = _ROW_RE.match(line.strip())
        if m:
            # Legacy bare form (hand-written or pre-R4 renders): cell padding
            # is ambiguous against genuine trailing whitespace; bare rows
            # keep the rstrip semantics they always had.
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


def _md_table(header: list[str], rows: list[list[str]]) -> list[str]:
    """Render a column-aligned Markdown table (canonical fmt style).

    Every cell is padded to its column's width so pipe positions are
    identical across all rows — the generated document is fmt-clean as
    written (PR #338 R7 P2).
    """
    widths = [
        max(len(header[i]), *(len(row[i]) for row in rows)) if rows else len(header[i])
        for i in range(len(header))
    ]
    out = ["| " + " | ".join(h.ljust(w) for h, w in zip(header, widths)) + " |"]
    out.append("|" + "|".join("-" * (w + 2) for w in widths) + "|")
    for row in rows:
        out.append("| " + " | ".join(c.ljust(w) for c, w in zip(row, widths)) + " |")
    return out


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
        REGISTRY_MARKER,
        "",
        "Auto-maintained by `af` (FXA-2330): one row per (PRJ prefix, project",
        "root) seen by `af guide/list/read/status`. The whole machine's project",
        "SOP map. Manage with `af register` / `af projects --prune`;",
        "hand-edited table rows survive regeneration. Doc id: USR-9000",
        "",
    ]
    lines += _md_table(
        ["PRJ", "Root", "Docs", "Last Seen"],
        [
            [e.prefix, "`" + _encode_cell(e.root) + "`", str(e.doc_count), e.last_seen]
            for e in _sorted(entries)
        ],
    )
    lines += [
        "",
        "---",
        "",
        "## Change History",
        "",
    ]
    lines += _md_table(
        ["Date", "Change", "By"],
        [[today, "Rows upserted in place above (auto)", "af"]],
    )
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

    Conflict cases (PR #338 R1/R2/R5 P1): (a) any other ``USR-9000-*.md``
    anywhere in the recursive USR scan scope (nested subdirectories
    included, ``logs/`` and rules+logs paths excluded — mirroring
    ``scan_documents``) — writing ours would create a duplicate prefix+ACID
    that fails layer validation; (b) the registry path itself holding
    anything that is not OUR registry. Ownership is the structured template
    marker (:data:`REGISTRY_MARKER`), with the pre-marker legacy template
    line as the upgrade path — table-shaped rows or prose mentions of
    FXA-2330 are NOT proof: a pre-existing custom doc with a parseable row
    would otherwise be silently replaced and its prose destroyed. Our own
    previously-rendered registry never conflicts (PR #338 R5/R7 P1).
    """
    if path.is_symlink():
        # A symlink occupant — dangling or not — is never replaced: a
        # dangling link defeats ``exists()`` and ``os.replace`` would destroy
        # the link itself (PR #338 R6 P2).
        return path
    if path.exists():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return path  # unreadable occupant — never overwrite blind
        if REGISTRY_MARKER in text or any(
            line.startswith(_LEGACY_OWNER_LINE) for line in text.splitlines()
        ):
            return None  # written by af — the marker survives every rewrite
        return path  # foreign — table-bearing or not, never destroy it
    try:
        for other in sorted(path.parent.rglob("USR-9000-*.md")):
            if other == path:
                continue
            rel = other.relative_to(path.parent)
            # Same exclusion predicate as scanner._scan_path_dir: a top-level
            # logs/ dir, and any rules/logs combination, are invisible to the
            # USR scan — an occupant there can never collide (PR #338 R4 P2).
            if rel.parts and rel.parts[0] == "logs":
                continue
            if "rules" in rel.parts and "logs" in rel.parts:
                continue
            return other
    except OSError:
        return path  # cannot even inspect the slot — refuse to write
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
    # Resolve the mode BEFORE the replace: an existing registry keeps its
    # permissions (no silent 0644→0600 reset from mkstemp), a fresh one gets
    # the umask-derived mode a plain open(path, "w") would produce (PR #338
    # R2 P2; shared core.fsmode behavior, same as _helpers.atomic_write).
    mode = resolve_write_mode(path)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".md.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.chmod(tmp_name, mode)
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

    Only a DEFINITIVE non-directory state is pruned (ENOENT, ENOTDIR, or the
    path now existing as a non-directory). Any other stat error —
    unavailable network mount, parent without search permission — is
    inconclusive, and the entry is KEPT: pruning on a transient condition
    would silently drop a live project from the catalog (PR #338 R1/R2 P2).
    """
    kept: list[RegistryEntry] = []
    removed: list[RegistryEntry] = []
    for e in entries:
        try:
            st = os.stat(e.root)
            if stat.S_ISDIR(st.st_mode):
                kept.append(e)
            else:
                removed.append(e)  # path exists but is no longer a directory
        except FileNotFoundError:
            removed.append(e)
        except NotADirectoryError:
            removed.append(e)  # a parent component is a file — cannot be a root
        except OSError:
            kept.append(e)  # inconclusive — never prune on transient errors
    return kept, removed
