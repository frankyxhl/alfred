"""Regression tests for CHG-2286: explicit UTF-8 at every Alfred document I/O site.

A6.1 (behavioural): with io.text_encoding patched to return "ascii" for None,
bare Path.read_text() must raise UnicodeDecodeError on a UTF-8 file containing
non-ASCII bytes; the same call with encoding="utf-8" must decode cleanly.

A6.2 (mechanical): no bare .read_text() / .write_text(content) / os.fdopen(fd, "w")
/ open(spec_path, "r") remains in src/fx_alfred/ production code.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

SRC = Path(__file__).resolve().parent.parent / "src" / "fx_alfred"


@pytest.fixture
def ascii_locale(monkeypatch):
    """Force io.text_encoding(None) to return 'ascii' (simulates Windows GBK / CP1252 path).

    Per CHG-2286 A6.1: locale.getpreferredencoding is bypassed by Path.read_text's
    C-level _PyOS_GetLocaleEncoding lookup, so we must patch io.text_encoding instead.
    """
    original = io.text_encoding

    def fake_text_encoding(encoding, stacklevel=2):
        return "ascii" if encoding is None else encoding

    monkeypatch.setattr(io, "text_encoding", fake_text_encoding)
    yield
    monkeypatch.setattr(io, "text_encoding", original)


def test_bare_read_text_fails_under_ascii_locale(ascii_locale, tmp_path):
    """A6.1 RED half: bare Path.read_text() crashes on UTF-8 bytes under simulated ASCII locale."""
    target = tmp_path / "non_ascii.md"
    target.write_bytes("中文测试".encode("utf-8"))
    with pytest.raises(UnicodeDecodeError):
        target.read_text()


def test_explicit_utf8_read_text_succeeds_under_ascii_locale(ascii_locale, tmp_path):
    """A6.1 GREEN half: encoding-pinned read_text decodes cleanly under simulated ASCII locale."""
    target = tmp_path / "non_ascii.md"
    target.write_bytes("中文测试".encode("utf-8"))
    assert target.read_text(encoding="utf-8") == "中文测试"


def _grep(pattern: str) -> list[str]:
    """Pure-Python scan of src/fx_alfred/ *.py for `pattern` — portable across Windows.

    Uses Path.rglob + re instead of subprocess grep so the suite runs on Windows
    too (stock Windows has no grep), which matters because this very PR fixes a
    Windows-locale bug (codex bot R1 catch on PR #172).
    """
    regex = re.compile(pattern)
    matches: list[str] = []
    for py_file in SRC.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                matches.append(f"{py_file}:{lineno}:{line}")
    return matches


def test_no_bare_read_text_in_production():
    """A6.2: no bare .read_text() call sites (Protocol def + docstring excluded)."""
    matches = _grep(r"\.read_text\(\s*\)")
    # Exclude Protocol method def at core/document.py:23 and docstring at :87
    real_matches = [m for m in matches if not re.search(r"(def read_text|\"\"\")", m)]
    assert real_matches == [], (
        f"Found {len(real_matches)} bare .read_text() call sites:\n"
        + "\n".join(real_matches)
    )


def test_no_bare_write_text_in_production():
    """A6.2: every .write_text(...) call passes encoding=...."""
    matches = _grep(r"\.write_text\(")
    unpinned = [m for m in matches if "encoding=" not in m]
    assert unpinned == [], (
        f"Found {len(unpinned)} bare .write_text() call sites:\n" + "\n".join(unpinned)
    )


def test_no_bare_os_fdopen_write_in_production():
    """A6.2: every os.fdopen(fd, 'w') passes encoding=...."""
    matches = _grep(r"os\.fdopen")
    unpinned = [m for m in matches if "encoding=" not in m]
    assert unpinned == [], (
        f"Found {len(unpinned)} bare os.fdopen() call sites:\n" + "\n".join(unpinned)
    )


def test_no_bare_open_spec_in_production():
    """A6.2: every open(spec_path, 'r') passes encoding=...."""
    matches = _grep(r"open\(spec")
    unpinned = [m for m in matches if "encoding=" not in m]
    assert unpinned == [], (
        f"Found {len(unpinned)} bare open(spec_path, 'r') call sites:\n"
        + "\n".join(unpinned)
    )
