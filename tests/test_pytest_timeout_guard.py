"""The repo-level pytest hang guard must actually fire (jury v2 review fix).

Proves the pyproject ``timeout = 60`` / ``timeout_method = "thread"``
configuration is not just declared but effective: a blocking test must
FAIL after the timeout instead of freezing the suite (the 2026-09-01
3.5h hang class). The probe runs a nested pytest with a small
``--timeout`` override so the proof costs ~2s instead of 60s.
"""

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


pytestmark = [pytest.mark.integration, pytest.mark.slow]

_PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"

_HANGING_PROBE = textwrap.dedent(
    """
    import time


    def test_blocks_forever():
        time.sleep(30)
    """
)


def test_hang_guard_configured_in_pyproject():
    """The suite-level guard is pinned in pyproject (60s, thread method)."""
    text = _PYPROJECT.read_text(encoding="utf-8")
    assert "timeout = 60" in text
    assert 'timeout_method = "thread"' in text


def test_hang_guard_fires_on_blocking_test(tmp_path):
    """A blocking test FAILS the nested run after the timeout, exit 1."""
    (tmp_path / "test_hanging_probe.py").write_text(_HANGING_PROBE, encoding="utf-8")

    env = dict(os.environ)
    env.pop("PYTEST_ADDOPTS", None)  # hermetic: only our CLI flags apply

    result = subprocess.run(
        [
            sys.executable,  # absolute interpreter path, never a PATH lookup
            "-m",
            "pytest",
            "--timeout=2",
            "--timeout-method=thread",  # the repo-configured method
            "-p",
            "no:cacheprovider",
            "test_hanging_probe.py",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,  # hard ceiling: a broken guard fails HERE, not by hanging
    )

    assert result.returncode == 1, (
        "blocking test must FAIL the run (exit 1), got "
        f"{result.returncode}:\n{result.stdout[-2000:]}"
    )
    # Thread method: the timer thread dumps stacks under the Timeout banner
    # and terminates the process via os._exit(1) — no per-test failure line.
    assert "test_blocks_forever" in result.stdout
    assert "+" * 20 + " Timeout " in result.stdout
