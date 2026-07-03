"""File-mode resolution for atomic writers (FXA-274 / DeepSeek FIX dedup).

Shared by commands/_helpers.py::atomic_write and core/preferences.py's
internal writer, both of which need to preserve or infer a Unix file
mode before replacing a target file via tempfile + os.replace.
"""

import os
import stat
from pathlib import Path


def resolve_write_mode(path: Path) -> int:
    """Resolve the mode to apply to a file about to be atomically replaced.

    If `path` already exists, reuse its current mode so an atomic
    replace doesn't silently change permissions on an existing file.

    If `path` does not exist yet, infer the mode a plain ``open(path, "w")``
    would have produced: 0o666 masked by the process umask. There is no
    direct API to read the umask without changing it, so this does the
    standard round-trip (set to 0, read the old value back, restore it
    immediately). The round-trip is process-wide; callers are synchronous
    CLI paths, so no other thread observes the momentarily-cleared umask.
    """
    if path.exists():
        return stat.S_IMODE(path.stat().st_mode)
    current_umask = os.umask(0)
    os.umask(current_umask)
    return 0o666 & ~current_umask
